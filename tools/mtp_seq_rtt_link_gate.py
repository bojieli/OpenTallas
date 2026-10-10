#!/usr/bin/env python3
"""Stress gate of dsfd_mtp_seq_rtt's receivers at the head die's actual relay chains (mtp-head-1010, 2026-10-10).

The system bench (tools/dsrom_mtp_rom_bench.py rtt_s0_*) proves the RTT sequencer exact in context, but its traffic never
stalls a receiver with flits in flight, so it cannot expose a short grant history. This gate runs the minimum link
(rtl/dsrom_sys/mtp/tb_mtp_link_rtt.sv: production ot_dsrom_mtp_ltx -> F registered relays -> receiver, R relays back,
1200 exact flits, bursts and long consumer stalls) at exactly the sequencer's receiver parameters:
    r: RESULT u_r      capture -> mtp 5 / mtp -> capture 6   H 14, D 15
    v: u_w / u_q       vm -> mtp 9 / mtp -> vm 10            H 22, D 23
    python3 tools/mtp_seq_rtt_link_gate.py one CASE --out DIR     (prints MTP_SEQ_RTT CASE PASS|FAIL)
Cases: pass_r, pass_v (ENABLE_RTT 1); fail_legacy_r, fail_legacy_v (legacy ot_dsrom_mtp_lrx, 3-cycle history, same D:
must overflow); fail_short_r (OT_MTP_NEG_SHORT_RTT).  A FAIL case reports FAIL when the receiver overflows, as required.
"""
import argparse, subprocess, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
SRC = ['rtl/dsrom_sys/mtp/ot_dsrom_mtp_link_pair.sv', 'rtl/dsrom_sys/mtp/ot_dsrom_mtp_link_rtt.sv', 'rtl/dsrom_sys/mtp/tb_mtp_link_rtt.sv']
CASES = dict(pass_r=(5, 6, 1, []), pass_v=(9, 10, 1, []), fail_legacy_r=(5, 6, 0, []), fail_legacy_v=(9, 10, 0, []),
             fail_short_r=(5, 6, 1, ['-DOT_MTP_NEG_SHORT_RTT']))


def one(name, out):
    f, r, en, defs = CASES[name]
    out.mkdir(parents=True, exist_ok=True)
    exe = out / f'{name}.vvp'
    cmd = ['iverilog', '-g2012', '-s', 'tb_mtp_link_rtt'] + [f'-Ptb_mtp_link_rtt.{k}={v}' for k, v in
                                                            dict(F=f, R=r, ENABLE=en, STRESS=1, DEPTH=f + r + 4).items()]
    c = subprocess.run(cmd + defs + ['-o', str(exe)] + SRC, cwd=ROOT, capture_output=True, text=True)
    if c.returncode:
        print(c.stdout + c.stderr); print(f'MTP_SEQ_RTT {name} BUILD_ERROR'); return 2
    p = subprocess.run(['vvp', str(exe)], cwd=ROOT, capture_output=True, text=True)
    (out / f'{name}.log').write_text(p.stdout + p.stderr)
    ok = p.returncode == 0 and 'PASS RTT_LINK' in p.stdout and 'sent=1200 received=1200' in p.stdout
    print(p.stdout[-600:])
    print(f'MTP_SEQ_RTT {name} {"PASS" if ok else "FAIL"}')
    return 0 if ok else 1


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('mode', choices=['one', 'all']); ap.add_argument('case', nargs='?'); ap.add_argument('--out', type=Path, required=True)
    a = ap.parse_args()
    if a.mode == 'one':
        sys.exit(one(a.case, a.out))
    rc = {n: one(n, a.out) for n in CASES}
    bad = [n for n, v in rc.items() if (v == 0) != n.startswith('pass')]
    print('MTP_SEQ_RTT GATE', 'PASS' if not bad else f'FAIL {bad}'); sys.exit(1 if bad else 0)
