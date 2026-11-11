from pathlib import Path
import subprocess

SRC = Path(__file__).with_name("core_tap_align.tcl").read_text()


def _proc():
    i = SRC.index("proc ta_step {now a0 nb}")
    return SRC[i:SRC.index("\n}\n", i) + 3]


def _step(now, a0, nb):
    p = subprocess.run(["tclsh"], input=_proc() + f"puts [ta_step {now} {a0} {nb}]\n",
                       text=True, capture_output=True)
    assert p.returncode == 0 and not p.stderr, p.stderr
    return float(p.stdout.strip())


def test_unmoved_tap_is_not_clamped_to_floor():
    # v512b tap 700011: 617 -> 617 after one calibration cell
    assert _step(617.0, 617.0, 1) == -1
    assert _step(616.5, 617.0, 1) == -1


def test_real_steps_keep_the_clamp():
    assert _step(637.0, 617.0, 1) == 20.0
    assert _step(625.0, 617.0, 1) == 12.0
    assert _step(700.0, 617.0, 2) == 30.0


def test_loop_uses_default_for_unmoved_tap():
    assert "set st [ta_step [lindex [dict get $m $n] 0] $a0 $nb]" in SRC
    assert "if {$st < 0} { set st 20.0;" in SRC


def test_twelve_ps_sizing_overshoot_is_what_the_default_avoids():
    deficit, real = 860.2 - 617.0, 21.5
    over_floor = int(deficit / 12.0 + 0.5) * real - deficit
    over_default = int(deficit / 20.0 + 0.5) * real - deficit
    assert over_floor > 150 and abs(over_default) < 30
