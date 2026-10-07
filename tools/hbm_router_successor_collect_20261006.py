#!/usr/bin/env python3
"""Collect the sole completed E1 router route; leave bulk objects on E1."""
import argparse
import hashlib
import io
import json
import re
from pathlib import Path
import subprocess
import tarfile
import time

REMOTE = '/srv/opentallas-scratch/codex/carson-router-successor-20261006/route-r2'
HOST = 'ot-epyc1tb'
SUB = 'asap7/carson_router_successor/base'

REMOTE_READ = r'''
import io,json,sys,tarfile
from pathlib import Path
r=Path('/srv/opentallas-scratch/codex/carson-router-successor-20261006/route-r2')
assert (r/'terminal.exit').is_file(), 'supervisor not terminal; keep monitoring'
v=json.loads((r/'route.json').read_text())
assert v['status'] in ('FLOW_FAIL_RETAINED','ROUTE_TERMINAL_NEEDS_REVIEW'),v['status']
if v['flow_returncode']==0:
    assert set(v['corners']) >= {'ss','ff','retained_sha256'}
files=[p for p in r.iterdir() if p.is_file() and p.suffix in ['.json','.jsonl','.log','.exit']]
w=r/'orfs'
files += [p for p in w.iterdir() if p.is_file() and p.suffix in ['.mk','.sdc','.tcl','.json','.py']]
for d in ['logs','reports']:
    files += [p for p in (w/d/'asap7/carson_router_successor/base').rglob('*')
              if p.is_file() and p.suffix in ['.log','.json','.rpt','.txt']]
for n in ['6_final.sdc']:
    p=w/'results/asap7/carson_router_successor/base'/n
    if p.exists():files.append(p)
with tarfile.open(fileobj=sys.stdout.buffer,mode='w|') as t:
    for p in sorted(set(files)):t.add(p,arcname=str(p.relative_to(r)),recursive=False)
'''

REMOTE_STATUS = r'''
import json
from pathlib import Path
r=Path('/srv/opentallas-scratch/codex/carson-router-successor-20261006/route-r2')
v=json.loads((r/'route.json').read_text())
print(json.dumps(dict(status=v['status'],terminal=(r/'terminal.exit').is_file())))
'''


def ssh_python(code):
    return ['ssh', HOST, "python3 - <<'PY'\n" + code + '\nPY']


def review(out, route):
    record = dict(status='NATIVE_FLOW_FAILURE_RETAINED',
                  flow_returncode=route['flow_returncode'],
                  physical_closed=False, parent_qualified=False,
                  boundary_scope='Standalone166.6ps min/max input/output and3.898fF load; externalfull73 producer/receiver/rootclock/reset unqualified',
                  loaded_boundary_allocation_sha256=route['actual_parent_allocation_sha256'],
                  latency=dict(tail_cycles=48,II_cycles=24,total_added_vs23=25,increment_vs28=20,compose_once=True))
    if route['flow_returncode']:
        return record
    corners = route['corners']
    record['corners'] = corners
    sdc = (out/'orfs/results'/SUB/'6_final.sdc').read_text()
    periods = [float(v) for v in re.findall(r'create_clock[^\n]*-period\s+(\S+)',sdc)]
    uncertainties = {k: [float(v) for v in re.findall(r'set_clock_uncertainty -'+k+r'\s+(\S+)',sdc)]
                     for k in ['setup','hold']}
    inputs = re.findall(r'set_input_delay\s+(\S+)[^\n]*',sdc)
    outputs = re.findall(r'set_output_delay\s+(\S+)[^\n]*',sdc)
    loads = re.findall(r'set_load -pin_load\s+(\S+)[^\n]*',sdc)
    exceptions = re.findall(r'^\s*set_(?:false_path|multicycle_path|disable_timing)[^\n]*',sdc,re.M)
    record['actual_final_SDC_boundary'] = dict(period_ps=periods,
        uncertainty_ps=uncertainties,input_delay_ps=sorted(set(map(float,inputs))),
        output_delay_ps=sorted(set(map(float,outputs))),
        output_pin_load_fF=sorted(set(map(float,loads))),
        input_delay_statements=len(inputs),output_delay_statements=len(outputs),
        output_pin_load_statements=len(loads),
        timing_exceptions=exceptions,
        final_SDC_sha256=hashlib.sha256(sdc.encode()).hexdigest(),
        clock_source='Standalone primary input; native child CTS propagated; externalfull73 root source not characterized',
        external_producer_receiver_clock_reset_qualified=False)
    logs = out/'orfs/logs'/SUB
    native = json.loads((logs/'6_report.json').read_text())
    drt = json.loads((logs/'5_2_route.json').read_text())
    record['native_final_classes'] = {
        k: v for k, v in native.items()
        if any(s in k for s in ['__timing__', '__clock__', '__utilization',
                                '__core__area', '__area__stdcell'])}
    record['native_routed_DRC_antenna'] = {
        k: v for k, v in drt.items() if 'drc_errors' in k or 'antenna' in k}
    def nonnegative(c):
        try:
            return float(corners[c]['metrics_raw']['OT_WS'])>=0
        except (KeyError,ValueError,TypeError):
            return False
    conditions = dict(
        corner_tools=all(corners[c]['returncode']==0 and not corners[c]['errors'] for c in ['ss','ff']),
        setup_SS=nonnegative('ss'),
        hold_FF=nonnegative('ff'),
        DRC=drt.get('detailedroute__route__drc_errors')==0,
        antenna=all(drt.get('detailedroute__antenna__violating__'+k)==0 for k in ['nets','pins']),
        electrical=all(native.get('finish__timing__drv__'+k)==0 for k in ['max_slew','max_cap','max_fanout']),
        native_all_setup=native.get('finish__timing__drv__setup_violation_count')==0,
        native_all_hold=native.get('finish__timing__drv__hold_violation_count')==0,
        unrelaxed_boundary=(periods==[833.] and uncertainties==dict(setup=[60.],hold=[25.])
                            and set(map(float,inputs))=={166.6}
                            and set(map(float,outputs))=={166.6}
                            and len(outputs)==55 and len(loads)==55
                            and set(map(float,loads))=={3.898} and not exceptions))
    record['standalone_contract_checks'] = conditions
    record['standalone_contract_closes'] = all(conditions.values())
    record['status'] = ('ACTUAL_ROUTED_STANDALONE_CONTRACT_PASS_PARENT_OPEN'
                        if all(conditions.values()) else 'ACTUAL_ROUTED_FAILURE_CLASSES_RETAINED')
    record['retained_final_sha256'] = corners['retained_sha256']
    record['actual_buffered_cell_utilization'] = native.get('finish__design__instance__utilization')
    record['utilization_target'] = [.55,.60]
    record['reset_scope'] = 'Global/native asynchronous checks retained; explicitRESETN paths in corner logs; no reset exception inferred'
    return record


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--wait', action='store_true', help='Read-only30s polling without a time limit')
    a = p.parse_args()
    if a.out.exists():
        p.error('preserve prior collection; use a new directory')
    # Read-only remote operation; no new tool job, route, synthesis or STA.
    if a.wait:
        while True:
            s = json.loads(subprocess.check_output(ssh_python(REMOTE_STATUS)))
            print(json.dumps(s), flush=True)
            if s['terminal']:
                break
            time.sleep(30)
    cmd = ssh_python(REMOTE_READ)
    result = subprocess.run(cmd, stdout=subprocess.PIPE, check=True)
    a.out.mkdir(parents=True)
    with tarfile.open(fileobj=io.BytesIO(result.stdout)) as t:
        t.extractall(a.out, filter='data')
    v = json.loads((a.out/'route.json').read_text())
    hashes = {str(f.relative_to(a.out)): hashlib.sha256(f.read_bytes()).hexdigest()
              for f in sorted(a.out.rglob('*')) if f.is_file()}
    for c in ['ss', 'ff']:
        if 'corners' in v:
            assert hashes[f'corner_{c}.log'] == v['corners'][c]['log_sha256']
            assert hashes[f'orfs/router_{c}.tcl'] == v['corners'][c]['tcl_sha256']
    if 'corners' in v:
        assert hashes[f'orfs/results/{SUB}/6_final.sdc'] == v['corners']['retained_sha256']['6_final.sdc']
    record = dict(status='ACTUAL_TERMINAL_RAW_EVIDENCE_COLLECTED_REVIEW_REQUIRED',
                  host=HOST, remote_root=REMOTE, sha256=hashes,
                  retained_bulk='All ODB/SPEF/GDS/DEF, source and build objects remain on E1',
                  physical_closed=False, parent_qualified=False,
                  synthesis_replayed=False, golden_replayed=False, STA_replayed=False)
    (a.out/'collection.json').write_text(json.dumps(record, indent=2)+'\n')
    verdict = review(a.out, v)
    (a.out/'verdict.json').write_text(json.dumps(verdict, indent=2)+'\n')
    print(json.dumps({k: record[k] for k in ['status','host','remote_root']}))


if __name__ == '__main__':
    main()
