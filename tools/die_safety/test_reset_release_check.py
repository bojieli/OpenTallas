#!/usr/bin/env python3
"""reset_release_check: a reset hop between two regional clocks is FOREIGN (fail); same region, landing ring and
synchroniser async input are not; an STA failure launched by a reset repeater into another region is RESET_XREG."""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

TOOL = Path(__file__).with_name('reset_release_check.py')
DIE_V = """module die_top ();
  qfd_rstsync rs_bump (.arst_n(n_rst_fwd), .ck(n_clk_a), .rso_d(n_rst_a));
  qfd_rst_rep r0 (.clk(n_clk_a), .d(n_rst_a), .q0(n_t1));
  qfd_rst_rep r1 (.clk(n_clk_a), .d(n_t1), .q0(n_t2));
  qfd_rlyrl_1_NE_65x30 land0 (.a(n_t2), .ck(n_clk_c), .b(n_t4));
  qfd_rst_rep r2 (.clk(n_clk_b),
     .d(n_t2), .q0(n_t3));
  blk u_blk (.ck(n_clk_b), .rst_n(n_t3));
endmodule
"""
SUMMARY = """Startpoint                           Endpoint                               Slack
--------------------------------------------------------------------------------
r1/q0 (qfd_rst_rep) r2/d (qfd_rst_rep) -7772.50
r2/q0 (qfd_rst_rep) u_blk/rst_n (blk) -10.00
x/q (dff) y/d (dff) -5.00
r0/q0 (qfd_rst_rep) r1/d (qfd_rst_rep) 12.00
"""


def run(tmp, *extra):
    out = Path(tmp) / 'r.json'
    p = subprocess.run([sys.executable, str(TOOL), '--die-v', str(Path(tmp) / 'die.v'), '--out', str(out), *extra],
                       capture_output=True, text=True)
    return p.returncode, json.loads(out.read_text()), p.stdout


def test_static_and_sta_classes():
    with tempfile.TemporaryDirectory() as tmp:
        (Path(tmp) / 'die.v').write_text(DIE_V)
        (Path(tmp) / 's.rpt').write_text(SUMMARY)
        rc, rep, _ = run(tmp)
        c = rep['static']['counts']
        assert rc == 1 and rep['verdict'] == 'FAIL'
        assert c.get('FOREIGN') == 1, c                       # r1 (a) -> r2 (b)
        assert c.get('LANDED') == 1 and c.get('SYNC', 0) == 0, c
        assert c.get('INTRA') == 3, c                         # rs_bump->r0, r0->r1, r2->u_blk
        rc, rep, line = run(tmp, '--setup', str(Path(tmp) / 's.rpt'), '--diagnostic', 'unit')
        k = rep['corners'][0]['counts']
        assert rc == 0 and 'DIAGNOSTIC' in line
        assert k == {'RESET_XREG': 1, 'RESET_INTRA': 1, 'OTHER': 1}, k


def test_landed_tree_passes():
    with tempfile.TemporaryDirectory() as tmp:
        (Path(tmp) / 'die.v').write_text(DIE_V.replace('qfd_rst_rep r2 (.clk(n_clk_b)', 'qfd_rst_rep r2 (.clk(n_clk_a)')
                                         .replace('blk u_blk (.ck(n_clk_b)', 'blk u_blk (.ck(n_clk_a)'))
        rc, rep, _ = run(tmp)
        assert rc == 0 and rep['verdict'] == 'PASS', rep['static']


if __name__ == '__main__':
    test_static_and_sta_classes()
    test_landed_tree_passes()
    print('PASS')
