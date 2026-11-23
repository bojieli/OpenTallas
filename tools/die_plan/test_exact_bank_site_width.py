"""BANK-SITE-WIDTH-1122 (COORD 19:5x/21:0x; KV kv3_pv_v3, OPUS-FIX-KV-PV-R7 754c304f): an exact internal bank sized for 1.188-um
sites that holds a 1.404-um DFFASRHQNx1 reset flop placed with "exact internal bank flop exceeds its footprint".  The wide member
now takes a bank site with no other site of its row under its width (the SOFTCS-EDGE-1122 rule of soft_cs_placement); refused
only when no such site is free.  Run on tclsh with mock OpenDB objects."""
import shutil
import subprocess

import pytest

from kit_istations import EXACT_BANK_TCL

MOCK = r'''
set ff_dbu 1000; set ff_sw 54; set ff_x0 0; set ff_y0 0; set ff_x1 100000; set ff_y1 100000
set ff_orient [dict create 0 R0 270 MX]
set is_n 0; set is_fh stdout
set LOC {}
proc mkmaster {nm w} { proc M_$nm {op} "switch \$op { getName {return $nm} getWidth {return $w} getHeight {return 270} }"; return M_$nm }
proc mkinst {nm m} {
  set c I_[string map {. _ [ _ ] _ $ _} $nm]
  proc $c {op args} "global LOC; switch \$op { getName {return {$nm}} getMaster {return $m} setLocation {dict set LOC {$nm} \$args} default {} }"
  return $c
}
set FF [mkmaster DFFHQNx1 1080]; set AR [mkmaster DFFASRHQNx1 1404]
proc blk_insts {} { global INSTS; return $INSTS }
proc ff_blk {op} { return [blk_insts] }
set ff_blk ff_blk
'''


def run(script):
    body = "if {[catch {" + script + "} err]} {puts \"ERR:$err\"; exit 1}\n"
    body += 'dict for {k v} $LOC {puts "AT $k [join $v { }]"}\n'
    r = subprocess.run(["tclsh"], input=MOCK + EXACT_BANK_TCL + body, text=True, capture_output=True)
    return r.returncode, r.stdout + r.stderr


@pytest.mark.skipif(not shutil.which("tclsh"), reason="no tclsh")
def test_wide_reset_flop_takes_free_edge_site():
    # 3 payload bits + epoch (eq, the async-reset flop, planned at 3.456 with 4.644 under it); bit 1 holds the row end -> swap
    rc, out = run(r'''
set INSTS [list [mkinst {u_b.q[0]} $FF] [mkinst {u_b.q[1]} $FF] [mkinst {u_b.eq} $AR] [mkinst {u_b.q[2]} $FF]]
is_exact_bank u_b 3 {{1.08 0} {4.644 0} {2.268 0} {3.456 0}} 1.188 0.27 ist:x 0
''')
    assert rc == 0, out
    assert "BANK-SITE-WIDTH" in out and "u_b.eq" in out
    assert "AT u_b.eq 4644 0" in out        # the last site of the row (nothing to its right)
    assert "AT u_b.q[1] 3456 0" in out      # swapped into the epoch's planned site
    assert "AT u_b.q[2] 2268 0" in out


@pytest.mark.skipif(not shutil.which("tclsh"), reason="no tclsh")
def test_no_free_edge_site_is_refused():
    # two wide members, one row end
    rc, out = run(r'''
set INSTS [list [mkinst {u_b.q[0]} $AR] [mkinst {u_b.eq} $AR]]
is_exact_bank u_b 1 {{1.08 0} {2.268 0}} 1.188 0.27 ist:x 0
''')
    assert rc != 0 and "no edge site is free" in out, out


@pytest.mark.skipif(not shutil.which("tclsh"), reason="no tclsh")
def test_fitting_bank_unchanged():
    rc, out = run(r'''
set INSTS [list [mkinst {u_b.q[0]} $FF] [mkinst {u_b.eq} $FF]]
is_exact_bank u_b 1 {{1.08 0} {2.268 0}} 1.188 0.27 ist:x 0
''')
    assert rc == 0 and "BANK-SITE-WIDTH" not in out, out
    assert "AT u_b.q[0] 1080 0" in out and "AT u_b.eq 2268 0" in out
