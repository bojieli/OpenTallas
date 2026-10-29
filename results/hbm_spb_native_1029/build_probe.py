"""Actual-width SPB signal routing probe. Assumed PHY envelope/pins, no clock/STA qualification.
usage: build_probe.py PLAN_DIR PIN_DIR PLACEMENT.json OUT_DIR
"""
import hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'tools/die_plan'));import schema,gen_phys,g2
D,PD,PF,O=map(Path,sys.argv[1:5]);P=schema.Plan(json.load(open(D/'die_plan.json')),D/'die_plan.json');T=P.types['q_spb0'];M=json.load(open(PF));O.mkdir(parents=True,exist_ok=True)
if hashlib.sha256((D/'die_plan.json').read_bytes()).hexdigest()!=M['plan_sha256']:raise ValueError('probe plan does not match exact native bank geometry')
cs={x['inst']:x for x in T['hard_cores']};lk,ep=cs['u_lk_S0'],cs['u_ep_S0']
pins={n:json.load(open(PD/c['pins_file'])) for n,c in cs.items()}
# LEF macro pins retain actual data-port coordinates; PHY envelope is the published1050um assumption.
lef=['VERSION 5.8 ;','BUSBITCHARS "[]" ;','DIVIDERCHAR "/" ;']
for n,macro,size,ports,yshift in [('u_lk_S0','PHY_SPB_PROBE',[600.048,1050],{'rx':'OUTPUT','tx':'INPUT','st':'OUTPUT'},34.56),('u_ep_S0','EP_SPB_PROBE',[241.92,397.44],{'sd_rx':'INPUT','sd_tx':'OUTPUT','sd_st':'INPUT'},0)]:
 lef += [f'MACRO {macro}',' CLASS BLOCK ;',' ORIGIN 0 0 ;',f' SIZE {size[0]} BY {size[1]} ;',' SYMMETRY X Y ;']
 for p in pins[n]:
  base=p['name'].split('[')[0]
  if base not in ports:continue
  x,y=p['x'],p['y']+yshift;half=.016
  lef += [f' PIN {p["name"]}',f'  DIRECTION {ports[base]} ;','  USE SIGNAL ;','  PORT',f'   LAYER {p["layer"]} ;',f'   RECT {x-half:.6f} {y-half:.6f} {x+half:.6f} {y+half:.6f} ;','  END',f' END {p["name"]}']
 lef += [' OBS']
 for layer in range(1,6):lef += [f'  LAYER M{layer} ;',f'   RECT 0 0 {size[0]} {size[1]} ;']
 lef += [' END',f'END {macro}']
lef+=['END LIBRARY'];(O/'macros.lef').write_text('\n'.join(lef)+'\n')
# Vector blackboxes describe the exact selected source endpoint directions.
v=['module spb_signal_probe();','wire[511:0] phy_rx,phy_tx,ep_tx,ep_rx;wire[1:0]phy_st,ep_st;']
lib=['library(spb_probe) {',' delay_model : table_lookup;',' time_unit : "1ps";',' voltage_unit : "1V";',' current_unit : "1mA";',' pulling_resistance_unit : "1kohm";',' capacitive_load_unit(1,ff);',' nom_process : 1;',' nom_voltage : 0.7;',' nom_temperature : 25;']
for width in (2,512):lib.append(f' type(bus{width}) {{base_type : array; data_type : bit; bit_width : {width}; bit_from : {width-1}; bit_to : 0; downto : true;}}')
for cell,inst,rows in [('PHY_SPB_PROBE','phy',[('rx',512,'phy_rx','output'),('tx',512,'phy_tx','input'),('st',2,'phy_st','output')]),('EP_SPB_PROBE','ep',[('sd_rx',512,'ep_rx','input'),('sd_tx',512,'ep_tx','output'),('sd_st',2,'ep_st','input')])]:
 connections=[];lib.append(f' cell({cell}) {{ area : 1;')
 for port,width,net,direction in rows:
  connections.append(f'.{port}({net})')
  lib.append(f'  bus({port}) {{ bus_type : bus{width}; direction : {direction}; capacitance : 0.001; }}')
 lib.append(' }');v.append(f'{cell} {inst} ('+', '.join(connections)+');')
lib.append('}');(O/'macros.lib').write_text('\n'.join(lib)+'\n')
places=[]
for inst,width,src,dst in [('u_hbm_spb0_rx',514,'{phy_st,phy_rx}','{ep_st,ep_rx}'),('u_hbm_spb0_tx',512,'ep_tx','phy_tx')]:
 stem='rx' if width==514 else 'tx';v += [f'wire[{width-1}:0] {stem}_0,{stem}_1,{stem}_2,{stem}_3,{stem}_4;',f'assign {stem}_0={src};',f'assign {dst}={stem}_4;']
 for stage in range(4):
  bank=next(e for e in M['entries'] if e['instance']==inst and e['stage']==stage)
  for bit,(x,y) in enumerate(bank['sites_um']):
   nm=f'{stem}_s{stage}_b{bit}';v.append(f'{g2.FLOP} {nm}(.D({stem}_{stage}[{bit}]),.QN({stem}_{stage+1}[{bit}]));');places.append((nm,x,y))
v += ['endmodule'];(O/'probe.v').write_text('\n'.join(v)+'\n');(O/'make_tracks.tcl').write_text(gen_phys.make_tracks_tcl(P))
W,H=T['outline_um'];tcl=[f'read_lef {g2.TECH_LEF}',f'read_lef {g2.SC_LEF}','read_lef /work/macros.lef','foreach lib [glob -nocomplain /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/*RVT_TT*.lib*] {read_liberty $lib}','read_liberty /work/macros.lib','read_verilog /work/probe.v','link_design spb_signal_probe',f'initialize_floorplan -die_area {{0 0 {W} {H}}} -core_area {{0 0 {W} {H}}} -site asap7sc7p5t','source /work/make_tracks.tcl','place_inst -name phy -location {103.68 0} -status FIRM','place_inst -name ep -location {181.44 1088.64} -status FIRM','create_blockage -region {40.04 0 767.368 1113.64}','create_blockage -region {181.44 1088.64 423.36 1486.08}','set rb [ord::get_db_block]','set dbu [$rb getDbUnitsPerMicron]','set row_orient {}','foreach row [$rb getRows] {lassign [$row getOrigin] x y;dict set row_orient $y [$row getOrient]}']
for nm,x,y in places:tcl += [f'set yy [expr {{round({y}*$dbu)}}]',f'if {{![dict exists $row_orient $yy]}} {{error "native bank off actual row: {nm}"}}',f'place_inst -name {nm} -location {{{x} {y}}} -orient [dict get $row_orient $yy] -status FIRM']
tcl += ['check_placement -verbose','set_routing_layers -signal M2-M7']
for k in range(2,8):tcl.append(f'set_global_routing_layer_adjustment M{k} 0.5')
tcl += ['global_route -congestion_iterations 50 -allow_congestion -verbose -congestion_report_file /work/congestion.rpt','write_db /work/probe_grt.odb','pin_access','puts SPB_SIGNAL_PROBE_DONE']
(O/'probe.tcl').write_text('\n'.join(tcl)+'\n')
(O/'run.sh').write_text('''#!/bin/bash
set -u
cd "$(dirname "$0")"
docker run --rm --name codex-spb-probe-$$ --cpus=4 --memory=32g --memory-swap=32g -v "$PWD":/work -w /work openroad/orfs:asap7lock bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -no_init -exit /work/probe.tcl > /work/grt.log 2>&1'
rc=$?
echo "$rc" > probe.exit
exit "$rc"
''');(O/'run.sh').chmod(0o755)
(O/'scope.json').write_text(json.dumps({'source_plan_sha256':M['plan_sha256'],'flops':len(places),'nets':'actualthreeSPBidentitynets,full514RX/ST+512TXfourstages','macro_obstructions':'fullPHY1050um andEP onM1-M5','signal_layers':'M2-M7','capacity_adjustment':0.5,'clock_included':False,'sta_included':False,'assumption':'PHYenvelopepublished; digitalpincoordsfromplan, no licensed IP abstract qualification','role':'componentG2estimate only, no fullpartition/clock/freezeclaim'},indent=1)+'\n')
print('generated',len(places),'FF signalprobe',O)
