"""Preparation tests only; never invoke Verilator or compile a wrapper."""
import importlib.util
import json
from pathlib import Path
import re
import subprocess

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('wrapper_prepare', ROOT/'tools/prepare_field_common_wrapper_gate.py')
M = importlib.util.module_from_spec(spec)
spec.loader.exec_module(M)


@pytest.fixture(scope='module')
def sources():
    return M.read_sources()


def undo(text, side):
    return re.sub(r'\b'+side+r'(ot_\w+)\b', lambda m:m[1], text)


@pytest.mark.parametrize('path', M.SOURCES)
def test_reference_identity(sources, path):
    assert undo(M.generate(sources)['ref_'+Path(path).name], 'ref_') == sources[path]


@pytest.mark.parametrize('path', M.SOURCES[1:])
def test_candidate_consumers_byte_exact(sources, path):
    assert undo(M.generate(sources)['cand_'+Path(path).name], 'cand_') == sources[path]


def test_helper_signatures_preserved(sources):
    original=sources[M.SOURCES[0]]
    new=M.replace_helpers(original)
    for name in ('ot_v41_ksadd','ot_v41_inc'):
        signature=r'module\s+'+name+r'\b.*?\);'
        assert re.search(signature,new,re.S)[0] == re.search(signature,original,re.S)[0]
    assert "{cout,s} = {1'b0,a} + {1'b0,b} + {{W{1'b0}},cin}" in new
    assert "{co,y} = {1'b0,a} + {{W{1'b0}},inc}" in new


def test_actual_mutant_only_changes_helper(sources):
    positive=M.generate(sources)
    negative=M.generate(sources, True)
    changed=[p for p in positive if positive[p]!=negative[p]]
    assert changed==['cand_ot_prefix.sv']
    assert "^ {{W{1'b0}},1'b1}" in negative[changed[0]]


def test_missing_declaration_rejected(sources):
    with pytest.raises(ValueError,match='declaration count'):
        M.replace_helpers(sources[M.SOURCES[0]].replace('module ot_v41_inc','module lost'))


def test_unexpected_dependency_rejected(sources):
    bad=dict(sources);bad[M.SOURCES[1]]+='\nmodule unqualified; endmodule\n'
    with pytest.raises(ValueError,match='module set'):
        M.generate(bad)


def test_source_pin_mismatch_before_generation(monkeypatch, tmp_path):
    monkeypatch.setattr(M.subprocess,'check_output',lambda *a,**k:b'wrong source')
    with pytest.raises(ValueError,match='source pin mismatch'):
        M.prepare(tmp_path/'fresh')
    assert not (tmp_path/'fresh').exists()


def test_prepare_and_no_overwrite(tmp_path):
    out=tmp_path/'fresh'
    record=M.prepare(out)
    before={p.name:p.read_bytes() for p in out.iterdir()}
    with pytest.raises(FileExistsError): M.prepare(out)
    assert before=={p.name:p.read_bytes() for p in out.iterdir()}
    assert record['status']=='PREPARED_NOT_EXECUTED'
    assert 'BLOCKED' in record['execution_gate']
    for p,h in record['files_sha256'].items(): assert M.sha((out/p).read_bytes())==h


@pytest.mark.parametrize('top',M.TOPS)
def test_aggregate_resource_bound(top):
    for phase,cmd in M.commands(top).items():
        assert cmd[:2]==['systemd-run','--user']
        for bound in ('MemoryMax=4294967296','MemorySwapMax=0','CPUQuota=200%','TasksMax=64'):
            assert bound in cmd
        assert 'timeout' in cmd and '--kill-after=5s' in cmd
        assert ('600s' if phase=='compile' else '60s') in cmd
        if phase=='compile': assert cmd[cmd.index('-j')+1]=='2'


def test_no_compile_entry_point():
    import ast
    tree=ast.parse((ROOT/'tools/prepare_field_common_wrapper_gate.py').read_text())
    subprocess_calls=[n for n in ast.walk(tree) if isinstance(n,ast.Call)
       and isinstance(n.func,ast.Attribute) and isinstance(n.func.value,ast.Name)
       and n.func.value.id=='subprocess']
    assert len(subprocess_calls)==1
    assert subprocess_calls[0].func.attr=='check_output'
    assert ast.literal_eval(subprocess_calls[0].args[0].elts[0])=='git'


@pytest.mark.parametrize('module,ports',[
 ('field_chain_case',('ro','rs','rf','rt','r_fault','co','cs','cf','ct','c_fault')),
 ('tb_tree16',('ro','rt','rp','rv','re','rf','co','ct','cp','cv','ce','cf')),
 ('tb_bf16',('ro','rv','rt','rfinal','re','rf','co','cv','ct','cfinal','ce','cf'))])
def test_bench_every_public_output_compared(module,ports):
    text=(ROOT/'rtl/test/tb_field_common_wrappers.sv').read_text()
    body=re.search(r'module '+module+r'\b.*?endmodule',text,re.S)[0]
    comparison=re.search(r'task compare_all;(.*?)endtask',body,re.S)[1]
    for port in ports: assert re.search(r'\b'+port+r'\b',comparison)
    assert '!==' in comparison
    assert '#1;compare_all()' in body.replace(' ','')
    reset=re.search(r'task reset_now;(.*?)endtask',body,re.S)[1]
    assert 'rst_n=0;' in reset and 'compare_all();' in reset


def test_binding_and_source_authority():
    record=json.loads((M.RECORD/'resource_estimate.json').read_text())
    assert record['source_commit']==M.SOURCE
    assert record['model_binding']['CUT']==379 and record['model_binding']['LAT']==8
    assert M.sha((ROOT/'tools/uarch_model.py').read_bytes())==record['model_binding']['sha256']
    assert record['resource_estimate']['compile_jobs']==2
    assert record['resource_estimate']['hard_aggregate_memory_bytes']==4*1024**3
    manifest=json.loads((ROOT/'results/rtl/w17_connected_token_preparation_20261001/L0_cli_recovery_launch.json').read_text())
    for path in M.SOURCES:
        assert manifest['source_sha256'][path]==record['source_pins'][path]['sha256']


def test_runner_denies_missing_go_before_mutation(tmp_path):
    spec=importlib.util.spec_from_file_location('wrapper_run',ROOT/'tools/run_field_common_wrapper_gate.py')
    runner=importlib.util.module_from_spec(spec);spec.loader.exec_module(runner)
    with pytest.raises(ValueError,match='GO token'):
        runner.run_gate(tmp_path/'record',tmp_path/'work',None)
    assert list(tmp_path.iterdir())==[]


def test_runner_rejects_false_review_before_mutation(monkeypatch,tmp_path):
    spec=importlib.util.spec_from_file_location('wrapper_run',ROOT/'tools/run_field_common_wrapper_gate.py')
    runner=importlib.util.module_from_spec(spec);spec.loader.exec_module(runner)
    review={'result_matches_owner_exactly':False}
    monkeypatch.setattr(runner.subprocess,'check_output',lambda *a,**k:json.dumps(review).encode())
    with pytest.raises(ValueError,match='review mismatch'):
        runner.run_gate(tmp_path/'record',tmp_path/'work','parent-0917adb00-wrapper-verification-only')
    assert list(tmp_path.iterdir())==[]


def test_port_map_covers_source_outputs(sources):
    bench=(ROOT/'rtl/test/tb_field_common_wrappers.sv').read_text()
    for mod in ('chain2','segtree2','bf16_lanes2'):
        text=sources['rtl/v41rom/ot_v41_'+mod+'.sv']
        header=text[text.index('module '):text.index(');',text.index('module '))]
        ports=re.findall(r'output\s+(?:wire|reg)\s+(?:\[[^\n]+?\]\s*)?(\w+)\s*[,\n]',header+'\n')
        instances=re.findall(r'(?:ref_|cand_)ot_v41_'+mod+r'\b.*?\);',bench,re.S)
        assert len(instances)==2
        for port in ports:
            for instance in instances: assert '.'+port+'(' in instance
        assert len(ports) in (5,6)
