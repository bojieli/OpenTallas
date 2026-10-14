#!/usr/bin/env python3
"""Exact selected source ACK inventory; source clocks are connectivity, not producers."""
from pathlib import Path
import json,hashlib,subprocess,argparse
R=Path(__file__).resolve().parents[2]
a=argparse.ArgumentParser();a.add_argument('--out',type=Path,required=True);args=a.parse_args()
nodes=[]
def node(port,idx,path,release,consumers,live="1'b1",init="1'b1"):
 nodes.append(dict(port=port,bit=idx,path=path,clock_pin=path+'.clk',production_clock_driver=None,epoch_request='dsfd_mtp_hrow_td.rst',production_reset_driver=None,local_release=release,consumer_live=live,reset_initialized=init,actual_consumer_states=consumers,added_witness_ff=2))
for p in range(3):
 base=f'g_part[{p}]'
 node('rst_ack_leaf',p*11,base+'.u_ig.u_ack',['rn','u_rx.live'],['inh','ihalf','flt','ev0','islot','ibeat','g_k[*].kd[1:0]','wc0[0]','u_rx.live','u_rx.g0','u_rx.valid'],'u_rx.live')
 for k in range(10):
  b=base+f'.g_c[{k}].'+('g_e' if k<5 else 'g_w')+'.u_b'
  node('rst_ack_leaf',p*11+1+k,b+'.u_ack',['rn'],['u_rs.s0','u_rs.s1','u_c.wi[0]','u_c.wo[0]','u_c.ri[0]','u_c.ro[0]','u_c.di[0]','u_c.dq[0]','u_c.s1','u_c.s2'])
 groups=[('g_hut.g_r',2,[0,1039,1054]),('g_hev.g_ev',2,[0,21]),('g_hev.g_rc',3,[0]),('g_hrp.g_r',2,[0])];offset=0
 for group,n,bits in groups:
  for i in range(n):
   b=base+f'.{group}[{i}]';idx=p*9+offset+i
   node('rst_ack_relay',idx,b+'.u_r.u_ack',['rn'],[f'o[{j}]' for j in bits],init=' && '.join(f'!o[{j}]' for j in bits))
   node('rst_ack_conditioner',idx,b+'.g_rst.u_rs.g_ack.u_ack',['q[0]','q[1]'],['q[0]','q[1]'])
  offset+=n
node('rst_ack_leaf',33,'u_hub.u_ack_c',['rn_c','u_q.g_rtt.u_rx.live'],['i_clr[0]','ev_c[*]','pr[*][0]','pflt[*]','r_v','o_rs[0]','skn','skw','skr','qr_q','v2','fq','o_flt','u_q.g_rtt.u_rx.live','u_q.g_rtt.u_rx.wp','u_q.g_rtt.u_rx.rp','u_q.g_rtt.u_rx.cnt','u_q.g_rtt.u_rx.grants','u_q.g_rtt.u_rx.g_output_pipe.valid'],'u_q.g_rtt.u_rx.live')
for i in range(6):node('rst_ack_leaf',34+i,f'u_hub.g_ack_a[{i}].u_ack',[f'rn_a[{i}]'],[f'g_rs[{i}].u_rsa.s0',f'g_rs[{i}].u_rsa.s1',f'g_p[{i//2}].g_s[slot in half {i%2}].cmp_r/wg_r/rg_r/ld_r']+(['g_p[%d].f0r'%(i//2)] if i%2==0 else []))
assert len(nodes)==94
src=['rtl/dsrom_sys/mtp/ot_dsrom_mtp_hrow_die.sv','rtl/dsrom_sys/mtp/ot_dsrom_mtp_hrow_tiles.sv','rtl/dsrom_sys/mtp/ot_dsrom_mtp_link_rtt.sv','rtl/dsrom_sys/s81_ph/relays/dsfd_die_relays.sv']
g=dict(schema='s81.hrow.final_consumer_ack.v1',source_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=R,text=True).strip(),source_sha256={p:hashlib.sha256((R/p).read_bytes()).hexdigest() for p in src},enable='OT_HROW_RESET_ACK',params=dict(HARD_RELAYS=1,DISTRIBUTED_RST=1,UT=2,CQ=3,WK=7,P=2),nodes=nodes,price=dict(original_relay_ff=18897,original_conditioner_ff=54,added_ack_ff=188,total_parent_ff=19139,datapath_latency_added=0,ack_consumer_edge_added=1,startup_controller_sync_ff=None,startup_latency=None,leaf_ownstate='retained source, not recounted into parent relay price'),default_behavior='Undefined macro: no new ports or ACK state; shared rstsync RESET_ACK defaults0 even with macro defined.',payload_policy='Unreset payload/SRAM contents remain uninitialized; valid/control reset governs use. ACK does not promise initialized SRAM or payload bits.',physical_qualification='OPEN: new ACK child interfaces/state require successor views; old CLOSED stands.',dependencies=dict(production_instance=None,global_origin=None,refclk_producer=None,global_reset_producer=None,refclk_phase=None,startup_admission='die/root owner: synchronize every genuine ACK then reduce; MTP C/E/D readiness remains additional prerequisite',pair_rc_budgets=None))
args.out.parent.mkdir(parents=True,exist_ok=True);args.out.write_text(json.dumps(g,indent=2)+'\n')
