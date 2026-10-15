import fnmatch,yaml
from pathlib import Path
from .models import TestManifest
from .utils import ToolError,run_git
REQ={"test_id","test_name","test_version","description","entrypoint","severity","confidence","category","supported_extensions","timeout_seconds","enabled_by_default","parameters"}
def clone_repository(url,branch,dest,timeout,token,commit=None):
    run_git(["clone","--quiet","--single-branch","--branch",branch,"--",url,str(dest)],timeout,token)
    if commit:
        resolved=run_git(["rev-parse","--verify",f"{commit}^{{commit}}"],timeout,token,dest); run_git(["merge-base","--is-ancestor",resolved,f"origin/{branch}"],timeout,token,dest); run_git(["checkout","--quiet","--detach",resolved],timeout,token,dest)
    return run_git(["rev-parse","HEAD"],timeout,token,dest)
def discover_manifests(root):
    out=[]; ids=set()
    for p in sorted((root/"checks").rglob("test.yml")):
        d=yaml.safe_load(p.read_text()); missing=REQ-set(d or {})
        if missing: raise ToolError(f"{p}: missing {sorted(missing)}")
        if d["test_id"] in ids: raise ToolError(f"Duplicate test {d['test_id']}")
        ids.add(d["test_id"]); ep=(p.parent/d["entrypoint"]).resolve()
        if p.parent.resolve() not in ep.parents or not ep.is_file(): raise ToolError(f"Bad entrypoint in {p}")
        out.append(TestManifest(**d,folder=p.parent.relative_to(root/"checks").as_posix(),manifest_path=p.relative_to(root).as_posix()))
    return out
def fmatch(folder,patterns): return any(folder==x or folder.startswith(x.rstrip("/")+"/") or fnmatch.fnmatch(folder,x) for x in patterns)
def select_tests(ms,r):
    ids={m.test_id for m in ms}; missing=(set(r.include_tests)|set(r.exclude_tests)|set(r.required_tests)|set(r.test_parameters))-ids
    if missing: raise ToolError(f"Unknown tests: {sorted(missing)}")
    opt=bool(r.include_tests or r.include_folders); out=[]
    for m in ms:
        inc=(m.test_id in r.include_tests or fmatch(m.folder,r.include_folders)) if opt else m.enabled_by_default
        exc=m.test_id in r.exclude_tests or fmatch(m.folder,r.exclude_folders)
        if inc and not exc: out.append(m)
    if not out: raise ToolError("No tests selected")
    return out
def merge(a,b):
    z=dict(a)
    for k,v in b.items(): z[k]=merge(z[k],v) if isinstance(v,dict) and isinstance(z.get(k),dict) else v
    return z
def validate(a,b,p=""):
    for k,v in b.items():
        n=f"{p}.{k}" if p else k
        if k not in a: raise ToolError(f"Unknown parameter {n}")
        if isinstance(v,dict): validate(a[k],v,n)
def resolved(m,r):
    o=r.test_parameters.get(m.test_id,{}); validate(m.parameters,o)
    return {"severity":r.test_severity_overrides.get(m.test_id,m.severity),"confidence":r.test_confidence_overrides.get(m.test_id,m.confidence),"parameters":merge(m.parameters,o)}
