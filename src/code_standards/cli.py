import argparse,json,os,sys
from pathlib import Path
import httpx,yaml
CONFIG=Path.home()/".code-standards/config.yml"
def server(v):
    s=v or os.getenv("CODE_STANDARDS_SERVER") or ((yaml.safe_load(CONFIG.read_text()) or {}).get("server") if CONFIG.is_file() else None)
    if not s:raise ValueError("Configure server with codestandards configure --server URL")
    return s.rstrip("/")
def val(x):
    try:return json.loads(x)
    except:return x
def params(items):
    out={}
    for item in items:
        left,sep,raw=item.partition("=")
        if not sep or "." not in left:raise ValueError("Expected T01.parameter=value")
        tid,path=left.split(".",1); cur=out.setdefault(tid,{})
        ps=path.split(".")
        for p in ps[:-1]:cur=cur.setdefault(p,{})
        cur[ps[-1]]=val(raw)
    return out
def parser():
    p=argparse.ArgumentParser(prog="codestandards"); s=p.add_subparsers(dest="cmd",required=True)
    c=s.add_parser("configure"); c.add_argument("--server",required=True)
    h=s.add_parser("health"); h.add_argument("--server")
    l=s.add_parser("list-tests"); l.add_argument("--server"); l.add_argument("--checks-branch",default="main")
    r=s.add_parser("run"); r.add_argument("--server"); r.add_argument("--application-repo",required=True); r.add_argument("--application-branch",required=True); r.add_argument("--application-commit"); r.add_argument("--client-name"); r.add_argument("--checks-branch",default="main"); r.add_argument("--include-test",action="append",default=[]); r.add_argument("--exclude-test",action="append",default=[]); r.add_argument("--include-folder",action="append",default=[]); r.add_argument("--exclude-folder",action="append",default=[]); r.add_argument("--include-path",action="append",default=[]); r.add_argument("--exclude-path",action="append",default=[]); r.add_argument("--test-param",action="append",default=[]); r.add_argument("--required-test",action="append",default=[]); r.add_argument("--block-on",action="append",default=[],choices=["Critical","High","Medium","Low"]); r.add_argument("--allow-required-test-error",action="store_true"); r.add_argument("--allow-blob-failure",action="store_true"); r.add_argument("--ci",action="store_true"); r.add_argument("--request-timeout",type=float,default=7200)
    v=s.add_parser("serve"); v.add_argument("--host",default="0.0.0.0"); v.add_argument("--port",type=int,default=8000); v.add_argument("--workers",type=int,default=1)
    return p
def main(argv=None):
    a=parser().parse_args(argv)
    try:
        if a.cmd=="configure":CONFIG.parent.mkdir(parents=True,exist_ok=True); CONFIG.write_text(yaml.safe_dump({"server":a.server.rstrip("/")})); print("Saved"); return 0
        if a.cmd=="health":print(httpx.get(server(a.server)+"/health").json()); return 0
        if a.cmd=="list-tests":
            d=httpx.get(server(a.server)+"/v1/checks",params={"branch":a.checks_branch},timeout=300).json()
            for x in d["tests"]:print(x["test_id"],x["test_name"])
            return 0
        if a.cmd=="run":
            payload={"application_repository_url":a.application_repo,"application_branch":a.application_branch,"application_commit":a.application_commit,"client_repository_name":a.client_name,"checks_branch":a.checks_branch,"include_tests":a.include_test,"exclude_tests":a.exclude_test,"include_folders":a.include_folder,"exclude_folders":a.exclude_folder,"include_paths":a.include_path or ["**"],"exclude_paths":a.exclude_path,"test_parameters":params(a.test_param),"required_tests":a.required_test,"blocking_severities":a.block_on,"allow_required_test_error":a.allow_required_test_error,"allow_blob_failure":a.allow_blob_failure,"ci":a.ci}
            q=httpx.post(server(a.server)+"/v1/runs",json=payload,timeout=a.request_timeout); q.raise_for_status(); d=q.json(); print(json.dumps(d,indent=2)); return d["exit_code"]
        if a.cmd=="serve":
            import uvicorn; uvicorn.run("code_standards.api:app",host=a.host,port=a.port,workers=a.workers); return 0
    except Exception as e:print("ERROR:",e,file=sys.stderr); return 2
if __name__=="__main__":raise SystemExit(main())
