#!/usr/bin/env python3
"""Prepare actual OWN/12-child/real-ICG static gating STA; no native qualification."""
import argparse
import hashlib
import json
import re
import shutil
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'hier_contract'))
import pinreg_audit as A


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--plan',required=True,type=Path);p.add_argument('--out',required=True,type=Path)
    a=p.parse_args();plan=json.loads(a.plan.read_text());a.out.mkdir(parents=True,exist_ok=True)
    binding=json.loads(Path(plan['binding_path']).read_text())
    assert hashlib.sha256(Path(plan['binding_path']).read_bytes()).hexdigest()==plan['binding_sha256']
    extraction=json.loads(Path(binding['mapping_packet']).read_text())
    row=next(r for r in extraction['rows'] if r['variant']=='eg')
    parent=json.loads(Path(binding['parent_EG']).read_text())['modules'][row['source_top']]
    assert parent['ports']['clk']['bits']==[2]
    assert parent['cells']['u_own']['connections']['cut_8870']==[8870]
    assert parent['cells']['u_own']['connections']['cut_2']==[2]
    for r in row['child_clocks']:
        g=parent['cells'][r['ICG_instance']]
        assert g['type']==binding['ICG_cell']
        assert g['connections']['CLK']==parent['ports'][r['parent_clock_port']]['bits']
        assert g['connections']['ENA']==[8870] and g['connections']['SE']==['0']
        assert parent['cells'][r['instance']]['connections']['clk']==g['connections']['GCLK']
        assert r['enable_own_port']=='cut_8870' and r['original_clock_bit']==7768
    views=[{'master':'ot_smh_own_eg','files':binding['own_files']},*[
        {'master':Path(v['directory']).name,'files':v['files']} for v in binding['children']]]
    tables={}
    for v in views:
        d=a.out/v['master'];d.mkdir(exist_ok=True)
        for record in v['files']:
            f=Path(record['path']);assert hashlib.sha256(f.read_bytes()).hexdigest()==record['sha256']
            shutil.copy2(f,d/f.name)
        tables[v['master']]=A.parse_lib(d/(v['master']+'_tt.lib'))
    seq=a.out/'SEQ';seq.mkdir(exist_ok=True)
    for c,rec in plan['SEQ_sources'].items():
        f=Path(rec['path']);assert hashlib.sha256(f.read_bytes()).hexdigest()==rec['sha256']
        shutil.copy2(f,seq/f.name)
    def connections(master,clock_pin,clock,selected=None):
        pins=tables[master]['pins'];selected=selected or {};buses={};scalar={}
        for pin,rec in pins.items():
            m=re.fullmatch(r'(\w+)\[(\d+)\]',pin)
            if m:buses.setdefault(m[1],[]).append((int(m[2]),rec['dir']))
            else:scalar[pin]=rec['dir']
        out=[]
        for pin,direction in scalar.items():
            if pin==clock_pin:value=clock
            elif pin in selected:value=selected[pin]
            elif direction=='output':value=''
            elif direction=='input':value="1'b1" if pin in ('VDD','rst_n','cut_3') else "1'b0"
            else:continue
            out.append(f'.{pin}({value})')
        for bus,rs in buses.items():
            assert len({d for i,d in rs})==1
            width=max(i for i,d in rs)+1;assert sorted(i for i,d in rs)==list(range(width))
            value='' if rs[0][1]=='output' else f"{width}'b0"
            out.append(f'.{bus}({value})')
        return ', '.join(out)
    net='module gating(input clk,'+','.join(r['parent_clock_port'] for r in row['child_clocks'])+');\nwire ena;\n'
    net+='ot_smh_own_eg own('+connections('ot_smh_own_eg','cut_2','clk',{'cut_8870':'ena'})+');\n'
    for i,r in enumerate(row['child_clocks']):
        net+=f"wire gc_{i};\n{binding['ICG_cell']} gate_{i}(.CLK({r['parent_clock_port']}), .ENA(ena), .SE(1'b0), .GCLK(gc_{i}));\n"
        net+=r['master']+f' child_{i}('+connections(r['master'],'clk',f'gc_{i}')+');\n'
    net+='endmodule\n';(a.out/'gating.v').write_text(net)
    for c in ('tt','ff','ss'):
        text='''set plat /OpenROAD-flow-scripts/flow/platforms/asap7
read_lef $plat/lef/asap7_tech_1x_201209.lef
read_lef $plat/lef/asap7sc7p5t_28_R_1x_220121a.lef
'''
        text+=f"read_liberty /probe/SEQ/{Path(plan['SEQ_sources'][c]['path']).name}\n"
        for v in views:
            text+=f"read_lef /probe/{v['master']}/{v['master']}.lef\nread_liberty /probe/{v['master']}/{v['master']}_{c}.lib\n"
        text+='read_verilog /probe/gating.v\nlink_design gating\n'
        text+='create_clock -name OWN_RAW -period 833.333 -waveform {0 416.6665} [get_ports clk]\n'
        for i,r in enumerate(row['child_clocks']):
            text+=f"create_clock -name RAW_{i} -period 833.333 -waveform {{0 416.6665}} [get_ports {r['parent_clock_port']}]\n"
            text+=f"create_generated_clock -name G_{i} -master_clock RAW_{i} -source [get_ports {r['parent_clock_port']}] -divide_by 1 [get_pins gate_{i}/GCLK]\n"
        text+='''set_input_transition 0 [all_inputs]
set_clock_transition 0 [get_clocks OWN_RAW]
# No generated GCLK slew override. Its real ICG output slew stays observable.
set_propagated_clock [all_clocks]
set_clock_uncertainty -setup 150 [all_clocks]
set_clock_uncertainty -hold 100 [all_clocks]
proc check_paths {tag} {
 set result [dict create]
 for {set i 0} {$i<12} {incr i} {
  foreach edge {rise fall} {
   foreach kind {max min} {
    set cmd [list find_timing_paths -from [get_pins own/cut_8870] -${edge}_to [get_pins gate_$i/ENA] -path_delay $kind -group_path_count 1]
    set paths [{*}$cmd]
    if {[llength $paths]!=1} {error "missing actual ENA $i $edge $kind check"}
    set path [lindex $paths 0]
    set sc [get_property [get_property $path startpoint_clock] full_name]
    set ec [get_property [get_property $path endpoint_clock] full_name]
    if {$sc ne "OWN_RAW" || $ec ne "RAW_$i"} {error "wrong actual gating clock association $i $sc $ec"}
    set slack [get_property $path slack]
    dict set result $i $edge $kind $slack
    puts "SM_GATE_PATH $tag $i $edge $kind slack=$slack launch=$sc capture=$ec"
   }
  }
 }
 return $result
}
'''
        ownR=plan['own_ENA'][c]['R_ps'];text+=f"set_clock_latency -source {-ownR} [get_clocks OWN_RAW]\n"
        text+=f"set ownarr [get_property [get_pins own/cut_2] arrival_max_rise]\nif {{abs($ownarr+{ownR})>0.01}} {{error \"OWN raw phase mismatch\"}}\n"
        text+=f'set baseline [check_paths {c}_before_entry_comp]\n'
        if c=='tt':text+='set levels [open /probe/TT_levels.tcl w]\n'
        else:text+='source /probe/TT_levels.tcl\n'
        for i,r in enumerate(plan['child_instances']):
            R=r['corners'][c]['child_R_ps']
            text+=f'''set rise [get_property [get_pins child_{i}/clk] arrival_max_rise]
set fall [get_property [get_pins child_{i}/clk] arrival_max_fall]
set slew [get_property [get_pins gate_{i}/GCLK] slew_max_rise]
puts "SM_GATE_CAL {c} {i} actual_parent={r['instance']} child={r['master']} childR={R} gate_rise=$rise gate_fall=[expr {{$fall-416.6665}}] GCLK_slew=$slew"
set_clock_latency -source [expr {{-{R}-$rise}}] [get_clocks RAW_{i}]
set sm_gate_delta({i}) [expr {{{R}+$rise}}]
set phi [expr {{[get_property [get_pins child_{i}/clk] arrival_max_rise]+{R}}}]
if {{abs($phi)>0.02}} {{error "child phase mismatch {i}"}}
puts "SM_GATE_PHI {c} {i} phi=$phi"
'''
            if c=='tt':
                text+=f'''set u [expr {{max({ownR},{R}+$rise)>300 ? 210 : 150}}]
puts $levels "set sm_gate_U({i}) $u"
puts "SM_GATE_LEVEL {i} TTtotalR=[expr {{{R}+$rise}}] uncertainty=$u"
'''
            else:text+=f'set u $sm_gate_U({i})\n'
            text+=f"set_clock_uncertainty -setup $u -from [get_clocks OWN_RAW] -to [get_clocks RAW_{i}]\n"
            text+=f'set current_U({i}) $u\n'
        if c=='tt':text+='close $levels\n'
        text+=f'''set after [check_paths {c}]
for {{set i 0}} {{$i<12}} {{incr i}} {{
 foreach edge {{rise fall}} {{
  foreach kind {{max min}} {{
   set before [dict get $baseline $i $edge $kind]
   set now [dict get $after $i $edge $kind]
   set expected [expr {{$before+($kind eq "max" ? -$sm_gate_delta($i)-($current_U($i)-150) : $sm_gate_delta($i))}}]
   if {{abs($now-$expected)>0.04}} {{error "gating phase/budget accounting mismatch $i $edge $kind"}}
   puts "SM_GATE_ACCOUNT {c} $i $edge $kind actual=$now expected=$expected"
  }}
 }}
}}
report_checks -from [get_pins own/cut_8870] -path_delay max -format full_clock_expanded -fields {{slew cap input fanout}} -group_path_count 12 -digits 6
report_checks -from [get_pins own/cut_8870] -path_delay min -format full_clock_expanded -fields {{slew cap input fanout}} -group_path_count 12 -digits 6
report_check_types -min_pulse_width -verbose
report_check_types -max_capacitance -verbose
report_arrival -digits 6 [get_pins own/cut_8870]
report_slews -digits 6 [get_pins own/cut_8870]
report_clock_properties [all_clocks]
write_sdc /probe/executed_{c}.sdc
puts "SM_GATING_PASS {c} static_diagnostic_only_no_native_phase_qualification"
exit
'''
        (a.out/f'probe_{c}.tcl').write_text(text)
    shutil.copy2(a.plan,a.out/'plan.json');shutil.copy2(plan['binding_path'],a.out/'binding.json')
    manifest={'helper_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'plan_sha256':hashlib.sha256(a.plan.read_bytes()).hexdigest(),'image_id':plan['image_id'],'mapping_assertions':'All12 parent RAW→ICG CLK, OWN8870→ENA, SE0, ICG GCLK→assignedchildCLK verified exactly. Fixture names child_i/gate_i explicitly surrogate labels bound to original instances.','IO_policy':'Only13 actual clock sources at top; macro resetn/cut3 static1, other unusedDATA0, outputsunused. Isolated timingarc only; no native/functional proof.','clock_wire_policy':'Zero-parasitics ideal entries/ENA wires. Real ICG insertion and output slew computed from actual childcap; original child insertion anchor0 does not establish its conditional R at delivered nonzero GCLK slew.'}
    (a.out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')


if __name__=='__main__':main()
