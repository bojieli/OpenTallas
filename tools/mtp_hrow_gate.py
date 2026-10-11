#!/usr/bin/env python3
"""Exact gate of the main-hidden row path to the DSpark primary die (mtp-dsbind 2026-10-10):
3 x ot_dsrom_mtp_hrow_tx -> stations -> dsfd_mtp_hrow (row store) <- dsfd_mtp_seed_launch (seed client).

    python3 tools/mtp_hrow_gate.py --out <dir> [--record <json>] [--only pos|mut]

Bench rtl/dsrom_sys/mtp/tb_mtp_hrow.sv (iverilog, real SRAM macro models).  Cases:
  pos_steady  two users; prefill, rejection (epoch +1: squashed rows re-land under the new epoch), all-accepted steps:
              every x beat equals the issued row version's beat
  pos_late    the descriptor arrives BEFORE the re-verified rows (the store holds the squashed old-epoch rows): the
              read must wait for the new version
  neg_drop    one part of a committed row lost: the row is never served (seed waits), the ring wrap is flagged
              (store fault[0]) -- PASS when rejected exactly so
Mutants (must FAIL): OT_HROW_MUT_NOEPOCH on pos_late (serves the stale squashed row), OT_HROW_MUT_NOPART on neg_drop
(serves a row with a missing part).
"""
import argparse, json, re, subprocess
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
SRC = ['rtl/dsrom_sys/mtp/ot_dsrom_mtp_hrow.sv', 'rtl/dsrom_sys/mtp/ot_dsrom_mtp_seed_launch.sv',
       'rtl/dsrom_sys/mtp/ot_dsrom_mtp_link_rtt.sv', 'rtl/dsrom_sys/mtp/ot_dsrom_mtp_link_pair.sv',
       'rtl/dsrom_sys/mtp/rtt/ot_dsrom_mtp_rstsync.sv',
       'physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v',
       'rtl/dsrom_sys/mtp/tb_mtp_hrow.sv']
POS = ['pos_steady', 'pos_late', 'neg_drop']
MUT = [('OT_HROW_MUT_NOEPOCH', 'pos_late'), ('OT_HROW_MUT_NOPART', 'neg_drop')]


def build(out, d=None):
    exe = out / ('sim' + ('_' + d if d else ''))
    subprocess.run(['iverilog', '-g2012', '-o', str(exe), '-s', 'tb_mtp_hrow'] + (['-D' + d] if d else [])
                   + [str(ROOT / s) for s in SRC], check=True)
    return exe


def run(exe, case):
    r = subprocess.run(['vvp', '-n', str(exe), f'+CASE={case}'], capture_output=True, text=True, timeout=7200)
    m = re.search(r'HROW_RESULT (.*)', r.stdout)
    rec = dict(case=case, rc=r.returncode, line=m.group(1) if m else None,
               errors=[l for l in r.stdout.splitlines() if l.startswith('HROW_ERR')][:10])
    if m:
        rec.update(dict(re.findall(r'(\w+)=(\S+)', m.group(1))))
    return rec


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--only', choices=['pos', 'mut'])
    ap.add_argument('--record', type=Path)
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    rec = dict(schema='opentallas.mtp-hrow-gate.v1', sources=SRC, cases=[], mutants=[])
    ok = mut_ok = True
    if a.only != 'mut':
        exe = build(a.out)
        for c in POS:
            r = run(exe, c); rec['cases'].append(r); ok &= r.get('result') == 'PASS'
            print(c, r.get('result'), r.get('cyc'), r.get('store_fault'), flush=True)
    if a.only != 'pos':
        for d, c in MUT:
            r = run(build(a.out, d), c); r['define'] = d; rec['mutants'].append(r); mut_ok &= r.get('result') == 'FAIL'
            print(d, c, r.get('result'), flush=True)
    rec['verdict'] = dict(positives_and_rejections=ok if a.only != 'mut' else None,
                          mutants_fail=mut_ok if a.only != 'pos' else None)
    if a.record:
        a.record.parent.mkdir(parents=True, exist_ok=True)
        a.record.write_text(json.dumps(rec, indent=1) + '\n')
    if a.only == 'mut':
        print('HROW_MUTANTS ' + ('FAIL_AS_REQUIRED' if mut_ok else 'NOT_DISCRIMINATING'))
        return 1 if mut_ok else 0
    print(f'HROW_GATE {"PASS" if ok and mut_ok else "FAIL"} positives={sum(1 for x in rec["cases"] if x.get("result") == "PASS")}')
    return 0 if ok and mut_ok else 1


if __name__ == '__main__':
    raise SystemExit(main())
