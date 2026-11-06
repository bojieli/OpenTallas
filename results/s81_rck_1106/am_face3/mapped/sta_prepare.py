import json,re
from pathlib import Path
p=Path(__file__).parent
leaf=(p/'leaf.sv').read_text();hs=leaf.index('module ot_s81_kp4_am_face3');he=leaf.index('endmodule',hs);lo=leaf[:hs].count('\n')+1;hi=leaf[:he].count('\n')+1
for top in ['old_am','new_am']:
 d=json.loads((p/(top+'.json')).read_text())['modules'][top];cells=d['cells'];drivers={}
 for name,c in cells.items():
  for port,direction in c['port_directions'].items():
   if direction=='output':
    for bit in c['connections'][port]:drivers[bit]=(name,c)
 def flop(bit):
  seen=set()
  while bit not in seen:
   seen.add(bit);name,c=drivers[bit]
   if c['type'].startswith('DFF'):return name
   assert c['type'].startswith(('INV','BUF')),c['type']
   ins=[b for port,direction in c['port_directions'].items() if direction=='input' for b in c['connections'][port]];assert len(ins)==1;bit=ins[0]
  raise AssertionError('cycle')
 am=flop(d['ports']['am_ok']['bits'][0]);face=[flop(x) for x in d['ports']['face_data']['bits'][532:544]]
 partial=[]
 for name,c in cells.items():
  if not c['type'].startswith('DFF'):continue
  m=re.search(r'leaf.sv:(\d+)',c.get('attributes',{}).get('src',''))
  if m and lo<=int(m[1])<=hi:partial.append(name)
 if top=='new_am':assert len(partial)==9,partial
 def pinlist(var,names,port):return '\n'.join('lappend '+var+' [get_pins {'+n+'/'+port+'}]' for n in names)+'\n'
 text='''source /work/lib_load.tcl
read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7_tech_1x_201209.lef
read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7sc7p5t_28_R_1x_220121a.lef
read_lef /work/macros/ot_s81_pma_rxm.lef
'''
 text+=f'read_verilog /work/am_map_fa/{top}.mapped.v\nlink_design {top}\n'
 text+='''create_clock -name rck -period 833 [get_ports clk]
set_clock_uncertainty -setup 0 [all_clocks]
set_clock_uncertainty -hold 25 [all_clocks]
set_clock_transition 20 [all_clocks]
set_input_delay 0 -clock rck [get_ports raw_v]
set_load 1 [all_outputs]
set_clock_latency -clock rck 250 [all_registers -clock rck -clock_pins]
set_clock_latency -clock rck 250 [get_pins prx/pma_rck]
proc measure {scope from to} {
 foreach delay {max min} {
  set ps [find_timing_paths -from $from -to $to -path_delay $delay -group_path_count 1 -endpoint_path_count 1 -sort_by_slack]
  if {![llength $ps]} {error "Missing actual path $scope $delay"}
  set pe [lindex $ps 0];set slack [sta::time_sta_ui [$pe slack]]
  puts "AM_MAP_RESULT $scope $delay $slack start=[get_full_name [get_property $pe startpoint]] end=[get_full_name [get_property $pe endpoint]]"
  report_checks -from $from -to $to -path_delay $delay -format full_clock_expanded -group_path_count 1
 }
}
'''
 text+=pinlist('faceD',face,'D')+pinlist('faceCK',face,'CLK')
 text+='measure native_PMA_to_face [get_pins prx/pma_rck] $faceD\n'
 if partial:
  text+=pinlist('partD',partial,'D')+pinlist('partCK',partial,'CLK')
  text+='measure native_PMA_to_pop4 [get_pins prx/pma_rck] $partD\n'
  text+='measure partial_counts_to_am_ok $partCK [get_pins {'+am+'/D}]\n'
 else:text+='measure face_to_pop12_am_ok $faceCK [get_pins {'+am+'/D}]\n'
 text+='puts AM_MAP_DONE\nexit\n';(p/(top+'.sta.tcl')).write_text(text)
