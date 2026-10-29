#!/usr/bin/env python3
"""Fresh HEAD clock + raw die signal GRT50, for initial CA planning only.

The real landed top/START nets replace this raw kit after fresh CA compose.
Clock cells and signal abstracts share one global_route; no old clock arrivals
are imported. Clock reservations are replaced by the actual clock nets while
PG and band-share obstructions remain. No P&R is launched by this writer.
"""
import argparse,json,re,sys
from pathlib import Path
W=Path(__file__).resolve().parents[2];sys.path.insert(0,str(W/'tools/die_plan'))
import die_trial as D,schema as S

def main():
 a=argparse.ArgumentParser(description=__doc__);a.add_argument('--kit',required=True);a.add_argument('--clock',required=True);a.add_argument('--out',required=True);a.add_argument('--plan',required=True);a=a.parse_args()
 kit,clock,out=map(Path,[a.kit,a.clock,a.out]);out.mkdir(parents=True,exist_ok=True);P=S.Plan(S.load(a.plan),Path(a.plan))
 reach=json.loads((clock/'actual_reach.json').read_text());assert reach['verdict']=='PASS','clock geometry has not passed actual reach'
 rv=(kit/'grt/route.v').read_text();cv=(clock/'ctree.v').read_text();rm=re.search(r'module\s+\w+\s*\(([^)]*)\);',rv);cm=re.search(r'module\s+ctree\s*\(([^)]*)\);',cv)
 rp=[p.strip() for p in rm[1].split(',') if p.strip()];cp=[p.strip() for p in cm[1].split(',') if p.strip()];assert not set(rp)&set(cp)
 pub=set(cp);rename=lambda n:n if n in pub else 'ck_'+n
 body=[];nets=[]
 for line in cv[cm.end():cv.rindex('endmodule')].splitlines():
  s=line.strip()
  if not s or s.startswith(('input','output')):continue
  m=re.fullmatch(r'wire\s+(\w+)\s*;',s)
  if m:nets.append(rename(m[1]));body.append('wire '+rename(m[1])+';');continue
  m=re.fullmatch(r'(\w+)\s+(\w+)\s*\((.*)\);',s)
  if m:body.append(m[1]+' ck_'+m[2]+' ('+re.sub(r'\.(\w+)\((\w+)\)',lambda n:'.'+n[1]+'('+rename(n[2])+')',m[3])+');');continue
  m=re.fullmatch(r'assign\s+(\w+)\s*=\s*(\w+)\s*;',s)
  if m:body.append('assign '+rename(m[1])+' = '+rename(m[2])+';');continue
  raise ValueError('unparsed clock statement: '+s)
 decl=[l for l in cv[cm.end():].splitlines() if l.strip().startswith(('input','output'))]
 (out/'combo.v').write_text('module die_combo ('+', '.join(rp+cp)+');\n'+'\n'.join(decl)+'\n'+rv[rm.end():rv.rindex('endmodule')]+'\n'+'\n'.join(body)+'\nendmodule\n')
 t=(kit/'grt/grt.tcl').read_text().split('source /work/grt/obs.tcl')[0]
 t=t.replace('read_verilog /work/grt/route.v','foreach f [glob $::env(LIBDIR)/*RVT_$::env(CORNER)_nldm*.lib*] { read_liberty $f }\nread_verilog /out/combo.v');t=re.sub(r'link_design \S+','link_design die_combo',t)
 ct=(clock/'ctree.tcl').read_text();lines=[l for l in ct.splitlines() if l.startswith('place_pin')]
 for l in ct.splitlines():
  if not l.startswith('place_inst'):continue
  m=re.search(r'-name (\S+) -location \{([-\d.]+) ([-\d.]+)\}',l)
  if not m:raise ValueError('unparsed physical clock body placement: '+l)
  orientation=re.search(r'-orientation (\S+)',l)
  lines.append(f'ot_place ck_{m[1]} {m[2]} {m[3]} {orientation[1] if orientation else "R0"}')
 # Preserve PG and signal-band ownership, avoid counting phantom clock wires
 # twice when the actual clock nets are present in this route.
 bands,regs=D.band_region_adjust(P,.75)
 for L,x0,y0,x1,y1 in D.pg_stripes(P)+D.band_share_obs(P,regs):lines.append(f'create_obstruction -region {{{x0:.3f} {y0:.3f} {x1:.3f} {y1:.3f}}} -layer {L}')
 lines+=['create_clock -name dck -period 833.000 [get_ports root]','set_routing_layers -signal M4-M9 -clock M8-M9']
 for L in ['M4','M5','M6','M7']:lines.append(f'set_global_routing_layer_adjustment {L} '+('0' if L in bands else '.75'))
 for L in ['M8','M9']:lines.append(f'set_global_routing_layer_adjustment {L} .4')
 lines+=['create_ndr -name ot_clock2w2s -width {M8 0.08 M9 0.08} -spacing {M8 0.08 M9 0.08}','set blk [ord::get_db_block]','set ndr [$blk findNonDefaultRule ot_clock2w2s]']
 lines+=['[$blk findNet root] setNonDefaultRule $ndr',
         'foreach i [$blk getInsts] { if {[string match ck_* [$i getName]]} { set p [$i findITerm Y]; if {$p == \"NULL\"} {error \"clock Y terminal missing\"}; [$p getNet] setNonDefaultRule $ndr } }']
 lines+=['global_route -congestion_iterations 50 -critical_nets_percentage 0 -allow_congestion -verbose -congestion_report_file /out/congestion_$::env(CORNER).rpt','write_guides /out/route_$::env(CORNER).guide','source /OpenROAD-flow-scripts/flow/platforms/asap7/setRC.tcl','delete_clock [get_clocks dck]','estimate_parasitics -global_routing','create_clock -name vclk -period 833.000','set_driving_cell -lib_cell BUFx24_ASAP7_75t_R -pin Y [get_ports root]','set_input_delay 0 -clock vclk [get_ports root]','set_load 3.0 [get_ports t_*]','set_output_delay 0 -clock vclk [get_ports t_*]']
 lines+=D.clock_edge_readout(cv,'/out/arr_$::env(CORNER).txt',period='833.000',cells='ck_*',tap_slew=True,prefix='ck_')
 lines+=['report_check_types -max_slew -max_capacitance -violators','write_db /out/combo_$::env(CORNER).odb','puts OT_DONE']
 (out/'combo.tcl').write_text(t+'\n'.join(lines)+'\n');(out/'scope.json').write_text(json.dumps({'scope':'initial CA planning; raw feedthrough/channel nets, not full landed top','grt_iterations':50,'corners':['TT','FF'],'period_ps':833,'signal_layers':'M4-M9','clock_layers':'M8-M9','clock_ndr':'2W2S','source_clock':'fresh current tree','load_basis':'3fF budget per tap; real tile545.3/445.7 annotation belongs to subsequent STA proof'},indent=1));print(json.dumps({'signal_ports':len(rp),'clock_ports':len(cp),'clock_cells':len([x for x in lines if x.startswith('place_inst')]),'out':str(out)}))
if __name__=='__main__':main()
