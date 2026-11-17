"""Actual graph cuts: preserve glue/top ABI, selected models, and refuse clock merging."""
import copy
import json
import sys
from pathlib import Path
import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[1]))
import hr_parent as P
import core_pins_hr as C


def fixture(tmp_path):
    ports = {n: dict(direction=d, bits=[b]) for n,d,b in [
        ('ck','input',2),('payload','input',3),('observed','output',5),
        ('static_setup_ready','input',6),('boot_image_ready','output',7)]}
    leaf = dict(attributes={}, parameter_default_values={},
                ports={n: dict(direction=d,bits=[b]) for n,d,b in [('ck','input',2),('d','input',3),('q','output',4)]},
                cells={}, netnames={})
    cell = lambda d,q: dict(type='leaf', parameters={}, attributes={},
                           port_directions=dict(ck='input',d='input',q='output'),
                           connections=dict(ck=[2],d=[d],q=[q]))
    top = dict(attributes=dict(top='1'), parameter_default_values=dict(NL='00000010'), ports=ports,
               cells=dict(a=cell(3,4),b=cell(6,7), invert=dict(type='$not', parameters=dict(A_WIDTH='1',Y_WIDTH='1',A_SIGNED='0'),
                   attributes={},port_directions=dict(A='input',Y='output'),connections=dict(A=[4],Y=[5]))), netnames={})
    path=tmp_path/'host.json';path.write_text(json.dumps(dict(modules=dict(current_host=top,leaf=leaf))))
    host=C.Host(path)
    records={}
    for m in ('ca','cb'):
        src=tmp_path/(m+'.sv');src.write_text(f'module {m}(input ck,d,output q); assign q=d;endmodule\n')
        p=tmp_path/(m+'.json');p.write_text(json.dumps(dict(module=m,files=[str(src)],port_decl={n:[d,0,0] for n,d in [('ck','input'),('d','input'),('q','output')]},port_holes={})));records[m]=str(p)
    return host,[dict(inst='host__ca',module='ca'),dict(inst='host__cb',module='cb')],{'host__ca':{'a':'a'},'host__cb':{'b':'b'}},records


def test_grouped_reference_keeps_real_boot_abi_and_glue(tmp_path):
    host,hcs,mem,rec=fixture(tmp_path)
    r=P.emit(host,hcs,mem,rec,{'ck':'clk'},{'clk':'ck'},tmp_path/'out','grouped',repo_root=tmp_path)
    j=json.loads(Path(r['parent_json']).read_text())['modules']['grouped']
    assert set(j['ports'])==set(host.J[host.top]['ports'])
    assert j['parameter_default_values']==dict(NL='00000010')
    assert set(j['cells'])=={'host__ca','host__cb','hr_glue_0'}
    assert j['cells']['hr_glue_0']['type']=='$not'
    # A real source-output inversion remains between child q and observed port.
    assert j['cells']['host__ca']['connections']['q']==j['cells']['hr_glue_0']['connections']['A']
    assert j['ports']['observed']['bits']==j['cells']['hr_glue_0']['connections']['Y']
    assert j['ports']['static_setup_ready']['bits']==j['cells']['host__cb']['connections']['d']
    assert j['ports']['boot_image_ready']['bits']==j['cells']['host__cb']['connections']['q']
    assert r['grouping_reference_equivalence']['status']=='PASS'
    assert r['selected_function_equivalent_to_reference'] is True
    assert 'fixed-shape parameter NL' in (tmp_path/'out/parameter_guards.sv').read_text()
    # The final guard artifact is generated only after a real parent source exists.
    import subprocess
    Path(r['parent_sv']).write_text('module grouped #(parameter NL=2)(input ck); endmodule\n')
    subprocess.run([sys.executable,str(tmp_path/'out/guard_parent.py')],check=True)
    guard=json.loads((tmp_path/'out/host_guard.json').read_text())
    assert guard['verdict']=='PASS' and guard['guarded_parent_sha256']


def test_selected_whole_provider_and_contract_are_separate(tmp_path):
    host,hcs,mem,rec=fixture(tmp_path)
    selected=json.loads(Path(rec['ca']).read_text());selected['files']=['selected.sv']
    (tmp_path/'selected.sv').write_text('module ca(input ck,d,output q); assign q=~d;endmodule\n')
    (tmp_path/'selected.json').write_text(json.dumps(selected))
    r=P.emit(host,hcs,mem,rec,{'ck':'clk'},{'clk':'ck'},tmp_path/'out','grouped',
             {'ca':dict(core_json='selected.json',added_data_edges=1)},repo_root=tmp_path)
    assert r['selected_function_equivalent_to_reference'] is False
    assert r['groups'][0]['contract']['added_data_edges']==1
    assert str(tmp_path/'selected.sv') in (tmp_path/'out/selected.f').read_text()
    assert str(tmp_path/'selected.sv') not in (tmp_path/'out/reference.f').read_text()


def test_selected_abi_mutant_is_refused(tmp_path):
    host,hcs,mem,rec=fixture(tmp_path)
    mutant=json.loads(Path(rec['ca']).read_text());mutant['port_decl']['d'][1]=1
    (tmp_path/'mutant.json').write_text(json.dumps(mutant))
    with pytest.raises(P.ParentError,match='changes the current core ABI'):
        P.emit(host,hcs,mem,rec,{'ck':'clk'},{'clk':'ck'},tmp_path/'out','grouped',{'ca':dict(core_json='mutant.json')},repo_root=tmp_path)


def test_distinct_phy_clocks_are_never_tied(tmp_path):
    host,hcs,mem,rec=fixture(tmp_path)
    top=host.J['current_host'];top['ports']['other_phy']=dict(direction='input',bits=[8]);top['cells']['b']['connections']['ck']=[8]
    hcs=[dict(inst='host__both',module='both')];mem={'host__both':{'a':'a','b':'b'}}
    p=tmp_path/'both.json';p.write_text(json.dumps(dict(module='both',files=[],port_decl=dict(ck_phy=['input',0,0],a__d=['input',0,0],a__q=['output',0,0],b__d=['input',0,0],b__q=['output',0,0]),port_holes={})))
    with pytest.raises(P.ParentError,match='separate clock domains cannot be collapsed'):
        P.emit(host,hcs,mem,{'both':str(p)},{'ck':'clk_clk_phy','other_phy':'clk_clk_phy'}, {'clk_clk_phy':'ck_phy'},tmp_path/'out','grouped',repo_root=tmp_path)


def test_real_unused_replica_output_and_literal_source_input(tmp_path):
    host,hcs,mem,rec=fixture(tmp_path)
    host.J['current_host']['ports'].pop('boot_image_ready')
    host.J['current_host']['cells']['b']['connections']['d']=['1']
    r=P.emit(host,hcs,mem,rec,{'ck':'clk'},{'clk':'ck'},tmp_path/'out','grouped',repo_root=tmp_path)
    j=json.loads(Path(r['parent_json']).read_text())['modules']['grouped']
    assert j['cells']['host__cb']['connections']['q']==[]
    assert j['cells']['host__cb']['connections']['d']==['1']
    assert r['reference_unused_outputs'][0]['pin']=='q'
    assert r['actual_source_constant_inputs']==[dict(inst='host__cb',pin='d',index=0,value='1')]


def test_nonmember_native_queue_memory_is_preserved(tmp_path):
    host,hcs,mem,rec=fixture(tmp_path)
    top=host.J['current_host']
    declaration=dict(hide_name=0,attributes={},width=8,start_offset=0,size=4)
    top['memories']={'queue':declaration}
    top['cells']['write_queue']=dict(type='$memwr_v2',parameters=dict(MEMID='\\queue',WIDTH='1000'),
        attributes={},port_directions=dict(ADDR='input',DATA='input',EN='input',CLK='input'),
        connections=dict(ADDR=[3,6],DATA=[3]*8,EN=[6]*8,CLK=[2]))
    top['cells']['read_queue']=dict(type='$memrd',parameters=dict(MEMID='\\queue',WIDTH='1000'),
        attributes={},port_directions=dict(ADDR='input',DATA='output'),connections=dict(ADDR=[3,6],DATA=list(range(20,28))))
    r=P.emit(host,hcs,mem,rec,{'ck':'clk'},{'clk':'ck'},tmp_path/'out','grouped',repo_root=tmp_path)
    j=json.loads(Path(r['parent_json']).read_text())['modules']['grouped']
    assert j['memories']=={'hr_mem_0':declaration}
    memory_cells=[c for c in j['cells'].values() if c['type'].startswith('$mem')]
    assert len(memory_cells)==2 and {c['parameters']['MEMID'] for c in memory_cells}=={'\\hr_mem_0'}
    assert r['grouping_reference_equivalence']['complete_glue_memories']==1


def test_glue_initialization_and_keep_intent_are_preserved(tmp_path):
    host,hcs,mem,rec=fixture(tmp_path)
    host.J['current_host']['netnames']['boot_state']=dict(hide_name=0,bits=[5],attributes=dict(init='0',keep='1',async_reg='1'))
    r=P.emit(host,hcs,mem,rec,{'ck':'clk'},{'clk':'ck'},tmp_path/'out','grouped',repo_root=tmp_path)
    j=json.loads(Path(r['parent_json']).read_text())['modules']['grouped']
    nets=[n for n in j['netnames'].values() if n.get('attributes',{}).get('keep')]
    assert len(nets)==1 and nets[0]['attributes']==dict(init='0',keep='1',async_reg='1')
    assert nets[0]['bits']==j['ports']['observed']['bits']
    assert r['glue_initialized_bits']==1
    assert '-noattr' not in (tmp_path/'out/write_parent.ys').read_text()
