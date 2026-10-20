#!/usr/bin/env python3
"""Actual all-driver buffer-collapsed32-load census; no timing/SAFE waiver."""
import sys,json,hashlib,re
from pathlib import Path
base=Path(sys.argv[1]);sys.path.insert(0,str(base/'src/tools'));import textbook_lint as T
top_name=sys.argv[2] if len(sys.argv)>2 else 'ot_hbm_svc_pc_ctrl_leaf_cfg_safe'
n=next((base/'routes/gate/work/orfs/results/asap7').glob('*/base/1_2_yosys.v'))
g,top=T.flatten(T.parse_verilog(n.read_text()),top_name);a=T.build(g,None);clks,_=T.clock_nets(g,a)
rows=[]
for x,d in a['driver'].items():
 if x<=3 or x in clks:continue
 ci=d[0]
 if ci>=0 and a['kind'][ci] in ('buf','tie'):continue
 total,ff,ex=T.bufinv_fanout(g,a,x,clks)
 if total<=32:continue
 todo=[x];seen=set();sinks=[]
 while todo:
  y=todo.pop()
  if y in seen:continue
  seen.add(y)
  for c,p,_ in a['loads'].get(y,()):
   if a['kind'][c]=='buf':todo.extend(T._out_nets(g,a,c))
   else:sinks.append({'kind':a['kind'][c],'cell':g.cells[c][1],'pin':p,'type':g.cells[c][0]})
 label=T.net_label(g,a,x);ctype='port'if ci<0 else a['kind'][ci]
 rows.append({'label':label,'loads':total,'flop_loads':ff,'root_type':ctype,'driver_cell':None if ci<0 else g.cells[ci][1],'driver_library':None if ci<0 else g.cells[ci][0],'net_name':g.net_name[x],'reset':T.is_reset_net(label,g.net_name[x],T.THRESHOLDS,port=ci<0),'sinks':sinks})
rows.sort(key=lambda x:-x['loads'])
out={'schema':'opentallas.hbm_bw_fanout_census.v1','source_netlist':str(n),'source_sha256':hashlib.sha256(n.read_bytes()).hexdigest(),'top':top,'excluded':'clocks, constant/tie roots, and buffer/inverter drivers; fanout collapses through BUF/INV to actual nonbuffer load pins plus ports','report_threshold':32,'roots':rows}
p=base/'fanout_gt32.json';p.write_text(json.dumps(out,indent=2)+'\n');print('CENSUS',len(rows),'roots');print(*[f"{z['loads']} {z['root_type']} reset={z['reset']} {z['label']}"for z in rows],sep='\n')
