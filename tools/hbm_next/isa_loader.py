"""Guarded repository default for the exact actual-a122 HGI-1R source format."""
import hashlib,importlib,json,sys
from pathlib import Path
BASE=Path(__file__).resolve().parent
REPO=BASE.parents[1]
VENDOR=BASE/'isa_v1r_20261019'


def load_isa(compiler_tools=None):
 manifest=json.loads((VENDOR/'manifest.json').read_text())
 tools=Path(compiler_tools).resolve()if compiler_tools else VENDOR
 modules=tools/'hbm_next'
 for name,expected in manifest['files'].items():
  p=modules/name
  if not p.is_file()or hashlib.sha256(p.read_bytes()).hexdigest()!=expected:raise ValueError(f'HGI-1R format snapshot mismatch: {p}')
 for name,expected in manifest['shared_repo_files'].items():
  p=REPO/name
  if not p.is_file()or hashlib.sha256(p.read_bytes()).hexdigest()!=expected:raise ValueError(f'HGI-1R shared format dependency mismatch: {p}')
 # Existing imports must also be the exact known format, never silently shadowed.
 for name in('isa_rows','image_check','fused_phase_check'):
  if name in sys.modules:
   p=Path(sys.modules[name].__file__)
   if hashlib.sha256(p.read_bytes()).hexdigest()!=manifest['files'][name+'.py']:raise ValueError(f'incompatible preloaded {name}: {p}')
 sys.path[:0]=[str(modules),str(REPO/'tools')]
 return importlib.import_module('isa_rows'),importlib.import_module('image_check')
