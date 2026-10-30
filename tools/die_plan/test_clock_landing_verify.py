from types import SimpleNamespace as N
from collections import defaultdict
from clock_landing_verify import Verification


def vehicle(mutant=None,reset_tree=None):
    cells=[];counter=iter(range(100,10000));drv=defaultdict(list)
    def cell(path,module,inputs,outs,ytype=None):
        ports={**inputs,**{p:[next(counter) for _ in range(n)] for p,n in outs.items()}}
        c=N(path=path,module=module,ports=ports,kind='glue' if ytype else 'leaf',ytype=ytype,params={'K':-1 if path=='b2.u_cland_y2' else -2,'DEPTH':4})
        cells.append(c)
        for p in outs:
            for bit,n in enumerate(ports[p]):drv[n].append((len(cells)-1,p,bit))
        return c
    def boolean(name,typ,a,b=None):return cell(name,typ,{'A':[a],**({'B':[b]} if b is not None else {})},{'Y':1},typ).ports['Y'][0]
    aclk,bclk,rst=1,2,3
    ar=cell('a.u_rst_in','ot_dp_rrelay',{'clk':[aclk],'d':[rst]},{'q':1}).ports['q'][0]
    br=cell('b.u_rst_in','ot_dp_rrelay',{'clk':[bclk],'d':[rst]},{'q':1}).ports['q'][0]
    bt=cell('b.u_rrl_0','ot_dp_rrelay',{'clk':[bclk],'d':[br]},{'q':1}).ports['q'][0]
    if mutant and mutant.startswith('ca'):
        # MESO-INTEG-1 count-aligned form: root origin in a, child origin in b on the tree bus y, CA ring
        at=cell('a.u_rrl_0','ot_dp_rrelay',{'clk':[aclk],'d':[ar]},{'q':1}).ports['q'][0]
        ao=cell('a.u_cland_origin','ot_dp_landing_root',{'clk':[aclk],'rst_raw_n':[at if mutant!='ca_root_reset' else ar]},{'start':1}).ports['start'][0]
        bo=cell('b.u_cland_origin','ot_dp_landing_origin',{'clk':[bclk],'rst_raw_n':[bt],'p_start':[ao if mutant!='ca_pstart' else bt]},{'start':1}).ports['start'][0]
        ring=cell('b.u_cland_y','ot_dp_clk_landing_ca' if mutant!='ca_oldring' else 'ot_dp_clk_landing',
                  {'clk':[bclk],'fclk':[aclk],'t_rst_n':[ao],'rst_n':[bo if mutant!='ca_ring_raw' else bt],'d':[8,9]},{'q':2,'ready':1,'fault':1})
    else:
        ring=cell('b.u_cland_y','ot_dp_clk_landing',{'clk':[bclk],'fclk':[aclk],'rst_n':[bt],'d':[8,9]},{'q':2,'ready':1,'fault':1})
    if mutant and mutant.startswith('car'):
        # DIE-KV-3/CAORIGIN: b2 shares region h1 with b (origin, tree port p); b2's start is relayed b -> b2
        b2r=cell('b2.u_rst_in','ot_dp_rrelay',{'clk':[bclk],'d':[rst]},{'q':1}).ports['q'][0]
        b2t=cell('b2.u_rrl_0','ot_dp_rrelay',{'clk':[bclk],'d':[b2r]},{'q':1}).ports['q'][0]
        tx=cell('b.u_cland_rstart_tx','ot_dp_landing_relay',{'clk':[bclk],'rst_raw_n':[bt],'d':[bo]},{'q':1}).ports['q'][0]
        rx=cell('b2.u_cland_rstart_rx','ot_dp_landing_relay',{'clk':[bclk],'rst_raw_n':[b2t],'d':[tx if mutant!='car_skip_tx' else bo]},{'q':1}).ports['q'][0]
        cell('b2.u_cland_y2','ot_dp_clk_landing_ca',{'clk':[bclk],'fclk':[aclk],'t_rst_n':[ao],'rst_n':[rx if mutant!='car_ring_origin' else bo],'d':[10,11]},{'q':2,'ready':1,'fault':1})
    if mutant=='fclk':ring.ports['fclk']=[bclk]
    if mutant=='reset_depth':ring.ports['rst_n']=[br]
    bc=cell('b.u_cland_collect_rst_n_t0','ot_dp_landing_collect',{'clk':[bclk],'rst_n':[bt],'ready_i':ring.ports['ready'],'fault_i':ring.ports['fault']},{'ready_o':1,'fault_o':1})
    bu=cell('b.u_cland_collect_rst_root_n','ot_dp_landing_collect',{'clk':[bclk],'rst_n':[br],'ready_i':bc.ports['ready_o'],'fault_i':bc.ports['fault_o']},{'ready_o':1,'fault_o':1})
    mr=cell('a.u_cland_monitor_0','ot_dp_clk_landing',{'clk':[aclk],'fclk':[bclk],'rst_n':[ar],'d':bu.ports['ready_o']+bu.ports['fault_o']},{'q':2,'ready':1,'fault':1})
    r=boolean('a.and0','$logic_and',mr.ports['q'][0],mr.ports['ready'][0]);nf=boolean('a.not0','$logic_not',mr.ports['fault'][0]);r=boolean('a.and1','$logic_and',r,nf)
    f=boolean('a.or0','$logic_or',mr.ports['q'][1],mr.ports['fault'][0])
    au=cell('a.u_cland_collect_rst_root_n','ot_dp_landing_collect',{'clk':[aclk],'rst_n':[ar],'ready_i':[r],'fault_i':[f]},{'ready_o':1,'fault_o':1})
    if mutant=='status':au.ports['ready_i']=[f]
    ogf=boolean('a.obs_or','$or',8,au.ports['fault_o'][0]);ogr=boolean('a.obs_and','$and' if mutant!='observer' else '$or',9,au.ports['ready_o'][0])
    obs=cell('a.u_sys_face','qfd_sys_face_lctx3_wrapped',{'obs_fault':[ogf],'seq_cfg_image_ready':[ogr]}, {})
    if mutant=='extra':cell('b.u_cland_unpriced','ot_dp_clk_landing',{}, {'q':1})
    tree=dict(root=[0,0],sync_stages=2,relays=[dict(name='u_rrl_0',q='rst_n_t0',d='rst_root_n',xy=[1,0])])
    A=dict(mask=dict(active=True),tree=tree,collector_root_node='rst_root_n',local_sources=[],children=[dict(part='b',node='rst_root_n',index=0,seam=True)])
    B=dict(mask=dict(active=True),tree=tree,collector_root_node='rst_root_n',local_sources=[dict(name='y',tap=0)],children=[])
    if mutant=='representative_child':A['children'][0]['part']='representative_only'
    if mutant=='different_status_tap':
        bt1=cell('b.u_rrl_1','ot_dp_rrelay',{'clk':[bclk],'d':[br]},{'q':1}).ports['q'][0]
        tree['relays'].append(dict(name='u_rrl_1',q='rst_n_t1',d='rst_root_n',xy=[2,0]))
        B['local_sources'][0]['tap']=1;bc.path='b.u_cland_collect_rst_n_t1';bc.ports['rst_n']=[bt1]
    raw=dict(partitions=[dict(name='a',type='A',origin_um=[0,0]),dict(name='b',type='B',origin_um=[10,0])],partition_types=dict(A=dict(outline_um=[10,10]),B=dict(outline_um=[10,10],buses=[dict(name='y',face='W',window_um=[0,2])])),ports=[dict(id='p',src=dict(part='a',bus='x'),dst=dict(part='b',bus='y'))])
    table=dict(ports=[dict(port='p',src='a',dst='b',width=1)],regions=[dict(tag='h0',parts=['a']),dict(tag='h1',parts=['b'])],collector=dict(root='a',edges=[dict(src='b',dst='a',dst_index=0,seam=True)],types=dict(A=A,B=B),observer=dict(part='a',module=obs.module,instance_suffix='u_sys_face',fault_port='obs_fault',ready_port='seq_cfg_image_ready')))
    if mutant and mutant.startswith('ca'):
        table['count_aligned']=dict(root='h0',ports={'p':dict(K=-2,depth=4,sched_lat=2,tree=True)},
                                    regions={'h0':dict(parent=None,tree_port=None,edge_fall=False,pad=0),
                                             'h1':dict(parent='h0',tree_port='p',edge_fall=False,pad=0)})
    if mutant and mutant.startswith('car'):
        raw['partitions'].append(dict(name='b2',type='B2',origin_um=[10,10]))
        raw['partition_types']['B2']=dict(outline_um=[10,10],buses=[dict(name='y2',face='W',window_um=[0,2])])
        raw['ports'].append(dict(id='p2',src=dict(part='a',bus='x2'),dst=dict(part='b2',bus='y2')))
        table['ports'].append(dict(port='p2',src='a',dst='b2',width=1))
        table['regions'][1]['parts']=['b','b2']
        table['collector']['types']['B2']=dict(mask=dict(active=False),tree=tree,local_sources=[dict(name='y2',tap=0)],children=[])
        if mutant.startswith('car_inactive'):
            # TOK-QC-4: the relay partition's type is an inactive landing type (collector tree None, QC slw_hc3)
            table['collector']['types']['B2']['tree']=None
        ca=table['count_aligned'];ca['ports']['p2']=dict(K=-1,depth=4,sched_lat=3,tree=False)
        ca['regions']['h0']['origin_part']='a';ca['regions']['h1']['origin_part']='b'
        if mutant!='car_no_parts':
            ca['parts']=dict(a=dict(region='h0',role='origin',src=None,stages=0),b=dict(region='h1',role='origin',src=None,stages=0),
                             b2=dict(region='h1',role='relay',src='b',stages=2))
    if mutant=='ca_wrong_count':ring.params['K']=-1
    if mutant=='ca_wrong_depth':ring.params['DEPTH']=8
    if mutant=='wrong_child':table['collector']['edges'][0]['src']='a'
    if mutant in ('count_regions','bad_region_count'):
        table['regions'][0].update(parts=2 if mutant=='bad_region_count' else 1,box_um=[0,0,10,10])
        table['regions'][1].update(parts=1,box_um=[10,0,20,10])
    if mutant=='unknown_region_schema':table['regions'][0]['parts']='1'
    if mutant and mutant.startswith('cast'):
        # DIE-HEAD-11 START-TREE compose slice: h1's start arrives on a start port (dedicated pin), not on crossing p
        ca=table['count_aligned'];ca['ports']['p']['tree']=False
        oc=next(c for c in cells if c.path=='b.u_cland_origin')
        src='st:h' if mutant.startswith('cast_stage') else 'h0'
        ca['regions']['h1'].update(parent=src,tree_port=f'start:{src}->h1')
        ca['start_ports']={f'start:{src}->h1':dict(src=src,dst='h1',src_part=None if src=='st:h' else 'a',dst_part='b')}
        if mutant in ('cast_stage','cast_stage_wrong'):
            ca['regions']['st:h']=dict(parent='h0',tree_port='start:h0->st:h',edge_fall=False,pad=0)
            ca['start_ports']['start:h0->st:h']=dict(src='h0',dst='st:h',src_part='a',dst_part=None)
            oc.ports['p_start']=[77]        # die-top start-stage port pst_h1
        if mutant=='cast_pstart':oc.ports['p_start']=[bt]
        if mutant=='cast_stage_wrong':oc.ports['p_start']=[ao]
    if mutant and mutant.startswith('outcopy'):
        # DIE-S81-27 wavefront out: rst_n_t0 is the tap of out relay u_rrl_0 (n_reset_consumers 0, one out);
        # u_rrl_0 drives rst_o_0, the tap net is driven by the same-d copy u_rrl_0_t
        if mutant!='outcopy_not_out':tree.update(n_reset_consumers=0,outs=[[1,0]])
        btc=next(c for c in cells if c.path=='b.u_rrl_0');btc.path='b.u_rrl_0_t'
        if mutant=='outcopy_wrong_d':btc.ports['d']=[rst]
    F=N(cells=cells);G=N(drv=drv,top_in={aclk:('clk_region_h0',0),bclk:('clk_region_h1',0),rst:('rst_n',0),77:('pst_h1',0)})
    live=None
    if mutant in ('spare_capacity','epoch_truncated','spare_epoch_truncated'):
        live={'p':1}
        if mutant!='epoch_truncated':
            table['ports'][0]['width']=8;raw['ports'][0]['width']=8
        if mutant!='spare_capacity':ring.ports['d']=ring.ports['d'][:-1];ring.ports['q']=ring.ports['q'][:-1]
    v=Verification(F,G,raw,table,{},live_widths=live,reset_tree=reset_tree)
    for port in obs.ports:v.observer_input(obs,port,0)
    return v.report()


def test_actual_landed_status_graph():assert vehicle()['errors']==[]


def test_wrong_source_clock_fails():assert any('fclk' in s for s in vehicle('fclk')['errors'])


def test_wrong_raw_reset_depth_fails():assert any('reset-parent/depth' in s for s in vehicle('reset_depth')['errors'])


def test_fault_as_ready_fails():assert any('ready_i' in s for s in vehicle('status')['errors'])


def test_wrong_real_observer_gate_fails():assert any('observer' in s for s in vehicle('observer')['errors'])


def test_unpriced_extra_ring_fails():assert any('unpriced' in s for s in vehicle('extra')['errors'])


def test_actual_count_regions_keep_exact_graph_checks():assert vehicle('count_regions')['errors']==[]

def test_region_count_mismatch_fails_closed():
    import pytest
    with pytest.raises(ValueError,match='actual parts'):vehicle('bad_region_count')


def test_unknown_region_parts_schema_fails_closed():
    import pytest
    with pytest.raises(ValueError,match='count or explicit list'):vehicle('unknown_region_schema')


def test_live_epoch_is_not_optional():assert any('payload/epoch' in x for x in vehicle('epoch_truncated')['errors'])

def test_allocated_spare_capacity_uses_authoritative_live_width():assert vehicle('spare_capacity')['errors']==[]

def test_spare_capacity_cannot_hide_truncated_epoch():assert any('payload/epoch' in x for x in vehicle('spare_epoch_truncated')['errors'])


def test_replica_child_uses_exact_top_edge():assert vehicle('representative_child')['errors']==[]


def test_ring_and_status_can_use_distinct_declared_taps():assert vehicle('different_status_tap')['errors']==[]

def test_wrong_child_edge_fails_actual_status_and_clock_checks():assert vehicle('wrong_child')['errors']


def test_count_aligned_ring_and_start_tree_verified():assert vehicle('ca')['errors']==[]


def test_count_aligned_mutants_fail():
    for m,frag in (('ca_pstart','p_start'),('ca_ring_raw','u_cland_y.rst_n'),('ca_oldring','expected ot_dp_clk_landing_ca'),
                   ('ca_root_reset','reset')):
        errs=vehicle(m)['errors']
        assert any(frag in e for e in errs),(m,errs)


def test_count_aligned_intra_region_relay_verified():assert vehicle('car')['errors']==[]


def test_count_aligned_relay_mutants_fail():
    for m,frag in (('car_skip_tx','u_cland_rstart_rx.d'),('car_ring_origin','u_cland_y2.rst_n'),
                   ('car_no_parts','one landed partition required')):
        errs=vehicle(m)['errors']
        assert any(frag in e for e in errs),(m,errs)


def test_start_tree_start_port_origin_verified():
    assert vehicle('cast')['errors']==[] and vehicle('cast_stage')['errors']==[]


def test_start_tree_start_port_mutants_fail():
    assert any('p_start' in e for e in vehicle('cast_pstart')['errors'])
    assert any('p_start' in e for e in vehicle('cast_stage_wrong')['errors'])   # stage parent: pst port only


def _plan_tree(tn):
    return dict(root=[0,0],sync_stages=2,relays=[dict(name='u_rrl_0',q='rst_n_t0',d='rst_root_n',xy=[1,0])])


def test_relay_rx_in_inactive_type_uses_plan_reset_tree():
    """TOK-QC-4: a start relay rx in a type whose collector tree is None is checked on the type's plan reset tree."""
    assert vehicle('car_inactive',reset_tree=_plan_tree)['errors']==[]


def test_relay_rx_in_inactive_type_fails_closed():
    # no plan tree -> FAIL (not skip, not crash)
    errs=vehicle('car_inactive',reset_tree=lambda tn:None)['errors']
    assert any('no planned reset tree for type B2' in e for e in errs),errs
    def boom(tn):raise KeyError(tn)
    errs=vehicle('car_inactive',reset_tree=boom)['errors']
    assert any('plan reset tree unavailable' in e for e in errs) and any('no planned reset tree' in e for e in errs),errs
    # MUTANT: a plan tree whose rst_n_t0 relay name differs from the bound relay -> the rx raw reset contract fails
    bad=lambda tn:dict(root=[0,0],sync_stages=2,relays=[dict(name='u_rrl_9',q='rst_n_t0',d='rst_root_n',xy=[1,0])])
    errs=vehicle('car_inactive',reset_tree=bad)['errors']
    assert any('b2.u_cland_rstart_rx' in e and 'reset-parent/depth' in e for e in errs),errs


def test_count_aligned_actual_count_and_depth_are_checked():
    assert any(' K differs' in e for e in vehicle('ca_wrong_count')['errors'])
    assert any('DEPTH differs' in e for e in vehicle('ca_wrong_depth')['errors'])


def test_shared_type_depth_is_the_maximum_of_all_used_instances():
    from clock_landing_verify import planned_ring_depths
    raw=dict(partitions=[dict(name='a',type='T'),dict(name='b',type='T')],ports=[dict(id='p',dst=dict(bus='x')),dict(id='q',dst=dict(bus='x'))])
    table=dict(ports=[dict(port='p',dst='a'),dict(port='q',dst='b')],count_aligned=dict(ports={'p':dict(depth=4),'q':dict(depth=8)}))
    assert planned_ring_depths(raw,table)=={('T','x'):8}


def test_out_relay_tap_copy_is_the_planned_hop():
    """DIE-S81-32/BIND (S81 verify256: 444 CLOCK_LANDING errors): at a wavefront out tap the tap net is driven by
    <relay>_t (reset_tree 68e405472), same d and depth as the planned out relay; the raw reset contract accepts it."""
    assert vehicle('outcopy')['errors']==[]


def test_out_relay_tap_copy_mutants_fail():
    # a _t name at a tap that is not an out-relay tap, or a _t copy with the wrong parent -> FAIL
    assert any('b.u_cland_y' in e and 'reset-parent/depth' in e for e in vehicle('outcopy_not_out')['errors'])
    assert any('b.u_cland_y' in e and 'reset-parent/depth' in e for e in vehicle('outcopy_wrong_d')['errors'])
