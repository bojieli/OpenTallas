#!/usr/bin/env python3
"""Exact gate of dsfd_mtp_seed_launch (DSpark primary die: seed descriptor -> seed program; mtp-dsbind 2026-10-10).

    python3 tools/mtp_seed_launch_gate.py --out <dir> [--record <json>]          # positives + negatives + mutants
    python3 tools/mtp_seed_launch_gate.py --out <dir> --only pos                  # positives + rejecting negatives
    python3 tools/mtp_seed_launch_gate.py --out <dir> --only mut                  # RTL mutants (must FAIL)

Bench rtl/dsrom_sys/mtp/tb_mtp_seed_launch.sv (iverilog).  Cases:
  pos_basic   two users, prefill + accepted / rejected steps (epoch +1), all-accepted 6-row step: every x beat equals the
              VM word of the expected (user, position), rows in order, one program start per descriptor
  pos_win     a prefill longer than the drafter window (300 > 256): only the last 256 rows are launched
  neg_drop    a descriptor lost on the lane: the next one leaves a gap -> rejected (fault[0]), nothing launched
  neg_stale   a contiguous descriptor with an older epoch -> rejected (fault[1])
  neg_replay  the same descriptor delivered twice -> the replay is rejected (fault[0])
The negatives are PASS when the DUT rejects as required.  Mutants (must FAIL): OT_SEEDL_MUT_NOGAP on neg_drop /
neg_replay, OT_SEEDL_MUT_NOEPOCH on neg_stale.
Prints SEED_LAUNCH_GATE PASS ... (all expectations met) or SEED_LAUNCH_GATE FAIL; with --only mut, prints
SEED_LAUNCH_MUTANTS FAIL_AS_REQUIRED when every mutant fails.
"""
import argparse
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ['rtl/dsrom_sys/mtp/ot_dsrom_mtp_seed_launch.sv', 'rtl/dsrom_sys/mtp/ot_dsrom_mtp_link_rtt.sv',
       'rtl/dsrom_sys/mtp/ot_dsrom_mtp_link_pair.sv', 'rtl/dsrom_sys/mtp/rtt/ot_dsrom_mtp_rstsync.sv',
       'rtl/dsrom_sys/mtp/tb_mtp_seed_launch.sv']
POS = ['pos_basic', 'pos_win', 'neg_drop', 'neg_stale', 'neg_replay']
MUT = [('OT_SEEDL_MUT_NOGAP', 'neg_drop'), ('OT_SEEDL_MUT_NOGAP', 'neg_replay'), ('OT_SEEDL_MUT_NOEPOCH', 'neg_stale')]


def build(out, define=None):
    exe = out / ('sim' + ('_' + define if define else ''))
    cmd = ['iverilog', '-g2012', '-o', str(exe), '-s', 'tb_mtp_seed_launch'] + (['-D' + define] if define else [])
    subprocess.run(cmd + [str(ROOT / s) for s in SRC], check=True)
    return exe


def run(exe, case):
    r = subprocess.run(['vvp', '-n', str(exe), f'+CASE={case}'], capture_output=True, text=True, timeout=3600)
    m = re.search(r'SEEDL_RESULT (.*)', r.stdout)
    rec = dict(case=case, rc=r.returncode, line=m.group(1) if m else None)
    if m:
        rec.update({k: v for k, v in re.findall(r'(\w+)=(\S+)', m.group(1))})
    rec['errors'] = [l for l in r.stdout.splitlines() if l.startswith('SEEDL_ERR')][:10]
    return rec


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--only', choices=['pos', 'mut'])
    ap.add_argument('--record', type=Path)
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    rec = dict(schema='opentallas.mtp-seed-launch-gate.v1', sources=SRC, cases=[], mutants=[])
    ok = True
    if a.only != 'mut':
        exe = build(a.out)
        for c in POS:
            r = run(exe, c)
            rec['cases'].append(r)
            ok &= r.get('result') == 'PASS'
            print(c, r.get('result'), r.get('fault'), 'desc_to_x', r.get('desc_to_x'), 'done_to_ps', r.get('done_to_ps'),
                  'row_gap', r.get('row_gap'), flush=True)
    mut_ok = True
    if a.only != 'pos':
        for d, c in MUT:
            r = run(build(a.out, d), c)
            r['define'] = d
            rec['mutants'].append(r)
            mut_ok &= r.get('result') == 'FAIL'
            print(d, c, r.get('result'), flush=True)
    b = next((x for x in rec['cases'] if x['case'] == 'pos_basic'), None)
    if b:
        rec['cycles'] = dict(desc_to_x=int(b['desc_to_x']), done_to_ps=int(b['done_to_ps']), row_gap=int(b['row_gap']),
                             basis='bench stations: descriptor FWD/RET 9/9, VM link 6/6 + 12-cycle VM latency, x / join 4 '
                                   'stations each way (desc_to_x = descriptor at the slab pin -> first x beat at its pin)')
    rec['verdict'] = dict(positives_and_rejections=ok if a.only != 'mut' else None,
                          mutants_fail=mut_ok if a.only != 'pos' else None)
    if a.record:
        a.record.parent.mkdir(parents=True, exist_ok=True)
        a.record.write_text(json.dumps(rec, indent=1) + '\n')
    if a.only == 'mut':
        print('SEED_LAUNCH_MUTANTS ' + ('FAIL_AS_REQUIRED' if mut_ok else 'NOT_DISCRIMINATING'))
        return 1 if mut_ok else 0          # a closure-loop 'fail' bench: non-zero when the mutants fail as required
    good = ok and mut_ok
    print(f'SEED_LAUNCH_GATE {"PASS" if good else "FAIL"} positives={sum(1 for x in rec["cases"] if x.get("result") == "PASS")}')
    return 0 if good else 1


if __name__ == '__main__':
    raise SystemExit(main())
