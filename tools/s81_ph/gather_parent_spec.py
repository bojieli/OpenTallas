#!/usr/bin/env python3
"""Emit a reviewable gather physical cluster draft; refuse runnable emission with missing views/pins.
No generated substitute views or assumed clock insertion are permitted.
"""
import argparse,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
def main():
 a=argparse.ArgumentParser();a.add_argument('--plan',required=True);a.add_argument('--out',required=True);a.add_argument('--require-bound',action='store_true');args=a.parse_args()
 plan=json.loads(Path(args.plan).read_text());children=[]
 for g in range(8):
  for k in range(4):
   side='w' if g<4 else 'e';master='dsfd_gth_r'+side
   children.append({'view':f'physical/ref_tile/{master}/views/{master}','count':1,'inst':f'g_c[{g}].g_k[{k}].g_{side}.u_l','at':[12.96+216*g,61.632+184.32*k],'orient':'R0'})
 children.append({'view':'physical/ref_tile/dsfd_gth_ctl/views/dsfd_gth_ctl','count':1,'inst':'u_ctl','at':[1598.4,8.64],'orient':'R0'})
 for r in plan['relay_children']:children.append({'view':r['view'],'count':1,'inst':r['instance'],'at':r['origin_um'],'orient':r['orient']})
 core=['ck']+[f'ck_l[{i}]' for i in range(32)]+[f'ck_r[{i}]' for i in range(132)]
 serial=['ckv','ck_r[132]'];cps=core+serial;assert len(cps)==167
 missing=[]
 for child in children:
  view=ROOT/child['view'];master=view.name
  for name in ('insertion.json',master+'.lef',master+'_tt.lib',master+'_ss.lib',master+'_ff.lib'):
   if not (view/name).is_file():missing.append(str((view/name).relative_to(ROOT)))
 io='physical/s81_die_pins/v18/dsfd_sp_gather_c.tcl'
 if not (ROOT/io).exists():missing.append(io)
 spec={'name':'dsfd_sp_gather_c_strip','top':'dsfd_sp_gather_c','kind':'cluster','sources':['rtl/dsrom_sys/s81_ph/ctrl_c/dsfd_sp_gather_c_cl.sv','rtl/dsrom_sys/s81_ph/dsfd_gth_strip.sv'],'defines':['S81PH_GTH_HARD','S81PH_GTH_DIE_CLOCKS','S81PH_GTH_CONTROL_STRIP'],'params':{},'outline':{'w':1728,'h':803.52},'clock':'entries','clock_port':'ck','clock_ports':cps,'clock_entry_domains':{'core':{'ratio':[1,1],'ports':core,'inputs':['rst','rW*','rE*','c_cmd'],'outputs':['t_capture','t_xgo','c_done','c_st']},'serial':{'ratio':[4,3],'ports':serial,'inputs':['rsv','f_vm','f_cd'],'outputs':[]}},'reset_ports':['rst','rsv'],'children':children,'child_lattice_um':.144,'io_tcl':io,'pins':{'W':[f'rW{i}' for i in range(6)],'E':[f'rE{i}' for i in range(6)]+['ck','ckv','rst','rsv','f_vm','c_cmd','c_done','c_st','t_xgo'],'S':['t_capture','f_cd'],'ANY':['ck_l','ck_r']},'recipe':2,'inhold':False,'outhold':False,'io_flop_at_pins':False,'route':{'pd':.5,'threads':16},'job':{'owner':'Codex:s81-gather-strip','branch':'codex/s81-gather-strip-v18','tag':'strip-candidate','hold_merge':'UNSUBMITTED DRAFT: real routedviews, authoritative133clockpins, fullpairreach/hold/PG/clockwire/price gates required','purpose':'Actual32leaf S8 gather +129.6x43.2ctl +133CLOSEDrelay instances; 0parentlogic and167directcompensatedclockentries; transporttc+1stream/f_cd+1serial/status+4/resetrelease+6','benches':[{'name':'full_shape_exact_and_mutants','cmd':"CONTROL_STRIP=1 DIE_CLOCKS=1 RESTART=1 J=4 bash rtl/dsrom_sys/s81_ph/test/run_gather_cl.sh $PWD {RUN}/cluster rtl/dsrom_sys/s81_ph/test/real_order_trace.json '2 20'",'expect':'pass','pass_regex':'GATHER_CL_GATE PASS','threads':24,'peak_ram_gb':64}],'extra_paths':['rtl/dsrom_sys/s81_ph','rtl/dsrom_sys/s81_ctrl','rtl/dsrom_sys/s81_glue','physical/s81_ph_views','physical/s81_die_pins/v18','tools/s81_ph','results/rtl/s81_ph_20261006/gather']},'pending_requirements':['full167clock sourcebinding with realchildR + measuredentrywireR','sourceexternal-to-entry totalhop and exactpairreach/hold','parentPG andcut utilization gates','immutableproductionnative81 throughput/latency price','arbitrary live aggregator fault/busy semantics beyond quiet fullclusterpoints'],'missing_bound_artifacts':sorted(set(missing)),'qualification':'OPEN_DRAFT'}
 if args.require_bound and missing:raise SystemExit('GATHER_PARENT REFUSED: missing actual bound artifacts '+str(len(set(missing))))
 Path(args.out).write_text(json.dumps(spec,indent=2)+'\n');print(f'GATHER_PARENT DRAFT {len(children)}children /167clockentries; missing{len(set(missing))} bound artifacts')
if __name__=='__main__':main()
