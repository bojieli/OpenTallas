"""Export exact selected ROLE89 sources from repository Git objects, no scratch fallback."""
import hashlib,json,subprocess
from pathlib import Path
HERE=Path(__file__).resolve().parent

def export_selected_role(repo,out):
 m=json.loads((HERE/'selected_role_sources.json').read_text());files=[]
 for relative,expected in m['files'].items():
  try:raw=subprocess.check_output(['git','show',m['source_commit']+':'+relative],cwd=repo,stderr=subprocess.PIPE)
  except subprocess.CalledProcessError as e:raise RuntimeError('Selected ROLE source Git object missing; no external source or automatic fetch is used: '+relative)from e
  if hashlib.sha256(raw).hexdigest()!=expected:raise ValueError('Selected ROLE source mismatch: '+relative)
  p=out/'selected_role_sources'/Path(relative).name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw);files.append(p)
 return files
