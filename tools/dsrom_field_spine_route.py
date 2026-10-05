#!/usr/bin/env python3
"""Run one immutable-source physical hold/slew successor; no RTL or gate replay."""
import argparse
import hashlib
import json
import os
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCES = [
    'physical/dsrom_field_spine/ot_v41_pqc_spine_screen.sv',
    'rtl/v41die/ot_v41_spine_pqc_w17w10.sv',
    'physical/dsrom_recovery_field/ot_hdc_actquant_screen_stub.sv',
    'rtl/hdc/ot_hdc_delay.sv', 'rtl/v41rom/ot_v41_kreg.sv', 'rtl/common/ot_prefix.sv',
]


def replicas(netlist, regions):
    text = netlist.read_text()
    instances = set(re.findall(r'^\s*DFF\w+\s+\\?(\S+)', text, re.M))
    names = {n.split('/')[0] for n in instances}
    patterns = dict(g_ixb=r'u_sp\.g_ixb\[\d+\]\.u_ix',
        g_ixq=r'u_sp\.g_ixq\[\d+\]\.u_ix',
        g_sel=r'u_sp\.g_reg\[\d+\]\.g_sel\[\d+\]\.u_s',
        u_rsfm=r'u_sp\.g_reg\[\d+\]\.u_rsfm', u_cc=r'u_sp\.u_cc',
        g_aqi=r'u_sp\.g_aqi\[\d+\]\.u_c',
        g_bwb=r'u_sp\.g_bwb\[\d+\]\.u_bwb')
    for i in range(5):
        patterns[f'u_oh{i}'] = rf'u_sp\.g_reg\[\d+\]\.u_oh{i}'
    expected = dict(g_ixb=32,g_ixq=8,g_sel=4*regions,u_rsfm=regions,
        u_cc=1,g_aqi=4,g_bwb=4,**{f'u_oh{i}':regions for i in range(5)})
    actual = {k:sum(bool(re.fullmatch(p,n)) for n in names) for k,p in patterns.items()}
    return dict(expected=expected, actual=actual, passed=(actual==expected))


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--recipe',required=True,choices=['c0r16_h20','c1r16_s40'])
    ap.add_argument('--run-dir',required=True,type=Path)
    ap.add_argument('--source-pins',required=True,type=Path)
    a=ap.parse_args()
    pins=json.loads(a.source_pins.read_text())
    for source in SOURCES:
        assert hashlib.sha256((ROOT/source).read_bytes()).hexdigest()==pins[source],source
    out=a.run_dir.resolve();out.mkdir(parents=True,exist_ok=False)
    (out/'tmp').mkdir()
    os.environ.update(NUM_CORES='16',OT_ORFS_NUM_CORES='16',TMPDIR=str(out/'tmp'),
        OT_FLOW_TIMEOUT_SECONDS='unlimited',OT_SYNTH_TIMEOUT_SECONDS='unlimited')
    pq=int(a.recipe[1]);margin='0.02' if pq==0 else '0.01';slew='30' if pq==0 else '40'
    args=['python3','tools/run_abi3_physical.py','--view','asap7',
        '--clock-period-ns','0.833333','--clock-uncertainty-ns','0.060',
        '--clock-uncertainty-hold-ns','0.025','--corner','TT','--orfs-corner','WC',
        '--hold-corners','WC,BC','--max-transition-ns','--max-fanout','32',
        '--slew-margin-percent',slew,'--hold-margin-ns',margin,
        '--orfs-var','ADDER_MAP_FILE=','--orfs-var','NUM_CORES=16',
        '--orfs-var','TMPDIR=/work/tmp','--keep-heavy-artifacts',
        '--synth-timeout-seconds','unlimited','--flow-timeout-seconds','unlimited',
        '--stages','pnr','--false-path-io','--top','ot_v41_pqc_spine_screen']
    for source in SOURCES:args+=['--source',source]
    args+=['--orfs-var','VERILOG_DEFINES=-DSYNTHESIS -DOT_PQ_ROM_PORTS',
        '--param',f'PQ={pq}','--param','R=16','--core-utilization','35',
        '--nickname-tag','dsfs_'+a.recipe,'--keep-workdir',str(out/'work'),
        '--output',str(out/'physical.json')]
    # /work is the unchanged driver's real Docker mount; temp files stay on NVMe.
    (out/'work/orfs/tmp').mkdir(parents=True)
    (out/'launch.json').write_text(json.dumps(dict(command=args,source_sha256=pins,
        recipe=a.recipe,RTL_immutable=True,model='dsrom_field_spine_route_price'),indent=2)+'\n')
    with (out/'flow.log').open('w') as log:
        rc=subprocess.run(args,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT).returncode
    record=dict(route_rc=rc,recipe=a.recipe,source_sha256=pins,verdict='FAIL_FLOW')
    if (out/'physical.json').exists() and list((out/'work').rglob('6_final.odb')):
        cmd=['python3','tools/w18/corner_sta.py','--orfs-dir',str(out/'work/orfs'),
            '--output',str(out/'corner_sta.json')]
        with (out/'corner_sta.log').open('w') as log:
            record['corner_rc']=subprocess.run(cmd,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT).returncode
        physical=json.loads((out/'physical.json').read_text());d=physical['design']
        netlist=next((out/'work/orfs/results/asap7').glob('*/base/6_final.v'))
        record['replicas']=replicas(netlist,16)
        record['area_um2']=d.get('area_um2');record['core_area_um2']=d.get('core_area_um2')
        record['SI']=d.get('signal_integrity_violations',{})
        record['drc']=d.get('drc');record['antenna']=d.get('antenna')
        if (out/'corner_sta.json').exists():
            sta=json.loads((out/'corner_sta.json').read_text())
            record['SS_ps']=sta['setup_ss']['worst_slack_ps'];record['FF_ps']=sta['hold_ff']['worst_slack_ps']
            clean=all(record['SI'].get(k)==0 for k in ['max_slew_violations','max_cap_violations','max_fanout_violations']) and record['drc']==0 and record['antenna']==0
            qualified=sta['closes_signoff'] and not sta['setup_ss']['errors'] and not sta['hold_ff']['errors']
            record['verdict']='PASS_SCREEN_ONLY' if rc==0 and record['corner_rc']==0 and qualified and clean and record['replicas']['passed'] else 'FAIL_PHYSICAL_SCREEN'
    (out/'terminal.json').write_text(json.dumps(record,indent=2)+'\n')
    print(json.dumps(record),flush=True)
    return 0 if record['verdict']=='PASS_SCREEN_ONLY' else 1


if __name__=='__main__':
    raise SystemExit(main())
