"""Verify real generated-core propagation, default equivalence and build refusal."""
import re
import subprocess
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import qwen_rom_arithmetic_contract_w12 as A
import qwen_rom_rt_core_emit_w12 as E

ROOT=Path(__file__).resolve().parents[1]
BASE='77dea5d06e19da0eacb67e4c98129665585397d8'


def test_default_build_flags_remain_empty_and_target_prices_full_chain():
 assert A.flags()==[]
 assert set(A.flags(True))=={'-GACC_LAT=7','-GTREE_LAT=7','-GMUL_LAT=6','-GFAST_ISSUE=1','-GKV_PREP=3'}
 assert A.DEFAULTS==dict(ACC_LAT=5,TREE_LAT=3,MUL_LAT=5,FAST_ISSUE=0,KV_PREP=0)


def test_actual_emitter_default_core_changes_only_new_declarations_and_forwarding():
 core=(ROOT/'rtl/hdc/ot_hdc_core_vector_weight.sv').read_text()
 old_source=subprocess.check_output(['git','show',BASE+':tools/qwen_rom_rt_core_emit_w12.py'],cwd=ROOT,text=True)
 old={'__file__':str(ROOT/'tools/qwen_rom_rt_core_emit_w12.py'),'__name__':'pinned_emitter'}
 exec(compile(old_source,'pinned_emitter','exec'),old)
 generated=E.emit(core)
 stripped=generated
 for name,value in A.DEFAULTS.items():
  assert f'parameter integer {name} = {value}' in generated
  assert f'.{name}({name})' in generated
  stripped=stripped.replace(f',\n    parameter integer {name} = {value}','')
  stripped=stripped.replace(f', .{name}({name})','')
 assert stripped==old['emit'](core)


def test_actual_die_defaults_and_forwarding_leave_other_source_identical():
 p='rtl/test/qwen_rom_runtime/ot_qwen_rom_rt_die_w12.sv'
 actual=(ROOT/p).read_text()
 old=subprocess.check_output(['git','show',BASE+':'+p],cwd=ROOT,text=True)
 stripped=actual
 for name,value in A.DEFAULTS.items():
  assert f'parameter integer {name} = {value}' in actual
  assert f'.{name}({name})' in actual
  stripped=stripped.replace(f'    parameter integer {name} = {value},\n','')
 stripped=stripped.replace('.MEM_EXTRA(MEM_EXTRA),\n        .ACC_LAT(ACC_LAT),.TREE_LAT(TREE_LAT),.MUL_LAT(MUL_LAT),\n        .FAST_ISSUE(FAST_ISSUE),.KV_PREP(KV_PREP)) core (','.MEM_EXTRA(MEM_EXTRA)) core (')
 assert stripped==old


def test_candidate_cli_refuses_before_creating_workdir_or_starting_tools(tmp_path):
 path=tmp_path/'never_created'
 cmd=[sys.executable,str(ROOT/'tools/qwen_rom_rt_token_w12.py'),'--physical-arithmetic-successor','--workdir',str(path),'--stages','absent','--token-oracle','absent','--preload','absent','--bd','41','--nws','5','--tws','38']
 p=subprocess.run(cmd,capture_output=True,text=True)
 assert p.returncode==2 and 'Candidate build blocked' in p.stderr
 assert not path.exists()


def test_source_current_model_absence_remains_blocked_without_changing_legacy_price():
 import uarch_model as U
 old=dict(U.QWEN_SS)
 r=A.prepare()
 assert r['status']=='blocked' and not r['physical_build_ready']
 assert r['model_price_joined']==hasattr(U,'qwen_rom_physical_successor')
 assert U.QWEN_SS==old and U.QWEN_SS['me_lat_extra']-U.QWEN_W12_TP4_ME_EXTRA_SS==54
