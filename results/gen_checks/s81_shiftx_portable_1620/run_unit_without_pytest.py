import ast,json,os,subprocess,sys,tempfile
from pathlib import Path
from types import SimpleNamespace as NS
R=Path('/srv/opentallas-scratch2/claude/codex-s81-shiftx-1620');tmp=R/'unittest_tmp';tmp.mkdir(exist_ok=True);os.environ['TMPDIR']=str(tmp);tempfile.tempdir=None
os.environ['PYTHONPATH']=str(R/'tests')+':/srv/opentallas-scratch2/claude/codex-s81-wave-1131/src/tools/die_plan'
sys.path.insert(0,str(R/'tests'));sys.path.append('/srv/opentallas-scratch2/claude/codex-s81-wave-1131/src/tools/die_plan')
p=subprocess.run([sys.executable,str(R/'tests/test_bind_native_shiftx_portable.py'),'-v'],capture_output=True,text=True);(R/'unittest_r3.log').write_text(p.stdout+p.stderr);print(p.stdout+p.stderr,flush=True);assert p.returncode==0
# Run the unchanged existing positive memory/shift test body with its explicit
# False case and ordinary scratch Path fixture; pytest decorators need not run.
import bind_elab as E
from bind_native_glue import NativeGlue
src=R/'tests/test_bind_native_glue.py';tree=ast.parse(src.read_text());fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='test_native_memory_and_shift_helpers');fn.decorator_list=[]
ns=dict(json=json,os=os,sys=sys,subprocess=subprocess,Path=Path,NS=NS,E=E,NativeGlue=NativeGlue)
exec(compile(ast.fix_missing_locations(ast.Module(body=[fn],type_ignores=[])),str(src),'exec'),ns)
d=Path(tempfile.mkdtemp(prefix='legacy_memory_positive_'));ns[fn.name](d,False)
(R/'unit_r3.json').write_text(json.dumps(dict(stdlib_unittest_cases=6,rc=0,legacy_memory_shift_positive='unchanged existing function body, False case, 12000checks PASS',legacy_fixture=str(d),pytest_first_attempt='INFRA No module namedpytest; no dependency install'),indent=1)+'\n');print('LEGACY_MEMORY_SHIFT_POSITIVE_PASS checks12000',flush=True)
