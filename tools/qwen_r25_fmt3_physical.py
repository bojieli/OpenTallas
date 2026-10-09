#!/usr/bin/env python3
"""Remote admitted SS/FF front_c candidate: model, exact gates, CTS calibration, route.

Run only on the measured compute host under its 64Gi admission guard. Source
archive is immutable and inventory-bounded. All completed/failing stages remain.
Legacy generators/default RTL are unchanged unless explicit candidate flags are set.
"""
import argparse
import ast
import hashlib
import json
import os
import re
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]

def cmd(args,log,env=None):
    with Path(log).open('w') as out:
        result=subprocess.run([str(a) for a in args],cwd=ROOT,stdout=out,stderr=subprocess.STDOUT,env=env)
    if result.returncode:
        raise RuntimeError(f'{log}: exit {result.returncode}')


def model(wide=False):
    tree=ast.parse((ROOT/'tools/uarch_model.py').read_text())
    node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name==('qwen_r25_fmt3_wide_model' if wide else 'qwen_r25_int8_unpack_model'))
    nodes=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in ('qwen_r25_int8_unpack_model','qwen_r25_fmt3_wide_model')]
    scope={};exec(compile(ast.Module(body=nodes,type_ignores=[]),'model','exec'),scope)
    return scope[node.name]()


def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--source-commit',required=True)
    p.add_argument('--generate-only',action='store_true',help='emit candidate and inspect source hooks without compute')
    p.add_argument('--wide',action='store_true',help='570.24um strip and 240um central corridor; separate candidate')
    a=p.parse_args();out=a.out.resolve();out.mkdir(parents=True,exist_ok=False)
    state={'source_commit':a.source_commit,'phase':'model','policy':'SS>=15ps FF>=15ps DRC0;833ps60/25uncertainty'}
    def save(): (out/'state.json').write_text(json.dumps(state,indent=2)+'\n')
    save()
    try:
        gen=ROOT/'tools/hbm_accel_smh_physical.py'
        # Empty explicit environment overrides prevent accidental TC setup reuse.
        env=dict(os.environ,OT_SMH_CORNER='WC');env.pop('OT_ORFS_CORNER_OVERRIDE',None);env.pop('OT_SMH_POST_SDC',None)
        m=model(a.wide);(out/'model.json').write_text(json.dumps(m,indent=2)+'\n')
        pins={}  # measured literal generator pin ABI is captured below
        common=[sys.executable,gen,'block','--piece','front_c','--variant','one','--src',ROOT,
            '--period','833','--skew','90','--die-skew','150','--pd','0.55','--cores','16',
            '--need','64','--no-admit','--top-param','ENABLE_INT8=1','--hold-mm','--hold-margin','40',
            '--hold-buffer-pct','60','--make-var','GPL_ROUTABILITY_DRIVEN=0']
        if a.wide:
            common += ['--geom',ROOT/'results/arch/qwen_on_r25_20261008/fmt3_physical_candidate/wide_geometry.json']
        def bind_endpoints(work):
            if a.wide:
                with (work/'hops.tcl').open('a') as f:
                    f.write('\n'+(ROOT/'physical/common_flow/qwen_fmt3_pin_endpoints.tcl').read_text())
                # Only the new candidate: match the literal neighbour planning
                # source phase before the first floorplan repair; remove core
                # source before CTS, preventing double-counting its actual tree.
                sdc=work/'constraint.sdc'
                text=sdc.read_text()
                refs=re.findall(r'set_clock_latency\s+-source\s+([0-9.]+)\s+\[get_clocks nbr_clk\]',text)
                if len(refs)!=1: raise RuntimeError('expected one explicit neighbour planning source')
                text+='\n# FMT3 wide preCTS planning phase, removed by PRE_CTS_TCL\n'
                text+=f'set_clock_latency -source {refs[0]} [get_clocks core_clk]\n'
                sdc.write_text(text)
                reset=work/'planning_reset.tcl'
                # Existing hold-buffer hook must run too; keep its exact body.
                old=work/'rt_hook.tcl'
                reset.write_text((old.read_text() if old.exists() else '')+'\n'+
                    'set_clock_latency -source 0 [get_clocks core_clk]\n'+
                    'if {[info commands ot_mm_on] ne \"\" && [ot_mm_on]} {\n'+
                    '  set_mode ff\n  set_clock_latency -source 0 [get_clocks core_clk]\n  set_mode ss\n}\n'+
                    'puts \"FMT3 planning phase removed before CTS; core source0, neighbour unchanged\"\n')
                with (work/'config.mk').open('a') as f:
                    f.write('\nexport PRE_CTS_TCL = /work/planning_reset.tcl\n')
                (work/'planning_reference.json').write_text(json.dumps(dict(
                    source_commit=a.source_commit,preCTS_core_source_ps=float(refs[0]),
                    preCTS_neighbour_source_ps=float(refs[0]),postCTS_core_source_ps=0,
                    unchanged='period, uncertainty, input/output delay and neighbour reference'),indent=2)+'\n')
        label='qwen_fmt3_wide' if a.wide else 'qwen_fmt3'
        cal=out/'cal';route=out/'route'
        cmd(common+['--label',label+'_cal','--out',cal,'--stop-after','cts',
            '--make-var','SKIP_CTS_REPAIR_TIMING=1'],out/'generate_cal.log',env)
        bind_endpoints(cal)
        geometry=json.loads((cal/'geometry.json').read_text())
        expected=([570.24,518.4] if a.wide else m['front_c_footprint_um'])
        assert geometry['die']==expected,(geometry['die'],expected)
        state.update(phase='exact_gates',geometry=geometry);save()
        if a.generate_only:
            state.update(phase='generated');save();return
        cmd([sys.executable,ROOT/'tools/qwen_r25_int8_gate.py','--out',out/'adapter_gate'],out/'adapter_gate.log',env)
        cmd([sys.executable,ROOT/'tools/test_qwen_r25_int8_image.py','--out',out/'image_gate'],out/'image_gate.log',env)
        state['phase']='calibration';save()
        cmd(['bash',cal/'run.sh'],out/'cal_driver.log',env)
        base=next((cal/'results/asap7').glob('*/base'))
        cmd([sys.executable,ROOT/'tools/closure_loop/ck_insertion.py','--base',base,'--clock','core_clk',
             '--route-corner','WC','--image','openroad/orfs:asap7lock','--output',out/'calib.json'],out/'calib.log',env)
        clock=json.loads((out/'calib.json').read_text())['env']
        ss,ff=clock['CK_SS_MEAN'],clock['CK_FF_MEAN']
        budget=dict(planning=m,calibrated_clock=clock,pin_abi_sha256=hashlib.sha256((cal/'pins.tcl').read_bytes()).hexdigest(),
            interface_setup_ps=390,local_setup_ps=383,hold='BC scene neighbour source at measured FF insertion;min30/0ps')
        (out/'budget.json').write_text(json.dumps(budget,indent=2)+'\n')
        cmd(common+['--label',label+'_ss','--out',route,'--lat',ss,'--lat-ff',ff,
                    '--make-var','SETUP_SLACK_MARGIN=15'],out/'generate_route.log',env)
        # The canonical generator's FF input reference uses SS source latency.
        # Supply the correct calibrated FF neighbour and cancel SS-FF output debt
        # in the FF repair scene only; setup scene remains SS and unchanged.
        bind_endpoints(route)
        ff_sdc=route/'ff_boundary.sdc'
        ff_sdc.write_text(f'set_clock_latency -source {ff} [get_clocks nbr_clk]\n'
                          'set_output_delay -min 0 -clock nbr_clk [all_outputs]\n')
        with (route/'config.mk').open('a') as f:f.write('export OT_MM_FF_SDC = /work/ff_boundary.sdc\n')
        # Source/pin maps must match the literal pre-build model and calibration.
        assert (cal/'pins.tcl').read_bytes()==(route/'pins.tcl').read_bytes()
        state.update(phase='route',route=str(route),calibrated_clock=clock);save()
        cmd(['bash',route/'run.sh'],out/'route_driver.log',env)
        if not (route/'corner_sta.json').exists(): raise RuntimeError('route did not produce final corner evidence')
        # Re-reference virtual neighbour per corner to actual routed insertion;
        # this is the balanced-clock plan, and removes stale calibration credit.
        import importlib.util
        spec=importlib.util.spec_from_file_location('sta',ROOT/'tools/w18/corner_sta.py');sta=importlib.util.module_from_spec(spec);spec.loader.exec_module(sta)
        setup=sta.run(route,'ss',["physical/hbm_accel_macros/ot_sram_1r1w_512x256_m1_r2c2"],
                      ['physical/common_flow/nbr_clk_measured.sdc'],'6_signoff.sdc')
        # Use a source-pinned hold post-SDC that applies the same measured clock
        # reference and a0ps sender minimum instead of SS-FF historical debt.
        hold=sta.run(route,'ff',["physical/hbm_accel_macros/ot_sram_1r1w_512x256_m1_r2c2"],
                     ['physical/common_flow/qwen_fmt3_ff_boundary.sdc'],'6_signoff.sdc')
        metrics=list((route/'logs/asap7').glob('*/base/5_2_route.json'))
        drc=None
        for f in metrics:
            d=json.loads(f.read_text());drc=d.get('detailedroute__route__drc_errors',d.get('detailedroute__route__drc_errors__count'))
        ss_slack=setup['worst_slack_ps'];ff_slack=hold['worst_slack_ps']
        qualified=ss_slack is not None and ff_slack is not None and ss_slack>=15 and ff_slack>=15 and drc==0
        verdict=dict(verdict='PASS' if qualified else 'FAIL',setup_ss=setup,hold_ff=hold,drc=drc,policy=state['policy'],
                     source_commit=a.source_commit,scope='single production front_c;balanced element interface budget')
        (out/'verdict.json').write_text(json.dumps(verdict,indent=2)+'\n')
        state.update(phase='terminal',verdict=verdict['verdict']);save()
    except Exception as error:
        state.update(phase='terminal',verdict='FAIL',reason=str(error));save();raise
if __name__=='__main__':main()
