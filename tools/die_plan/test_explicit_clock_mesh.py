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
    assert n['wide_merge_um']<=2.0
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


def test_jog_y_track_runs_m8_to_m9_strap_and_reports_stub():
    """HEAD-R23: a tap with a PG-aware jog track jogs on M8 at that y to the nearest M9 strap."""
    m=mesh();m['taps']=[dict(xy=[3.,4.2],jog_y=5.)];m['tap_jog_um']=4.
    t=E.conductor_graph(m)['taps'][0]
    assert t['anchor']==['M9',0.,5.] and t['port_node']==['M8',3.,5.]
    assert t['jog_um']==3. and t['stub_um']==0.8
    m['tap_jog_um']=2.
    with pytest.raises(ValueError,match='no M9 strap'): E.conductor_graph(m)


def test_jog_y_on_m8_strap_attaches_without_jog():
    m=mesh();m['taps']=[dict(xy=[7.,0.9],jog_y=0.)];m['tap_jog_um']=4.
    g=E.conductor_graph(m);t=g['taps'][0]
    assert t['anchor']==t['port_node']==['M8',7.,0.] and t['jog_um']==0.
