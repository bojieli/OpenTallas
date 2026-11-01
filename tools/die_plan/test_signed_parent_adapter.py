"""Actual-readset refusal and native-gold separation for opt-in parent PREP."""
import json
from pathlib import Path
import sys
from types import SimpleNamespace
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parent))
import signed_parent_adapter as A


def native_leaf(tmp_path):
    kit = tmp_path / 'leaf_kit'
    (kit / 'views').mkdir(parents=True)
    (kit / 'signoff').mkdir()
    (kit / 'lec').mkdir()
    pins = [dict(bus='clk', bit=None), dict(bus='q', bit=None)]
    (kit / 'pins.json').write_text(json.dumps(pins))
    (kit / 'core.json').write_text(json.dumps(dict(module='child', port_decl={'clk':['input',0,0], 'q':['output',0,0]})))
    (kit / 'views/child.lef').write_text('MACRO child\n SIZE 2 BY 2 ;\n PIN clk\n DIRECTION INPUT ;\n END clk\n PIN q\n DIRECTION OUTPUT ;\n END q\nEND child\n')
    for c in ('tt','ff'):
        (kit / f'views/child_{c}.lib').write_text('library(child) { cell(child) { pin(clk) { direction : input; clock : true; } pin(q) {direction : output;} } }')
    so = dict(verdict='SIGNED', policy=dict(period_ps=833), checks=dict(clock=dict(by_corner={
        c:dict(pinflops=dict(n=1, mean=m, min=m, max=m)) for c,m in [('tt',100),('ff',80)]})))
    (kit / 'signoff/signoff.json').write_text(json.dumps(so))
    (kit / 'lec/lec.json').write_text(json.dumps(dict(verdict='EQUIVALENT', top='child', netlist='/work/base/6_final.v', black_boxes={})))
    return kit


def test_native_export_keeps_signed_means_and_refuses_unsigned(tmp_path):
    kit = native_leaf(tmp_path)
    out = tmp_path / 'child'
    result = A.export_native_view(kit, out, 'child')
    assert result['tt_insertion_ps'] == 100 and result['ff_insertion_ps'] == 80
    assert result['pins'] == 2
    so = json.loads((kit / 'signoff/signoff.json').read_text());so['verdict']='NOT_SIGNED'
    (kit / 'signoff/signoff.json').write_text(json.dumps(so))
    with pytest.raises(ValueError,match='actual SIGNED'):
        A.export_native_view(kit,tmp_path/'bad','child')
    assert not (tmp_path/'bad').exists()


def test_actual_flattened_duplicate_master_is_not_hidden_by_basename(tmp_path):
    a = tmp_path/'a';b=tmp_path/'b';a.mkdir();b.mkdir()
    for p,w in [(a/'child.lef',2),(b/'child.lef',3)]:p.write_text(f'MACRO child\n SIZE {w} BY 2 ;\nEND child\n')
    readset=tmp_path/'actual_parent_lefs.f'
    readset.write_text(f'{a}/child.lef\n{b}/child.lef\n')
    with pytest.raises(ValueError,match='duplicate actual flattened master child'):
        A.master_census(readset,{'child':a/'child.lef'})
    readset.write_text(f'{a}/child.lef\n{a}/child.lef\n')
    assert len(A.master_census(readset,{'child':a/'child.lef'})['masters'])==1
    with pytest.raises(ValueError,match='missing actual flattened LEF readset'):
        A.master_census(None,{})


def test_default_off_and_missing_native_producer(tmp_path):
    assert A.prepare_generated_type(SimpleNamespace(types={'t':{}}),'t',tmp_path,[]) is None
    assert not list(tmp_path.iterdir())
    with pytest.raises(ValueError,match='native parent KIT producer'):
        A.formal_inputs({})


def test_generated_backend_preserves_native_gold_and_existing_clock_rows(tmp_path):
    kit = native_leaf(tmp_path)
    view = tmp_path/'child'
    A.export_native_view(kit,view,'child')
    kd=tmp_path/'parent';(kd/'rtl').mkdir(parents=True)
    source=kd/'rtl/parent.sv'
    text='module child(input clk,output q);assign q=clk;endmodule\nmodule top(input clk,output q);child u_c(.clk(clk),.q(q));endmodule\n'
    source.write_text(text)
    config='export DESIGN_NAME = top\nexport VERILOG_FILES = /work/rtl/parent.sv\n'
    (kd/'config.mk').write_text(config)
    rows=[dict(inst='u_c',pin='clk',tap='actual_parent_tap',signed=True,corners={c:dict(mean_ps=m) for c,m in [('tt',100),('ff',80)]})]
    rows.append(dict(inst='u_other',pin='clk',rise_ps=123,tap='grid',signed=False,basis='legacy_etm_max_bound'))
    (kd/'core_latency.json').write_text(json.dumps(dict(rows=rows)))
    clock_before=(kd/'core_latency.json').read_bytes()
    typ=dict(module='top',outline_um=[10,10],signed_parent_source=dict(views={str(view):str(view)}),hard_cores=[dict(inst='u_c',module='child')])
    p=SimpleNamespace(types={'t':typ},die=dict(period_ps=833))
    ledger=A.prepare_generated_type(p,'t',kd,[('u_c','child',str(view/'child.lef'),str(view/'child_tt.lib'),1,1,'R0')])
    assert source.read_text()==text and (kd/'config.mk').read_text()==config
    assert (kd/'core_latency.json').read_bytes()==clock_before
    physical=(kd/'signed_parent/physical_rtl/parent.sv').read_text()
    assert 'module child' not in physical and 'module top' in physical
    assert 'actual_parent_tap' in (kd/'signed_parent/contract/core_latency.txt').read_text()
    assert 'native-parent EQ' in ledger['status']
    assert ledger['complete_parent_ff_table'] is False
    merged=json.loads((kd/'signed_parent/physical_core_latency.json').read_text())['rows']
    assert merged[0]['signed'] is True and merged[1]==rows[1]
    assert not (kd/'signed_parent/physical_core_latency_ff.txt').exists()
    assert 'SYNTH_BLACKBOXES = child' in (kd/'signed_parent/physical_config.mk').read_text()


def test_formal_materializer_requires_both_actual_readsets_and_expands_gate(tmp_path):
    kit=native_leaf(tmp_path);view=tmp_path/'child';A.export_native_view(kit,view,'child')
    parent=tmp_path/'native_parent';(parent/'rtl').mkdir(parents=True);(parent/'macros').mkdir()
    source=parent/'rtl/native.sv'
    source.write_text('module child(input clk,output q);assign q=clk;endmodule\nmodule top(input clk,output q);child u_c(.clk(clk),.q(q));endmodule\n')
    (parent/'config.mk').write_text('export DESIGN_NAME = top\nexport VERILOG_FILES = /work/rtl/native.sv\nexport ADDITIONAL_LIBS = /work/macros/child_tt.lib\n')
    (parent/'macros/child_tt.lib').write_bytes((view/'child_tt.lib').read_bytes())
    gate=tmp_path/'mapped_parent.v';gate.write_text('module top(input clk,output q);child u_c(.clk(clk),.q(q));endmodule\n')
    child=tmp_path/'6_final.v';child.write_text('module child(input clk,output q);assign q=clk;endmodule\n')
    packet=dict(module='child',parameters={},added_cycles=0,leaf_release_qualified=True,
                canonical_source_sha256={'rtl/native.sv':A.digest(source)},
                backing_artifact_sha256={'base/6_final.v':A.digest(child),'lec/lec.json':A.digest(view/'lec_post.json')},
                views={f'views/child/child{x}':A.digest(view/f'child{x}') for x in ('.lef','_tt.lib','_ff.lib')})
    qp=tmp_path/'qualified.json';qp.write_text(json.dumps(packet))
    parent_f=tmp_path/'actual_parent_lefs.f';parent_f.write_text(str(view/'child.lef')+'\n')
    desc=dict(native_kit=str(parent),parent_gate_netlist=str(gate),parent_lef_readset=str(parent_f),
              children=[dict(view_signoff=str(view/'signoff.json'),qualified_packet=str(qp),final_netlist=str(child))])
    with pytest.raises(ValueError,match='missing actual flattened LEF readset'):
        A.materialize_formal(desc,tmp_path/'missing')
    assert not (tmp_path/'missing').exists()
    die_f=tmp_path/'actual_die_lefs.f';die_f.write_text(str(view/'child.lef')+'\n');desc['die_lef_readset']=str(die_f)
    out=tmp_path/'formal';r=A.materialize_formal(desc,out)
    assert 'NOT RUN' in r['status']
    assert (out/'native_gold/native.sv').read_bytes()==source.read_bytes()
    assert 'module child' in (out/'expanded_parent_gate.v').read_text()
    assert '/work/native_gold/native.sv' in (out/'config.mk').read_text()
    assert 'child_tt.lib' not in (out/'config.mk').read_text()
    child.write_text(child.read_text()+'\n// altered netlist\n')
    with pytest.raises(ValueError,match='differs from qualified actual final netlist'):
        A.materialize_formal(desc,tmp_path/'mutated')


def test_private_plan_optin_schema_is_accepted_and_narrow():
    import jsonschema
    import schema
    prop=schema.SCHEMA['properties']['partition_types']['additionalProperties']['properties']['signed_parent_source']
    jsonschema.validate({'views':{'declared/view':'qualified/view'}},prop)
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate({'views':{},'activate':True},prop)
