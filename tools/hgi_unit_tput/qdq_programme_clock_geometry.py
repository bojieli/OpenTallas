#!/usr/bin/env python3
"""Read retained actual CTS coordinates/clock arrivals and per-command FF hold paths."""
import argparse,importlib.util,subprocess
from pathlib import Path
ap=argparse.ArgumentParser();ap.add_argument('run',type=Path);ap.add_argument('kit');ap.add_argument('--routed',action='store_true');a=ap.parse_args();r=a.run.resolve();src=r/'src';w=r/('native_route/work/orfs' if a.routed else 'routes/gate/work/orfs');b=next((w/'results/asap7').glob('*/base'));rel='/work/'+str(b.relative_to(w))
spec=importlib.util.spec_from_file_location('C',src/'tools/w18/corner_sta.py');C=importlib.util.module_from_spec(spec);spec.loader.exec_module(C)
for c in ('tt','ff'):
 s=C.script(c,rel,['physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2'],[f'physical/ref_tile/{a.kit}/signoff.sdc'],sdc_name='4_cts.sdc').replace('/6_final.odb','/4_cts.odb').replace(f'read_spef {rel}/6_final.spef',f'source {C.PLAT}/setRC.tcl\nestimate_parasitics -placement').split('puts "OT_CORNER')[0]
 if a.routed:
  s=s.replace('/4_cts.odb','/6_final.odb').replace('/4_cts.sdc','/6_final.sdc').replace(f'source {C.PLAT}/setRC.tcl\nestimate_parasitics -placement',f'read_spef {rel}/6_final.spef')
 s+='''
sta::worst_slack_cmd max
set f [open /work/geometry_CORNER.tsv w]
set block [ord::get_db_block]
set dbu [[ord::get_db_tech] getDbUnitsPerMicron]
set ot_missing 0
foreach p [all_registers -clock_pins] {
 set n [get_full_name [get_cells -of_objects $p]]
 set i [$block findInst [string map [list {[} {\\[} {]} {\\]}] $n]]
 if {$i eq "NULL"} {incr ot_missing;if {$ot_missing<=4} {puts "NO_ODB_INSTANCE $n"};continue}
 lassign [$i getLocation] x y
 puts $f "$n\t[[$i getMaster] getName]\t[expr {double($x)/$dbu}]\t[expr {double($y)/$dbu}]\t[get_property $p arrival_max_rise]"
}
close $f
foreach p [find_timing_paths -path_delay min -to [get_ports command*] -group_path_count 5000 -endpoint_path_count 1] {
 puts "COMMAND_HOLD [get_full_name [get_property $p endpoint]] [get_property $p slack]"
}
report_checks -path_delay min -to [get_ports command*] -group_path_count 48 -endpoint_path_count 1 -format full_clock_expanded
exit
'''.replace('CORNER',c)
 p=w/f'geometry_{c}.tcl';p.write_text(s)
 cmd=['docker','run','--rm','-v',f'{src}:/src:ro','-v',f'{w}:/work','openroad/orfs:latest','/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad','-no_init','-exit',f'/work/{p.name}']
 out=subprocess.run(cmd,capture_output=True,text=True);(w/f'geometry_{c}.log').write_text(out.stdout+'\n'+out.stderr)
 print(c,out.returncode,flush=True)
 if out.returncode:raise SystemExit(out.returncode)
