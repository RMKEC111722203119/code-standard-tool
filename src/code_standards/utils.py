import base64,fnmatch,os,re,secrets,subprocess,time
from datetime import datetime,timezone
from pathlib import Path
from urllib.parse import urlparse
class ToolError(Exception): pass
def debug(message):
    print(f"[code-standards] {message}",flush=True)
def new_run_id(): return f"RUN-{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}-{secrets.token_hex(4)}"
def safe_component(v): return re.sub(r"[^A-Za-z0-9._-]+","-",v).strip(".-")[:120] or "unknown"
def repository_name_from_url(url):
    v=url.rstrip("/"); path=v.split(":",1)[1] if v.startswith("git@") and ":" in v else urlparse(v).path; name=path.rstrip("/").split("/")[-1]; return safe_component(name[:-4] if name.endswith(".git") else name)
def git_env(token):
    e={"PATH":os.environ.get("PATH","/usr/bin:/bin"),"HOME":os.environ.get("HOME","/tmp"),"GIT_TERMINAL_PROMPT":"0","GIT_CONFIG_NOSYSTEM":"1"}
    for name in ("SYSTEMROOT","WINDIR","TEMP","TMP","USERPROFILE","HOMEDRIVE","HOMEPATH"):
        if os.environ.get(name):
            e[name]=os.environ[name]
    for name in ("HTTP_PROXY","HTTPS_PROXY","ALL_PROXY","http_proxy","https_proxy","all_proxy","NO_PROXY","no_proxy"):
        if os.environ.get(name):
            e[name]=os.environ[name]
    if token:
        enc=base64.b64encode(f"x-access-token:{token}".encode()).decode(); e.update({"GIT_CONFIG_COUNT":"1","GIT_CONFIG_KEY_0":"http.extraHeader","GIT_CONFIG_VALUE_0":f"AUTHORIZATION: basic {enc}"})
    return e
def run_git(args,timeout,token=None,cwd=None):
    command=["git","-c","core.hooksPath=/dev/null","-c","protocol.file.allow=never",*args]
    transient_errors=("could not resolve host","unable to access","connection timed out","connection reset","network is unreachable")
    for attempt in range(1,4):
        debug(f"git start operation={args[0] if args else 'unknown'} attempt={attempt}/3 cwd={cwd} timeout={timeout}s")
        try:
            p=subprocess.run(command,cwd=cwd,env=git_env(token),capture_output=True,text=True,timeout=timeout)
        except subprocess.TimeoutExpired:
            if attempt<3:
                debug(f"git timed out; retrying attempt={attempt+1}/3")
                time.sleep(attempt)
                continue
            raise ToolError("Git timed out after 3 attempts")
        if p.returncode == 0:
            debug(f"git completed output_length={len(p.stdout)}")
            return p.stdout.strip()
        safe_stderr=p.stderr[-2000:].strip()
        if attempt<3 and any(error in p.stderr.lower() for error in transient_errors):
            debug(f"git transient failure return_code={p.returncode} stderr={safe_stderr!r}; retrying attempt={attempt+1}/3")
            time.sleep(attempt)
            continue
        debug(f"git failed return_code={p.returncode} stderr={safe_stderr!r}")
        raise ToolError("Git failed: "+p.stderr[-1000:].replace(token or "___","***"))
def collect_files(root,includes,excludes):
    debug(f"file collection start root={root} includes={len(includes)} excludes={len(excludes)}")
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
    result=sorted(out)
    debug(f"file collection completed count={len(result)}")
    return result
