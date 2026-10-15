import json,os,subprocess,sys,time
from concurrent.futures import ThreadPoolExecutor,as_completed
from pathlib import Path
from .checks import resolved
from .models import TestExecution
def one(m,checks,app,files,request,root,out,default_timeout):
    d=root/m.test_id; d.mkdir(); inp=d/"input.json"; result=d/"output.json"; ep=checks/Path(m.manifest_path).parent/m.entrypoint
    inp.write_text(json.dumps({"contract_version":"1.0","project_dir":str(app),"files":files,"test_configuration":resolved(m,request),"execution_context":{"application_repository_url":request.application_repository_url,"application_branch":request.application_branch,"application_commit":request.application_commit,"checks_branch":request.checks_branch}},indent=2))
    start=time.monotonic()
    try: p=subprocess.run([sys.executable,str(ep),"--input",str(inp),"--output",str(result)],cwd=d,stdin=subprocess.DEVNULL,capture_output=True,text=True,timeout=m.timeout_seconds or default_timeout,env={"PATH":os.environ.get("PATH",""),"HOME":str(d),"PYTHONDONTWRITEBYTECODE":"1"})
    except subprocess.TimeoutExpired: return TestExecution(test_id=m.test_id,test_name=m.test_name,test_version=m.test_version,status="ERROR",summary="Timeout",required=m.test_id in request.required_tests)
    dur=round(time.monotonic()-start,3)
    if not result.is_file(): return TestExecution(test_id=m.test_id,test_name=m.test_name,test_version=m.test_version,status="ERROR",summary="No output",duration_seconds=dur,required=m.test_id in request.required_tests)
    try:
        data=json.loads(result.read_text()); findings=data.get("findings",[])
        with out.open("w") as f:
            for x in findings: f.write(json.dumps(x,ensure_ascii=False)+"\n")
        return TestExecution(test_id=m.test_id,test_name=m.test_name,test_version=m.test_version,status="ERROR" if p.returncode else data.get("status","ERROR"),summary=data.get("summary",""),files_received=data.get("files_received",len(files)),files_scanned=data.get("files_scanned",0),findings_count=len(findings),duration_seconds=dur,exit_code=p.returncode,required=m.test_id in request.required_tests,errors=data.get("errors",[]),warnings=data.get("warnings",[]))
    except Exception as e: return TestExecution(test_id=m.test_id,test_name=m.test_name,test_version=m.test_version,status="ERROR",summary=str(e),duration_seconds=dur,required=m.test_id in request.required_tests)
def execute_tests(ms,checks,app,files,request,root,combined,max_workers,default_timeout):
    root.mkdir(parents=True); per={m.test_id:root/f"{m.test_id}.jsonl" for m in ms}; results={}
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        fs={pool.submit(one,m,checks,app,files,request,root,per[m.test_id],default_timeout):m.test_id for m in ms}
        for f in as_completed(fs): results[fs[f]]=f.result()
    with combined.open("w") as dst:
        for m in ms:
            if per[m.test_id].is_file(): dst.write(per[m.test_id].read_text())
    return [results[m.test_id] for m in ms]
