from types import SimpleNamespace as N
from collections import defaultdict
from clock_landing_verify import Verification


def vehicle(mutant=None):
    cells=[];counter=iter(range(100,10000));drv=defaultdict(list)
    def cell(path,module,inputs,outs,ytype=None):
        ports={**inputs,**{p:[next(counter) for _ in range(n)] for p,n in outs.items()}}
        c=N(path=path,module=module,ports=ports,kind='glue' if ytype else 'leaf',ytype=ytype)
        cells.append(c)
        for p in outs:
            for bit,n in enumerate(ports[p]):drv[n].append((len(cells)-1,p,bit))
        return c
    def boolean(name,typ,a,b=None):return cell(name,typ,{'A':[a],**({'B':[b]} if b is not None else {})},{'Y':1},typ).ports['Y'][0]
    aclk,bclk,rst=1,2,3
    ar=cell('a.u_rst_in','ot_dp_rrelay',{'clk':[aclk],'d':[rst]},{'q':1}).ports['q'][0]
    br=cell('b.u_rst_in','ot_dp_rrelay',{'clk':[bclk],'d':[rst]},{'q':1}).ports['q'][0]
    bt=cell('b.u_rrl_0','ot_dp_rrelay',{'clk':[bclk],'d':[br]},{'q':1}).ports['q'][0]
    ring=cell('b.u_cland_y','ot_dp_clk_landing',{'clk':[bclk],'fclk':[aclk],'rst_n':[bt],'d':[8,9]},{'q':2,'ready':1,'fault':1})
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
    raw=dict(partitions=[dict(name='a',type='A',origin_um=[0,0]),dict(name='b',type='B',origin_um=[10,0])],partition_types=dict(A=dict(outline_um=[10,10]),B=dict(outline_um=[10,10])),ports=[dict(id='p',src=dict(part='a',bus='x'),dst=dict(part='b',bus='y'))])
    table=dict(ports=[dict(port='p',src='a',dst='b',width=1)],regions=[dict(tag='h0',parts=['a']),dict(tag='h1',parts=['b'])],collector=dict(root='a',types=dict(A=A,B=B),observer=dict(part='a',module=obs.module,instance_suffix='u_sys_face',fault_port='obs_fault',ready_port='seq_cfg_image_ready')))
    if mutant in ('count_regions','bad_region_count'):
        table['regions'][0].update(parts=2 if mutant=='bad_region_count' else 1,box_um=[0,0,10,10])
        table['regions'][1].update(parts=1,box_um=[10,0,20,10])
    if mutant=='unknown_region_schema':table['regions'][0]['parts']='1'
    F=N(cells=cells);G=N(drv=drv,top_in={aclk:('clk_region_h0',0),bclk:('clk_region_h1',0),rst:('rst_n',0)})
    v=Verification(F,G,raw,table,{})
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
