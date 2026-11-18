"""FABLE-FIX-QC-N 11-17: the latch_except_hb4 pad chain is sited at its core pin (two dont_touch HB4 cells of one chain were 73.2 um apart, cbn_q01 3_4 RSZ-3006)."""
import re
import subprocess
import tempfile
from pathlib import Path

SRC = (Path(__file__).resolve().parent / "core_input_anchor.tcl").read_text()


def proc(name):
    m = re.search(r"^proc " + re.escape(name) + r"\s+\{[^\n]*?\}\s+\{", SRC, re.M)
    i, d = m.end(), 1
    while d:
        c = SRC[i]
        i += 1
        if c == "\\":
            i += 1
            continue
        d += (c == "{") - (c == "}")
    return SRC[m.start():i]


def test_pad_chain_groups_keep_chain_order_per_leaf_and_ignore_other_cells():
    t = proc("nka_pad_groups") + r"""
set rows {{x.u_hdly_lk_a_tap_0.g_b[0].g_k[2].u_hb 2 I2} {x.u_hdly_lk_a_tap_0.g_b[0].g_k[0].u_hb 0 I0} {x.u_hdly_lk_a_tap_0.g_b[0].g_k[1].u_hb 1 I1}
          {y.u_hdly_lk_b_tap_0.g_b[0].g_k[0].u_hb 0 J0} {x.u_other.g_b[0].g_k[0].u_hb 0 Z}}
dict for {k v} [nka_pad_groups $rows] { puts "G $k $v" }
"""
    with tempfile.TemporaryDirectory() as d:
        f = Path(d) / "p.tcl"
        f.write_text(t)
        out = subprocess.run(["tclsh", str(f)], capture_output=True, text=True, check=True).stdout
    assert "G x.u_hdly_lk_a_tap_0 I0 I1 I2" in out and "G y.u_hdly_lk_b_tap_0 J0" in out and "Z" not in out


def test_the_anchor_places_the_chain_outward_from_the_pin_and_the_pipe_register_last():
    i = SRC.index("OT_NK_PAD_ANCHOR")
    blk = SRC[SRC.index("set nka_padrows"):i]
    assert "lreverse $cells" in blk and "1.5 + 2.0 * $j" in blk and "nka_pipe_chain $an" in blk
    assert "puts $nka_out [$c getName]" in blk            # released to PLACED for DPL with the other FIRM anchors


def test_a_three_pad_chain_and_its_pipe_register_stay_inside_the_xstn_halo():
    """core_input_chain.tcl keeps the xstn strip 9 um (nc_halo) off the macro edge (wx0 = edge + nc_halo).  The chain sited at 2 + 4 j put the
    third HB4 at 10 um and the pipe register at 14 um: inside the strip, on the sites the xstn fill uses (r650 vs r648).  At 1.5 + 2.0 j the three
    HB4 are at 1.5 / 3.5 / 5.5 um and the pipe register at 7.5 um (cell widths about 1.4 um), all below the 9 um halo."""
    halo = float(re.search(r"set nc_halo \[expr \{round\(([0-9.]+) \* ", (Path(__file__).resolve().parent / "core_input_chain.tcl").read_text()).group(1))
    assert halo == 9.0
    last = 1.5 + 2.0 * 3                                  # the pipe register after N = 3 pad cells
    assert last + 1.4 / 2 < halo
    assert "1.5 + 2.0 * $j" in SRC
