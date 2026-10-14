from pathlib import Path
import sys,collections,json,hashlib
run=Path('/srv/opentallas-scratch2/claude/closure-loop/s81be-gray-m7-c7cf30d5d');sys.path.insert(0,str(run/'src/tools'));import textbook_lint as T
p=run/'routes/s81be_gray_m7_c7cf30d5d/work/orfs/results/asap7/opentallas_dsfd_vm_be_sl_asap7_s81ph_s81be_gray_m7_c7cf30d5d/base/1_2_yosys.v';g,top=T.flatten(T.parse_verilog(p.read_text()),'dsfd_vm_be_sl');a=T.build(g,None);clk,sinks=T.clock_nets(g,a);groups=collections.Counter();pf=[];fan=[]
for ci,(typ,n,pins) in enumerate(g.cells):
 if a['kind'][ci]=='ff':
  if n.startswith('g_pf[0].'):k='P2_region0'
  elif n.startswith('g_pf[1].'):k='P2_region1'
  elif n.startswith('u_rc0.'):k='return_FIFO0'
  elif n.startswith('u_rc1.'):k='return_FIFO1'
  elif n.startswith('g_xb['):k='X_bus_registered_copies'
  elif n.startswith('g_bl[') or n.startswith('bl_'):k='bus_lanes'
  else:k='other_pin_alignment_status_control'
  groups[k]+=1
  if k.startswith('P2_'):pf.append(dict(instance=n,master=typ,clock_nets=[g.net_name[x] for x in pins.get('CLK',[])]))
  if n.startswith(('g_pf[0].u_pc.q[2]','g_pf[1].u_pc.q[2]')):
   for pn in ('QN','Q'):
    for x in pins.get(pn,[]):
     tot,ff,ex=T.bufinv_fanout(g,a,x,clk);fan.append(dict(instance=n,pin=pn,total_load_pins=tot,FF_load_pins=ff,example=ex,net=g.net_name[x]))
print(json.dumps(dict(schema='opentallas.be_gray_actual_root_load_ledger.v1',source_commit='c7cf30d5d',netlist_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),roots=[dict(root=f'{k[0]}:{k[1]}',**v) for k,v in sinks.items()],FF_state_by_region=dict(groups),P2_mapped_FF=pf,overloaded_control_outputs=fan,physical_global_producers_bound=False),indent=2))
