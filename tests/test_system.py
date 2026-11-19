import json
import pytest
from fastapi.testclient import TestClient
from app.core import AI, Store, Settings, Pipeline, ABSTAIN, parse_document
from app.main import create_app

@pytest.fixture
def client(tmp_path):
    with TestClient(create_app(Settings(data_dir=str(tmp_path)), {'alpha':'a','beta':'b'})) as c:
        yield c

A={'X-API-Key':'alpha'}; B={'X-API-Key':'beta'}
def ingest(c,name='policy.txt',content=b'P1 incidents must be acknowledged within 15 minutes.',headers=A):
    return c.post('/api/documents',headers=headers,files={'file':(name,content)})
def query(c,q='What is the P1 incident response?',headers=A):
    return c.post('/api/query',headers=headers,json={'question':q})

def test_auth_required(client):
    assert client.get('/api/documents').status_code==401
    assert client.post('/api/query',json={'question':'hello'}).status_code==401

def test_end_to_end_citations_and_trace(client):
    assert ingest(client).status_code==201
    r=query(client); assert r.status_code==200
    d=r.json(); assert '15 minutes' in d['answer']; assert d['verified']
    assert d['verification_type']=='verbatim_only'
    assert d['citations'][0]['source']=='policy.txt'
    assert [s['node'] for s in d['trace']['spans']]==['retrieve','answer','review']
    trace=client.get('/api/traces/'+d['trace']['request_id'],headers=A).json()
    assert trace['output_tokens']==0
    assert trace['estimated_generation_cost_usd'] is None
    assert 'answer' not in trace and 'question' not in trace

def test_workspace_isolation(client):
    ingest(client)
    assert client.get('/api/documents',headers=B).json()==[]
    assert query(client,headers=B).json()['answer']==ABSTAIN
    d=query(client).json()
    assert client.get('/api/traces/'+d['trace']['request_id'],headers=B).status_code==404
    doc=client.get('/api/documents',headers=A).json()[0]
    client.delete('/api/documents/'+doc['document_id'],headers=B)
    assert len(client.get('/api/documents',headers=A).json())==1

def test_reingestion_idempotency_and_delete(client):
    first=ingest(client).json(); assert ingest(client).json()==first
    assert client.get('/api/documents',headers=A).json()[0]['chunks']==1
    assert client.delete('/api/documents/'+first['document_id'],headers=A).status_code==204
    assert query(client).json()['answer']==ABSTAIN

def test_unknown_question_abstains(client):
    ingest(client)
    assert query(client,'Who won the Wimbledon championship?').json()['answer']==ABSTAIN

def test_structured_csv(client):
    r=ingest(client,'services.csv',b'service,owner\npayments,Payments Platform\n')
    assert r.status_code==201
    d=query(client,'Who owns payments?').json()
    assert 'Payments Platform' in d['answer']
    assert 'row 2' in d['citations'][0]['location']

def test_invalid_and_oversized_inputs(client):
    assert ingest(client,'bad.exe',b'abc').status_code==400
    assert ingest(client,'empty.txt',b' ').status_code==400
    assert ingest(client,'huge.txt',b'x'*2_000_001).status_code==413
    assert query(client,' ').status_code==422
    assert query(client,'x'*2001).status_code==422

def test_rate_limit(client):
    for _ in range(60): assert client.get('/api/documents',headers=A).status_code==200
    assert client.get('/api/documents',headers=A).status_code==429
    assert client.get('/api/documents',headers=B).status_code==200

def test_persistence_and_chunk_overlap(tmp_path):
    s=Settings(data_dir=str(tmp_path)); store=Store(s,AI(s))
    store.ingest('a','x.txt',b'Important recovery instruction. '*80); store.close()
    store=Store(s,AI(s))
    assert store.documents('a')[0]['chunks']>1
    assert store.search('a','recovery instruction')
    store.close()

def test_pdf_parser():
    from io import BytesIO
    from reportlab.pdfgen import canvas
    b=BytesIO(); c=canvas.Canvas(b); c.drawString(40,700,'P1 response is 15 minutes.'); c.save()
    chunks=parse_document('policy.pdf',b.getvalue())
    assert '15 minutes' in chunks[0][0]; assert 'page 1' in chunks[0][1]

def test_invalid_citation_retries_then_abstains(client):
    ingest(client)
    ai=client.app.state.store.ai
    ai.s.mode='gemini'  # Stub external model calls; retrieval uses precomputed demo vectors.
    ai.embed=lambda texts,query=False: ai.vectorizer.transform(texts).toarray().tolist()
    ai.generate=lambda *args: ({'answer':'Invented answer','citations':['S99']}, {'input_tokens':5,'output_tokens':5,'thinking_tokens':0,'generation_ms':2})
    d=query(client).json()
    assert d['answer']==ABSTAIN
    assert d['trace']['attempts']==2
    assert d['trace']['spans'][-1]['node']=='abstain'

def test_reviewer_feedback_repairs_answer(client):
    ingest(client); ai=client.app.state.store.ai; ai.s.mode='gemini'
    ai.embed=lambda texts,query=False: ai.vectorizer.transform(texts).toarray().tolist()
    responses=iter([{'answer':'60 minutes [S1]','citations':['S1']}, {'supported':False,'feedback':'Use 15 minutes.'},
                    {'answer':'15 minutes [S1]','citations':['S1']}, {'supported':True,'feedback':'Supported.'}])
    ai.generate=lambda *args: (next(responses),{'input_tokens':10,'output_tokens':5,'thinking_tokens':2,'generation_ms':10})
    d=query(client).json(); assert d['verified']; assert d['trace']['attempts']==2
    assert d['trace']['input_tokens']==40; assert d['trace']['thinking_tokens']==8

def test_provider_error_is_sanitized(client):
    ingest(client)
    def fail(*args,**kwargs): raise RuntimeError('secret-key-must-never-leak')
    client.app.state.store.ai.embed=fail
    r=query(client); assert r.status_code==502
    assert 'secret-key' not in r.text

def test_production_configuration_guard(monkeypatch,tmp_path):
    monkeypatch.setenv('ENVIRONMENT','production')
    with pytest.raises(ValueError): create_app(Settings(data_dir=str(tmp_path)),{'local-demo-key':'demo'})
    with pytest.raises(ValueError): create_app(Settings(data_dir=str(tmp_path)),{'a'*32:'demo'})

def test_gemini_sdk_adapter_shapes(monkeypatch):
    from types import SimpleNamespace
    from google import genai
    calls=[]
    class Models:
        def embed_content(self,**kwargs):
            calls.append(kwargs)
            return SimpleNamespace(embeddings=[SimpleNamespace(values=[.1]*768) for _ in kwargs['contents']])
        def generate_content(self,**kwargs):
            calls.append(kwargs)
            return SimpleNamespace(text='{"answer":"supported","citations":["S1"]}',usage_metadata=SimpleNamespace(prompt_token_count=20,candidates_token_count=5,thoughts_token_count=2))
    monkeypatch.setenv('GEMINI_API_KEY','test-only-key')
    monkeypatch.setattr(genai,'Client',lambda **kwargs: SimpleNamespace(models=Models()))
    ai=AI(Settings(mode='gemini'))
    assert len(ai.embed(['a','b']))==2
    ai.embed(['question'],query=True)
    assert calls[0]['config'].task_type=='RETRIEVAL_DOCUMENT'
    assert calls[1]['config'].task_type=='RETRIEVAL_QUERY'
    result,usage=ai.generate('Instructions',{'question':'test'})
    assert result['citations']==['S1']; assert usage['input_tokens']==20
    assert calls[2]['config'].response_mime_type=='application/json'

def test_ui_and_openapi_served(client):
    r=client.get('/')
    assert r.status_code==200 and 'FieldKit' in r.text and 'textContent' in r.text
    assert client.get('/openapi.json').json()['info']['version']=='1.0.0'
