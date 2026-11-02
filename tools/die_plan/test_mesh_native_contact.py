"""Geometry and real input contracts only; physical routing is a later view gate."""
from types import SimpleNamespace as NS
import copy
import pytest
import mesh_native_contact as N
import explicit_clock_mesh as E
import clock_routed as C


def fixture(tmp_path, orient='R0'):
    libraries={}
    for corner in ['TT','FF']:
        p=tmp_path/(corner+'.lib');p.write_text('library(test) {cell(native) {pin(clk) {direction: input; clock: true;}}}')
        libraries[corner]=p
    layer=NS(getName=lambda:'M5',getRoutingLevel=lambda:5)
    shape=NS(getTechLayer=lambda:layer,xMin=lambda:107952,yMin=lambda:94800,xMax=lambda:108000,yMax=lambda:95280)
    term=NS(getName=lambda:'clk',getIoType=lambda:'INPUT',getMPins=lambda:[NS(getGeometry=lambda:[shape])])
    master=NS(getName=lambda:'native',getWidth=lambda:218592,getHeight=lambda:187488)
    inst=NS(getName=lambda:'native_tail',getMaster=lambda:master,getOrigin=lambda:(950400,5512320),getOrient=lambda:orient)
    it=NS(getInst=lambda:inst,getMTerm=lambda:term,getNet=lambda:NS(getName=lambda:'mesh'))
    contract=dict(master='native',clock_pins=['clk'],outline_um=[218.592,187.488],
                  source_identity='exact-current-component',scope='free-interface component source',
                  pin_contract_identity='exact-current-pin-profile',
                  clock_pin_rects_um={'clk':[107.952,94.8,108.,95.28]})
    return it,libraries,contract


def contact(tmp_path):
    it,libs,contract=fixture(tmp_path);d=N.descriptor(it,libs,contract)
    d.update(anchor=['M8',1056.24,5605.2],pg=dict(pitch_um=4.32,origin_um=[0.,0.],
             width_um={'M8':.672,'M9':.672},wire_width_um=.16,spacing_um=.08))
    return d


def test_actual_m5_clock_under_both_pg_axes_escapes_above_native_obstructions(tmp_path):
    d=contact(tmp_path);assert d['xy']==pytest.approx([1058.376,5607.36])
    path=N.access_path(d)
    assert path[-1]==('M5',1058.376,5607.36)
    assert {p[0]for p in path}=={'M5','M6','M7','M8','M9'}
    assert all(a[1]==b[1]or a[2]==b[2]for a,b in zip(path,path[1:])if a[0]==b[0])
    for layer,x,y in path:
        if layer in ('M8','M9'):
            v=y if layer=='M8'else x
            assert min(v%4.32,4.32-v%4.32)>.496-1e-8
    assert all(d['rect'][0]<=x<=d['rect'][2]and d['rect'][1]<=y<=d['rect'][3]
               for layer,x,y in path if layer=='M5')


def test_declared_clock_name_or_lef_use_cannot_replace_actual_typed_clock_source(tmp_path):
    it,libs,contract=fixture(tmp_path)
    bad=dict(contract,source_identity='')
    with pytest.raises(ValueError,match='source contract'):N.descriptor(it,libs,bad)
    libs['FF'].write_text('library(test) {cell(native) {pin(clk) {direction: input; clock: false;}}}')
    with pytest.raises(ValueError,match='FF:.*clock:true'):N.descriptor(it,libs,contract)


def test_native_source_outline_and_pg_anchor_fail_closed(tmp_path):
    it,libs,contract=fixture(tmp_path)
    with pytest.raises(ValueError,match='outline differs'):
        N.descriptor(it,libs,dict(contract,outline_um=[112.32,103.68]))
    d=contact(tmp_path);d['anchor']=['M9',1058.4,5605.2]
    with pytest.raises(ValueError,match='PG spacing'):N.access_path(d)


def test_regular_mesh_connects_actual_native_iterm_and_rejects_synthetic_native_rc(tmp_path):
    d=contact(tmp_path);a=d['anchor'];b=['M8',1060.56,5605.2]
    graph=dict(edges=[[a,b]],vias=0,drivers=[],cell_loads=[],taps=[],native_inputs=[d])
    w=dict(name='mesh',ndr='4w',mesh_graph=graph);lines=[];rec={}
    E.routed_mesh_tcl(lines,w,{}, {},C.BUF_DEFAULT,rec)
    text='\n'.join(lines)
    assert '$e addITerm [IT {native_tail} {clk}]' in text
    assert 'addBTerm' not in text and 'native_shape_found' in text
    assert rec['native_pin_stairs']==1 and E.access_paths(w,{},C.BUF_DEFAULT)[0][-1][0]=='M5'
    with pytest.raises(ValueError,match='actual extracted SPEF'):
        E.mesh_spef_section(w,{},C.BUF_DEFAULT,{}, {})


def test_emitter_rejects_invented_pin_point_and_missing_actual_source_libs(tmp_path):
    d=contact(tmp_path)
    bad=copy.deepcopy(d);bad['xy'][0]+=4.32
    with pytest.raises(ValueError,match='actual transformed pin metal'):
        N.validate_descriptor(bad)
    del d['libraries']
    with pytest.raises(ValueError,match='actual typed clock'):
        N.validate_descriptor(d)


def test_same_source_master_outline_does_not_alias_distinct_native_pin_profiles(tmp_path):
    it,libs,contract=fixture(tmp_path)
    # Current VMS profiles differ by .336 um despite the same RTL/master/outline.
    wrong=copy.deepcopy(contract)
    wrong['clock_pin_rects_um']['clk']=[108.288,94.8,108.336,95.28]
    with pytest.raises(ValueError,match='differs from current source/plan pin profile'):
        N.descriptor(it,libs,wrong)
    d=contact(tmp_path);d['source_contract']=wrong
    with pytest.raises(ValueError,match='differs from current source/plan pin profile'):
        N.validate_descriptor(d)
    del contract['pin_contract_identity']
    with pytest.raises(ValueError,match='explicit current source/plan pin-profile contract'):
        N.descriptor(it,libs,contract)
