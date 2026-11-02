from pathlib import Path
import json,re,shutil,copy
r=Path(__file__).resolve().parent
p=json.load(open(r/'halo_regen/NW.json'));source=p['cells']['N1']
net=next(v for v in p['nets'].values()if v['kind']=='tree'and v['drv']=='N1')
assert net['loads']==['M0_0','M0_1'],net
for form in ['near','east']:
 original=r/f'loaded_mesh_contact_{form}';o=r/f'joint_N1_mesh_{form}';o.mkdir(exist_ok=True)
 for f in ['pilot.def','fixed_mesh.tcl','mesh_contact_route.tcl','ndr.tcl','rcx.tcl','run.sh']:shutil.copy2(original/f,o/f)
 scope=json.load(open(original/'scope.json'));scope['cells']['N1']=dict(x=source['x'],y=source['y'],lib=source['master'],orient='R0')
 cells=scope['cells'];s=(o/'pilot.def').read_text()
 def section(name,lines):
  global s
  s=re.sub(rf'(?ms)^{name} \d+ ;.*?^END {name}',f'{name} {len(lines)} ;\n'+'\n'.join(lines)+f'\nEND {name}',s)
 section('COMPONENTS',[f'- {n} {c["lib"]} + FIXED ( {round(c["x"]*1000)} {round(c["y"]*1000)} ) '+('FS'if c['orient']=='MX'else'N')+' ;'for n,c in cells.items()])
 section('PINS',['- drive0 + NET input0 + DIRECTION INPUT + USE CLOCK + LAYER M9 ( -20 -40 ) ( 20 40 ) + FIXED ( 313204 270000 ) N ;','- mesh_contact + NET ck_mesh + DIRECTION OUTPUT + USE CLOCK + LAYER M9 ( -20 -40 ) ( 20 40 ) + FIXED ( 257040 270000 ) N ;'])
 section('NETS',['- input0 ( PIN drive0 ) ( N1 A ) + USE CLOCK ;','- n_N1 ( N1 Y ) ( M0_0 A ) ( M0_1 A ) + USE CLOCK ;'])
 windows=[(c['x']-4,c['y']-2,c['x']+7.2,c['y']+2.27)for c in cells.values()];ys=sorted({100,450}|{v for a,b,c,d in windows for v in (b,d)});blocks=[]
 for ya,yb in zip(ys,ys[1:]):
  xx=50
  for a,b in sorted((max(50,a),min(350,c))for a,b,c,d in windows if b<(ya+yb)/2<d)+[(350,350)]:
   if a>xx:blocks +=[f'- LAYER M{l} RECT ( {round(xx*1000)} {round(ya*1000)} ) ( {round(a*1000)} {round(yb*1000)} ) ;'for l in range(2,8)]
   xx=max(xx,b)
 for core in scope['cores']:
  a,b,c,d=core['rect'];blocks +=[f'- LAYER M{l} RECT ( {round(max(50,a)*1000)} {round(max(100,b)*1000)} ) ( {round(min(350,c)*1000)} {round(min(450,d)*1000)} ) ;'for l in range(1,6)]
 section('BLOCKAGES',blocks);(o/'pilot.def').write_text(s)
 t=(o/'mesh_contact_route.tcl').read_text().replace('{drive0 drive1}','{drive0}').replace('{input0 input1}','{input0 n_N1}');(o/'mesh_contact_route.tcl').write_text(t)
 scope.update(scope='Actual current-union N1 fork (complete real fanout M0_0/M0_1 A) → actual two driver Y → retained local physical mesh → L_clk BUFx4f/A. Component physical source/contact integration only; global input phase/nativeK/current station event held.',source=dict(cell='N1',master=source['master'],xy=[source['x'],source['y']],period_ps=833,input_transition_ps=40,actual_complete_fanout=net['loads'],omitted_source_fanout=[]),release_qualified=False)
 (o/'scope.json').write_text(json.dumps(scope,indent=2))
 sta='''set P /OpenROAD-flow-scripts/flow/platforms/asap7
foreach f [glob $P/lib/NLDM/*RVT_$::env(CORNER)_nldm*.lib*] {read_liberty $f}
read_db /o/route.odb
read_spef /o/route.spef
create_clock -name core -period 833 [get_ports drive0]
set_input_transition 40 [get_ports drive0]
set_clock_uncertainty -setup 0 [get_clocks core]
set_clock_uncertainty -hold 25 [get_clocks core]
# Actual two-driver mesh is an analog boundary: measure its real source A pins.
set_disable_timing [get_cells {M0_0 M0_1}]
set_propagated_clock [all_clocks]
report_checks -unconstrained -path_delay max -group_path_count 1
set fp [open /o/joint_N1_arr_$::env(CORNER).txt w]
foreach name {N1/A N1/Y M0_0/A M0_1/A} {
 set p [get_pins $name]
 puts $fp "$name [get_property $p arrival_max_rise] [get_property $p arrival_min_rise] [get_property $p slew_max_rise] [get_property $p arrival_max_fall] [get_property $p arrival_min_fall] [get_property $p slew_max_fall]"
}
close $fp
puts OT_ACTUAL_N1_FANOUT_READOUT_DONE
'''
 (o/'joint_N1_sta.tcl').write_text(sta)
 run=(o/'run.sh').read_text().replace('> /o/route.log 2>&1\'','> /o/route.log 2>&1; for corner in TT FF; do CORNER=$corner openroad -no_init -threads 1 -exit /o/joint_N1_sta.tcl > /o/sta_$corner.log 2>&1; done\'');(o/'run.sh').write_text(run)
print('Actual N1 complete fanout4cell pair built,833ps source, retained PG/macroblocks; no globalphase/nativeK claim')
