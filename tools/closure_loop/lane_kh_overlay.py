#!/usr/bin/env python3
"""lane_kh_overlay.py SRC  (synth-resta 2026-10-08): keep the replicated SU lane as ONE synthesised module.

The Qwen ROM core route with the stream unit inside (route_core.sh fallback suffix 'u', --su-in) flattens the 64
ot_hdc_vstream_lane instances of ot_hdc_vstream_rt into the core in the prep yosys run (synth -flatten -noabc) and
again in ORFS synthesis.  Every opt re-run then walks the 64-lane flat netlist while constants and sdff/dffe patterns
creep one pipeline stage per re-run: core_pu-30619b552-tt / core_pu_done_io80-751b7b4d4(-tt) sat 8-22 h in the prep
yosys (40-54 GB RSS) without finishing.  The fix is the hfd_coll / norm-MEM1 pattern: (* keep_hierarchy *) on the lane
INSTANCE (attribute only, same module, same logic), so yosys optimises and ABC maps the lane once.

This patches SRC/tools/qwen_rom_core_ctx_claude.py of a job snapshot so the emitted gen/ot_hdc_vstream_rt.sv carries
the attribute (on its own line, so the prep's module_closure() still finds the lane instance); the patched emitter
asserts the emitted text equals the unpatched emission with exactly that one attribute line removed (exactness by construction).  Idempotent.  --selftest checks the check
(an equal text passes, a one-operator mutant fails).
"""
import sys
from pathlib import Path

OLD = '(a.out / "gen/ot_hdc_vstream_rt.sv").write_text(E.E.emit_vstream(E.E.VSTREAM.read_text()))'
ATTR = "(* keep_hierarchy *)\n        "   # own line: module_closure() matches instances at line start
INST = "ot_hdc_vstream_lane #("
NEW = ("_vs = E.E.emit_vstream(E.E.VSTREAM.read_text()); "
       f"_kh = _vs.replace({INST!r}, {ATTR + INST!r}, 1); "
       f"assert _kh.count({ATTR!r}) == _vs.count({ATTR!r}) + 1 and _kh.replace({ATTR + INST!r}, {INST!r}, 1) == _vs, "
       "'lane_kh: emitted vstream is not the original + one keep_hierarchy'; "
       '(a.out / "gen/ot_hdc_vstream_rt.sv").write_text(_kh)  # lane_kh_overlay')


def exact(orig, kh):
    return kh.count(ATTR) == orig.count(ATTR) + 1 and kh.replace(ATTR + INST, INST, 1) == orig


def selftest():
    orig = "x\n        " + INST + ".WR(WR)) u_lane (.a(b & c));\n"
    kh = orig.replace(INST, ATTR + INST, 1)
    mut = kh.replace("b & c", "b | c")
    assert exact(orig, kh) and not exact(orig, mut) and not exact(orig, orig)
    print("LANE_KH SELFTEST PASS (equal passes, mutant and missing attribute fail)")


def main():
    if sys.argv[1:] == ["--selftest"]:
        return selftest()
    p = Path(sys.argv[1]) / "tools/qwen_rom_core_ctx_claude.py"
    t = p.read_text()
    if "# lane_kh_overlay" in t:
        print(f"lane_kh: {p} already patched")
        return
    if t.count(OLD) != 1:
        sys.exit(f"lane_kh: emitter line not found exactly once in {p}")
    p.write_text(t.replace(OLD, NEW))
    print(f"lane_kh: patched {p}")


if __name__ == "__main__":
    main()
