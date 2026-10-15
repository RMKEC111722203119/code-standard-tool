import shutil,tempfile
from pathlib import Path
from .blob import BlobStore
from .checks import clone_repository,discover_manifests,select_tests
from .executor import execute_tests
from .models import RunStatus,PolicyStatus,RunResponse
from .reports import summarize,excel_parts,json_parts,write_index
from .utils import new_run_id,collect_files,repository_name_from_url,safe_component
class Orchestrator:
    def __init__(self,s,blob_factory=BlobStore): self.s=s; self.blob_factory=blob_factory
    def list_checks(self,branch):
        self.s.work_root.mkdir(parents=True,exist_ok=True); w=Path(tempfile.mkdtemp(dir=self.s.work_root))
        try:
            c=w/"checks"; commit=clone_repository(self.s.checks_repository_url,branch,c,self.s.git_timeout_seconds,self.s.git_token); return {"branch":branch,"commit":commit,"tests":[x.model_dump() for x in discover_manifests(c)]}
        finally: shutil.rmtree(w,ignore_errors=True)
    def run(self,r):
        run=new_run_id(); repo=safe_component(r.client_repository_name or repository_name_from_url(r.application_repository_url)); branch=safe_component(r.application_branch); prefix=BlobStore.run_prefix(repo,branch,run)
        self.s.work_root.mkdir(parents=True,exist_ok=True); w=Path(tempfile.mkdtemp(prefix=run+"-",dir=self.s.work_root)); app=w/"application"; checks=w/"checks"; execution=w/"execution"; reports=w/"reports"; fp=w/"findings.jsonl"; errors=[]; warnings=[]
        try:
            ac=clone_repository(r.application_repository_url,r.application_branch,app,self.s.git_timeout_seconds,self.s.git_token,r.application_commit); cc=clone_repository(self.s.checks_repository_url,r.checks_branch,checks,self.s.git_timeout_seconds,self.s.git_token)
            files=collect_files(app,r.include_paths,r.exclude_paths); selected=select_tests(discover_manifests(checks),r); ex=execute_tests(selected,checks,app,files,r,execution,fp,self.s.maximum_parallel_tests,self.s.default_test_timeout_seconds)
            total,counts,blocking=summarize(fp,r); errored=[x for x in ex if x.status=="ERROR"]; required=[x for x in errored if x.required]; status=RunStatus.PARTIAL if errored else RunStatus.FINDINGS_FOUND if total else RunStatus.CLEAN
            summary={"run_id":run,"repository_name":repo,"branch_path":branch,"blob_prefix":prefix,"application_commit":ac,"checks_commit":cc,"files_scanned":len(files),"findings_total":total,"findings_by_severity":counts}
            ep=excel_parts(reports,fp,total,run,r,ac,cc,ex,summary,self.s.excel_rows_per_sheet,self.s.excel_findings_per_file,errors,warnings); jp=json_parts(reports,fp,total,run,r,ac,cc,self.s.json_findings_per_file); base=self.s.public_base_url
            for x in ep: x.blob_name=f"{prefix}/{x.filename}"; x.download_url=f"{base}/v1/runs/{repo}/{branch}/{run}/reports/excel/{x.part}"
            for x in jp: x.blob_name=f"{prefix}/{x.filename}"; x.download_url=f"{base}/v1/runs/{repo}/{branch}/{run}/reports/json/{x.part}"
            write_index(reports,run,repo,branch,summary,ep,jp); publication="UPLOADED"
            try:self.blob_factory(self.s).upload_run_reports(reports,repo,branch,run)
            except Exception as e: publication="FAILED"; errors.append(f"Blob publication failed: {e}")
            blocked=bool(blocking) or (bool(required) and not r.allow_required_test_error) or (publication=="FAILED" and not r.allow_blob_failure); exit_code=1 if blocking else 0
            if (required and not r.allow_required_test_error) or (publication=="FAILED" and not r.allow_blob_failure): exit_code=2
            return RunResponse(run_id=run,repository_name=repo,branch_path=branch,standards_status=status,policy_status=PolicyStatus.BLOCKED if blocked else PolicyStatus.PASSED,exit_code=exit_code,application_repository_url=r.application_repository_url,application_branch=r.application_branch,application_commit=ac,checks_branch=r.checks_branch,checks_commit=cc,files_scanned=len(files),tests_total=len(ex),tests_passed=sum(x.status=="PASSED" for x in ex),tests_failed=sum(x.status=="FAILED" for x in ex),tests_errored=len(errored),findings_total=total,findings_by_severity=counts,blocking_findings=blocking,blob_publication_status=publication,blob_prefix=prefix,reports_url=f"{base}/v1/runs/{repo}/{branch}/{run}/reports",excel_reports=ep,json_reports=jp,test_executions=ex,errors=errors,warnings=warnings)
        finally: shutil.rmtree(w,ignore_errors=True)
