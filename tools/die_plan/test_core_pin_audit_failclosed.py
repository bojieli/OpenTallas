"""Generated legacy shells propagate a failing audit; both auditors report failure to callers."""
import ast,json,os,runpy,subprocess,sys
from pathlib import Path
from types import SimpleNamespace as NS
import pytest
ROOT=Path(__file__).resolve().parents[2]
RUNNERS=['physical/die_plan/qwen_compute/cores/legacy/gen_core_kit_qc.py','physical/die_plan/s81/cores/legacy/gen_core_kit_legacy.py','physical/die_plan/s81/cores/svc/run_kit.sh','physical/die_plan/qwen_kvsys/cores/harden/run_kit_kv.sh','physical/die_plan/hbm_arch_cores/run_kit_hbm.sh']

@pytest.mark.parametrize('relative',RUNNERS)
@pytest.mark.parametrize('initial,audit,expected',[(0,0,0),(0,1,1),(7,0,7)])
def test_actual_runner_audit_status(relative,initial,audit,expected):
    text=(ROOT/relative).read_text()
    if relative.endswith('.py'):
        text=next(n.value for n in ast.walk(ast.parse(text)) if isinstance(n,ast.Constant) and isinstance(n.value,str) and 'openroad -python -exit /work/pin_audit' in n.value)
    line=next(x for x in text.splitlines() if 'openroad -python -exit /work/pin_audit' in x)
    line=line.replace('\\"','"').replace('\\$','$').rstrip(' \\\n')
    line=line.replace('/work/pin_audit.log','/dev/null')
    result=subprocess.run(['bash','-c',f'openroad() {{ return {audit}; }}; rc={initial}; O=fake; '+line+' exit "$rc"'],capture_output=True)
    assert result.returncode==expected,result.stderr.decode()

@pytest.mark.parametrize('relative',['tools/die_plan/pin_audit.py','physical/die_plan/s81/cores/svc/pin_audit_core.py'])
@pytest.mark.parametrize('extra,expected',[(False,0),(True,1)])
def test_real_auditor_cli_status(relative,extra,expected,tmp_path,monkeypatch):
    term=NS(getName=lambda:'unexpected_data',getSigType=lambda:'SIGNAL',getBPins=lambda:[])
    block=NS(getDefUnits=lambda:1000,getDieArea=lambda:NS(xMax=lambda:10000,yMax=lambda:10000),getBTerms=lambda:[term] if extra else [])
    db=NS(getChip=lambda:NS(getBlock=lambda:block))
    monkeypatch.setitem(sys.modules,'odb',NS(dbDatabase=NS(create=lambda:db),read_db=lambda *_:db))
    pins=tmp_path/'pins.json';pins.write_text('[]');out=tmp_path/'audit.json'
    for k,v in {'PINS':str(pins),'OUT':str(out),'ODB':'fake'}.items():monkeypatch.setenv(k,v)
    with pytest.raises(SystemExit) as exc:runpy.run_path(str(ROOT/relative),run_name='__main__')
    assert exc.value.code==expected
    assert json.loads(out.read_text())['verdict']==('FAIL' if extra else 'PASS')
