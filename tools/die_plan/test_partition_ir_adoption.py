"""Exercise fresh kit staging and the actual shell-quoted init, with fake engines."""
import ast
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from types import SimpleNamespace
import pytest
import core_flow
import partition_ir

ROOT=Path(__file__).resolve().parents[2]
TOOL=ROOT/'tools/die_plan'
S81=ROOT/'physical/die_plan/s81/cores/legacy/gen_core_kit_legacy.py'
QC=ROOT/'physical/die_plan/qwen_compute/cores/legacy/gen_core_kit_qc.py'


def load(path,name):
    spec=importlib.util.spec_from_file_location(name,path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module


def runner(family):
    if family=='partition':return load(TOOL/'gen_phys.py','ir_partition').RUN_KIT
    if family=='s81':return load(S81,'ir_s81').run_kit(True)
    if family=='qc':return load(QC,'ir_qc').RUN_KIT
    rel={'kv':'qwen_kvsys/cores/harden/run_kit_kv.sh','hbm':'hbm_arch_cores/run_kit_hbm.sh'}[family]
    return (ROOT/'physical/die_plan'/rel).read_text()


def test_stage_is_self_contained_and_never_launches_sidecar(tmp_path,monkeypatch):
    monkeypatch.setattr(partition_ir.subprocess,'run',lambda *a,**k:pytest.fail('stage launched analysis'))
    policy=partition_ir.stage(tmp_path,'PATH-KV physical kit lane')
    assert (tmp_path/'partition_ir.py').read_bytes()==Path(partition_ir.__file__).read_bytes()
    assert policy['initial_status']=='NOT_RUN' and policy['sidecar_owner']=='PATH-KV physical kit lane'
    assert policy['die_ir_required'] and not policy['automatic_sidecar']


@pytest.mark.parametrize('relative',[
 'physical/die_plan/qwen_kvsys/cores/harden/gen_core_kit_kv.py',
 'physical/die_plan/qwen_compute/cores/legacy/gen_core_kit_qc.py',
 'physical/die_plan/s81/cores/legacy/gen_core_kit_legacy.py',
])
def test_actual_core_generator_stages_ir_helper_with_owner(tmp_path,relative):
    tree=ast.parse((ROOT/relative).read_text())
    calls=[n for n in ast.walk(tree) if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute)
           and isinstance(n.func.value,ast.Name) and n.func.value.id=='core_flow' and n.func.attr=='apply']
    assert len(calls)==1
    namespace=dict(core_flow=core_flow,kd=tmp_path,ib=core_flow.binding(250,200),ibind=core_flow.binding(250,200),
        mod='fixture',TIME_UNIT_PS=1.0,hm=5.0,rec={},own={},a=SimpleNamespace(stock_rc=False,hold_ff_margin=5.0))
    eval(compile(ast.Expression(calls[0]),relative,'eval'),namespace)
    policy=json.loads((tmp_path/'partition_ir_policy.json').read_text())
    assert (tmp_path/'partition_ir.py').is_file()
    assert 'PATH-' in policy['sidecar_owner'] and policy['die_ir_required']


def test_hbm_actual_stage_cli_and_partition_stage_call(tmp_path):
    path=ROOT/'physical/die_plan/hbm_arch_cores/gen_core_kit_hbm.py'
    tree=ast.parse(path.read_text())
    nodes=[n for n in ast.walk(tree) if isinstance(n,ast.Expr) and isinstance(n.value,ast.Call)
           and any(isinstance(x,ast.Constant) and x.value=='stage' for x in ast.walk(n))]
    assert len(nodes)==1
    exec(compile(ast.fix_missing_locations(ast.Module(nodes,type_ignores=[])),str(path),'exec'),
         dict(subprocess=subprocess,sys=sys,TOOL=TOOL,kd=tmp_path/'hbm'))
    assert json.loads((tmp_path/'hbm/partition_ir_policy.json').read_text())['sidecar_owner']=='PATH-HBM physical kit lane'
    tree=ast.parse((TOOL/'gen_phys.py').read_text())
    calls=[n for n in ast.walk(tree) if isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id=='stage_partition_ir']
    assert len(calls)==1
    eval(compile(ast.Expression(calls[0]),'gen_phys.py','eval'),
         dict(stage_partition_ir=partition_ir.stage,kd=tmp_path/'partition',P=SimpleNamespace(name='qwen_compute')))
    assert (tmp_path/'partition/partition_ir.py').is_file()


@pytest.mark.parametrize('family',['partition','s81','qc','kv','hbm'])
def test_actual_runner_quote_forwards_defer_flag_and_preserves_patch_failure(tmp_path,family):
    text=runner(family)
    assert subprocess.run(['bash','-n'],input=text,text=True,capture_output=True).returncode==0
    script=tmp_path/'run.sh';script.write_text(text)
    kit=tmp_path/'kit';kit.mkdir()
    binpath=tmp_path/'bin';binpath.mkdir()
    docker=binpath/'docker'
    docker.write_text('#!/usr/bin/env python3\nimport sys,json,os\na=sys.argv[1:]\nif "-lc" in a:\n open(os.environ["CAPTURE"],"w").write(a[a.index("-lc")+1]);sys.exit(1)\nsys.exit(0)\n')
    docker.chmod(0o755)
    capture=tmp_path/'payload'
    env=dict(os.environ,PATH=str(binpath)+':'+os.environ['PATH'],CAPTURE=str(capture))
    subprocess.run(['bash',str(script),str(kit),'place','2','1'],env=env,text=True,capture_output=True)
    payload=capture.read_text()
    match=re.search(r'python3 -I /work/partition_ir\.py patch /OpenROAD-flow-scripts/flow/scripts \|\| exit \$\?; export OT_DEFER_PARTITION_IR=1;',payload)
    assert match,payload[:700]
    # The real quoted script is exercised with a tiny patch stand-in; no IR engine.
    stub=tmp_path/'partition_ir.py';stub.write_text('import sys,os\nassert sys.argv[1:]==["patch","/OpenROAD-flow-scripts/flow/scripts"]\nsys.exit(int(os.environ["PATCH_EXIT"]))\n')
    fragment=match.group(0).replace('/work/partition_ir.py',str(stub))
    ok=subprocess.run(['bash','-c',fragment+' printf "DEFER=%s" "$OT_DEFER_PARTITION_IR"'],
                      env=dict(os.environ,PATCH_EXIT='0'),capture_output=True,text=True)
    assert ok.returncode==0 and ok.stdout=='DEFER=1',ok.stderr
    bad=subprocess.run(['bash','-c',fragment+' echo SHOULD_NOT_REACH'],
                       env=dict(os.environ,PATCH_EXIT='31'),capture_output=True,text=True)
    assert bad.returncode==31 and 'SHOULD_NOT_REACH' not in bad.stdout


def test_unmodernized_s81_legacy_bytes_unchanged():
    text=load(S81,'ir_s81_legacy').run_kit(False)
    assert hashlib.sha256(text.encode()).hexdigest()=='a70a25f57b9dad96bc2bbae058403ab8c113bfc88cf1fe41289d849e581bc08c'
    assert 'OT_DEFER_PARTITION_IR' not in text and 'partition_ir.py' not in text
