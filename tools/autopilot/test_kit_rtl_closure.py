import importlib.util
import json
import shutil
import sys
from pathlib import Path
import pytest
sys.path.insert(0, str(Path(__file__).parent))
import kit_rtl_closure as C
sys.path.insert(0, str(Path(__file__).parents[1] / 'die_plan'))
import kit_gen_lint as L


def vehicle(tmp_path):
    src, bind, work = [tmp_path / n for n in ('src', 'bind', 'attempt')]
    for p in (src,bind,work/'rtl'):
        p.mkdir(parents=True)
    kd=work/'rtl'
    for p in (src/'leaf.sv',bind/'bind_cells.sv',kd/'wrapper.sv'):
        p.write_text('module '+p.stem+'; endmodule\n')
    files=[kd/'wrapper.sv',bind/'bind_cells.sv',src/'leaf.sv']
    (bind/'bind_report.json').write_text('{"errors":[]}')
    (kd/'kit_rtl.f').write_text('\n'.join(map(str,files))+'\n')
    (kd/'kit_rtl.json').write_text(json.dumps(dict(bind_out=str(bind),files=list(map(str,files)))))
    return src,bind,kd


def receipt(kd):
    meta=json.loads((kd/'kit_rtl.json').read_text())
    (kd/'kit_rtl_paths.json').write_text(json.dumps(dict(src_tree='unused',filelist=str(kd/'kit_rtl.f'),files=(kd/'kit_rtl.f').read_text().splitlines(),input_closure=meta['input_closure'])))


def test_packaged_dependency_survives_source_retirement_and_checks_content(tmp_path):
    src,bind,kd=vehicle(tmp_path)
    C.package(kd,src)
    receipt(kd)
    shutil.rmtree(src); shutil.rmtree(bind)
    assert L.kit_rtl_paths(kd)==([],True)
    meta=json.loads((kd/'kit_rtl.json').read_text())
    assert (Path(meta['bind_out'])/'bind_report.json').is_file()
    leaf=Path((kd/'kit_rtl.f').read_text().splitlines()[-1])
    leaf.write_text('stale mutation')
    assert 'content mismatch' in L.kit_rtl_paths(kd)[0][0]


def test_outside_source_is_rejected_before_packaging(tmp_path):
    src,bind,kd=vehicle(tmp_path)
    outside=tmp_path/'old_tree.sv';outside.write_text('module wrong;endmodule')
    with (kd/'kit_rtl.f').open('a') as f:f.write(str(outside)+'\n')
    with pytest.raises(ValueError,match='invalid source'):C.package(kd,src)
    assert not (kd/'kit_rtl.producer.json').exists()


def test_lexical_attempt_path_survives_changed_scratch_alias(tmp_path):
    src,bind,kd=vehicle(tmp_path)
    alias=tmp_path/'scratch_alias';alias.symlink_to(kd.parent,target_is_directory=True)
    C.package(alias/'rtl',src)
    assert all(str(alias) in x for x in (kd/'kit_rtl.f').read_text().splitlines())
    receipt(alias/'rtl')
    assert L.kit_rtl_paths(alias/'rtl')==([],True)


def test_copyback_rewrites_filelist_prefix_but_not_json(tmp_path):
    src,bind,kd=vehicle(tmp_path)
    C.package(kd,src)
    dest=tmp_path/'relocated'/'rtl'
    shutil.copytree(kd,dest)
    old_files=(kd/'kit_rtl.f').read_text().splitlines()
    new_files=[str(dest)+p[len(str(kd)):] for p in old_files]
    meta=json.loads((dest/'kit_rtl.json').read_text())
    (dest/'kit_rtl_paths.json').write_text(json.dumps(dict(
        src_tree=str(src),filelist=str(kd/'kit_rtl.f'),files=new_files,
        input_closure=meta['input_closure'])))
    shutil.rmtree(kd);shutil.rmtree(src);shutil.rmtree(bind)
    assert L.kit_rtl_paths(dest)==([],True)
    Path(new_files[-1]).write_text('wrong copied bytes')
    assert 'content mismatch' in L.kit_rtl_paths(dest)[0][0]


def test_native_preparation_before_seal_and_real_metadata_readers(tmp_path):
    import kit_topology as K
    import count_strap_evidence as E
    src,bind,kd=vehicle(tmp_path)
    bound=bind/'rtl'/'m_bound.sv';bound.parent.mkdir()
    bound.write_text('module m_bound(input clk,input rst_n);\nendmodule\n')
    paths=(kd/'kit_rtl.f').read_text().splitlines();paths[1]=str(bound)
    (kd/'kit_rtl.f').write_text('\n'.join(paths)+'\n')
    meta=json.loads((kd/'kit_rtl.json').read_text());meta.update(bound_module='m_bound',bound_type='t',instances=['part'],files=paths,bound_only_pins=[dict(port='strap',dir='input',width=2)])
    (kd/'kit_rtl.json').write_text(json.dumps(meta))
    raw={'partition_types':{'t':{'buses':[], 'internal_stations':[], 'count_straps':[dict(name='strap',width=2)]}}}
    (bind/'native_topology.json').write_text(json.dumps(K.native_contract(raw)))
    (bind/'bind_tie_audit.json').write_text(json.dumps(dict(verdict='PASS',rows=[['part','strap',"2'b10"]])))
    C.inputs(kd,src)
    # Original complete bind remains the verifier input until native preparation.
    m=json.loads((kd/'kit_rtl.json').read_text())
    assert m['bind_out']==str(bind)
    assert K.localize_bound(kd) is None
    assert L.kit_rtl_paths(kd)==([],False)  # no generated kit receipt yet
    local=kd/'m_bound.sv';local.write_text(local.read_text()+'// canonical native preparation\n')
    census=K.source_census({'partition_types':{'t':{'buses':[], 'internal_stations':[]}}},'t',kd)
    assert census['problems']==[]
    (kd/'kit_topology.json').write_text(json.dumps(census))
    (kd/'kit_topology_prepared.json').write_text(json.dumps(dict(source_sha256=census['source_sha256'])))
    C.seal(kd);receipt(kd)
    assert L.kit_rtl_paths(kd)==([],True)
    m=json.loads((kd/'kit_rtl.json').read_text())
    assert K.bind_matches(raw,'t',m['bind_out'])
    evidence=E.write_for_kit(kd,raw['partition_types']['t'],kd/'kit_rtl.json')
    assert evidence['parent_ties']=={'strap':{'part':"2'b10"}}
    bound_before=local.read_bytes()
    local.write_text('wrong later source')
    with pytest.raises(ValueError,match='receipt mismatch|changed without'):C.seal(kd)


def test_unverified_preparation_mutation_cannot_be_sealed(tmp_path):
    src,bind,kd=vehicle(tmp_path)
    C.inputs(kd,src)
    (kd/'wrapper.sv').write_text('arbitrary source change')
    with pytest.raises(ValueError,match='without canonical preparation'):C.seal(kd)


def test_runtime_relocation_updates_metadata_but_not_original_roots(tmp_path):
    src,bind,kd=vehicle(tmp_path)
    C.package(kd,src);receipt(kd)
    before=json.loads((kd/'kit_rtl.json').read_text())['input_closure']
    dest=tmp_path/'target_attempt'/'rtl';shutil.copytree(kd,dest)
    C.relocate(dest)
    after=json.loads((dest/'kit_rtl.json').read_text())['input_closure']
    assert after['roots']==before['roots'] and after['files']==before['files']
    assert after['runtime_directory']==str(dest)
    for p in (dest/'kit_rtl.f').read_text().splitlines():assert Path(p).is_relative_to(dest)
    # The generated lint receipt is relocated by the same actual-host step.
    gen=dest.parent/'gen'/'t';gen.mkdir(parents=True)
    old_receipt=json.loads((kd/'kit_rtl_paths.json').read_text())
    (gen/'kit_rtl_paths.json').write_text(json.dumps(old_receipt))
    # Simulate a fresh target copy before its actual-host relocate.
    meta=json.loads((dest/'kit_rtl.json').read_text());meta['input_closure']['runtime_directory']=str(kd);(dest/'kit_rtl.json').write_text(json.dumps(meta))
    C.relocate(dest)
    shutil.rmtree(kd);shutil.rmtree(src);shutil.rmtree(bind)
    assert L.kit_rtl_paths(gen)==([],True)


def test_actual_stage_shell_prefix_and_failure_guard(tmp_path):
    import subprocess
    from kit_wave import kit_rtl_closure_cmd
    src,bind,kd=vehicle(tmp_path)
    cmd=kit_rtl_closure_cmd(str(kd.parent),str(src),'inputs',chain=False,guard=True)+'printf STAGE_OK'
    result=subprocess.run(['bash','-c',cmd],text=True,capture_output=True)
    assert result.returncode==0,result.stderr
    assert result.stdout.endswith('STAGE_OK')
    result=subprocess.run(['bash','-c',kit_rtl_closure_cmd(str(kd.parent),str(src),'seal',chain=False)],text=True,capture_output=True)
    assert result.returncode==0,result.stderr
    # An unexpected unprepared source mutation prevents all later GEN work.
    (kd/'wrapper.sv').write_text('mutated after seal')
    cmd=kit_rtl_closure_cmd(str(kd.parent),str(src),'seal',chain=False,guard=True)+'printf BAD_GEN'
    result=subprocess.run(['bash','-c',cmd],text=True,capture_output=True)
    assert result.returncode and 'BAD_GEN' not in result.stdout


def test_bind_metadata_copy_is_hash_checked(tmp_path):
    src,bind,kd=vehicle(tmp_path)
    C.package(kd,src);receipt(kd)
    meta=json.loads((kd/'kit_rtl.json').read_text())
    p=Path(meta['bind_out'])/'bind_report.json'
    p.write_text('{"errors":["stale count"]}')
    assert any('metadata content mismatch' in e for e in L.kit_rtl_paths(kd)[0])


def test_die_wide_sinks_file_is_not_copied_into_the_attempt(tmp_path):
    src,bind,kd=vehicle(tmp_path)
    (bind/'bind_sinks.json').write_text('{"a": 1}')
    (bind/'bind_names.json').write_text('{}')
    C.package(kd,src)
    receipt(kd)
    out=kd/'closure'/'bind'
    assert not (out/'bind_sinks.json').exists() and (out/'bind_names.json').is_file()
    note=json.loads((out/'bind_sinks.omitted.json').read_text())
    assert note['original']==str(bind/'bind_sinks.json') and note['size']==8
    assert 'closure/bind/bind_sinks.json' not in json.loads((kd/'kit_rtl.json').read_text())['input_closure']['files']
    assert L.kit_rtl_paths(kd)==([],True)
