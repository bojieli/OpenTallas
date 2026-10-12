#!/usr/bin/env python3
"""child_ins_env.py VIEW_DIR... -> "master ps master ps ..." (TT-lib clock-pin insertion, max_clock_tree_path) for
physical/common_flow/spine_child_ins.tcl (OT_SPINE_CHILD_INS).  A view dir holds <master>.lef + <master>_tt.lib; a
view without a TT lib or without clock-tree arcs is an error (the spine would balance it as 0 ps)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "hier_contract"))
import child_lint  # noqa: E402

out = []
for d in sys.argv[1:]:
    p = Path(d)
    lefs = sorted(p.glob("*.lef"))
    if not lefs:
        sys.exit(f"child_ins_env: no LEF in {d}")
    m = lefs[0].stem
    lib = p / f"{m}_tt.lib"
    if not lib.exists():
        sys.exit(f"child_ins_env: {lib} missing")
    ins = child_lint.clock_insertion(lib.read_text(errors="replace"))
    if not ins:
        sys.exit(f"child_ins_env: no clock-tree arcs in {lib}")
    out += [m, f"{max(v['max_ps'] for v in ins.values()):.1f}"]
print(" ".join(out))
