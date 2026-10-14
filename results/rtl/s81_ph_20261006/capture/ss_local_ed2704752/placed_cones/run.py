import pathlib,importlib.util,json,subprocess,hashlib
stage=pathlib.Path.cwd()
src=pathlib.Path('/srv/opentallas-scratch/claude/ref_gate/dsfd_capt_x8_dual-20261014-001954/src')
base=next((src.parent/'routes/gate/work/orfs/results/asap7').glob('*/base'))
subprocess.run(['python3',str(src/'tools/closure_loop/ck_insertion.py'),'--base',str(base),'--all-clocks','--route-corner','TC','--output',str(stage/'insertion.json')],check=True)
measure=json.loads((stage/'insertion.json').read_text())['clock_measurements']
spec=importlib.util.spec_from_file_location('ck',src/'tools/closure_loop/ck_insertion.py');ck=importlib.util.module_from_spec(spec);spec.loader.exec_module(ck)
for corner in ['ss','ff','tt']:
 prefix=ck.tcl(corner,'4_1_cts.odb','4_cts.sdc',False,'core_clk').split('set regs {}')[0]
 body='''
create_clock -name core_clk -period 833.333 [get_ports {ck[0]}]
create_clock -name ser_clk -period 1111.110667 [get_ports {ckv[0]}]
set_clock_uncertainty -setup 60 [get_clocks {core_clk ser_clk}]
set_clock_uncertainty -hold 25 [get_clocks {core_clk ser_clk}]
set_propagated_clock [all_clocks]
set_clock_latency -source @CORE_R@ [get_clocks core_clk]
set_clock_latency -source @SER_R@ [get_clocks ser_clk]
foreach pair {{core_clk core_clk} {ser_clk ser_clk} {core_clk ser_clk} {ser_clk core_clk}} {
 lassign $pair launch capture
 puts "OT_CONE_BEGIN @CORNER@ $launch $capture"
 set starts [all_registers -clock_pins -clock [get_clocks $launch]]
 set ends [all_registers -data_pins -clock [get_clocks $capture]]
 foreach sense {max min} {
 set paths [find_timing_paths -from $starts -to $ends -path_delay $sense -group_path_count 1 -endpoint_path_count 1 -sort_by_slack]
 if {![llength $paths]} {error "Missing actual cone"}
 set p [lindex $paths 0]
 puts "OT_CONE @CORNER@ $launch $capture $sense [get_property $p slack] [get_full_name [get_property $p startpoint]] [get_full_name [get_property $p endpoint]]"
 report_checks -from $starts -to $ends -path_delay $sense -format full_clock_expanded -group_path_count 1 -endpoint_path_count 1
 }
 puts "OT_CONE_END @CORNER@ $launch $capture"
}
set bank 0
foreach inst [[ord::get_db_block] getInsts] {if {[string match *bank_n* [$inst getName]]} {incr bank}}
puts "OT_BANK_INSTANCES $bank"
report_checks -path_delay max -format full_clock_expanded -group_path_count 5
exit
'''
 for key,val in {'@CORE_R@':-measure['ck[0]'][corner]['boundary']['mean'],'@SER_R@':-measure['ckv[0]'][corner]['boundary']['mean'],'@CORNER@':corner}.items():body=body.replace(key,str(val))
 script=stage/(corner+'.tcl');script.write_text(prefix+body)
 result=subprocess.run(['docker','run','--rm','-v',str(base)+':/base:ro','-v',str(stage)+':/audit:ro','openroad/orfs:latest','/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad','-no_init','-exit','/audit/'+script.name],capture_output=True,text=True)
 (stage/(corner+'.log')).write_text(result.stdout+result.stderr)
 for line in result.stdout.splitlines():
  if line.startswith(('OT_CONE ','OT_BANK_INSTANCES')):print(line,flush=True)
 if result.returncode:raise SystemExit(result.returncode)
(stage/'placed_hashes.json').write_text(json.dumps({n:hashlib.sha256((base/n).read_bytes()).hexdigest() for n in ['4_1_cts.odb','4_cts.sdc']},indent=2)+'\n')
