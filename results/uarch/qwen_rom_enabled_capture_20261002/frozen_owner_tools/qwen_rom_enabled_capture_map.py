#!/usr/bin/env python3
"""Map full exact enabled capture cone and screen its actual cell pin loads at SS.

No P&R, new engine RTL or clock relaxation. Missing wire/skew/control buffering
remains explicit. Preserve every failed build and preparation source hash.
"""
import argparse
import shutil
import hashlib
import json
import re
from pathlib import Path
from qwen_rom_kv_finite_window_gate import guarded_process
from qwen_rom_macro_capture_sta import parse_slack

ROOT=Path(__file__).resolve().parents[1]


def block(text,start):
    pos=text.index('{',start);depth=1;i=pos+1
    while depth:
        depth+=(text[i]=='{')-(text[i]=='}');i+=1
    return text[start:i]


def merge(libraries):
    text=libraries[0].read_text();prefix=text[:re.search(r'\bcell\s*\(',text).start()]
    known={m[2]:block(prefix,m.start()) for m in re.finditer(r'\b(lu_table_template|power_lut_template)\s*\(([^)]+)\)',prefix)}
    cells={};extra=[]
    for path in libraries:
        raw=path.read_text();header=raw[:re.search(r'\bcell\s*\(',raw).start()]
        for m in re.finditer(r'\b(lu_table_template|power_lut_template)\s*\(([^)]+)\)',header):
            definition=block(header,m.start())
            if m[2] not in known:known[m[2]]=definition;extra.append(definition)
            elif re.sub(r'\s+','',known[m[2]])!=re.sub(r'\s+','',definition):raise ValueError('Conflicting timing template '+m[2])
        for m in re.finditer(r'\bcell\s*\(([^)]+)\)',raw):
            name=m[1].strip().strip('"');definition=block(raw,m.start())
            if name in cells and cells[name]!=definition:raise ValueError('Conflicting cell '+name)
            cells[name]=definition
    return prefix+'\n'.join(extra+list(cells.values()))+'\n}\n',cells


def timing_subset(merged,cells,counts):
    """Keep canonical templates/cell bodies; discard only unmapped cells.

    The ABC input remains the full merged library. This STA view avoids
    diagnostics on unused library-only cells without waiving any diagnostics
    on an instantiated cell or changing any timing/pin definition.
    """
    missing=set(counts)-set(cells)-{'ot_rom_4096x266_m8'}
    if missing:raise ValueError('Unbound mapped cells: '+str(sorted(missing)))
    prefix=merged[:re.search(r'\bcell\s*\(',merged).start()]
    return prefix+'\n'.join(cells[name] for name in sorted(counts) if name in cells)+'\n}\n'


def path_loads(output):
    return [dict(fanout=int(m[1]),cap_fF=float(m[2]),slew_ps=float(m[3]),
                 delay_ps=float(m[4]),pin=m[5]) for m in re.finditer(
        r'^\s+(\d+)\s+([\d.]+)\s+([\d.]+)\s+([-\d.]+)\s+[-\d.]+\s+[\^v]\s+(\S+)',output,re.M)]


def run(preparation,libraries,workdir,result,yosys,sta):
    if workdir.exists() or result.exists():raise ValueError('Refusing to reuse/overwrite evidence')
    prep=json.loads((preparation/'preparation.json').read_text());cone=(preparation/'exact_cone.v').read_bytes()
    if hashlib.sha256(cone).hexdigest()!=prep['cone_sha256']:raise ValueError('Cone hash mismatch')
    for p,h in prep['source_sha256'].items():
        if hashlib.sha256((ROOT/p).read_bytes()).hexdigest()!=h:raise ValueError('Preparation source changed: '+p)
    merged,cells=merge(libraries);workdir.mkdir(parents=True);(workdir/'mapped_lib_ss.lib').write_text(merged)
    lib=workdir/'mapped_lib_ss.lib';macro=ROOT/'physical/asap7_memory_macros/ot_rom_4096x266_m8/ot_rom_4096x266_m8_ss.lib'
    script=workdir/'synth.ys';script.write_text(f'''read_liberty -lib {lib}
read_liberty -lib {macro}
read_verilog {preparation.resolve()/'exact_cone.v'}
hierarchy -check -top qwen_current_enabled_capture
synth -top qwen_current_enabled_capture
dfflibmap -liberty {lib}
abc -liberty {lib}
clean
stat -liberty {lib}
write_verilog -noattr -noexpr {workdir/'mapped.v'}
write_json {workdir/'mapped.json'}
''')
    rc,output=guarded_process([yosys,'-s',str(script)],workdir,workdir/'synth.log')
    record=dict(schema='opentallas.qwen-rom-enabled-capture-map.v1',status='FAIL_MAPPING',build_returncode=rc,
        preparation_sha256=hashlib.sha256((preparation/'preparation.json').read_bytes()).hexdigest(),
        source_sha256=prep['source_sha256'],mapper_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        tool_sha256={name:hashlib.sha256(Path(shutil.which(exe) or exe).resolve().read_bytes()).hexdigest() for name,exe in [('yosys',yosys),('sta',sta)]},
        macro_library_sha256=hashlib.sha256(macro.read_bytes()).hexdigest(),library_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in libraries},
        full_geometry_model=prep['model'],physical_build_ready=False,adoption=False,
        period_ps=833.333333,setup_uncertainty_ps=60,hold_uncertainty_ps=25,
        actual_wire_parasitics_bound=False,actual_clock_skew_bound=False,
        added_cycles=0,existing_MEM_EXTRA_charged_once=True,
        boundary='Exact full10-ROM enabled capture cone mapped at SS. Cell-pin capacitance is real mapped-library demand; wires/skew and physically inserted control/clock buffering are absent. No source changes, P&R or rate adoption.')
    if rc==0:
        net=json.loads((workdir/'mapped.json').read_text())['modules']['qwen_current_enabled_capture']
        counts={}
        for c in net['cells'].values():counts[c['type']]=counts.get(c['type'],0)+1
        if counts.get('ot_rom_4096x266_m8')!=10:raise ValueError('Macro geometry dropped')
        area=sum(count*float(re.search(r'\barea\s*:\s*([\d.]+)',cells[name])[1]) for name,count in counts.items() if name in cells)
        record.update(mapped_cell_counts=counts,mapped_logic_cell_area_um2=area,
                      mapped_netlist_sha256=hashlib.sha256((workdir/'mapped.v').read_bytes()).hexdigest(),
                      merged_library_sha256=hashlib.sha256(lib.read_bytes()).hexdigest())
        timing_lib=workdir/'used_ss_timing.lib';timing_lib.write_text(timing_subset(merged,cells,counts))
        record['timing_library_sha256']=hashlib.sha256(timing_lib.read_bytes()).hexdigest()
        tcl=workdir/'timing.tcl';tcl.write_text(f'''read_liberty {macro}
read_liberty {timing_lib}
read_verilog {workdir/'mapped.v'}
link_design qwen_current_enabled_capture
create_clock -name clk -period 833.333333 [get_ports clk]
set_clock_uncertainty -setup 60 [get_clocks clk]
set_clock_uncertainty -hold 25 [get_clocks clk]
set_clock_transition 20 [get_clocks clk]
report_units
report_checks -path_delay max -format full_clock_expanded -digits 6 -fields {{slew cap input net fanout}}
report_check_types -max_capacitance -max_slew -max_fanout
exit
''')
        trc,timing=guarded_process([sta,'-exit',str(tcl)],workdir,workdir/'timing.log')
        try:slack=parse_slack(timing) if trc==0 else None
        except ValueError:slack=None
        macro_tcl=workdir/'macro_paths.tcl'
        macro_tcl.write_text(tcl.read_text().replace('report_checks -path_delay max', 'report_checks -from [get_cells -hierarchical *u_rom] -path_delay max').replace('report_check_types -max_capacitance -max_slew -max_fanout\n',''))
        mrc,mtiming=guarded_process([sta,'-exit',str(macro_tcl)],workdir,workdir/'macro_paths.log')
        try:mslack=parse_slack(mtiming) if mrc==0 else None
        except ValueError:mslack=None
        loads=path_loads(timing);macro_loads=path_loads(mtiming)
        record.update(SS_macro_enabled_capture_slack_ps=mslack,macro_timing_returncode=mrc,
                      macro_path_pin_loads=macro_loads,worst_path_pin_loads=loads,
                      max_path_control_pin_load=max(loads,key=lambda x:x['fanout']) if loads else None,
                      library_limit_violations_present='(VIOLATED)' in timing.split('max slew')[-1] if 'max slew' in timing else None,
                      LUT_extrapolation_not_calibrated=True,FF_hold_in_context_closed=False,
                      macro_timing_report_sha256=hashlib.sha256((workdir/'macro_paths.log').read_bytes()).hexdigest(),
                      timing_returncode=trc,SS_worst_setup_slack_ps=slack,
                      status='BLOCKED_PRE_ROUTE_TIMING' if slack is not None and mslack is not None and (slack<0 or mslack<0) else 'BLOCKED_ROUTED_CONTEXT_REQUIRED' if slack is not None and mslack is not None else 'FAIL_TIMING_REPLAY',
                      timing_report_sha256=hashlib.sha256((workdir/'timing.log').read_bytes()).hexdigest())
    result.parent.mkdir(parents=True,exist_ok=True)
    with result.open('x') as f:json.dump(record,f,indent=2,sort_keys=True);f.write('\n')
    print(json.dumps(record,indent=2))
    return 1


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    for name in ['preparation','workdir','result']:ap.add_argument('--'+name,type=Path,required=True)
    ap.add_argument('--library',type=Path,action='append',required=True)
    ap.add_argument('--yosys',required=True);ap.add_argument('--sta',required=True);a=ap.parse_args()
    return run(a.preparation,a.library,a.workdir.resolve(),a.result,a.yosys,a.sta)


if __name__=='__main__':raise SystemExit(main())
