import asyncio
from functools import lru_cache
from fastapi import FastAPI,HTTPException,Query
from fastapi.responses import StreamingResponse
from . import __version__
from .config import load_settings
from .blob import BlobStore
from .models import RunRequest,RunResponse
from .orchestrator import Orchestrator
from .utils import debug
app=FastAPI(title="Code Standards Tool",version=__version__)
@lru_cache
def settings(): return load_settings()
@app.get("/health")
def health(): return {"status":"healthy","version":__version__}
@app.get("/v1/checks")
async def list_checks(branch:str=Query("main")):
    debug(f"GET /v1/checks received branch={branch!r}")
    try:return await asyncio.to_thread(Orchestrator(settings()).list_checks,branch)
    except Exception as e:
        debug(f"GET /v1/checks failed error={e!r}")
        raise HTTPException(400,str(e)) from e
@app.post("/v1/runs",response_model=RunResponse)
async def run(request:RunRequest):
    debug(f"POST /v1/runs received application_branch={request.application_branch!r} checks_branch={request.checks_branch!r} include_tests={request.include_tests} include_paths={len(request.include_paths)}")
    try:return await asyncio.to_thread(Orchestrator(settings()).run,request)
    except Exception as e:
        debug(f"POST /v1/runs failed error={e!r}")
        import traceback; traceback.print_exc()
        raise HTTPException(500,str(e)) from e
def part(index,kind,n):
    for x in index.get(f"{kind}_reports",[]):
        if x["part"]==n:return x
    raise HTTPException(404,"Report part not found")
@app.get("/v1/runs/{repository}/{branch}/{run_id}/reports")
def reports(repository:str,branch:str,run_id:str): return BlobStore(settings()).read_index(repository,branch,run_id)
@app.get("/v1/runs/{repository}/{branch}/{run_id}/reports/excel/{number}")
def excel(repository:str,branch:str,run_id:str,number:int):
    s=BlobStore(settings()); x=part(s.read_index(repository,branch,run_id),"excel",number); return StreamingResponse(s.chunks(x["blob_name"]),media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",headers={"Content-Disposition":f'attachment; filename="{x["filename"]}"'})
@app.get("/v1/runs/{repository}/{branch}/{run_id}/reports/json/{number}")
def json_report(repository:str,branch:str,run_id:str,number:int):
    s=BlobStore(settings()); x=part(s.read_index(repository,branch,run_id),"json",number); return StreamingResponse(s.chunks(x["blob_name"]),media_type="application/json",headers={"Content-Disposition":f'attachment; filename="{x["filename"]}"'})
