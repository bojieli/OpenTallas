"""Materialize reviewed native SPB banks against actual scoped bound wrappers.

This is a source integration diagnostic. Whole-die binding, final atomic plan,
kit GEN/RT and physical signoff remain separate gates.
"""
import hashlib,importlib.util,json,sys
from pathlib import Path
root=Path(__file__).resolve().parents[2]
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def dump(p,v):p.write_text(json.dumps(v,indent=1)+'\n')
def run(planfile,sourcefile,rawdir,placementfile,out):
 planfile,sourcefile,rawdir,placementfile,out=map(Path,(planfile,sourcefile,rawdir,placementfile,out))
 if out.exists():raise ValueError('preserve existing materialization')
 P=json.loads(planfile.read_text());S=json.loads(sourcefile.read_text());R=json.loads((rawdir/'contract.json').read_text());place=json.loads(placementfile.read_text())
 assert S['schema']=='opentallas.hbm.selected_source_part_graph.v1'
 parts=['NW_spb0','NE_spb0'];cells=S['cells'];edges=[]
 for part in parts:
  cs={c['plan_instance']:c for c in cells if c['partition']==part}
  assert set(cs)=={'u_lk_S0','u_ep_S0'}
  for src,sp,dst,dp,w in [('u_ep_S0','sd_tx','u_lk_S0','tx',512),('u_lk_S0','rx','u_ep_S0','sd_rx',512),('u_lk_S0','st','u_ep_S0','sd_st',2)]:
   a,b=cs[src]['ports'][sp],cs[dst]['ports'][dp]
   assert a['width']==b['width']==w and a['bits']==b['bits'],(part,sp,dp,'not direct identity bits')
   assert len(b['sources'])==w
   for bit,d in enumerate(b['sources']):
    assert (d['kind'],d['path'],d['port'],d['bit'],d['stages'])==('pin',cs[src]['path'],sp,bit,0),d
   edges.append(dict(src_partition=part,dst_partition=part,src_plan_instance=src,src_port=sp,dst_plan_instance=dst,dst_port=dp,width=w,bit_pairs=[[i,i]for i in range(w)]))
 for typ in ['q_spb0','q_spb0__physical_v1']:
  t=P['partition_types'][typ];hc={c['inst']:c for c in t['hard_cores']}
  assert t['outline_um']==[1745.28,1503.36]
  assert hc['u_lk_S0']['module']=='ot_pdie_serdes' and hc['u_lk_S0']['origin_um']==[103.68,34.56] and hc['u_lk_S0']['outline_um']==[600.048,600.48]
  assert hc['u_ep_S0']['module']=='hfd_ep_static' and hc['u_ep_S0']['origin_um']==[181.44,1088.64] and hc['u_ep_S0']['outline_um']==[241.92,397.44]
  assert [40.04,0.,767.368,1113.64] in t['clock']['keepouts_um']
 out.mkdir(parents=True)
 graph=dict(schema='opentallas.hbm.spb0_actual_graph.v1',source_json=S['source_json'],source_packet_sha256=sha(sourcefile),manifest=S['manifest'],partitions=parts,cells=[{k:c[k]for k in ['path','module','partition','plan_instance','params']}for c in cells],edges=edges)
 dump(out/'actual_graph.json',graph)
 place['rebased_from']=dict(plan_sha256=place['plan_sha256'],actual_graph_sha256=place['actual_graph_sha256'],placement_sha256=sha(placementfile),physical_frame_unchanged=True)
 place['plan_sha256']=sha(planfile);place['actual_graph_sha256']=sha(out/'actual_graph.json');dump(out/'placement.json',place)
 C=dict(schema='opentallas.hbm.spb0_contract.v2',partitions=parts,plan_sha256=sha(planfile),placement_file='placement.json',prior_station_realization='NONE',rx_depth=4,tx_depth=4,lk_instance='u_lk_S0',ep_instance='u_ep_S0',lk_bound_instance='u_u_lk_S0',ep_bound_instance='u_u_ep_S0',lk_module='ot_pdie_serdes',ep_module='hfd_ep_static',lk_clock_port='clk',ep_clock_port='clk',lk_reset_port='rst',ep_reset_port='rst_n',clock_expression='clk',reset_expression='rst_n_t20',lk_reset_expression='rst_n',ep_reset_expression='rst_n_t20',reset_policy='RX_CAPTURE_EP_CONTROL_ONLY',actual_bound_contract_sha256=sha(rawdir/'contract.json'))
 for rec in R['parts']:
  actual={c['plan_instance']:c for c in rec['cores']}
  for ident,bound,resetport,resetexpr in [('u_lk_S0','u_u_lk_S0','rst','rst_n'),('u_ep_S0','u_u_ep_S0','rst_n','rst_n_t20')]:
   a=actual[ident];assert a['emitted_instance']==bound
   for port,expr,desc in [('clk','clk',['clk','stream']),(resetport,resetexpr,['rst','low'])]:
    d=a['clock_reset'][port];assert d['width']==1 and d['bound_expression']==expr and d['source']==desc
  raw=rawdir/(rec['type']+'.sv');assert sha(raw)==rec['sha256']
 dump(out/'contract.json',C)
 spec=importlib.util.spec_from_file_location('spb_mechanism',root/'tools/die_plan/hbm_spb0_assets/spb0_native.py');M=importlib.util.module_from_spec(spec);spec.loader.exec_module(M)
 for rec in R['parts']:M.run(rawdir/(rec['type']+'.sv'),out/'actual_graph.json',out/'contract.json',out/rec['type'])
 dump(out/'status.json',dict(status='ACTUAL_SCOPED_SOURCE_TRANSFORMED_NOT_FULL_BIND_OR_GEN',source_packet=sha(sourcefile),parts=parts,rtl_added_cycles=dict(rx_st=4,tx=4),model_added_cycles=dict(rx_st=2,tx=0),remaining=['staggered-reset mechanism proof','atomic plan opt-in/full bind','actual GEN/RT and reviewed physical gates']))
if __name__=='__main__':run(*sys.argv[1:])
