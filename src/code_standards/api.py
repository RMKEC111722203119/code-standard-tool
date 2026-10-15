import asyncio
from functools import lru_cache
from fastapi import FastAPI,HTTPException,Query
from fastapi.responses import StreamingResponse
from . import __version__
from .config import load_settings
from .blob import BlobStore
from .models import RunRequest,RunResponse
from .orchestrator import Orchestrator
app=FastAPI(title="Code Standards Tool",version=__version__)
@lru_cache
def settings(): return load_settings()
@app.get("/health")
def health(): return {"status":"healthy","version":__version__}
@app.get("/v1/checks")
async def list_checks(branch:str=Query("main")):
    try:return await asyncio.to_thread(Orchestrator(settings()).list_checks,branch)
    except Exception as e:raise HTTPException(400,str(e))
@app.post("/v1/runs",response_model=RunResponse)
async def run(request:RunRequest):
    try:return await asyncio.to_thread(Orchestrator(settings()).run,request)
    except Exception as e:raise HTTPException(500,str(e))
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
