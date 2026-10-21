"""Read-only collector for the sealed partial-key PV minimum; never runs a DUT."""
import argparse,hashlib,importlib.util,json,re
from pathlib import Path

MANIFEST_SHA='64bb832617079f0759ca5a527f587d5caaf98c372a5571a40d66949fefb649ce'
RUNNER_SHA='83aae310c0a83444df293f7889deb813644baae1634a82570f37b1b79d17e7f4'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def check_rows(log,spec):
    errors=[];rows=[];seen=set();values=0
    lines=[line for line in log.splitlines() if line.startswith('SLICE_SM_ROW')]
    for line in lines:
        m=re.fullmatch(r'SLICE_SM_ROW cyc=(\d+) row=(\d+) data=([0-9a-fA-F]{64})',line)
        if not m:errors.append('malformed SM row record');continue
        cycle,row,data=int(m[1]),int(m[2]),int(m[3],16)
        rows.append(dict(cycle=cycle,row=row,data=m[3]))
        if not spec['begin_edge']<=cycle<=spec['end_edge']:errors.append('SM output outside candidate window')
        if not 0<=row<64:errors.append('SM row address outside0..63');continue
        if row in seen:errors.append('duplicate SM row address');continue
        seen.add(row)
        for col in range(8):
            values+=1
            if (data>>(32*col))&0xffffffff!=int(spec['expected_words'][8*row+col],16):errors.append(f'SM word mismatch row{row} column{col}')
    if len(lines)!=64 or len(rows)!=64 or seen!=set(range(64)):errors.append('missing/extra/incomplete SM rows')
    summaries=re.findall(r'^SLICE_SM_SUMMARY total=(\d+) unique=(\d+) first=(-?\d+) last=(-?\d+)$',log,re.M)
    first=min((r['cycle'] for r in rows),default=None);last=max((r['cycle'] for r in rows),default=None)
    if len(summaries)!=1 or tuple(map(int,summaries[0]))!=(64,64,first,last):errors.append('SM summary count/date mismatch')
    if any(b['cycle']<a['cycle'] for a,b in zip(rows,rows[1:])):errors.append('SM output cycles not monotonic')
    return dict(passed=not errors,errors=errors,rows=rows,unique_addresses=len(seen),word_comparisons=values,
                actual_first_cycle=first,actual_last_cycle=last,candidate_window=[spec['begin_edge'],spec['end_edge']])


def collect(case,run_log,run_receipt):
    case=Path(case).resolve();run_log=Path(run_log).resolve()
    if case/'out' not in run_log.parents:raise ValueError('raw run log must belong to sealed case output directory')
    if sha(case/'source.sha256')!=MANIFEST_SHA or sha(case/'build_only.sh')!=RUNNER_SHA:raise ValueError('sealed manifest/runner mismatch')
    entries=[]
    for line in (case/'source.sha256').read_text().splitlines():
        digest,relative=line.split('  ',1);p=case/relative
        if p.resolve()!=case and case not in p.resolve().parents:raise ValueError('manifest path escapes case')
        if sha(p)!=digest:raise ValueError('sealed source/programme mismatch '+relative)
        entries.append(relative)
    if len(entries)!=210 or sum(p.startswith('bundle/') for p in entries)!=206:raise ValueError('expected exact210/206 readset')
    binary=case/'out/obj/Vtb_hbm_slice';exe_sha=sha(binary)
    recorded=(case/'out/binary.sha256').read_text().split()[0]
    if exe_sha!=recorded:raise ValueError('actual new executable differs from build-only binary receipt')
    receipt=json.loads(Path(run_receipt).read_text())
    if receipt.get('exit_code')!=0 or type(receipt.get('exit_code')) is not int:
        raise ValueError('real run exit receipt must report zero exit status')
    if receipt.get('raw_run_sha256')!=sha(run_log) or receipt.get('executable_sha256')!=exe_sha:
        raise ValueError('real run receipt log/executable identity mismatch')
    if not receipt.get('started_at_UTC') or not receipt.get('finished_at_UTC'):
        raise ValueError('real run start/finish clocks required')
    pre=json.loads((case/'preflight.json').read_text());spec=json.loads((case/'sm_node_scoreboard.json').read_text())
    if pre['NEV_required']!=5968 or pre['fixed_end']!=85510 or pre['fault_faces']!=85:raise ValueError('finite programme contract mismatch')
    expected_sha=hashlib.sha256(b''.join(int(w,16).to_bytes(4,'little') for w in spec['expected_words'])).hexdigest()
    if expected_sha!=spec['golden_sha256']:raise ValueError('scoreboard golden identity mismatch')
    module_spec=importlib.util.spec_from_file_location('sealed_pv_checker',case/'bundle/check_slice_run.py')
    checker=importlib.util.module_from_spec(module_spec);module_spec.loader.exec_module(checker)
    generic=checker.check_run(case/'bundle/slice/replay/replay_candidate',run_log,boundary=case/'bundle/slice/boundary.json',tb_source=case/'bundle/slice/tb_slice.sv')
    log=run_log.read_text();node=check_rows(log,spec)
    errors=list(generic['errors'])+node['errors']
    if generic['summary'].get('stream_edges')!=85510:errors.append('actual fixed observation end differs from85510')
    return dict(status='PASS_PARTIAL_KEY_COMPONENT' if not errors else 'FAIL_PARTIAL_KEY_COMPONENT',passed=not errors,
                hardware_executed=True,full_ATT_PV=False,qualifies_native_layer=False,qualifies_native_chain=False,
                scope=spec['arithmetic_scope'],errors=errors,raw_run_sha256=sha(run_log),actual_new_executable_sha256=exe_sha,
                sealed_manifest_sha256=MANIFEST_SHA,sealed_runner_sha256=RUNNER_SHA,golden_sha256=expected_sha,run_receipt_sha256=sha(run_receipt),
                generic=generic,node=node,downstream_VM_drain_qualified=False,page_reuse_qualified=False)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--case',type=Path,required=True);p.add_argument('--run-log',type=Path,required=True);p.add_argument('--run-receipt',type=Path,required=True);p.add_argument('--out',type=Path)
    a=p.parse_args()
    try:r=collect(a.case,a.run_log,a.run_receipt)
    except (OSError,ValueError,KeyError) as e:r=dict(status='REFUSED_MISSING_OR_MISMATCHED_EVIDENCE',passed=False,hardware_execution_qualification=False,errors=[str(e)])
    payload=json.dumps(r,indent=1)+'\n'
    if a.out:a.out.write_text(payload)
    print(payload,end='');raise SystemExit(0 if r['passed'] else 1)
