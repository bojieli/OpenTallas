#!/usr/bin/env python3
"""Prepare exact two-master nominal M5 placement-RC diagnostic, not closure."""
import argparse
import hashlib
import json
import re
import shutil
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'hier_contract'))
import pinreg_audit as A


def clock_box(lef):
    m=re.search(r'\bPIN\s+clk\s+(.*?)\n\s*END\s+clk\s',lef.read_text(),re.S)
    assert m
    pairs=re.findall(r'LAYER\s+(\S+)\s*;\s*RECT\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s*;',m[1])
    assert pairs and len({p[0] for p in pairs})==1,pairs
    layer=pairs[0][0];rects=[list(map(float,p[1:])) for p in pairs]
    # Published clock access rectangles may overlap; only a truly rectangular
    # continuous union is allowed for source-port coincidence, never a bbox gap.
    assert len({(r[0],r[2]) for r in rects})==1,rects
    intervals=sorted((r[1],r[3]) for r in rects);end=intervals[0][1]
    for lo,hi in intervals[1:]:assert lo<=end;end=max(end,hi)
    return layer,[rects[0][0],intervals[0][0],rects[0][2],end]


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--view-root',required=True,type=Path);p.add_argument('--plan',required=True,type=Path)
    p.add_argument('--out',required=True,type=Path);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=True)
    plan=json.loads(a.plan.read_text());shutil.copy2(a.plan,a.out/'plan.json')
    views=plan['actual_views'];meta={};libs={}
    for role,r in views.items():
        source=a.view_root/r['view'];dest=a.out/role;dest.mkdir(exist_ok=True)
        for rel,h in r['files'].items():
            f=a.view_root/rel;assert hashlib.sha256(f.read_bytes()).hexdigest()==h
            shutil.copy2(f,dest/f.name)
        lef=dest/(r['master']+'.lef');layer,rect=clock_box(lef)
        ox,oy=r['origin_um'];meta[role]={**r,'clock_layer':layer,'clock_rect_global_um':[rect[0]+ox,rect[1]+oy,rect[2]+ox,rect[3]+oy]}
        libs[role]=A.parse_lib(dest/(r['master']+'_tt.lib'))
    # Actual bus declarations inferred from the published flattened ETM pins.
    def groups(lib,direction):
        out={}
        for pin,pdata in lib['pins'].items():
            if pdata['dir']!=direction:continue
            m=re.fullmatch(r'(\w+)\[(\d+)\]',pin)
            if m:out.setdefault(m[1],[]).append(int(m[2]))
        for bus,indices in out.items():assert sorted(indices)==list(range(max(indices)+1)),bus
        return {bus:max(indices)+1 for bus,indices in out.items()}
    b=libs['bank_Q'];d=libs['existing_BX_D'];bg=groups(b,'input');bo=groups(b,'output');dg=groups(d,'input');do=groups(d,'output')
    assert bo['q']==512 and dg['d']==512
    connections=['.clk(ca)',".rst_n(1'b1)",".re(1'b0)",".we(1'b0)",".VDD(1'b1)",".VSS(1'b0)"]
    connections += [f'.{bus}({n}\'b0)' for bus,n in bg.items()]
    connections += [f'.{bus}(bank_{bus})' for bus in bo]
    decl='\n'.join(f'wire [{n-1}:0] bank_{bus};' for bus,n in bo.items())
    station=[".clk(cb)",".VDD(1'b1)",".VSS(1'b0)",'.d(bxd)']
    station += [f'.{bus}()' for bus in do]
    selected=["1'b0"]*512;selected[511-219]='bank_q[286]'
    net='module pair(input ca,cb);\n'+decl+'\nwire [511:0] bxd;\nassign bxd={'+','.join(selected)+'};\n'
    net+=f"{meta['bank_Q']['master']} bank("+', '.join(connections)+');\n'
    net+=f"{meta['existing_BX_D']['master']} bx("+', '.join(station)+');\nendmodule\n'
    (a.out/'pair.v').write_text(net)
    for co in ('tt','ff','ss'):
        text='''set plat /OpenROAD-flow-scripts/flow/platforms/asap7
read_lef $plat/lef/asap7_tech_1x_201209.lef
read_lef $plat/lef/asap7sc7p5t_28_R_1x_220121a.lef
'''
        for role,r in meta.items():text+=f"read_lef /probe/{role}/{r['master']}.lef\nread_liberty /probe/{role}/{r['master']}_{co}.lib\n"
        text+='''read_verilog /probe/pair.v
link_design pair
set sites {}
foreach lib [[ord::get_db] getLibs] {foreach site [$lib getSites] {lappend sites [$site getName]}}
set sites [lsort -unique $sites]
if {[llength $sites]!=1} {error "ambiguous actual placement site"}
initialize_floorplan -site [lindex $sites 0] -die_area {0 0 345.6 211.68} -core_area {0 0 345.6 211.68}
set block [ord::get_db_block]
set dbu [[ord::get_db_tech] getDbUnitsPerMicron]
'''
        for role,inst,port in [('bank_Q','bank','ca'),('existing_BX_D','bx','cb')]:
            r=meta[role];x,y=r['origin_um'];coords=r['clock_rect_global_um']
            text+=f'''set i [$block findInst {inst}]
$i setLocation [expr {{round({x}*$dbu)}}] [expr {{round({y}*$dbu)}}]
$i setOrient R0
$i setPlacementStatus FIRM
set bt [$block findBTerm {port}]
set bp [odb::dbBPin_create $bt]
$bp setPlacementStatus FIRM
set layer [[ord::get_db_tech] findLayer {r['clock_layer']}]
odb::dbBox_create $bp $layer {' '.join('[expr {round('+str(z)+'*$dbu)}]' for z in coords)}
set actual [[$i findITerm clk] getBBox]
set source [$bt getBBox]
foreach axis {{xMin yMin xMax yMax}} {{
  if {{[$actual $axis] != [$source $axis]}} {{error "clock entry coincidence mismatch {inst} $axis"}}
}}
puts "PAIR_CLOCK_GEOMETRY {co} {inst} coincidence=exact layer={r['clock_layer']}"
'''
        text+='''create_clock -name A -period 833.333 -waveform {0 416.6665} [get_ports ca]
create_clock -name B -period 833.333 -waveform {0 416.6665} [get_ports cb]
set_input_transition 0 [get_ports {ca cb}]
set_clock_transition 0 [all_clocks]
set_clock_uncertainty -setup 210 [all_clocks]
set_clock_uncertainty -hold 100 [all_clocks]
set_propagated_clock [all_clocks]
proc sample {tag} {
  foreach kind {max min} {
    set paths [find_timing_paths -from [get_pins {bank/q[286]}] -to [get_pins {bx/d[219]}] -path_delay $kind -group_path_count 1]
    if {[llength $paths]!=1} {error "missing selected actual macro path $kind"}
    set p [lindex $paths 0]
    puts "PAIR_PATH $tag $kind slack=[get_property $p slack]"
  }
  report_checks -from [get_pins {bank/q[286]}] -to [get_pins {bx/d[219]}] -path_delay max -format full_clock_expanded -fields {slew cap input fanout} -digits 6
  report_checks -from [get_pins {bank/q[286]}] -to [get_pins {bx/d[219]}] -path_delay min -format full_clock_expanded -fields {slew cap input fanout} -digits 6
}
'''
        for role,clk in [('bank_Q','A'),('existing_BX_D','B')]:text+=f"set_clock_latency -source {-plan['corners'][co][role]['R_ps']} [get_clocks {clk}]\n"
        text+=f'''sample "{co}_pin_cap_only"
source $plat/setRC.tcl
# This specific estimate treats all Manhattan wire as nominal M5; it is not
# extracted M4-access/via/M5 topology or SS RC qualification.
set_wire_rc -signal -layer M5
set_wire_rc -clock -layer M5
estimate_parasitics -placement
'''
        # Measure actual same-corner entry estimate at lambda0, then compensate.
        for inst,clk,role in [('bank','A','bank_Q'),('bx','B','existing_BX_D')]:
            R=plan['corners'][co][role]['R_ps']
            text+=f'''set_clock_latency -source 0 [get_clocks {clk}]
set wire [get_property [get_pins {inst}/clk] arrival_max_rise]
puts "PAIR_ENTRY {co} {inst} lambda0_wire=$wire childR={R}"
set_clock_latency -source [expr {{-$wire-{R}}}] [get_clocks {clk}]
set now [get_property [get_pins {inst}/clk] arrival_max_rise]
if {{abs($now+{R})>0.01}} {{error "entry compensation failure {inst}"}}
puts "PAIR_COMP {co} {inst} phi=[expr {{$now+{R}}}]"
'''
        text+=f'''sample "{co}_nominal_M5"
report_arrival -digits 6 [get_pins {{bank/q[286]}}]
report_arrival -digits 6 [get_pins {{bx/d[219]}}]
report_clock_properties [all_clocks]
write_sdc /probe/executed_{co}.sdc
write_db /probe/pair_{co}.odb
puts "PAIR_PASS {co} nominal_M5_placementRC_diagnostic"
exit
'''
        (a.out/f'probe_{co}.tcl').write_text(text)
    manifest={'scope':__doc__,'plan_sha256':hashlib.sha256(a.plan.read_bytes()).hexdigest(),'actual_views':meta,'source_generator_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'geometry_model':'Nominal M5 for all Manhattan wire; exact source/destination master positions, M4 access and M5 corridor only geometry plan, not extracted mixed-layer/via path.'}
    (a.out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')


if __name__=='__main__':main()
