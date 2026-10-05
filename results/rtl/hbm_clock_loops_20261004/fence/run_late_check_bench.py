#!/usr/bin/env python3
"""LATE_CHECK=1 fence bench: the HA1 live-mutation fixture (tools/hbm_accel/run_txcount.py's
generated tb_w6_live.sv) with the successor instantiated LATE_CHECK=1. Every protocol case is
unchanged. The corruption cases keep the original's in-cycle safety check (no ready/valid on the
corrupting cycle: the in-cycle dirty gate) and move only the exact fault report one edge later;
a single-bit witness error or a single live-copy upset is held one edge and scrubbed on the
second; the UE row stays frozen
exactly as in the original. The RTL $fatal obligations (candidate encode == encode(next_raw);
no handshake on a dirty row) run on every cycle of every bench.
Also runs the actual W4/W6 tx-count bench with LATE_CHECK=1 and compares its log to LATE_CHECK=0.
Usage: run_late_check_bench.py <ha1_out_dir_from_run_txcount> <out_dir>"""
import subprocess, sys
from pathlib import Path
root = Path(__file__).resolve().parents[4]
ha1, out = Path(sys.argv[1]), Path(sys.argv[2]); out.mkdir(parents=True, exist_ok=False)
tb = (ha1 / 'tb_w6_live.sv').read_text()
rep = [
 ("ot_hbm_rf_visibility_fence_live #(.ENABLE(1)) dut(", "ot_hbm_rf_visibility_fence_live #(.ENABLE(1),.LATE_CHECK(1)) dut("),
 ('''      tick; check(dut.enabled.protected_state==pristine,"single-bit ECC scrub");''',
  '''      check(!host_ack_ready && !req_ready,"dirty row releases nothing in-cycle");
      tick; check(!fault && dut.enabled.protected_state==(pristine^(144'd1<<i)),"dirty row held one edge");
      tick; check(!fault && dut.enabled.protected_state==pristine,"single-bit ECC scrub on the second edge");'''),
 ('''    tick; check(dut.enabled.live_a==dut.enabled.live_b,"single live-copy self-repair");''',
  '''    check(!host_ack_ready && !visible_valid,"disagreeing live copies release nothing in-cycle");
    tick; check(!fault && dut.enabled.live_a!=dut.enabled.live_b,"disagreeing row held one edge");
    tick; check(!fault && dut.enabled.live_a==dut.enabled.live_b,"single live-copy repaired on the second edge");'''),
 ('''    #1; check(fault && quarantine && !host_ack_ready && !visible_valid,"two live copies quarantine before release");''',
  '''    #1; check(!host_ack_ready && !visible_valid && !req_ready,"two live copies release nothing in-cycle");
    tick; check(fault && quarantine && !host_ack_ready && !visible_valid,"two live copies quarantine one edge later");'''),
 ('''    #1; check(fault && quarantine && !host_ack_ready && !req_ready,"double-bit ECC fail closed");''',
  '''    #1; check(!host_ack_ready && !req_ready,"double-bit ECC releases nothing in-cycle");
    tick; check(fault && quarantine && !host_ack_ready && !req_ready,"double-bit ECC fail closed one edge later");'''),
]
for a, b in rep:
    assert tb.count(a) == 1, a[:80]
    tb = tb.replace(a, b)
(out / 'tb_w6_live_late.sv').write_text(tb)
pkg = root / 'rtl/gpu/w6/ot_gpu_w6_secded_pkg.sv'
dut = root / 'rtl/hbm_accel/txcount/ot_hbm_rf_visibility_fence_live.sv'
def run(name, top, files, params=()):
    exe = out / (name + '.vvp')
    c = subprocess.run(['iverilog', '-g2012', '-s', top, *params, '-o', str(exe), *map(str, files)], capture_output=True, text=True)
    r = subprocess.run(['vvp', str(exe)], capture_output=True, text=True) if c.returncode == 0 else None
    log = c.stdout + c.stderr + ('' if r is None else r.stdout + r.stderr)
    (out / (name + '.log')).write_text(log)
    ok = r is not None and r.returncode == 0 and 'FAIL' not in r.stdout
    print(name, 'PASS' if ok else 'FAIL'); return ok, ('' if r is None else r.stdout)
ok1, l1 = run('w6_live_mutation_late', 'tb_w6_fullwidth_fence', [pkg, dut, out / 'tb_w6_live_late.sv'])
ok0, l0 = run('w6_live_mutation_lc0', 'tb_w6_fullwidth_fence', [pkg, dut, ha1 / 'tb_w6_live.sv'])
e1 = [l for l in l1.splitlines() if l.startswith('W6_EDGE')]; e0 = [l for l in l0.splitlines() if l.startswith('W6_EDGE')]
# the late fixture waits extra edges in case 50 (scrub/UE) and the appended two-copy case:
# compare (case, kind, identity) for every accepted handshake, and edge numbers before case 50
import re as _re
def key(l): return _re.sub(r' edge=\d+', '', l)
def case(l): return int(_re.search(r'case=(\d+)', l).group(1))
same = [key(a) for a in e0] == [key(b) for b in e1] and [a for a in e0 if case(a) < 50] == [b for b in e1 if case(b) < 50]
print('edge_logs_identical', same, len(e0), len(e1))
e1, e0 = (e0, e0) if same else (e1, e0)
prefix = 'results/uarch/Euclid_W4_RFACK_identity_contract_20261003/selfcontained-peer-r10/design/'
act = [pkg, root/'rtl/hbm_accel/txcount/ot_hbm_txcount_sm.sv', dut, root/'rtl/hbm_accel/txcount/ot_hbm_txcount_tap.sv',
       root/(prefix+'ot_gpu_rf_service.sv'), root/(prefix+'ot_sram_1r1w_128x256_m1_r2c2.v'), root/'rtl/hbm_accel/txcount/tb_txcount_actual_w4_w6.sv']
atb = (root/'rtl/hbm_accel/txcount/tb_txcount_actual_w4_w6.sv').read_text()
late_tb = out/'tb_txcount_actual_w4_w6_late.sv'
late_tb.write_text(atb.replace('ot_hbm_rf_visibility_fence_live #(', 'ot_hbm_rf_visibility_fence_live #(.LATE_CHECK(1),'))
okA, lA = run('actual_w4_w6_late', 'tb_txcount_actual_w4_w6', act[:-1] + [late_tb])
okB, lB = run('actual_w4_w6_lc0', 'tb_txcount_actual_w4_w6', act)
print('actual_logs_identical', lA == lB)
sys.exit(0 if (ok1 and ok0 and okA and okB and e1 == e0 and lA == lB) else 1)
