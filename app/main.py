import json, os, secrets, threading, time
from collections import defaultdict, deque
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import Depends, FastAPI, File, Header, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool
from .core import AI, Pipeline, Settings, Store

class Question(BaseModel):
    question: str = Field(min_length=3, max_length=2000)


def create_app(settings: Settings | None = None, keys: dict[str,str] | None = None):
    settings = settings or Settings()
    keys = keys if keys is not None else json.loads(os.getenv('WORKSPACE_KEYS', '{"local-demo-key":"demo"}'))
    if not keys or any(not isinstance(k,str) or not k or not isinstance(v,str) or not v for k,v in keys.items()):
        raise ValueError('WORKSPACE_KEYS must map API keys to workspace names.')
    if os.getenv('ENVIRONMENT') == 'production':
        if 'local-demo-key' in keys or any(len(k)<32 for k in keys):
            raise ValueError('Production requires non-default API keys of at least 32 characters.')
        if not settings.qdrant_url:
            raise ValueError('Production requires external persistent QDRANT_URL.')
    @asynccontextmanager
    async def lifespan(app):
        store=Store(settings, AI(settings)); app.state.store=store; app.state.pipeline=Pipeline(store)
        yield
        store.close()
    app=FastAPI(title='FieldKit Enterprise Knowledge Assistant', version='1.0.0', lifespan=lifespan)
    calls=defaultdict(deque); lock=threading.Lock()
    def authorize(x_api_key: str = Header(default='')):
        workspace=next((v for k,v in keys.items() if secrets.compare_digest(k,x_api_key)),None)
        if workspace is None:
            raise HTTPException(401,'Valid X-API-Key required.')
        with lock:
            now=time.monotonic(); queue=calls[workspace]
            while queue and queue[0]<now-60: queue.popleft()
            if len(queue)>=60: raise HTTPException(429,'Rate limit exceeded. Retry in a minute.')
            queue.append(now)
        return workspace
    @app.get('/',include_in_schema=False)
    def home(): return FileResponse(Path(__file__).parent/'static'/'index.html')
    @app.get('/health')
    def health(): return {'status':'ok','mode':settings.mode}
    @app.get('/api/documents')
    def documents(workspace=Depends(authorize)):
        return app.state.store.documents(workspace)
    @app.post('/api/documents',status_code=201)
    async def upload(file: UploadFile=File(...),workspace=Depends(authorize)):
        raw=await file.read(2_000_001)
        await file.close()
        if len(raw)>2_000_000: raise HTTPException(413,'Maximum file size is 2 MB.')
        try: return await run_in_threadpool(app.state.store.ingest,workspace,file.filename or 'upload.txt',raw)
        except (ValueError,UnicodeError) as exc: raise HTTPException(400,str(exc)) from None
        except Exception: raise HTTPException(502,'Document processing failed. Check the file and provider configuration.') from None
    @app.delete('/api/documents/{document_id}',status_code=204)
    def delete(document_id:str,workspace=Depends(authorize)):
        app.state.store.delete(workspace,document_id)
    @app.post('/api/query')
    def query(body:Question,workspace=Depends(authorize)):
        if not body.question.strip(): raise HTTPException(422,'Question cannot be blank.')
        try: return app.state.pipeline.query(workspace,body.question.strip())
        except Exception: raise HTTPException(502,'Answer generation failed. Check provider availability and configuration.') from None
    @app.get('/api/traces/{request_id}')
    def trace(request_id:str,workspace=Depends(authorize)):
        result=app.state.store.get_trace(workspace,request_id)
        if result is None: raise HTTPException(404,'Trace not found.')
        return result
    return app

app=create_app()
