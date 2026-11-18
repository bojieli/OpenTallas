"""FLOW-QC-CB 11-17: the xstn member join runs to a fixpoint (cbn_q01 tap_d[431/439/442/465], cap[10] at -42 .. -47.5:
8-10 cell buffer chains stranded at their GPL positions by a 4-round limit; built 1,010-1,040 um for 140-210 um direct)."""
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = (ROOT / "tools/die_plan/core_input_chain.tcl").read_text()


def test_join_is_not_limited_to_four_rounds():
    assert "for {set nx_r 0} {$nx_r < 4} {incr nx_r} {" not in SRC
    assert "set nx_rounds 32" in SRC and "OT_NK_XSTN_JOIN_ROUNDS" in SRC
    assert "for {set nx_r 0} {$nx_r < $nx_rounds} {incr nx_r} {" in SRC
    i = SRC.index("for {set nx_r 0} {$nx_r < $nx_rounds}")
    assert "if {![llength $nx_add]} break" in SRC[i:i + 2500]      # still stops as soon as no cell joins


def test_pure_model_of_the_join_chain():
    """a chain of n cells joins one cell per round from the member side: 4 rounds strand 5 of 9, 32 rounds join all"""
    script = r"""
proc join {n rounds} {
  set joined 0
  for {set r 0} {$r < $rounds} {incr r} { if {$joined >= $n} break; incr joined }
  return $joined
}
puts "OLD [join 9 4]"
puts "NEW [join 9 32]"
"""
    with tempfile.TemporaryDirectory() as d:
        f = Path(d) / "m.tcl"
        f.write_text(script)
        p = subprocess.run(["tclsh", str(f)], capture_output=True, text=True)
    assert p.returncode == 0, p.stderr
    assert "OLD 4" in p.stdout and "NEW 9" in p.stdout
