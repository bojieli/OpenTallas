"""HEAD-TILE-ETAP opt-in (DIE-HEAD-53 canary, COORD 10-31): tap_balance.tcl's whole-family early-source core re-hang
and its 30 ps stage price run only with OT_TAP_CORE_ETAP=1 (set by head_tile_c9.install for s81_head hd_tile only).
Unset, the core pass is the pre-ETAP one: own-tap tree source / port fallback and 18 ps a stage."""
import re
from pathlib import Path

TB = (Path(__file__).resolve().parent / "tap_balance.tcl").read_text()

# the pre-ETAP late-pin source selection and sizing (origin/main 79254088d), which the default path must keep verbatim
PRE_ETAP_LATE = """        lassign [tb_outside $it] px py
        set best ""; set bd 0
        foreach b [tb_tree_bufs [$bt getNet]] {
          lassign $b bn bpin bnet bx by
          set q [get_pins -quiet $bpin]
          if {$q eq ""} continue
          set ba [tb_rise $q 1]
          if {$ba eq "" || $ba + 20.0 > $need} continue
          set dd [expr {abs($bx - $px) + abs($by - $py)}]
          if {$best eq "" || $dd < $bd} { set best [list $bnet $ba]; set bd $dd }
        }
        if {$best eq ""} {
          set src [$bt getNet]; set base 0.0
        } else {
          lassign $best src base
        }
        set nb [expr {max(1, int(round(($need - $base - 20.0) / 18.0 * 0.75)))}]
      } else {
        set src [$it getNet]
        set nb [expr {max(1, int(round($d / $tb_cstage * 0.75)))}]
      }
"""


def _etap_block():
    i = TB.index("        if {$tb_etap} {\n")
    j = TB.index("\n        }\n", i)
    return TB[i:j]


def test_etap_flag_default_off():
    assert 'set tb_etap [expr {[info exists ::env(OT_TAP_CORE_ETAP)] && $::env(OT_TAP_CORE_ETAP) eq "1"}]' in TB
    # stage price: 18 ps (pre-ETAP) unless ETAP is on or OT_TAP_CORE_STAGE_PS is given
    assert "($tb_etap ? 30.0 : 18.0)" in TB
    assert TB.index("set tb_etap ") < TB.index("set tb_cstage ")


def test_etap_only_inside_gate():
    blk = _etap_block()
    for tok in ("tb_core_sources $mode", "tb_hang_path $it", "tb_core_path $sx", "OT_TAP_CORE_ETAP $p", "OT_TAP_CORE_SRC",
                "OT_TAP_CORE_SEG_UM", "_ce${tb_tag}"):
        assert TB.count(tok) == blk.count(tok) >= 1, tok
    assert blk.rstrip().endswith("continue")


def test_default_path_is_pre_etap():
    assert TB.count(PRE_ETAP_LATE) == 1
    assert TB.index(_etap_block()) < TB.index(PRE_ETAP_LATE)
    # the gate sits after the pre-ETAP skips, so an ETAP-off run takes exactly the old late-pin branch
    late = TB[TB.index("      if {$d < 0} {\n"):TB.index(PRE_ETAP_LATE)]
    assert re.search(r"if \{\[dict exists \$tb_hung \$p\]\} continue\n\s+set need \[expr \{\$tgt - \$L\}\]\n"
                     r"\s+if \{\$need < 20\.0\} continue\n\s+if \{\$tb_etap\} \{\n", late)
