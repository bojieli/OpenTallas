#!/usr/bin/env python3
"""STA screen of indexed Qwen memory -> RVT capture, SS setup and FF hold.

Direct ungated capture is an optimistic component screen, not the mapped
enabled-capture cone, routed tile/spine, clock tree or PG qualification.
"""
import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path
from qwen_rom_kv_finite_window_gate import guarded_process

ROOT=Path(__file__).resolve().parents[1]
MACROS={'ot_rom_4096x266_m8':(266,12,False,0,0),
        'ot_sram_1r1w_128x256_m1_r2c2':(256,7,True,14,16),
        'ot_sram_1r1w_512x128_m4_r2c2':(128,9,True,14,14)}


def netlist(name):
    width,aw,sram,rr,cr=MACROS[name]
    ports=f'.clk(clk),.r_ce_in(ce),.r_addr_in(addr),.rd_out(q),.w_ce_in(1\'b0),.w_addr_in({aw}\'b0),.wd_in({width}\'b0),.w_mask_in({width}\'b0),.rr_en(2\'b0),.rr_addr({rr}\'b0),.cr_en(2\'b0),.cr_sel({cr}\'b0)' if sram else '.clk(clk),.ce_in(ce),.addr_in(addr),.rd_out(q)'
    return f'''module macro_capture(input clk,ce,input [{aw-1}:0] addr,output raw,captured);
wire [{width-1}:0] q;
{name} memory({ports});
assign raw=q[0];
DFFHQNx1_ASAP7_75t_R capture(.CLK(clk),.D(q[0]),.QN(captured));
endmodule
'''


def parse_slack(output):
    matches=re.findall(r'([-\d.]+)\s+slack\s+\((MET|VIOLATED)\)',output)
    if len(matches)!=1 or 'time 1ps' not in output:raise ValueError('Missing unique ps path/slack')
    if re.search(r'^(?:Error|Warning):',output,re.M):raise ValueError('STA diagnostics require review')
    return float(matches[0][0])


def run(workdir,result,seq_ss,seq_ff,sta):
    if workdir.exists() or result.exists():raise ValueError('Refusing to overwrite build/evidence')
    workdir.mkdir(parents=True)
    seq={'ss':seq_ss.resolve(),'ff':seq_ff.resolve()};pins={}
    for corner,path in seq.items():
        raw=path.read_bytes()
        if b'time_unit : "1ps"' not in raw or b'DFFHQNx1_ASAP7_75t_R' not in raw:raise ValueError('Capture library contract changed')
        pins['capture_'+corner]=hashlib.sha256(raw).hexdigest()
    for p in ['rtl/hdc/ot_qwen_rom_tile_w12.sv','tools/uarch_model.py','tools/qwen_rom_macro_capture_sta.py','tools/qwen_rom_kv_finite_window_gate.py']:
        pins[p]=hashlib.sha256((ROOT/p).read_bytes()).hexdigest()
    executable=Path(sta).resolve();pins['STA_executable']=hashlib.sha256(executable.read_bytes()).hexdigest()
    index=json.loads((ROOT/'physical/asap7_memory_macros/index.json').read_text());rows=[]
    cases=[(name,corner,20,2.88,False) for name in MACROS for corner in ['ss','ff']]
    cases.append(('ot_rom_4096x266_m8','ss',320,46.08,True))
    for name,corner,slew,load,negative in cases:
        label=name+'_'+corner+('_adverse' if negative else '')
        macro=ROOT/f'physical/asap7_memory_macros/{name}/{name}_{corner}.lib'
        raw=macro.read_bytes();h=hashlib.sha256(raw).hexdigest()
        if h!=index['macros'][name]['views'][macro.name]:raise ValueError('Macro liberty index mismatch')
        pins[str(macro.relative_to(ROOT))]=h
        verilog=workdir/(label+'.v');verilog.write_text(netlist(name))
        delay='max' if corner=='ss' else 'min'
        script=workdir/(label+'.tcl')
        script.write_text(f'''read_liberty {{{macro}}}
read_liberty {{{seq[corner]}}}
read_verilog {{{verilog}}}
link_design macro_capture
create_clock -name clk -period 833.333333 [get_ports clk]
set_clock_uncertainty -setup 60 [get_clocks clk]
set_clock_uncertainty -hold 25 [get_clocks clk]
set_clock_transition {slew} [get_clocks clk]
set_load {load} [get_ports raw]
report_units
report_checks -to [get_pins capture/D] -path_delay {delay} -format full_clock_expanded -digits 6 -fields {{slew cap input net fanout}}
exit
''')
        logfile=workdir/(label+'.log');rc,output=guarded_process([str(executable),'-exit',str(script)],workdir,logfile)
        try:slack=parse_slack(output) if rc==0 else None
        except ValueError:slack=None
        rows.append(dict(macro=name,corner=corner,clock_transition_ps=slew,added_load_fF=load,
                         negative_control=negative,returncode=rc,slack_ps=slack,
                         report=logfile.name,report_sha256=hashlib.sha256(logfile.read_bytes()).hexdigest(),
                         netlist_sha256=hashlib.sha256(verilog.read_bytes()).hexdigest(),script_sha256=hashlib.sha256(script.read_bytes()).hexdigest()))
    good=all(r['slack_ps'] is not None and (r['slack_ps']<0 if r['negative_control'] else r['slack_ps']>=0) for r in rows)
    r=dict(schema='opentallas.qwen-rom-macro-capture-sta.v1',status='PASS_COMPONENT_SCREEN' if good else 'FAIL',
           source_ref=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),source_sha256=pins,rows=rows,
           period_ps=833.333333,SS_setup_uncertainty_ps=60,FF_hold_uncertainty_ps=25,
           actual_tile_enabled_capture_mapped=False,wire_parasitics_bound=False,clock_tree_bound=False,RF_service_closed=False,PG_fit_closed=False,
           physical_build_ready=False,adoption=False,
           claim_boundary='Direct ungated macro-to-RVT-flop STA with ideal clock/interconnect and stated added load. Source ROM MEM_EXTRA capture has enable/feedback logic absent here. Positive slack is an optimistic bound, not routed in-context closure. No new engine, P&R, second position or rate proof.')
    result.parent.mkdir(parents=True,exist_ok=True)
    with result.open('x') as f:json.dump(r,f,indent=2,sort_keys=True);f.write('\n')
    print(json.dumps({'status':r['status'],'rows':rows},indent=2))
    return 0 if good else 1


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    for name in ['workdir','result','seq-ss','seq-ff']:ap.add_argument('--'+name,type=Path,required=True)
    ap.add_argument('--sta',required=True);a=ap.parse_args()
    return run(a.workdir.resolve(),a.result,a.seq_ss,a.seq_ff,a.sta)


if __name__=='__main__':raise SystemExit(main())
