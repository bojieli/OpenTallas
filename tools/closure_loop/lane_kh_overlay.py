#!/usr/bin/env python3
"""lane_kh_overlay.py SRC  (synth-resta 2026-10-08): keep the replicated SU lane as ONE synthesised module.

The Qwen ROM core route with the stream unit inside (route_core.sh fallback suffix 'u', --su-in) flattens the 64
ot_hdc_vstream_lane instances of ot_hdc_vstream_rt into the core in the prep yosys run (synth -flatten -noabc) and
again in ORFS synthesis.  Every opt re-run then walks the 64-lane flat netlist while constants and sdff/dffe patterns
creep one pipeline stage per re-run: core_pu-30619b552-tt / core_pu_done_io80-751b7b4d4(-tt) sat 8-22 h in the prep
yosys (40-54 GB RSS) without finishing.  The fix is the hfd_coll / norm-MEM1 pattern: (* keep_hierarchy *) on the lane
INSTANCE (attribute only, same module, same logic), so yosys optimises and ABC maps the lane once.

Measured (2026-10-08, local, core_pu 3banmsup prep): kept lane + -noshare -nofsm finishes the prep in 9 min (5 GB);
the flat prep was still in the first coarse opt loop after 10 min at 32 GB (8-22 h on the fleet).

This patches SRC/tools/qwen_rom_core_ctx_claude.py (and the ORFS SYNTH_ARGS in route_core.sh) of a job snapshot so the emitted gen/ot_hdc_vstream_rt.sv carries
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
# yosys 0.68 with a kept lane under synth -flatten: FSM extraction hit an RTLIL memory assert / segfault in the
# following OPT_CLEAN (nondeterministic), and the SAT-based SHARE pass ran > 10 min on the core; both are optimisations
# with no functional effect (FSM re-encoding, operator sharing), so the prep and the ORFS synthesis skip them.
OLD_SYN = 'lines.append(line + " -noabc")'
NEW_SYN = 'lines.append(line + " -noabc -noshare -nofsm")  # lane_kh_overlay'
OLD_ORFS = "--orfs-var ADDER_MAP_FILE= "
NEW_ORFS = "--orfs-var ADDER_MAP_FILE= --orfs-var 'SYNTH_ARGS=-noshare -nofsm' "


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
    root = Path(sys.argv[1])
    for rel, pairs in (("tools/qwen_rom_core_ctx_claude.py", ((OLD, NEW), (OLD_SYN, NEW_SYN))),
                       ("physical/qwen_die_masters/jobs/route_core.sh", ((OLD_ORFS, NEW_ORFS),))):
        p = root / rel
        t = p.read_text()
        for old, new in pairs:
            if new in t:
                continue
            if t.count(old) != 1:
                sys.exit(f"lane_kh: {old!r} not found exactly once in {p}")
            t = t.replace(old, new)
        p.write_text(t)
        print(f"lane_kh: patched {p}")


if __name__ == "__main__":
    main()
