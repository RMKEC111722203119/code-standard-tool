from enum import Enum
from typing import Any
from pydantic import BaseModel,Field,field_validator,model_validator
class RunStatus(str,Enum): CLEAN="CLEAN"; FINDINGS_FOUND="FINDINGS_FOUND"; PARTIAL="PARTIAL"; ERROR="ERROR"
class PolicyStatus(str,Enum): PASSED="PASSED"; BLOCKED="BLOCKED"
class RunRequest(BaseModel):
    application_repository_url:str; application_branch:str; application_commit:str|None=None; client_repository_name:str|None=None; checks_branch:str="main"
    include_tests:list[str]=Field(default_factory=list); exclude_tests:list[str]=Field(default_factory=list); include_folders:list[str]=Field(default_factory=list); exclude_folders:list[str]=Field(default_factory=list)
    include_paths:list[str]=Field(default_factory=lambda:["**"]); exclude_paths:list[str]=Field(default_factory=list); test_parameters:dict[str,dict[str,Any]]=Field(default_factory=dict)
    test_severity_overrides:dict[str,str]=Field(default_factory=dict); test_confidence_overrides:dict[str,str]=Field(default_factory=dict); required_tests:list[str]=Field(default_factory=list); blocking_severities:list[str]=Field(default_factory=list)
    allow_required_test_error:bool=False; allow_blob_failure:bool=False; ci:bool=False
    @field_validator("blocking_severities")
    @classmethod
    def sev(cls,v):
        v=[x.title() for x in v]; bad=set(v)-{"Critical","High","Medium","Low"}
        if bad: raise ValueError(f"Unknown severity: {bad}")
        return v
    @model_validator(mode="after")
    def selection(self):
        if self.include_tests and self.exclude_tests: raise ValueError("Use include-test or exclude-test, not both")
        return self
class TestManifest(BaseModel):
    test_id:str; test_name:str; test_version:str; description:str; entrypoint:str; severity:str; confidence:str; category:str; supported_extensions:list[str]; timeout_seconds:int=300; enabled_by_default:bool=True; parameters:dict[str,Any]=Field(default_factory=dict); folder:str=""; manifest_path:str=""
class TestExecution(BaseModel):
    test_id:str; test_name:str; test_version:str; status:str; summary:str=""; files_received:int=0; files_scanned:int=0; findings_count:int=0; duration_seconds:float=0; exit_code:int|None=None; required:bool=False; errors:list[Any]=Field(default_factory=list); warnings:list[Any]=Field(default_factory=list)
class ReportPart(BaseModel):
    part:int; kind:str; blob_name:str; filename:str; first_finding:int|None=None; last_finding:int|None=None; download_url:str=""
class RunResponse(BaseModel):
    run_id:str; repository_name:str; branch_path:str; standards_status:RunStatus; policy_status:PolicyStatus; exit_code:int; application_repository_url:str; application_branch:str; application_commit:str; checks_branch:str; checks_commit:str; files_scanned:int; tests_total:int; tests_passed:int; tests_failed:int; tests_errored:int; findings_total:int; findings_by_severity:dict[str,int]; blocking_findings:int; blob_publication_status:str; blob_prefix:str; reports_url:str; excel_reports:list[ReportPart]=Field(default_factory=list); json_reports:list[ReportPart]=Field(default_factory=list); test_executions:list[TestExecution]=Field(default_factory=list); errors:list[str]=Field(default_factory=list); warnings:list[str]=Field(default_factory=list)
