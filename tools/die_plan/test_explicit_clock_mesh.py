"""Physical continuous mesh inventory and multi-driver aliasing regressions."""
import copy
import pytest
import explicit_clock_mesh as E


def mesh():
    return dict(ndr='8w',M8=[dict(y=0.,x0=0.,x1=20.),dict(y=10.,x0=0.,x1=20.)],
                M9=[dict(x=0.,y0=0.,y1=10.),dict(x=20.,y0=0.,y1=10.)],
                vias=[dict(x=x,y=y) for x in (0.,20.) for y in (0.,10.)],
                drivers=[dict(group='g1',xy=[0.,0.]),dict(group='g2',xy=[20.,10.])],
                taps=[dict(xy=[10.,0.],part='p')])


def test_continuous_graph_preserves_all_cycle_edges_and_vias():
    g=E.conductor_graph(mesh())
    assert g['vias']==4 and g['connected_components']==1
    assert len(g['edges'])==len(g['nodes']) # exactly one cycle, no missing chord
    assert len(g['drivers'])==2


def test_crossing_via_inventory_fails_closed():
    m=mesh();m['vias'].append(dict(x=0.,y=0.))
    with pytest.raises(ValueError,match='VIA89 inventory'): E.conductor_graph(m)
    m=mesh();m['vias'].pop()
    with pytest.raises(ValueError,match='VIA89 inventory'): E.conductor_graph(m)


def test_tap_jog_is_metal_and_port_does_not_move():
    m=mesh();m['taps']=[dict(xy=[10.,3.])];m['tap_jog_um']=4.
    g=E.conductor_graph(m)
    t=g['taps'][0]
    assert t['anchor']==['M8',10.,0.]
    assert t['port_node']==['M9',10.,3.]
    assert g['vias']==5
    assert [['M9',10.,0.],['M9',10.,3.]] in g['edges']


def test_attach_joins_all_driver_units_and_removes_fake_leaf_stubs():
    cells={'a':dict(group=1,kind='node'),'b':dict(group=2,kind='node')}
    nets=[dict(name='l1',drv='a',loads=['port:t1']),dict(name='l2',drv='b',loads=['port:t2'])]
    out=dict(taps=[dict(port='t1'),dict(port='t2')],fixed_wires=[dict(name='l1'),dict(name='l2')],meta={})
    c,n,p,o=E.attach_mesh(dict(mesh=mesh()),cells,nets,[('output','t1'),('output','t2')],out)
    assert len(n)==1 and n[0]['drv_units']==['a','b']
    assert n[0]['port_aliases']==['msh_t_0']
    assert p==[('output','msh_t_0')]
    assert o['fixed_wires'][0]['explicit_mesh']
    assert o['meta']['explicit_mesh']['driver_units']==2


def test_attach_rejects_omitted_mesh_driver():
    m=mesh();m['drivers'].pop()
    cells={'a':dict(group=1,kind='node'),'b':dict(group=2,kind='node')}
    nets=[dict(name='l1',drv='a',loads=['port:t1']),dict(name='l2',drv='b',loads=['port:t2'])]
    with pytest.raises(ValueError,match='omits tree leaves'):
        E.attach_mesh(dict(mesh=m),cells,nets,[],dict(taps=[],fixed_wires=[],meta={}))


def test_clock_netlist_keeps_multiple_mesh_boundary_aliases(tmp_path):
    import die_clock_mesh as D
    cells={k:dict(group=i,kind='node') for i,k in enumerate(('a','b'))}
    nets=[dict(name='root',drv='port:root',loads=['a','b']),
          dict(name='ck_mesh_explicit',drv='a',drv_units=['a','b'],loads=['port:t0','port:t1'],
               port_aliases=['t0','t1'])]
    p=tmp_path/'mesh.v'
    ren=D.write_verilog(cells,nets,[('input','root'),('output','t0'),('output','t1')],p)
    text=p.read_text()
    assert 'ck_mesh_explicit' not in ren
    assert 'assign t0 = ck_mesh_explicit;' in text and 'assign t1 = ck_mesh_explicit;' in text
    assert text.count('.Y(ck_mesh_explicit)')==2


def test_wide_band_ndr_obeys_asap7_spacing_and_via_enclosure():
    import die_clock_mesh as D
    n=D.NDR['2x16w'];v=n['via89']
    assert n['width']==1.28 and n['space']==1.0
    assert n['wide_merge_um']<1.805
    assert (v['cols']-1)*v['pitch']+v['cut']+2*v['enc_m9']<=n['width']


def test_native_mesh_rc_keeps_all_drivers_and_boundary_ports():
    import die_clock as DC
    m=mesh();g=E.conductor_graph(m)
    cells={'a':dict(x=0.,y=0.,group=1,kind='node'),
           'b':dict(x=20.,y=10.,group=2,kind='node')}
    for d,u in zip(g['drivers'],('a','b')):d['units']=[u]
    for i,t in enumerate(g['taps']):t['port']='tap'+str(i)
    w=dict(name='ck_mesh_explicit',ndr='8w',mesh_graph=g)
    s=E.mesh_spef_section(w,cells,'BUFx24_ASAP7_75t_R',DC.LAYER_RC,DC.VIA_KOHM)
    assert '*I a:Y O' in s and '*I b:Y O' in s and '*P tap0 O' in s
    assert s.count('*D_NET ')==1 and s.count('*END')==1


def test_rcx_width_inventory_includes_all_pieces_and_mesh():
    import clock_routed as C
    M=dict(meta=dict(ndr='16w'),fixed_wires=[dict(pieces=[dict(ndr='4w'),dict(ndr='2x16w')]),
                                         dict(ndr='8w',explicit_mesh=True)])
    assert C.actual_ndr_widths(M)==[.16,.32,1.28]


def test_mixed_shield_census_uses_wide_segment_actual_spacing_class():
    wires=[dict(name='narrow',ndr='4w',segs=[('M8',0.,0.,10.,0.)],clock_topology_version=2),
           dict(name='wide',ndr='2x16w',segs=[('M8',0.,3.5,10.,3.5)],clock_topology_version=2)]
    stripes,ties,census=E.mixed_shield_analysis(wires,[],'VSS')
    assert len(stripes)==4 and ties['stripes']==4
    assert census['spacing']>0
    assert any(r['required_space_um']==1.0 for r in census['rows'])
    assert ties['untied'] # no PG grid was supplied; it cannot qualify shield continuity


def test_mixed_rcx_tables_must_cover_every_actual_width():
    import clock_routed as C
    def rules(widths):
        return '\n'.join(f'Metal {lay} RESOVER\nWIDTH Table {len(widths)} entries: '+ ' '.join(map(str,widths))+'\n'
                         for lay in (8,9))
    actual=[.16,.32,.64,1.28]
    old=C.rules_width_inventory_check(rules([.04,.64]),actual)
    assert not old['ok'] and old['selected_widths_um'][8]['0.16']==.04
    assert old['selected_widths_um'][9]['1.28']==.64
    assert C.rules_width_inventory_check(rules([.04]+actual),actual)['ok']


def test_mesh_reserved_before_tree_with_physical_vss_shields():
    shapes=E.mesh_reservation_shapes(mesh())
    assert any(s[1]=='ck_mesh_explicit' and s[2]=='mesh' for s in shapes)
    assert any(s[1]=='VSS' and s[2]=='pg' for s in shapes)
    # All mesh metal keeps its real 0.32um width; no global16w substitution.
    assert all(abs(s[4]-s[3]-.32)<1e-6 for s in shapes)


def test_declared_entry_terminal_has_actual_stack_and_keeps_location():
    m=mesh();m['taps']=[dict(xy=[10.,3.],terminal_layer='M4')];m['tap_jog_um']=4.
    g=E.conductor_graph(m)
    assert g['taps'][0]['port_node']==['M4',10.,3.]
    assert g['vias']==10  # four crossings, one jog turn, five M9..M4 cuts
    edges={tuple(map(tuple,e)) for e in g['edges']}
    for k in range(4,9):
        assert tuple(sorted((('M'+str(k),10.,3.),('M'+str(k+1),10.,3.)))) in edges
    with pytest.raises(ValueError,match='terminal layer'):
        m['taps'][0]['terminal_layer']='M2';E.conductor_graph(m)


def test_declared_m9_entry_can_rise_from_m8_branch():
    m=mesh();m['taps']=[dict(xy=[3.,5.],terminal_layer='M9')];m['tap_jog_um']=4.
    g=E.conductor_graph(m)
    assert g['taps'][0]['port_node']==['M9',3.,5.]
    assert g['vias']==6


def test_terminal_access_descends_in_gap_then_draws_true_m5_pin_escape():
    import clock_routed as C
    m=mesh();m['taps']=[dict(xy=[3.,7.852],terminal_access_xy=[3.,10.],terminal_layer='M5')]
    g=E.conductor_graph(m);t=g['taps'][0]
    assert t['port_node']==['M5',3.,7.852] and t['anchor']==['M8',3.,10.]
    edges={tuple(map(tuple,e)) for e in g['edges']}
    assert tuple(sorted((('M5',3.,7.852),('M5',3.,10.)))) in edges
    assert all(a[1:]==(3.,10.) for e in edges for a in e if a[0] in ('M6','M7'))
    for d in g['drivers']:d['units']=[]
    w=dict(name='ck_mesh_explicit',ndr='8w',mesh_graph=g)
    sh=E.access_shapes(w,{},'BUFx24_ASAP7_75t_R')
    assert any(l=='M5' and abs(x0-2.988)<1e-6 and abs(y0-7.84)<1e-6 and abs(y1-10.012)<1e-6 for _,l,x0,y0,x1,y1 in sh)
    assert not any(l=='M8' and y0<7.852<y1 for _,l,x0,y0,x1,y1 in sh)


def test_terminal_access_rejects_diagonal_long_or_upper_layer_escape():
    m=mesh();m['taps']=[dict(xy=[3.,3.],terminal_access_xy=[4.,5.],terminal_layer='M5')]
    with pytest.raises(ValueError,match='Manhattan'):E.conductor_graph(m)
    m['taps'][0].update(terminal_access_xy=[3.,6.])
    with pytest.raises(ValueError,match='local reach'):E.conductor_graph(m)
    m['taps'][0].update(terminal_access_xy=[3.,5.],terminal_layer='M9')
    with pytest.raises(ValueError,match='lower-metal'):E.conductor_graph(m)


def test_lower_terminal_escape_not_shielded_as_top_metal_and_native_rc_kept():
    import die_clock as DC
    import die_clock_mesh as D
    m=mesh();m['taps']=[dict(xy=[3.,7.852],terminal_access_xy=[3.,10.],terminal_layer='M5')]
    cells={'a':dict(x=0.,y=0.,group=1,kind='node'),'b':dict(x=20.,y=10.,group=2,kind='node')}
    nets=[dict(name='l1',drv='a',loads=['port:t1']),dict(name='l2',drv='b',loads=['port:t2'])]
    _,_,_,out=E.attach_mesh(dict(mesh=m),cells,nets,[],dict(taps=[],fixed_wires=[],meta={}))
    w=out['fixed_wires'][0]
    assert all(s[0] in ('M8','M9') for s in w['segs'])
    assert w['terminal_wire_um']==pytest.approx(2.148)
    rc=dict(DC.LAYER_RC);rc['M5']=(10.,2.)
    with pytest.raises(ValueError,match='missing declared layer coefficients'):
        E.mesh_spef_section(w,cells,D.BUF,rc,DC.VIA_KOHM)
    via=dict(DC.VIA_KOHM,M5=.0634,M6=.0752,M7=.0834)
    text=E.mesh_spef_section(w,cells,D.BUF,rc,via)
    # The M5 wire is21.48 kOhm at this controlled layer-RC value, without
    # incorrectly scaling by8w's rf=.125.
    assert '21.480000000' in text


def test_terminal_rc_basis_is_explicit_measured_file_and_retains_top_rc():
    import die_clock as DC
    w=dict(terminal_rc_tcl='tools/die_plan/setRC_rcx_asap7.tcl')
    rc,via=E.terminal_rc_basis(w,DC.LAYER_RC,DC.VIA_KOHM,{'M5'},{'M5','M6','M7','M8'})
    assert rc['M5']==pytest.approx((.0189935,.098))
    assert rc['M8']==DC.LAYER_RC['M8']
    assert via['M5']==pytest.approx(.0634) and via['M6']==pytest.approx(.0752) and via['M7']==pytest.approx(.0834)
    assert len(w['terminal_rc_basis']['sha256'])==64
    with pytest.raises(ValueError,match='repository-relative'):
        E.terminal_rc_basis(dict(terminal_rc_tcl='/tmp/no.tcl'),{}, {},{'M5'},set())
    with pytest.raises(ValueError,match='missing:'):
        E.terminal_rc_basis(dict(terminal_rc_tcl='missing.tcl'),{}, {},{'M5'},set())
