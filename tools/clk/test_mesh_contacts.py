"""Regular fixed conductor adapter physical contact and fail-closed regressions."""
import pytest
import mesh_contacts as M
import clock_routed as C
import explicit_clock_mesh as E


def specimen():
    # Actual first NW union mesh fork/leaf geometry, cropped physical vehicle.
    cells={'M0_0':dict(master=C.BUF_DEFAULT,x=316.224,y=132.57),
           'M0_1':dict(master=C.BUF_DEFAULT,x=316.224,y=407.16),
           'L_clk':dict(master='BUFx4f_ASAP7_75t_R',x=85.266,y=136.08)}
    geom=dict(core_geometry='contents_and_hard_cores',drivers=['M0_0','M0_1'],mesh_loads=['L_clk'],core_loads=[],
              drv_anchor={'M0_0':[257.04,135.],'M0_1':[257.04,405.]},
              tap_node={'L_clk':[85.472,136.08]},taps_on_v=[],vx=[257.04],
              hy=[136.08,403.92],x_span=[50.,350.],y_span=[100.,450.],W=8121.,H=4250.)
    params=dict(pg_pitch=4.32,row_h=.27,strap_layers={'h':'M8','v':'M9'})
    return dict(cells=cells,geom=geom),params


def test_actual_displaced_contacts_use_pg_gaps_and_native_buffer_input():
    p,m=specimen();w,c,r=M.adapt(p,m)
    for a,b in w['mesh_graph']['edges']:
        if a[0]==b[0]:
            assert a[1]==b[1] or a[2]==b[2]
            # Every top-layer conductor keeps the actual .672um PG stripe clear.
            normal=a[2] if a[0]=='M8' else a[1]
            assert min(normal%4.32,4.32-normal%4.32)>.336+.08
    assert r['actual_driver_contacts']==2 and r['buffer_input_contacts']==1
    assert not w['mesh_graph']['taps']
    lines,_=C.routed_tcl([w],c,{},C.BUF_DEFAULT,'CONTACT')
    assert '$e addITerm [IT L_clk A]' in lines
    assert not any('addBTerm' in line for line in lines)


def test_missing_native_hooks_cannot_be_turned_into_boundary_aliases():
    p,m=specimen();p['geom']['core_loads']=['K_native'];p['geom']['mesh_loads'].append('K_native')
    with pytest.raises(ValueError,match='native child clock hooks unimplemented'):
        M.adapt(p,m)
    w,_,record=M.adapt(p,m,allow_missing_native=True)
    assert record['missing_native_hooks']==['K_native']
    assert not record['release_qualified'] and not w['mesh_graph']['taps']
