"""Replay captured Qwen producer compilation, relocating only its ROOT."""
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
source = INPUT / 'h3_qwen_complete_native.py.source'
tree = ast.parse(source.read_text())
for node in tree.body:
    if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'ROOT' for t in node.targets):
        node.value = ast.parse('Path(' + repr(str(ROOT)) + ')', mode='eval').body
module = types.ModuleType('captured_qwen_compiler'); module.__file__ = str(source)
exec(compile(ast.fix_missing_locations(tree), str(source), 'exec'), module.__dict__)
program = module.compile_native()
raw = module.canonical(program)
if gzip.decompress((INPUT / 'Qwen_native.json.gz').read_bytes()) != raw:
    old = json.loads(gzip.decompress((INPUT / 'Qwen_native.json.gz').read_bytes()))
    def difference(a,b,path=''):
        if type(a)!=type(b):return (path,'type',str(type(a)),str(type(b)))
        if isinstance(a,dict):
            if a.keys()!=b.keys():return (path,'keys',str(a.keys()-b.keys()),str(b.keys()-a.keys()))
            for key in a:
                got=difference(a[key],b[key],path+'.'+str(key))
                if got:return got
        elif isinstance(a,list):
            if len(a)!=len(b):return (path,'len',len(a),len(b))
            for i,(x,y) in enumerate(zip(a,b)):
                got=difference(x,y,path+'['+str(i)+']')
                if got:return got
        elif a!=b:return (path,'value',str(a)[:200],str(b)[:200])
    detail=difference(old,program)
    print(json.dumps({'status':'FAIL_QWEN_PRODUCER_REPLAY','difference':detail}))
    raise ValueError('captured Qwen producer replay mismatch')
print(json.dumps({'status':'PASS_PINNED_QWEN_COMPILER_SNAPSHOT_REPLAY',
    'snapshot_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'coverage':program['coverage'],
    'relocation':'AST ROOT assignment only; source snapshot unchanged'}))
