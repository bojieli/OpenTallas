#!/usr/bin/env python3
"""Minimum baseline-link repair execution. No cut-through/PHY/rate substitution.

Run remotely: exact component cases first, then one contextual mapped route.
Pinned originals are only read; bench instantiation copies select the opt-in.
"""
import argparse, ast, hashlib, json, math, os, re, subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
RTL=['rtl/dsrom_sys/ot_dsrom_link_rt_clock.sv','rtl/dsrom_sys/ot_dsrom_link_rt_clock_core.sv',
     'rtl/dsrom_sys/ot_dsrom_link_rt.sv','rtl/dsrom_sys/ot_dsrom_link_chan.sv','rtl/link/ot_link_crc32.sv']
def model():
    p=ROOT/'tools/uarch_model.py'
    n=next(n for n in ast.parse(p.read_text()).body if isinstance(n,ast.FunctionDef) and n.name=='dsrom_baseline_link_clock_repair')
    ns=dict(math=math,hashlib=hashlib,ROOT=ROOT,DFF_UM2=.2916)
    exec(compile(ast.Module(body=[n],type_ignores=[]),str(p),'exec'),ns)
    return ns[n.name]()
def run(cmd,log,cwd=ROOT):
    with open(log,'w') as f:
        f.write('ARGV '+json.dumps([str(x) for x in cmd])+'\n');f.flush()
        p=subprocess.run(cmd,cwd=cwd,stdout=f,stderr=subprocess.STDOUT)
    if p.returncode:raise RuntimeError(f'{log}: exit {p.returncode}')
def sim(work):
    cases=[('wrap_credit',dict(CH=8,CRED=32,SEQW=8),['+n=1500','+gap=0','+bpm=2']),
           ('replay_backpressure',dict(CH=8,CRED=32,SEQW=8,EFWD=37,EREV=29),['+n=1000','+gap=10','+bpm=1']),
           ('board_rate',dict(CH=156,CRED=512,SEQW=10),['+n=1500','+gap=0','+bpm=2'])]
    rows=[]
    for name,defs,args in cases:
        src=(ROOT/'rtl/test/dsrom_sys/tb_dsrom_link_rt.sv').read_text().replace('ot_dsrom_link_rt #(', 'ot_dsrom_link_rt_clock #(.ENABLE_CLOCK_REPAIR(1), ',1)
        tb=work/(name+'.sv');tb.write_text(src)
        exe=work/(name+'.vvp')
        run(['iverilog','-g2012','-s','tb_dsrom_link_rt','-o',str(exe)]+['-D'+k+'='+str(v) for k,v in defs.items()]+[str(tb)]+[str(ROOT/s) for s in RTL],work/(name+'.compile.log'))
        run(['vvp','-n',str(exe),'+seed=81','+case='+name]+args,work/(name+'.run.log'))
        text=(work/(name+'.run.log')).read_text()
        summary=re.search(r'LINKRT_SUMMARY .*',text)
        if not summary or 'result=PASS' not in summary.group():raise RuntimeError(text[-2000:])
        if re.search(r'=x(?:\s|$)',summary.group()):raise RuntimeError('unknown component status: '+summary.group())
        rows.append(dict(case=name,summary=summary.group(),defines=defs))
    # Actual full residual over both pinned baseline legs; same payload/PHY.
    src=(ROOT/'rtl/test/dsrom_sys/tb_dsrom_1m_hop.sv').read_text().replace('ot_dsrom_link_rt #(', 'ot_dsrom_link_rt_clock #(.ENABLE_CLOCK_REPAIR(1), ')
    tb=work/'hop.sv';tb.write_text(src);exe=work/'hop.vvp'
    run(['iverilog','-g2012','-s','tb_dsrom_1m_hop','-DCHU=11','-o',str(exe),str(tb)]+[str(ROOT/s) for s in RTL],work/'hop.compile.log')
    run(['vvp','-n',str(exe),'+bytes=40976','+seed=81','+case=baseline_clock1'],work/'hop.run.log')
    text=(work/'hop.run.log').read_text();summary=re.search(r'HOP_SUMMARY .*',text)
    if not summary or 'result=PASS' not in summary.group():raise RuntimeError(text[-2000:])
    if re.search(r'=x(?:\s|$)',summary.group()):raise RuntimeError('unknown hop status: '+summary.group())
    rows.append(dict(case='full_baseline_hop',summary=summary.group()))
    out=dict(model=model(),cases=rows,source_sha256={s:hashlib.sha256((ROOT/s).read_bytes()).hexdigest() for s in RTL},physical_qualified=False)
    (work/'exact.json').write_text(json.dumps(out,indent=2)+'\n')
def route(work):
    # The same full 64B control/CRC component as the failed baseline screen;
    # queue depth16 is a contextual leaf vehicle, NOT the selected512 queue.
    from chip_assembly import case as cs
    from chip_assembly.harden import CORNER_LIBS
    preparation=model()['minimum_context']
    if not preparation['prebuild_reserved_capacity_pass']:raise RuntimeError('minimum context reservation does not fit')
    (work/'preparation.json').write_text(json.dumps(preparation,indent=2)+'\n')
    nickname='dsrom_baseline_clock1'
    sdc='''create_clock -name clk -period 833.333333 [get_ports clk]
set_clock_uncertainty -setup 60 [get_clocks clk]
set_clock_uncertainty -hold 25 [get_clocks clk]
set_input_delay -max 100 -clock clk [get_ports {in_valid in_data* in_last out_ready channel_cycles*}]
set_input_delay -min 30 -clock clk [get_ports {in_valid in_data* in_last out_ready channel_cycles*}]
set_output_delay -max 60 -clock clk [all_outputs]
set_output_delay -min 25 -clock clk [all_outputs]
set_load 0.6 [all_outputs]
set_false_path -from [get_ports rst_n]
'''
    params=dict(FLIT_BYTES=64,TX_STAGES=2,RX_STAGES=2,CHANNEL_CYCLES=1,CREDITS=16,SEQW=5)
    spec=cs.CaseSpec(nickname=nickname,top='ot_dsrom_link_rt_clock_core',sources=RTL[1:],die_um=(240.,180.),sdc=sdc,place_density=.5,extra={'CORNER':'WC','ABC_AREA':0,'ADDER_MAP_FILE':'','NUM_CORES':4})
    spec.params=params;cs.write_case(work,spec)
    cmd=['docker','run','--rm','-v',str(ROOT)+':/src:ro','-v',str(work)+':/work','-w','/OpenROAD-flow-scripts/flow','openroad/orfs:latest','bash','-lc',"source /OpenROAD-flow-scripts/env.sh; make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work FLOW_VARIANT=base finish; rc=$?; chmod -R a+rwX /work; exit $rc"]
    run(cmd,work/'route.log')
    # Use final extracted SPEF/SDC, propagated CTS, both actual signoff corners.
    base=work/'results/asap7'/nickname/'base'
    net=base/'6_final.v';spef=base/'6_final.spef'
    from chip_assembly import orfs
    orfs.normalise_netlist(net)
    for corner,kind,unc in [('SS','max',60),('FF','min',25)]:
        libs='\n'.join('read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/'+f for f in CORNER_LIBS[corner])
        tcl=libs+f'\nread_verilog /work/results/asap7/{nickname}/base/6_final.v\nlink_design ot_dsrom_link_rt_clock_core\nread_sdc /work/constraint.sdc\nset_propagated_clock [all_clocks]\nread_spef /work/results/asap7/{nickname}/base/6_final.spef\nreport_checks -path_delay {kind} -digits 3\nputs "WNS [sta::worst_slack_cmd {kind}]"\n'
        (work/(corner+'.tcl')).write_text(tcl)
        run(['docker','run','--rm','-v',str(work)+':/work','openroad/orfs:latest','bash','-lc',f'source /OpenROAD-flow-scripts/env.sh; sta /work/{corner}.tcl'],work/(corner+'.log'))
    record=dict(component='baseline_clock1',params=params,die_um=[240,180],selected_512_queue_qualified=False,context_io=dict(input_max_ps=100,input_min_ps=30,output_max_ps=60,output_min_ps=25,load_fF=.6),corners={})
    for c in ['SS','FF']:
        txt=(work/(c+'.log')).read_text();m=re.search(r'WNS\s+([-+0-9.eE]+)',txt)
        record['corners'][c]=dict(wns_ps=float(m.group(1))*1e12 if m else None)
    record['component_closes']=all(x['wns_ps'] is not None and x['wns_ps']>=0 for x in record['corners'].values())
    (work/'physical.json').write_text(json.dumps(record,indent=2)+'\n')
def main():
    a=argparse.ArgumentParser();a.add_argument('phase',choices=['model','sim','route']);a.add_argument('--work',type=Path,required=True);args=a.parse_args();w=args.work.resolve();w.mkdir(parents=True,exist_ok=True)
    if args.phase=='model':(w/'model.json').write_text(json.dumps(model(),indent=2)+'\n')
    elif args.phase=='sim':sim(w)
    else:route(w)
if __name__=='__main__':main()
