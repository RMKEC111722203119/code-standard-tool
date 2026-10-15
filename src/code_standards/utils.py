import base64,fnmatch,os,re,secrets,subprocess
from datetime import datetime,timezone
from pathlib import Path
from urllib.parse import urlparse
class ToolError(Exception): pass
def new_run_id(): return f"RUN-{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}-{secrets.token_hex(4)}"
def safe_component(v): return re.sub(r"[^A-Za-z0-9._-]+","-",v).strip(".-")[:120] or "unknown"
def repository_name_from_url(url):
    v=url.rstrip("/"); path=v.split(":",1)[1] if v.startswith("git@") and ":" in v else urlparse(v).path; name=path.rstrip("/").split("/")[-1]; return safe_component(name[:-4] if name.endswith(".git") else name)
def git_env(token):
    e={"PATH":os.environ.get("PATH","/usr/bin:/bin"),"HOME":os.environ.get("HOME","/tmp"),"GIT_TERMINAL_PROMPT":"0","GIT_CONFIG_NOSYSTEM":"1"}
    if token:
        enc=base64.b64encode(f"x-access-token:{token}".encode()).decode(); e.update({"GIT_CONFIG_COUNT":"1","GIT_CONFIG_KEY_0":"http.extraHeader","GIT_CONFIG_VALUE_0":f"AUTHORIZATION: basic {enc}"})
    return e
def run_git(args,timeout,token=None,cwd=None):
    p=subprocess.run(["git","-c","core.hooksPath=/dev/null","-c","protocol.file.allow=never",*args],cwd=cwd,env=git_env(token),capture_output=True,text=True,timeout=timeout)
    if p.returncode: raise ToolError("Git failed: "+p.stderr[-1000:].replace(token or "___","***"))
    return p.stdout.strip()
def collect_files(root,includes,excludes):
    defaults=[".git/**","**/.git/**","**/__pycache__/**","**/.venv/**","**/venv/**","**/node_modules/**","**/dist/**","**/build/**","**/code-standards-results/**"]; out=[]
    for cr,ds,fs in os.walk(root,followlinks=False):
        c=Path(cr); ds[:]=[d for d in ds if not (c/d).is_symlink()]
        for f in fs:
            a=c/f
            if a.is_symlink(): continue
            r=a.relative_to(root).as_posix()
            if includes and not any(fnmatch.fnmatch(r,x) for x in includes): continue
            if any(fnmatch.fnmatch(r,x) for x in defaults+excludes): continue
            out.append(r)
    return sorted(out)
