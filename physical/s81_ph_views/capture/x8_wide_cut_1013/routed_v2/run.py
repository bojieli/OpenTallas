import pathlib,importlib.util,json,subprocess,hashlib
stage=pathlib.Path.cwd()
src=pathlib.Path('/srv/opentallas/claude/closure-loop/dsfd_capt_x8_dual-v2-bc2c93f92/src')
base=next((src.parent/'routes/dsfd_capt_x8_dual_v2_bc2c93f92/work/orfs/results/asap7').glob('*/base'))
subprocess.run(['python3',str(src/'tools/closure_loop/ck_insertion.py'),'--base',str(base),'--all-clocks','--routed','--route-corner','TC','--output',str(stage/'insertion.json')],check=True)
measure=json.loads((stage/'insertion.json').read_text())['clock_measurements']
spec=importlib.util.spec_from_file_location('ck',src/'tools/closure_loop/ck_insertion.py'); ck=importlib.util.module_from_spec(spec);spec.loader.exec_module(ck)
for corner in ['tt','ff','ss']:
 prefix=ck.tcl(corner,'6_final.odb','6_final.sdc',True,'core_clk').split('set regs {}')[0]
 R={p:measure[p+'[0]'][corner]['boundary']['mean'] for p in ['ck','ckv']}
 body=r'''
create_clock -name core_clk -period 833.333 [get_ports {ck[0]}]
create_clock -name ser_clk -period 1111.110667 [get_ports {ckv[0]}]
set_clock_uncertainty -setup 60 [get_clocks {core_clk ser_clk}]
set_clock_uncertainty -hold 25 [get_clocks {core_clk ser_clk}]
set_propagated_clock [all_clocks]
set_clock_latency -source @CORE_R@ [get_clocks core_clk]
set_clock_latency -source @SER_R@ [get_clocks ser_clk]
foreach pair {{core_clk ser_clk core serial} {ser_clk core_clk serial core}} {
 lassign $pair launch capture a b
 foreach sense {max min} {
  set paths [find_timing_paths -from [all_registers -clock_pins -clock [get_clocks $launch]] -to [all_registers -data_pins -clock [get_clocks $capture]] -path_delay $sense -group_path_count 1 -endpoint_path_count 1 -sort_by_slack]
  if {![llength $paths]} {error "missing actual crossing $launch/$capture/$sense"}
  set p [lindex $paths 0]
  puts "@MARKER@ {\"corner\":\"@CORNER@\",\"launch\":\"$a\",\"capture\":\"$b\",\"sense\":\"$sense\",\"startpoint\":\"[get_full_name [get_property $p startpoint]]\",\"endpoint\":\"[get_full_name [get_property $p endpoint]]\",\"slack_ps\":[get_property $p slack]}"
 }
}
if {"@CORNER@" eq "tt"} {
 set block [ord::get_db_block]
 set dbu [$block getDbUnitsPerMicron]
 foreach net [$block getNets] {
  if {![$net isSpecial]} continue
  foreach sw [$net getSWires] {
   foreach box [$sw getWires] {
    set layer [$box getTechLayer]
    if {$layer eq "NULL" || [$layer getName] ne "M5"} continue
    set x0 [expr {[$box xMin]/double($dbu)}]; set x1 [expr {[$box xMax]/double($dbu)}]
    set y0 [expr {[$box yMin]/double($dbu)}]; set y1 [expr {[$box yMax]/double($dbu)}]
    if {($y0 <= 0.192 && $y1 >= 0) || ($y0 <= 136.08 && $y1 >= 135.888)} {puts "OT_CAPTURE_PG [$net getName] $x0 $y0 $x1 $y1"}
   }
  }
 }
}
exit
'''
 for name,val in {'@CORE_R@':-R['ck'],'@SER_R@':-R['ckv'],'@CORNER@':corner,'@MARKER@':'OT_CAPTURE_PHASE' if corner!='ss' else 'OT_CAPTURE_SENSITIVITY'}.items():body=body.replace(name,str(val))
 script=stage/(corner+'.tcl');script.write_text(prefix+body)
 cmd=['docker','run','--rm','-v',str(base)+':/base:ro','-v',str(stage)+':/audit:ro','openroad/orfs:latest','/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad','-no_init','-exit','/audit/'+script.name]
 result=subprocess.run(cmd,capture_output=True,text=True);(stage/(corner+'.log')).write_text(result.stdout+result.stderr)
 print('CORNER',corner,'rc',result.returncode,flush=True)
 for line in result.stdout.splitlines():
  if line.startswith(('OT_CAPTURE_PHASE ','OT_CAPTURE_SENSITIVITY ','OT_CAPTURE_PG ')):print(line,flush=True)
 if result.returncode:raise SystemExit(result.returncode)
(stage/'routed_hashes.json').write_text(json.dumps({n:hashlib.sha256((base/n).read_bytes()).hexdigest() for n in ['6_final.odb','6_final.sdc','6_final.spef']},indent=2)+'\n')
