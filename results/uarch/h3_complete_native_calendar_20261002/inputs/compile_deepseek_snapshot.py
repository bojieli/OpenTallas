"""Execute captured producer compiler with filesystem root relocation only."""
import ast
import gzip
import hashlib
import json
from pathlib import Path
import sys
import types
ROOT = Path(__file__).resolve().parents[4]
INPUT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'tools'))
source = INPUT / 'h3_deepseek_complete_native.py.source'
tree = ast.parse(source.read_text())
for node in tree.body:
    if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'ROOT' for t in node.targets):
        node.value = ast.parse('Path(' + repr(str(ROOT)) + ')', mode='eval').body
    if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'SCALAR_DEPENDENCY' for t in node.targets):
        node.value = ast.Constant(str((INPUT / 'h3_exact_scalar_contract.py').relative_to(ROOT)))
module = types.ModuleType('captured_deepseek_compiler')
module.__file__ = str(source)
exec(compile(ast.fix_missing_locations(tree), str(source), 'exec'), module.__dict__)
program = module.compile_all()
path = INPUT / 'DeepSeek_native.json.gz'
raw = json.dumps(program, sort_keys=True, separators=(',', ':')).encode()
if path.exists():
    if gzip.decompress(path.read_bytes()) != raw:
        raise ValueError('captured producer compiler replay mismatch')
else:
    path.write_bytes(gzip.compress(raw, mtime=0))
print(json.dumps({'status':'PASS_PINNED_DEEPSEEK_COMPILER_SNAPSHOT_REPLAY',
    'snapshot_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
    'coverage':program['coverage'], 'templates':len(program['templates']),
    'relocation':'AST ROOT and scalar dependency path assignments only; source snapshot unchanged'}))
