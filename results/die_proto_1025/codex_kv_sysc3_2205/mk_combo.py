import re,sys,os
# DIE-FT: combined die GRT = die_trial signal kit (abstracts, M4-M7) + die clock tree (die_trial ctree, M8-M9) in ONE global_route
K,C,O=sys.argv[1:4]   # kit dir, clock dir (ctree.v, ctree_ck89.tcl), out dir
os.makedirs(O,exist_ok=True)
rv=open(K+'/grt/route.v').read(); cv=open(C+'/ctree.v').read()
mh=re.match(r'\s*module\s+(\w+)\s*\(([^)]*)\);',rv); rports=[p.strip() for p in mh.group(2).split(',') if p.strip()]
rbody=rv[mh.end():rv.rindex('endmodule')]
mc=re.search(r'module\s+ctree\s*\(([^)]*)\);',cv,re.S); cports=[p.strip() for p in mc.group(1).split(',') if p.strip()]
cbody=cv[mc.end():cv.rindex('endmodule')]
assert not set(rports)&set(cports)
P=set(cports)
def f(n): return n if n in P else 'ck_'+n
out=[]
for line in cbody.split('\n'):
    s=line.strip()
    if not s or s.startswith(('input','output')): continue
    m=re.match(r'wire\s+(\w+)\s*;',s)
    if m: out.append(f'  wire {f(m.group(1))};'); continue
    m=re.match(r'(\w+)\s+(\w+)\s*\((.*)\);',s)
    if m:
        conns=re.sub(r'\.(\w+)\((\w+)\)',lambda q:f'.{q.group(1)}({f(q.group(2))})',m.group(3))
        out.append(f'  {m.group(1)} ck_{m.group(2)} ({conns});'); continue
    m=re.match(r'assign\s+(\w+)\s*=\s*(\w+)\s*;',s)
    if m: out.append(f'  assign {f(m.group(1))} = {f(m.group(2))};'); continue
    raise SystemExit('unparsed: '+s)
decl=[l for l in cv[mc.end():].split('\n') if l.strip().startswith(('input','output'))]
v=f"module die_combo ({', '.join(rports+cports)});\n"+'\n'.join(decl)+'\n'+rbody+'\n'.join(out)+'\nendmodule\n'
open(O+'/combo.v','w').write(v)
t=open(K+'/grt/grt.tcl').read()
ct=open(C+'/ctree_ck89.tcl').read()
pins=[l for l in ct.split('\n') if l.startswith('place_pin')]
insts=[re.sub(r'-name (\S+)',r'-name ck_\1',l) for l in ct.split('\n') if l.startswith('place_inst')]
pre=t.split('source /work/grt/obs.tcl')[0]
pre=pre.replace('read_verilog /work/grt/route.v','read_verilog /out/combo.v').replace(re.search(r'link_design \S+',pre).group(0),'link_design die_combo')
corner=os.environ.get('CORNER','TT')
tail=f"""source /work/grt/obs.tcl
{chr(10).join(pins)}
{chr(10).join(insts)}
puts "OT_T clockplaced [expr {{[clock seconds]-$t0}}]"
foreach f [glob $::env(LIBDIR)/*RVT_$::env(CORNER)_nldm*.lib*] {{ read_liberty $f }}
create_clock -name dck -period 833.333 [get_ports root]
set_routing_layers -signal M4-M7 -clock M8-M9
set_global_routing_layer_adjustment M4 0.5
set_global_routing_layer_adjustment M5 0.5
set_global_routing_layer_adjustment M6 0.5
set_global_routing_layer_adjustment M7 0.5
set_global_routing_layer_adjustment M8 0.4
set_global_routing_layer_adjustment M9 0.4
if {{[catch {{global_route -congestion_iterations 5 -allow_congestion -verbose -congestion_report_file /out/congestion_$::env(CORNER).rpt}} e]}} {{ puts "OT_GRT_ERROR $e" }}
puts "OT_T grt [expr {{[clock seconds]-$t0}}]"
write_guides /out/route_$::env(CORNER).guide
source /OpenROAD-flow-scripts/flow/platforms/asap7/setRC.tcl
delete_clock [get_clocks dck]
estimate_parasitics -global_routing
create_clock -name vclk -period 833.333
set_driving_cell -lib_cell BUFx24_ASAP7_75t_R -pin Y [get_ports root]
set_input_delay 0 -clock vclk [get_ports root]
set_load 3.0 [get_ports t_*]
set_output_delay 0 -clock vclk [get_ports t_*]
set fh [open /out/arr_$::env(CORNER).txt w]
foreach p [get_ports t_*] {{ set n [get_full_name $p]; puts $fh "T $n [expr {{833.333 - [get_property $p slack_max_rise]}}] [get_property $p slack_min_rise]" }}
close $fh
report_checks -through [get_ports t_*] -path_delay max -group_path_count 1 -format full -fields {{cap slew fanout}}
report_check_types -max_slew -max_capacitance -violators
puts OT_DONE
"""
# liberty must be read before link: move read_liberty up
tail=tail.replace("foreach f [glob $::env(LIBDIR)/*RVT_$::env(CORNER)_nldm*.lib*] { read_liberty $f }\n","")
pre=pre.replace('read_verilog /out/combo.v',"foreach f [glob $::env(LIBDIR)/*RVT_$::env(CORNER)_nldm*.lib*] { read_liberty $f }\nread_verilog /out/combo.v")
pre=pre.replace('/work/grt/tracks.tcl','/work/grt/tracks.tcl')
open(O+'/combo.tcl','w').write(pre+tail)
print('ports',len(rports),len(cports),'ck insts',len(insts),'pins',len(pins))
