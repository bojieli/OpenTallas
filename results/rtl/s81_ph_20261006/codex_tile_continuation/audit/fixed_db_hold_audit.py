#!/usr/bin/env python3
"""Read-only STA audit on EPYC3. No route/ECO, source mutation or acceptance record."""
import json, pathlib, subprocess, hashlib
ROOT=pathlib.Path('/srv/opentallas-scratch2/scratch/claude/closure-loop')
OUT=pathlib.Path('/srv/opentallas-scratch2/scratch/codex/s81-tiles/hold-audit-1ee4b8967')
OUT.mkdir(parents=True,exist_ok=True)
cases=[('dsfd_ctrl_pc','093da5918',332,191,330,196),('dsfd_svcio_od','093da5918',280,156,None,None),('dsfd_colt_lane','7345266ce-e',494,276,None,None)]
for master,sha,L,bmin,Lh,hmin in cases:
    run=ROOT/f's81ph-{master}-{sha}'
    label=f's81ph_{master}_{sha.replace("-","_")}'
    work=run/'routes'/label/'work/orfs'
    src=pathlib.Path((run/'cl/SRC_DIR').read_text().strip())
    script=(work/'w18_sta_ff.tcl').read_text().split('puts "OT_CORNER')[0]
    script+='''
proc outs {} {
 set d [dict create]
 foreach p [all_outputs] {set s [get_property $p slack_min]; if {$s ne "INF"} {dict set d [get_full_name $p] $s}}
 return $d
}
proc summary {name d} {
 set worst 1e9
 dict for {p s} $d {if {$s < $worst} {set worst $s}}
 puts "AUDIT $name output_worst_ps=$worst pins=[dict size $d]"
}
summary original [outs]
set oc {}; set oh {}
foreach p [all_outputs] {
 set n [get_full_name $p]
 if {[llength [get_clocks -quiet vclk_h]] && [regexp {^(k_v|k_addr|k_len|k_tag|k_we|k_wdata|k_wstrb|kr_rdy|phy_rst_n)(\\[|$)} $n]} {lappend oh $p} else {lappend oc $p}
}
'''
    script+=f'set_output_delay -min {L-bmin-40} -clock vclk $oc\n'
    if Lh: script+=f'set_output_delay -min {Lh-hmin-40} -clock vclk_h $oh\n'
    script+='set new [outs]\nsummary new_formula $new\n'
    script+=f'set_clock_latency {bmin} [get_clocks vclk]\nset_output_delay -min -15 -clock vclk $oc\nset_clock_uncertainty -hold 50 -from [get_clocks core_clk] -to [get_clocks vclk]\n'
    if Lh:script+=f'set_clock_latency {hmin} [get_clocks vclk_h]\nset_output_delay -min -15 -clock vclk_h $oh\nset_clock_uncertainty -hold 50 -from [get_clocks hbm_clk] -to [get_clocks vclk_h]\n'
    script+='''set explicit [outs]
summary explicit_zero_wire_FF_model $explicit
set maxdiff 0
set worstport ""
dict for {p s} $new {set diff [expr {abs($s-[dict get $explicit $p])}]; if {$diff>$maxdiff} {set maxdiff $diff;set worstport $p}}
puts "AUDIT equivalence max_abs_diff_ps=$maxdiff worstport=$worstport"
if {$maxdiff > 0.001} {exit 1}
exit
'''
    tcl=OUT/f'{master}.tcl';tcl.write_text(script)
    cmd=['docker','run','--rm','--network','none','-v',f'{work}:/work:ro','-v',f'{src}:/src:ro','-v',f'{OUT}:/audit:ro','openroad/orfs:asap7lock','/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad','-no_init','-exit',f'/audit/{master}.tcl']
    with (OUT/f'{master}.log').open('w') as f: r=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT)
    inputs={}
    for p in (work/'results').glob('asap7/*/base/6_final.*'):
        if p.suffix in ('.odb','.sdc','.spef'):inputs[str(p)]=hashlib.sha256(p.read_bytes()).hexdigest()
    (OUT/f'{master}.json').write_text(json.dumps(dict(master=master,source=sha,rc=r.returncode,inputs=inputs,script_sha256=hashlib.sha256(tcl.read_bytes()).hexdigest(),note='Original pre-ECO physical database; conditional IO model comparison, NOT closure/adoption'),indent=2)+'\n')
    print(master,'rc',r.returncode,flush=True)
    for line in (OUT/f'{master}.log').read_text().splitlines():
        if line.startswith('AUDIT') or 'Error' in line:print(line,flush=True)
