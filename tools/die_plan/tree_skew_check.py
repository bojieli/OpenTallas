"""Source-tree skew check: a kit-wave source tree whose generator writes a construct its own checker does not accept.

FLOWGEN-1116: two gen-stage classes were one cause -- a pinned source tree carried the generator half of a change
but not the checker half (gen_phys wrote per-port tap_offset SDC lines, the tree sdc_lint predated tap_offset_ps ->
SdcLintError on s81 slice_station; the QC tree hard_landing predated ring_reset -> "hard landing actual child proof
failed: shared rst_xn[..]").  Run this on a tree before it is pinned as dies.<die>.src; exit 1 lists every pair
whose writer is present and whose reader is missing.   usage: python3 -I tree_skew_check.py TREE [TREE ...]
"""
import sys
from pathlib import Path

# (writer file, writer marker, reader file, reader marker, what breaks)
PAIRS = (
    ("gen_phys.py", "def tap_offset_lines", "sdc_lint.py", "tap_offset_ps",
     "kit SDC carries per-port -early/-late offset lines that sdc_lint rejects as a bad clock window"),
    ("gen_phys.py", "def tap_window_port_table", "sdc_lint.py", "tap_window_port_ps",
     "kit SDC carries measured per-port tap windows that sdc_lint rejects"),
    ("face_guard.py", "ring_reset=False", "hard_landing.py", "ring_reset=",
     "hard-child proof fails every replicated rst_xn ring reset as shared"),
)


def check(tree):
    d = Path(tree) / "tools" / "die_plan"
    bad = []
    for wf, wm, rf, rm, why in PAIRS:
        w, r = d / wf, d / rf
        if not w.is_file() or not r.is_file():
            continue
        if wm in w.read_text() and rm not in r.read_text():
            bad.append(f"{tree}: {wf} has `{wm}` but {rf} lacks `{rm}`: {why}")
    return bad


def main(argv):
    bad = [b for t in argv for b in check(t)]
    for b in bad:
        print("TREE_SKEW " + b)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
