import json
from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient,ContentSettings
from .utils import ToolError,safe_component
class BlobStore:
    def __init__(self,s):
        if not s.azure_account_url or "YOUR_ACCOUNT" in s.azure_account_url: raise ToolError("Azure Blob not configured")
        self.container=BlobServiceClient(s.azure_account_url,credential=DefaultAzureCredential(exclude_interactive_browser_credential=True)).get_container_client(s.azure_container)
    @staticmethod
    def run_prefix(repo,branch,run): return "/".join(map(safe_component,(repo,branch,run)))
    def upload_run_reports(self,dir,repo,branch,run):
        prefix=self.run_prefix(repo,branch,run)
        for p in dir.iterdir():
            if p.is_file():
                ct="application/json" if p.suffix==".json" else "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                with p.open("rb") as f:self.container.upload_blob(f"{prefix}/{p.name}",f,overwrite=False,content_settings=ContentSettings(content_type=ct))
        return prefix
    def read_index(self,repo,branch,run): return json.loads(self.container.get_blob_client(f"{self.run_prefix(repo,branch,run)}/report_index.json").download_blob().readall())
    def chunks(self,name): yield from self.container.get_blob_client(name).download_blob().chunks()
