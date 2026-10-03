#!/usr/bin/env python3
"""Read-only collection of inherited DS die GRT and qframe jobs; never launches a flow."""
import argparse
import gzip
import hashlib
import importlib.util
import json
import re
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

REMOTE = r'''
import datetime,hashlib,json,pathlib,subprocess
B=pathlib.Path('/srv/opentallas-scratch/claude')
out={'observed_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'host':subprocess.check_output(['hostname'],text=True).strip(),'files':{},'runs':{}}
def save(p):
 if p.is_file():
  b=p.read_bytes(); out['files'][str(p)]={'sha256':hashlib.sha256(b).hexdigest(),'text':b.decode(errors='replace')}
  return str(p)
 return None
for name in ('C_local_k16','C_band_k16'):
 p=B/'dsrom-die-feas/runs'/name
 out['runs'][name]={'kind':'die_grt','path':str(p),'files':{n:save(p/n) for n in ('receipt.json','manifest.json','grt.log','exit_code','time.log','run.tcl')},'grt_odb_exists':(p/'grt.odb').is_file()}
for name in ('A_r3_mig','B_r3_mig','C_r2_mig','D_r2'):
 p=B/'qframe'/name; o=p/('work/orfs' if name=='D_r2' else 'orfs')
 f={'exit_code':save(p/'exit_code'),'signoff':save(B/'qframe/signoff'/f'{name}.json'),'signoff_exit':save(B/'qframe/signoff'/f'{name}.done')}
 for key,pat in [('route_log','logs/asap7/*/base/5_2_route*.log'),('place_log','logs/asap7/*/base/3_3_place_gp*.log'),('report','logs/asap7/*/base/6_report.json'),('drc','reports/asap7/*/base/5_route_drc.rpt')]:
  pp=list(o.glob(pat)); f[key]=save(max(pp,key=lambda x:x.stat().st_mtime)) if pp else None
 finals=list(o.glob('results/asap7/*/base/6_final.odb'))
 out['runs'][name]={'kind':'qframe','path':str(p),'files':f,'final_odb_exists':bool(finals)}
for p in (B/'dsrom-die-feas/STATUS.md', B/'qframe/STATUS.md', B/'qframe/chain.log',B/'dsrom-die-feas/jobs/run_grt.sh',B/'qframe/jobs/qframe_chain2.sh'):
 save(p)
out['processes']=subprocess.check_output(['ps','-eo','pid,etime,args'],text=True)
out['processes']='\n'.join(l for l in out['processes'].splitlines() if any(t in l for t in ('detail_route.tcl','global_place.tcl','dsfeas-','qframe_chain2.sh')) and 'bash -c' not in l)
print(json.dumps(out,sort_keys=True))
'''

FRAMES = {'A_r3_mig': [521.64, 178.47], 'B_r3_mig': [521.64, 223.02],
          'C_r2_mig': [510.84, 126.9], 'D_r2': [510.84, 151.2]}


def get(snapshot, run, field):
    p = run['files'].get(field)
    return snapshot['files'][p]['text'] if p else None


def exit_code(text):
    m = re.search(r'^exit=(\d+)$', text or '', re.M)
    return int(m[1]) if m else None


def analyse(snapshot):
    # A snapshot is immutable read evidence, not an accepted-cycle or implementation model.
    for value in snapshot['files'].values():
        if hashlib.sha256(value['text'].encode()).hexdigest() != value['sha256']:
            raise ValueError('snapshot source hash mismatch')
    rows = {}
    for name, run in snapshot['runs'].items():
        ex = exit_code(get(snapshot, run, 'exit_code'))
        row = {'kind': run['kind'], 'remote_path': run['path'], 'exit_code': ex,
               'state': 'RUNNING_OR_TERMINAL_MARKER_ABSENT' if ex is None else 'TERMINAL',
               'physical_admission': False}
        if run['kind'] == 'die_grt':
            text = get(snapshot, run, 'grt.log') or ''
            final = re.findall(r'GRT-0096\] Final congestion report:(.*?)Total\s+(\d+)\s+(\d+)\s+([\d.]+)%\s+(\d+)\s*/\s*(\d+)\s*/\s*(\d+)', text, re.S)
            overflow = int(final[-1][-1]) if final else None
            row.update({'manifest': json.loads(get(snapshot, run, 'manifest.json') or '{}'),
                        'final_overflow': overflow, 'bundled_global_route_pass':
                        (ex == 0 and overflow == 0 and run['grt_odb_exists']) if ex is not None else None,
                        'real_tech_pin_access_qualified': False, 'PDN_204W_qualified': False,
                        'actual_clock_wire_stages': None})
        else:
            text = get(snapshot, run, 'route_log') or ''
            final = re.findall(r'Number of violations\s*[=:]\s*(\d+)', text)
            progress = re.findall(r'(?:with|,|=)\s*(\d+) violations', text)
            # Final markers may appear several times, one per DRT iteration; require completion too.
            drc = get(snapshot, run, 'drc')
            final_count = int(final[-1]) if final else None
            routed = None
            if ex is not None:
                routed = ex == 0 and run['final_odb_exists'] and final_count == 0 and drc is not None and not drc.strip()
            signoff = json.loads(get(snapshot, run, 'signoff') or '{}')
            corners = signoff.get('corners', {})
            ss = corners.get('SS', {}).get('timing', {}).get('setup_wns_ns')
            ff = corners.get('FF', {}).get('timing', {}).get('hold_wns_ns')
            complete_sta = exit_code(get(snapshot, run, 'signoff_exit')) == 0
            row.update({'frame_um': FRAMES[name], 'frame_area_um2': FRAMES[name][0]*FRAMES[name][1],
                        'progress_violations': int(progress[-1]) if progress else None,
                        'final_route_violations': final_count if ex is not None else None,
                        'routability_pass': routed, 'SS_setup_wns_ns': ss, 'FF_hold_wns_ns': ff,
                        'signoff_complete': complete_sta, 'SS_FF_timing_pass':
                        (ss >= 0 and ff >= 0) if complete_sta and ss is not None and ff is not None else None,
                        'pipeline_owner': 'Epicurus', 'full_timing_and_DRV_verdict': 'NOT_ADMITTED'})
        rows[name] = row
    passing = [r for r in rows.values() if r.get('routability_pass') is True]
    observed = min(passing, key=lambda r:r['frame_area_um2']) if passing else None
    return {'schema': 'opentallas.dsrom.physical_handover_collection.v1',
            'observed_utc': snapshot['observed_utc'], 'host': snapshot['host'], 'runs': rows,
            'smallest_observed_routable_frame_um': observed['frame_um'] if observed else None,
            'tested_frame_comparison_complete': all(rows[n].get('routability_pass') is not None for n in FRAMES),
            'minimum_frame_proved': False,
            'selected_policy': 'DS4096-TP4-S58-PAR2-NP2048', 'new_hardware_jobs': 0,
            'full_die_admitted': False,
            'next_actions': ['Collect existing C_r2_mig and D_r2 terminal DRC/SS/FF; preserve A/B FAIL',
                             'Use existing C local/band bundled GRT results before another variant',
                             'Bind native pin/OBS abstracts, actual PHY homes, 204W supply sources and complete relay/reset routes'],
            'limits': ['Bundled k16 GRT does not prove native pin/via access or detailed-route fit',
                       'Inherited PHY strips are assumed, not measured provider abstracts',
                       '204W PDN and complete CTS preparation are unimplemented in inherited tool',
                       'Clock wire stages and single-user latency need actual routed endpoints; not zero',
                       'No element reframe or pipeline modification; Epicurus retains pipeline ownership']}


def collect(snapshot_path, out_path):
    if snapshot_path.exists() or out_path.exists():
        raise SystemExit('refuse to overwrite evidence; select a new snapshot directory')
    p = subprocess.run(['ssh', '-i', '/home/ubuntu/.ssh/agidock_ot', '-o', 'BatchMode=yes',
                        'ubuntu@5.199.165.104', 'python3 -'], input=REMOTE, text=True,
                       stdout=subprocess.PIPE, check=True)
    snapshot = json.loads(p.stdout)
    snapshot_path.parent.mkdir(parents=True, exist_ok=True)
    snapshot_path.write_bytes(gzip.compress(json.dumps(snapshot,sort_keys=True).encode(),mtime=0))
    result = analyse(snapshot)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(result, indent=2, sort_keys=True)+'\n')
    return snapshot, result


def watch_finished(snapshot, result):
    return all(r['state']=='TERMINAL' and
               (r['kind']=='die_grt' or r['signoff_complete'] or
                not snapshot['runs'][name]['final_odb_exists'])
               for name,r in result['runs'].items())


def source_audit():
    root=Path(__file__).resolve().parents[1]
    spec=importlib.util.spec_from_file_location('inherited_die',root/'tools/dsrom_die_feasibility.py')
    inherited=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(inherited)
    geometry=inherited.geometry('C',False)
    instances,nets=inherited.build_grt(geometry,'local')
    return {'die_um':list(inherited.DIE_UM), 'die_area_mm2':858.0,
            'field_elements':len(geometry['elems']), 'cfg_macros':len(geometry['cfgs']),
            'local_case_instances':len(instances),
            'clock_declared_in_real_element_ports':any(p[0]=='clk' for pp in inherited.element_ports('q') for p in pp),
            'clock_endpoints_in_bundled_connectivity':sum(p=='clk' for n in nets for _,p in [n.src,*n.dsts]),
            'cfg_phase_bits_in_inherited_ctl_expression':6, 'selected_cfg_phase_bits_required':10,
            'assumed_PHY_home_names':[b.name for b in geometry['blocks'] if b.name.startswith(('PAR2_','COLL_'))],
            'capture_home_input':inherited.CAPTURE_HOME, 'capture_home_current_R49_c9_bound':False,
            'real_tech_job_implementations':False, 'clock_latency_edges':None,
            'power_W_for_requested_PDN':inherited.HOTTEST_DIE_W, 'PDN_204W_implemented':False}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--collect', action='store_true')
    ap.add_argument('--snapshot', type=Path)
    ap.add_argument('--out', type=Path)
    ap.add_argument('--watch-root', type=Path, help='read-only snapshots every 60s until existing routes/signoff terminate')
    ap.add_argument('--source-audit', type=Path)
    args = ap.parse_args()
    if args.source_audit:
        if args.collect or args.snapshot or args.out or args.watch_root:
            ap.error('source-audit is exclusive')
        args.source_audit.write_text(json.dumps(source_audit(),indent=2,sort_keys=True)+'\n')
        return
    if args.watch_root:
        if args.collect or args.snapshot or args.out:
            ap.error('watch-root is exclusive with collect/snapshot/out')
        while True:
            directory = args.watch_root/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')
            try:
                snapshot,result = collect(directory/'snapshot.json.gz', directory/'model.json')
                print(json.dumps({'snapshot':str(directory),'terminal':watch_finished(snapshot,result)}),flush=True)
                if watch_finished(snapshot,result):
                    return
            except subprocess.CalledProcessError as e:
                print(json.dumps({'snapshot':str(directory),'collection_error':e.returncode}),flush=True)
            time.sleep(60)
    if args.snapshot is None or args.out is None:
        ap.error('snapshot and out required for collection/replay')
    if args.collect:
        snapshot,result = collect(args.snapshot,args.out)
    else:
        snapshot = json.loads(gzip.decompress(args.snapshot.read_bytes()))
        result = analyse(snapshot)
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(result, indent=2, sort_keys=True)+'\n')
    print(json.dumps({n:r['state'] for n,r in result['runs'].items()}))


if __name__ == '__main__':
    main()
