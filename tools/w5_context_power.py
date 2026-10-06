#!/usr/bin/env python3
"""Actual mapped W5 context activity and raw residual power; no energy credit.
The RTL precheck is solely preparation for the source-changing mapped bench.
"""
from pathlib import Path
import argparse,hashlib,json,subprocess,sys
import rom_stage_pg_power as base
import signoff_analysis as so
ROOT=Path(__file__).resolve().parents[1]
BENCH=ROOT/'rtl/experimental/w5_context/tb_w5_context_activity.sv'
SOURCES=[s for s in (ROOT/'results/rtl/rom_stage_context_20261005/sources.txt').read_text().splitlines()
         if '_bb.v' not in s]

def build(work, netlist=None):
    work.mkdir(parents=True,exist_ok=True)
    text=BENCH.read_text();removed=[]
    if netlist:
        text,removed=so.gate_level_bench(text,'ot_w5_context')
    bench=work/'bench.sv';bench.write_text(text)
    ctx=ROOT/'rtl/experimental/w5_context/ot_w5_context.sv'
    ref=work/'context_ref.sv';ref.write_text(ctx.read_text().replace('module ot_w5_context #','module ot_w5_context_ref #',1).replace('ot_w5_retn #','ot_v41_retn_w17w10 #'))
    top=work/'so_icarus_top.sv'
    top.write_text((ROOT/'tools/signoff/icarus_top.sv.in').read_text().replace('`timescale 1ps/1ps','`timescale 1fs/1fs')
                  .replace('@BENCH@','tb_w5_context_activity').replace('@HALF_PS@','416667').replace('@SCOPES@','bench.dut'))
    extra=[]
    if netlist:
        gl=work/'ot_w5_context_gl.v';so.netlist_accepting_params(netlist,gl,so.rtl_param_overrides([BENCH],'ot_w5_context'))
        types=so.netlist_cell_types(gl)|{'ICGx1_ASAP7_75t_R','DLLx1_ASAP7_75t_R'};extra=[gl]
    else:types={'ICGx1_ASAP7_75t_R','DLLx1_ASAP7_75t_R'}
    cells=work/'cells.v';cm=so.write_cell_models(base.LIBERTY,cells,types)
    rtl=[ROOT/s for s in SOURCES if not (netlist and s==str(ctx.relative_to(ROOT)))]
    exe=work/'sim.vvp';cmd=['iverilog','-g2012','-DSYNTHESIS','-s','so_icarus_top','-o',str(exe),
                          str(top),str(bench),str(ref),str(cells),*[str(p) for p in extra+rtl],str(ROOT/'rtl/v41die/ot_v41_retn_w17w10.sv'),str(ROOT/'rtl/v41rom/ot_v41_ret.sv')]
    p=subprocess.run(cmd,capture_output=True,text=True)
    (work/'build.log').write_text(p.stdout+p.stderr)
    meta={'mapped':bool(netlist),'source_sha256':{s:so.sha256_file(ROOT/s) for s in SOURCES},
          'bench_sha256':so.sha256_file(BENCH),'sim_period_ns':0.833334,'physical_period_ns':0.8333333333333333,
          'cell_models':cm,'removed_statements':removed,'compile_rc':p.returncode}
    if netlist:meta.update(netlist=str(netlist),netlist_sha256=so.sha256_file(netlist))
    (work/'build.json').write_text(json.dumps(meta,indent=2)+'\n')
    if p.returncode:raise RuntimeError('build failed; retained '+str(work/'build.log'))
    return exe,meta

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('command',choices=['rtl-precheck','activity','timing','power'])
    p.add_argument('--work',type=Path,required=True);p.add_argument('--routed',type=Path)
    p.add_argument('--hard-cfg',action='store_true')
    a=p.parse_args();a.work=a.work.resolve()
    global BENCH
    if a.hard_cfg: BENCH=ROOT/'rtl/experimental/w5_context/tb_w5_cfg_context.sv'
    if a.command=='rtl-precheck':
        exe,meta=build(a.work);r=subprocess.run(['vvp','-n',str(exe)],capture_output=True,text=True,cwd=a.work)
        log=r.stdout+r.stderr;(a.work/'sim.log').write_text(log)
        meta.update(run_rc=r.returncode,pass_=(r.returncode==0 and 'PASS actual W5 context' in log))
        (a.work/'precheck.json').write_text(json.dumps(meta,indent=2)+'\n');print(log,end='');return 0 if meta['pass_'] else 1
    if not a.routed:p.error('--routed required; actual mapped gate level only')
    if a.command=='activity':
        base.DUT='ot_w5_context';base.build=build;base.HALF_PS=416667
        base.WINDOWS={'active':(3000,4500),'pg_idle':(5000,6000),'cg_idle':(21000,22000)}
        return base.activity(a)
    if a.command=='timing':
        original=so.session_script
        diagnostic=(ROOT/'physical/w5_context/measure.tcl').read_text()
        so.session_script=lambda *args,**kwargs:original(*args,**kwargs)+'\n'+diagnostic
        r=so.analyze(a.routed,a.work,label='actual_w5_context_SSFF',record=None,saif=None,
          saif_scope='',groups=[],corners=['SS','FF'],derate=0,ir_sources=[],bump_pitch_um=140,
          cycles_per_token=None,activity_meta=None,tt_stages=['clock','timing'])
        (a.work/'timing.json').write_text(json.dumps(r,indent=2)+'\n')
        return 0
    act=json.loads((a.work/'activity.json').read_text())
    if not act['pass']:raise RuntimeError('mapped activity did not pass')
    res={'scope':'one actual protected W5 context; raw mapped TT activity/residual only',
         'physical_period_ns':0.8333333333333333,'energy_credit':False,'fairness_claim':False,
         'activity':act,'states':{}}
    for n,s in act['saif'].items():
        r=so.analyze(a.routed,a.work/('power_'+n),label='w5_context_'+n,record=None,
          saif=Path(s['path']),saif_scope='dut',groups=[],corners=['TT'],derate=0,
          ir_sources=[],bump_pitch_um=140,cycles_per_token=None,activity_meta=None,tt_stages=['power'])
        res['states'][n]={'power_w':r['corners']['TT']['power_w'],
                          'annotation':r['corners']['TT']['activity_annotation'],'routed':r['routed']}
    (a.work/'power.json').write_text(json.dumps(res,indent=2)+'\n');print(json.dumps(res['states'],indent=2));return 0
if __name__=='__main__':sys.exit(main())
