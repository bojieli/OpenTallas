#!/usr/bin/env python3
"""Extract SS/FF child STA with real protected SRAM and propagated clocks.

Stand-in parent ports remain conditional. No nominal clkQ substitutions or
SRAM timing exceptions: the final netlist, RCX SPEF, SDC and each macro's own
corner liberty determine every memory read/capture and address/write path.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MACRO = 'ot_sram_1r1w_512x128_m4_r2c2'
TCL = r'''
set P /OpenROAD-flow-scripts/flow/platforms/asap7
foreach f [lsort [glob $P/lib/NLDM/*_RVT_TAG_*.lib*]] {read_liberty $f}
read_liberty /src/physical/asap7_memory_macros/MACRO/MACRO_CORNER.lib
read_verilog /route/6_final.v
link_design ot_hdc_v41_fh_macro_ctx
read_sdc /route/6_final.sdc
read_spef /route/6_final.spef
set_propagated_clock [all_clocks]
report_units
puts "FHCAP clocks"; report_clock_properties
set macros [get_cells -hierarchical *u_sram]
set mq [get_pins -hierarchical *u_sram/rd_out*]
set ma [get_pins -hierarchical *u_sram/r_addr_in*]
set mw [get_pins -hierarchical *u_sram/w*_in*]
set mc [get_pins -hierarchical *u_sram/clk]
puts "FHCAP macros [llength $macros] readpins [llength $mq] addresspins [llength $ma] clockpins [llength $mc]"
if {[llength $macros]!=64 || [llength $mq]!=8192 || [llength $mc]!=64} {error "Not full G4W16 real SRAM context"}
puts "FHCAP setup"; report_worst_slack -max -digits 6
puts "FHCAP hold"; report_worst_slack -min -digits 6
set nv 0; set nh 0;set eps [all_registers -data_pins]
foreach p $eps {
 set s [get_property $p slack_max];if {$s!="INF" && $s<0} {incr nv}
 set s [get_property $p slack_min];if {$s!="INF" && $s<0} {incr nh}
}
puts "FHCAP failing setup $nv hold $nh of [llength $eps]"
puts "FHCAP path worst_setup"
report_checks -path_delay max -group_path_count 1 -format full_clock_expanded -digits 6
puts "FHCAP path worst_hold"
report_checks -path_delay min -group_path_count 1 -format full_clock_expanded -digits 6
puts "FHCAP path SRAM_read_setup"
report_checks -from $mq -path_delay max -group_path_count 1 -format full_clock_expanded -digits 6
puts "FHCAP path SRAM_read_hold"
report_checks -from $mq -path_delay min -group_path_count 1 -format full_clock_expanded -digits 6
puts "FHCAP path SRAM_address_setup"
report_checks -to $ma -path_delay max -group_path_count 1 -format full_clock_expanded -digits 6
puts "FHCAP path SRAM_address_hold"
report_checks -to $ma -path_delay min -group_path_count 1 -format full_clock_expanded -digits 6
puts "FHCAP path SRAM_write_setup"
report_checks -to $mw -path_delay max -group_path_count 1 -format full_clock_expanded -digits 6
puts "FHCAP path SRAM_write_hold"
report_checks -to $mw -path_delay min -group_path_count 1 -format full_clock_expanded -digits 6
puts "FHCAP slew"
report_check_types -max_slew -violators -digits 6 -no_line_splits
puts "FHCAP cap"
report_check_types -max_capacitance -violators -digits 6 -no_line_splits
puts "FHCAP fanout"
report_check_types -max_fanout -violators -digits 6 -no_line_splits
puts "FHCAP macro_clock_checks"
report_check_types -min_period -min_pulse_width -violators -digits 6 -no_line_splits
puts "FHCAP end"
'''


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--route-base',type=Path,required=True)
    ap.add_argument('--out',type=Path,required=True)
    a=ap.parse_args();base=a.route_base.resolve();out=a.out.resolve()
    out.mkdir(parents=True,exist_ok=False)
    inputs=[base/f'6_final.{ext}' for ext in ('v','spef','sdc','odb')]
    for p in inputs:
        if not p.is_file():raise SystemExit(f'Missing final artifact {p}')
    text=inputs[2].read_text()
    for expr in (r'-period\s+833\.333',r'-setup\s+60(?:\.0*)?\b',r'-hold\s+25(?:\.0*)?\b'):
        if not re.search(expr,text):raise SystemExit('Clock/uncertainty mismatch')
    rec=dict(scope='G4W16 conditional child with real protected SRAM clock/load/capture paths and first consumers; not fullparent proof',
             original_sha256={p.name:sha(p) for p in inputs},
             tools_sha256={p:sha(ROOT/p) for p in ('tools/dsrom_fh_capture_sta.py','tools/run_abi3_physical.py','tools/orfs_allcorner_spef.py')},
             period_ps=833.333,setup_uncertainty_ps=60,hold_uncertainty_ps=25,corners={},adopted=False)
    for corner in ('ss','ff'):
        tcl=TCL.replace('TAG',corner.upper()).replace('MACRO',MACRO).replace('CORNER',corner)
        (out/f'{corner}.tcl').write_text(tcl)
        cmd=['docker','run','--rm','-e','OMP_NUM_THREADS=16','-v',f'{ROOT}:/src:ro','-v',f'{base}:/route:ro','-v',f'{out}:/out',
             'openroad/orfs:latest','bash','-lc',f'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; sta -exit /out/{corner}.tcl']
        p=subprocess.run(cmd,capture_output=True,text=True);log=p.stdout+p.stderr
        (out/f'{corner}.log').write_text(log)
        r=dict(exit=p.returncode,macro_lib_sha256=sha(ROOT/'physical/asap7_memory_macros'/MACRO/f'{MACRO}_{corner}.lib'))
        for k in ('setup','hold'):
            m=re.search(rf'FHCAP {k}\s+worst slack (?:max|min) (\S+)',log)
            r[k+'_wns_ps']=float(m.group(1)) if m else None
        m=re.search(r'FHCAP failing setup (\d+) hold (\d+) of (\d+)',log)
        if m:r.update(failing_setup_endpoints=int(m[1]),failing_hold_endpoints=int(m[2]),endpoints=int(m[3]))
        m=re.search(r'FHCAP macros (\d+) readpins (\d+) addresspins (\d+) clockpins (\d+)',log)
        if m:r.update(macros=int(m[1]),readpins=int(m[2]),addresspins=int(m[3]),clockpins=int(m[4]))
        blocks=re.split(r'FHCAP path (\w+)\n',log)
        for i in range(1,len(blocks)-1,2):
            name,body=blocks[i],blocks[i+1].split('FHCAP ')[0]
            m=re.search(r'(-?[\d.]+)\s+slack \((?:MET|VIOLATED)\)',body)
            r[name+'_slack_ps']=float(m[1]) if m else None
        for k in ('slew','cap','fanout','macro_clock_checks'):
            body=log.split(f'FHCAP {k}\n')[-1].split('FHCAP ')[0]
            violations=[line.strip() for line in body.splitlines() if '(VIOLATED)' in line]
            r[k+'_violations']=violations
            if k=='slew':r['internal_slew_violations']=[v for v in violations if '/' in v.split()[0]]
        r['valid']=p.returncode==0 and 'Error' not in log and r.get('macros')==64 and r.get('clockpins')==64 and all(r.get(k) is not None for k in ('setup_wns_ps','hold_wns_ps','failing_setup_endpoints','failing_hold_endpoints','SRAM_read_setup_slack_ps','SRAM_read_hold_slack_ps','SRAM_address_setup_slack_ps','SRAM_address_hold_slack_ps','SRAM_write_setup_slack_ps','SRAM_write_hold_slack_ps'))
        rec['corners'][corner]=r
    ss,ff=rec['corners']['ss'],rec['corners']['ff']
    rec['timing_met']=ss['valid'] and ff['valid'] and ss['setup_wns_ps']>=0 and ff['hold_wns_ps']>=0 and ss['failing_setup_endpoints']==0 and ff['failing_hold_endpoints']==0
    rec['signal_integrity_met']=all(r['valid'] and not any(r[k+'_violations'] for k in ('slew','cap','fanout','macro_clock_checks')) for r in rec['corners'].values())
    (out/'sta.json').write_text(json.dumps(rec,indent=2)+'\n')
    print(json.dumps(rec,indent=2))

if __name__=='__main__':main()
