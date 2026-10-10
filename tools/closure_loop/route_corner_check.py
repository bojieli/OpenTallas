#!/usr/bin/env python3
"""LOOP-CORNER (2026-10-10): prove from the ORFS logs which liberty corner a route ACTUALLY repaired setup at.

   route_corner_check.py <run dir> [--want TT] [--include-cal]   exit 0: every setup corner read only <want> liberties

The verdict check ttb_routed_at_TC used to pass on any 'TC ...' line in <run>/cl/ttb_corner.txt; the tt_overlay writes such a
line for unrelated patches (direct config.mk), so SM piece routes that loaded SS liberties (the generator ignored
OT_ORFS_CORNER_OVERRIDE) were judged "routed at TC".  This reads the read_liberty lines the place / CTS / GRT stages
logged (`read_liberty -corner <C> <file>`): a corner whose libraries are not all FF is a setup corner, and every setup
corner must read only <want> std-cell (*_TT_nldm*) and macro (*_tt.lib) views.  No logs or no liberty lines: fail
(unproven).  Earlier attempts (*.attempt*), the source snapshot and (unless --include-cal) the CTS-only calibrate
directories (*_cal) are ignored."""
import os
import re
import sys

STAGE_LOGS = ("3_3_place_gp.log", "3_4_place_resized.log", "4_1_cts.log", "5_1_grt.log")
LIB_RE = re.compile(r"^\s*read_liberty\s+(?:-corner\s+(\S+)\s+)?(\S+)", re.M)
TAG_RE = re.compile(r"_(SS|TT|FF)_nldm|_(ss|tt|ff)\.lib(?:\.gz)?$")


def tag(path):
    m = TAG_RE.search(os.path.basename(path))
    return (m.group(1) or m.group(2)).upper() if m else None


def find_logs(root, include_cal=False):
    out = []
    for d, dirs, files in os.walk(root):
        dirs[:] = [x for x in dirs if ".attempt" not in x and not (d == root and x in ("src", "cl"))
                   and (include_cal or not x.endswith("_cal"))]
        out += [os.path.join(d, f) for f in files if f in STAGE_LOGS]
    return sorted(out)


def check(root, want="TT", include_cal=False):
    """(ok, lines): one line per log, '<log>: <corner>=<setup tags> ...'"""
    logs = find_logs(root, include_cal)
    if not logs:
        return False, [f"no ORFS stage log ({'/'.join(STAGE_LOGS)}) under {root}: routed corner unproven"]
    ok, seen, lines = True, False, []
    for f in logs:
        try:
            text = open(f, errors="replace").read()
        except OSError as e:
            ok = False
            lines.append(f"{f}: unreadable ({e})")
            continue
        corners = {}
        for c, lib in LIB_RE.findall(text):
            t = tag(lib)
            if t:
                corners.setdefault(c or "(single)", set()).add(t)
        # a single-corner load (no CORNERS) reads the setup and FF views into one scene: the non-FF tags are its setup corner
        setup = {c: t - {"FF"} for c, t in corners.items() if t - {"FF"}}
        if not setup:
            continue
        seen = True
        bad = {c: t for c, t in setup.items() if t != {want}}
        ok = ok and not bad
        lines.append(f"{'BAD' if bad else 'ok '} {os.path.relpath(f, root)}: "
                     + " ".join(f"{c}={'+'.join(sorted(t))}" for c, t in sorted(setup.items())))
    if not seen:
        return False, lines + [f"no read_liberty -corner lines in {len(logs)} stage logs under {root}: routed corner unproven"]
    return ok, lines


def main(argv):
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__)
        return 2
    want = argv[argv.index("--want") + 1].upper() if "--want" in argv else "TT"
    ok, lines = check(argv[0], want, "--include-cal" in argv)
    print("\n".join(lines[-12:]))
    print(f"ROUTE_CORNER {'OK' if ok else 'FAIL'} (setup corners must read {want} liberties)")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
