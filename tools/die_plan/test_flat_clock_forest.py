import copy
from pathlib import Path
from types import SimpleNamespace
import tempfile
import pytest
import flat_clock_forest as F


def fixture():
    t=dict(module='m',outline_um=[100,100])
    sink=dict(name='u/q',master='DFFHQNx1_ASAP7_75t_R',clock_pin='CLK',source_root='clk',xy_um=[52,50])
    p=dict(schema='opentallas.flat_clock_forest.v1',module='m',outline_um=[100,100],build_allowed=True,
        install_stage='post_place_pre_cts',input_slew_ps=80,wire_rc=dict(r_kohm_um=.0214161,c_ff_um=.113298),geometry_review='review.png; LOOK; actual legal cohort',
        model_source='native geometry + TT/FF NLDM + per-master spice_cell/g021; no measured timing',measured_timing_used=False,
        roots={'clk':dict(kind='primary',xy_um=[50,50],node='ot_flat_clk_0',qualification={c:dict(slew_max_ps=20,sink_latency_ps={'u/q':250}) for c in ['TT','FF']})},
        cells=[dict(name='ot_flat_clk_0',root='clk',parent='port:clk',master='BUFx24_ASAP7_75t_R',
            placement=dict(origin_um=[49.194,49.95],centre_um=[50.004,50.085],size_um=[1.62,.27],orient='R0'),sinks=[sink])],
        related_pair_model={c:{k:dict(max_ps=0,over80=0) for k in ['primary','same_forwarded']} for c in ['TT','FF']})
    return t,p


def test_explicit_tree_uses_native_primitives_without_pin_or_data_edits():
    t,p=fixture();text=F.emit(t,p)
    assert 'ot_ci_tree_begin "clk"' in text
    assert 'ot_ci_tree_sink "ot_flat_clk_0" "u/q/CLK"' in text
    assert 'ot_flat_native_guard' in text and 'ot_flat_graph_guard' in text
    assert 'place_pin' not in text and 'ot_ci_clock_entry' not in text
    assert text.index('ot_flat_native_guard')<text.index('ot_ci_cell')


@pytest.mark.parametrize('mutation',[
    lambda p:p.update(build_allowed=False),
    lambda p:p.update(install_stage='pre_gpl'),
    lambda p:p['cells'][0].update(parent='ot_flat_clk_0'),
    lambda p:p['cells'][0].update(master='BUFx2_ASAP7_75t_R'),
    lambda p:p['cells'][0]['sinks'][0].update(source_root='fclk_other'),
    lambda p:p['cells'][0]['sinks'].append(copy.deepcopy(p['cells'][0]['sinks'][0])),
    lambda p:p['cells'][0]['placement'].update(origin_um=[-1,0]),
    lambda p:p['roots']['clk']['qualification']['FF'].update(slew_max_ps=81),
    lambda p:p['roots']['clk']['qualification']['TT'].update(sink_latency_ps={}),
    lambda p:p['related_pair_model']['FF']['primary'].update(max_ps=81),
])
def test_fail_closed_ownership_model_and_footprint(mutation):
    t,p=fixture();mutation(p)
    with pytest.raises(ValueError):F.emit(t,p)


def test_forwarded_cannot_be_stolen_by_primary():
    t,p=fixture();p['roots']['fclk_in_i[0]']=copy.deepcopy(p['roots']['clk']);p['roots']['fclk_in_i[0]']['kind']='forwarded'
    p['cells'][0]['sinks'][0]['source_root']='fclk_in_i[0]'
    with pytest.raises(ValueError,match='primary root stealing'):F.validate(t,p)


def test_absent_optin_is_byte_unchanged():
    with tempfile.TemporaryDirectory() as td:
        k=Path(td);(k/'pre_cts.tcl').write_text('original')
        assert not F.install(SimpleNamespace(types={'t':dict(module='m')}),'t',k)
        assert (k/'pre_cts.tcl').read_text()=='original'
        assert len(list(k.iterdir()))==1


def graph_fixture():
    """Independent tiny OpenDB-shaped graph for exact-leaf negative controls."""
    import tkinter
    tc=tkinter.Tcl()
    objects={
        'B':{'findBTerm':{'clk':'BT'},'findInst':{'ot_flat_clk_0':'I0','ot_flat_clk_1':'I1','ot_flat_clk_2':'I2','q0':'Q0','q1':'Q1'}},
        'T':{'getDbUnitsPerMicron':1000},'BT':{'getIoType':'INPUT','getBBox':'BP','getNet':'R'},
        'BP':{'xMin':50000,'xMax':50000,'yMin':50000,'yMax':50000},
        'M':{'getName':'BUFx24_ASAP7_75t_R'},'MF':{'getName':'DFFHQNx1_ASAP7_75t_R'},
        'MA':{'getIoType':'INPUT','getName':'A'},'MY':{'getIoType':'OUTPUT','getName':'Y'},'MC':{'getIoType':'INPUT','getName':'CLK'},
    }
    for j in range(3):
        objects[f'I{j}']={'getName':f'ot_flat_clk_{j}','getMaster':'M','isDoNotTouch':1,'getLocation':[49000+j*2000,50000],
                            'getOrient':'R0','findITerm':{'A':f'A{j}','Y':f'Y{j}'}}
        objects[f'A{j}']={'getInst':f'I{j}','getMTerm':'MA','getNet':'R' if j==0 else 'N0'}
        objects[f'Y{j}']={'getInst':f'I{j}','getMTerm':'MY','getNet':f'N{j}'}
    for j in range(2):
        objects[f'Q{j}']={'getName':f'q{j}','getMaster':'MF','getBBox':f'QB{j}','findITerm':{'CLK':f'C{j}'}}
        objects[f'QB{j}']={'xMin':53000+j*1000,'xMax':53000+j*1000,'yMin':51000+j*1000,'yMax':51000+j*1000}
        objects[f'C{j}']={'getInst':f'Q{j}','getMTerm':'MC','getNet':f'N{j+1}'}
    for net,terms in {'R':['A0'],'N0':['Y0','A1','A2'],'N1':['Y1','C0'],'N2':['Y2','C1']}.items():
        objects[net]={'getITerms':terms,'getSigType':'CLOCK','isDoNotTouch':1}
    def flat(value):
        if isinstance(value,dict):return tc.call('dict','create',*[x for k,v in value.items() for x in [k,flat(v)]])
        if isinstance(value,list):return tc.call('list',*value)
        return value
    tc.setvar('objects',flat(objects))
    tc.eval('''namespace eval ord {}
proc ord::get_db_block {} {return B}
proc ord::get_db_tech {} {return T}
proc dispatch {obj method args} {
 set result [dict get $::objects $obj $method]
 if {[llength $args]} {return [dict get $result [lindex $args 0]]}
 return $result
}
''')
    for obj in objects:tc.eval(f'interp alias {{}} {obj} {{}} dispatch {obj}')
    tc.setvar('ot_flat_roots',flat({'clk':['primary','ot_flat_clk_0',50,50]}))
    tc.setvar('ot_flat_cells',flat({f'ot_flat_clk_{j}':['BUFx24_ASAP7_75t_R','port:clk' if j==0 else 'ot_flat_clk_0','clk',49+2*j,50,49.81+2*j,50.135,'R0',1.62,.27] for j in range(3)}))
    tc.setvar('ot_flat_sinks',flat({f'q{j}':['clk','clk','DFFHQNx1_ASAP7_75t_R','CLK',53+j,51+j,f'ot_flat_clk_{j+1}'] for j in range(2)}))
    tc.call('source',str(Path(F.__file__).with_name('flat_clock_forest_guard.tcl')))
    tc.eval('proc all_clocks {} {return C}; proc get_property {obj prop} {return SRC}; proc get_full_name {obj} {return clk}')
    return tc


def test_native_graph_and_same_root_leaf_swap_control():
    import tkinter
    t=graph_fixture();t.call('ot_flat_graph_guard')
    t.eval('dict set ::objects C0 getNet N2')
    with pytest.raises(tkinter.TclError,match='exact sink leaf changed'):t.call('ot_flat_graph_guard')


def test_native_graph_clock_driver_edit_control():
    import tkinter
    t=graph_fixture();t.eval('dict set ::objects N1 getITerms {Y1 C0 Y2}')
    with pytest.raises(tkinter.TclError,match='clock driver edited'):t.call('ot_flat_graph_guard')


def test_install_keeps_frozen_pins_and_replaces_only_known_clock_method(monkeypatch):
    import json
    import gen_phys
    t,p=fixture()
    with tempfile.TemporaryDirectory() as td:
        d=Path(td);k=d/'kit';k.mkdir();(d/'forest.json').write_text(json.dumps(p));t['flat_clock_forest_file']='forest.json'
        (k/'pre_cts.tcl').write_text('source /work/clock_taps.tcl\n')
        (k/'cts_post.tcl').write_text(Path(F.__file__).with_name('cts_post.tcl').read_text())
        (k/'landing_exports.tcl').write_text('# native declared export')
        (k/'setRC_rcx.tcl').write_text('set_wire_rc -clock -resistance .0214161 -capacitance .113298\n')
        P=SimpleNamespace(types={'t':t},path=d/'plan.json')
        monkeypatch.setattr(gen_phys,'clock_pins',lambda *_:[('clk',50,50)])
        assert F.install(P,'t',k)
        pre=(k/'pre_cts.tcl').read_text()
        apply=(k/'flat_clock_forest_apply.tcl').read_text()
        assert apply.index('ot_flat_input_nets')<apply.index('source /work/landing_exports.tcl')<apply.index('ot_ci_tree_begin')
        assert 'place_pin' not in (k/'flat_clock_forest_apply.tcl').read_text()
        assert 'TritonCTS not run' in (k/'core_infra_cts.tcl').read_text()
        assert 'ot_flat_graph_guard' in (k/'cts_post.tcl').read_text()


def test_legalizer_uses_actual_occupied_rows_without_moving_cells():
    tech=dict(dbu=1000,core=[0,0,10000,10000],
              rows=[dict(rect=[0,y,10000,y+270],site=54,orient='R0') for y in range(0,10000,270)],
              masters={'BUFx8_ASAP7_75t_R':[648,270]},
              obstacles=[dict(name='movable_native_logic',kind='placed',rect=[4000,5130,6000,5400])])
    candidate=dict(nodes=[dict(name=f'ot_flat_clk_{j}',master='BUFx8_ASAP7_75t_R',xy=[5,5.265]) for j in range(2)])
    before=copy.deepcopy(tech)
    placed,report=F.legalize_drivers(candidate,tech)
    assert tech==before and report['max_displacement_um']<=2
    for p in placed.values():
        x,y=p['origin_um'];w,h=p['size_um']
        assert not (x<6-1e-9 and 4<x+w-1e-9 and y<5.4-1e-9 and 5.13<y+h-1e-9)
    assert placed['ot_flat_clk_0']['origin_um']!=placed['ot_flat_clk_1']['origin_um']
    tech['obstacles']=[dict(name='full',kind='placed',rect=[0,0,10000,10000])]
    with pytest.raises(ValueError,match='no empty legal clock site'):F.legalize_drivers(candidate,tech)
