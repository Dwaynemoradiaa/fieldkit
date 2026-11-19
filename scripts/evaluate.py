"""Offline smoke benchmark, not a production quality or semantic RAG benchmark."""
import contextlib, io, json, statistics, tempfile
from pathlib import Path
from fastapi.testclient import TestClient
from app.main import create_app
from app.core import Settings

ROOT=Path(__file__).resolve().parents[1]
CASES=[
 ('What is the response time for a P1 incident?', 'incident_runbook.md','15 minutes'),
 ('How often does the incident commander post a status update?', 'incident_runbook.md','30 minutes'),
 ('What is the domestic hotel expense limit?', 'expense_policy.txt','4,500'),
 ('When must reimbursement claims be submitted?', 'expense_policy.txt','30 days'),
 ('Who owns the payments service?', 'service_catalog.csv','Payments Platform'),
 ('What is the recovery time objective for analytics?', 'service_catalog.csv','4 hours'),
 ('Who won the Wimbledon championship?',None,None),
 ('What is the capital of Argentina?',None,None),
]
def main():
    results=[]
    with tempfile.TemporaryDirectory() as d, contextlib.redirect_stdout(io.StringIO()):
        with TestClient(create_app(Settings(data_dir=d),{'evaluation':'eval'})) as c:
            headers={'X-API-Key':'evaluation'}
            for path in sorted((ROOT/'samples').iterdir()):
                r=c.post('/api/documents',headers=headers,files={'file':(path.name,path.read_bytes())}); r.raise_for_status()
            for question,source,term in CASES:
                r=c.post('/api/query',headers=headers,json={'question':question}); r.raise_for_status(); answer=r.json()
                passed=(not answer['verified']) if source is None else (term in answer['answer'] and any(x['source']==source for x in answer['citations']))
                results.append({'question':question,'passed':passed,'expected_source':source,'actual_sources':[x['source'] for x in answer['citations']], 'latency_ms':answer['trace']['latency_ms']})
    report={'mode':'demo','dataset':'8 synthetic smoke cases; not representative of enterprise workloads',
            'passed':sum(r['passed'] for r in results),'total':len(results),'median_latency_ms':round(statistics.median(r['latency_ms'] for r in results),2),'cases':results}
    print(json.dumps(report,indent=2))
    (ROOT/'docs'/'evaluation_results.json').write_text(json.dumps(report,indent=2)+'\n')
    return 0 if all(r['passed'] for r in results) else 1
if __name__=='__main__': raise SystemExit(main())
