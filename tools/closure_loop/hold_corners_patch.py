#!/usr/bin/env python3
"""closure-loop ROUTE HOLD CORNERS (2026-10-07): make a job's source-snapshot tools/run_abi3_physical.py honour
OT_ROUTE_HOLD_CORNERS (main carries the same code; this patches snapshots pinned before it).

Why: every loop route recipe runs --orfs-corner WC --hold-corners WC,BC with ONE SDC whose virtual IO clock sits at the
WC (SS) insertion.  At BC the launch/capture clock is ~40% earlier (SE_s6: 196 vs 360 ps), so every IO path shows a
FAKE BC hold violation of about the SS-FF insertion difference (SE_s6 route SDC: wo[*] output hold WC +106 / BC -121):
flow hold buffers by the thousand (SE_s6 7,531, SW_s4 5,939, ctrl_pc 11,732; RSZ-0060 / DPL-0033 deaths elsewhere).
OT_ROUTE_HOLD_CORNERS=primary keeps place-and-route repair at the primary corner only, where the route IO model is
consistent; FF hold is closed after the route by the hold ECO against the exact FF sign-off constraints.  Sign-off
(tools/w18/corner_sta.py, SS + FF) is unchanged.
   hold_corners_patch.py <src snapshot dir>      (idempotent; original kept as run_abi3_physical.py.pre_holdcorners)"""
import shutil
import sys
from pathlib import Path

ANCHOR = "    args = build_parser().parse_args(argv)\n"
CODE = r'''    _ot_rhc = os.environ.get("OT_ROUTE_HOLD_CORNERS", "").strip()
    if _ot_rhc and args.hold_corners:
        # closure loop (2026-10-07): route-time repair corners; "primary" = --orfs-corner (or the first listed corner)
        _ot_new = (args.orfs_corner or args.hold_corners.split(",")[0].strip()) if _ot_rhc == "primary" else _ot_rhc
        # a step hook that times a dropped corner by name (s81_ph vclk_latency.tcl: report_clock_latency -scenes BC)
        # would error (counted as an ORFS flow error) and fall back to a different IO model: keep the corners then
        _ot_drop = [c.strip() for c in args.hold_corners.split(",") if c.strip() not in _ot_new.split(",")]
        _ot_seen, _ot_todo, _ot_hit = set(), [h.split("=", 1)[-1] for h in (args.step_tcl or [])], None
        while _ot_todo and _ot_drop and not _ot_hit:
            _ot_f = _ot_todo.pop()
            _ot_p = Path(_ot_f[5:] if _ot_f.startswith("/src/") else _ot_f)
            if str(_ot_p) in _ot_seen or not _ot_p.is_file():
                continue
            _ot_seen.add(str(_ot_p))
            _ot_t = _ot_p.read_text(errors="replace")
            if any(re.search(rf"(-scenes|-corner|ot_clk_ins)\s+{re.escape(c)}\b", _ot_t) for c in _ot_drop):
                _ot_hit = str(_ot_p)
            _ot_todo += re.findall(r"^\s*source\s+(\S+)", _ot_t, re.M)
        if _ot_hit:
            print(f"OT_ROUTE_HOLD_CORNERS={_ot_rhc}: kept {args.hold_corners}: step hook {_ot_hit} times corner(s) "
                  f"{_ot_drop} by name", file=sys.stderr)
        else:
            print(f"OT_ROUTE_HOLD_CORNERS={_ot_rhc}: place-and-route repair corners {args.hold_corners} -> {_ot_new} "
                  f"(FF hold: post-route hold ECO; sign-off unchanged)", file=sys.stderr)
            args.hold_corners = _ot_new
'''
MARK = "OT_ROUTE_HOLD_CORNERS"


def patch(src):
    f = Path(src) / "tools/run_abi3_physical.py"
    if not f.is_file():
        return "no run_abi3_physical.py"
    s = f.read_text()
    if "kept {args.hold_corners}: step hook" in s:
        return "already supports OT_ROUTE_HOLD_CORNERS (hook-aware)"
    if MARK in s:                        # first patch generation (no step-hook check): upgrade it
        i = s.index('    _ot_rhc = os.environ.get("OT_ROUTE_HOLD_CORNERS", "").strip()\n')
        j = s.index('        args.hold_corners = _ot_new\n', i) + len('        args.hold_corners = _ot_new\n')
        f.write_text(s[:i] + CODE + s[j:])
        return f"upgraded {f}"
    if s.count(ANCHOR) != 1 or "\nimport os" not in s:
        return "anchor not found: not patched (route keeps its own hold corners)"
    shutil.copy2(f, f.with_suffix(".py.pre_holdcorners"))
    f.write_text(s.replace(ANCHOR, ANCHOR + CODE))
    return f"patched {f}"


if __name__ == "__main__":
    print("hold_corners_patch:", patch(sys.argv[1]))
