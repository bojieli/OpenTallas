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
    if _ot_rhc == "mm":
        # FLOW-HOLD (2026-10-07): multi-mode route-time repair, SS setup (scene WC) + FF hold (scene BC) each under its
        # own constraints (tools/orfs_hold_mm.tcl, patched into the flow container by tools/orfs_hold_mm.py)
        _ot_p = args.orfs_corner or (args.hold_corners or "WC").split(",")[0].strip()
        args.hold_corners = ",".join(dict.fromkeys([_ot_p, "BC"]))
        args.orfs_var = list(args.orfs_var or []) + ["OT_HOLD_MM=1"]
        _ot_ff = " ".join(("/src/" + f.lstrip("/")) if not f.startswith("/src/") else f
                          for f in os.environ.get("OT_MM_FF_SDC", "").split() if f)
        if _ot_ff:
            args.orfs_var.append(f"OT_MM_FF_SDC={_ot_ff}")
        print(f"OT_ROUTE_HOLD_CORNERS=mm: repair scenes {args.hold_corners} (SS setup + FF hold), FF SDCs [{_ot_ff}]",
              file=sys.stderr)
        _ot_rhc = ""
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
DOCKER_ANCHOR = '"python3 /src/tools/orfs_allcorner_spef.py "'
DOCKER_MM = '"python3 /src/tools/orfs_hold_mm.py /OpenROAD-flow-scripts/flow/scripts && "\n            '



def patch(src):
    f = Path(src) / "tools/run_abi3_physical.py"
    if not f.is_file():
        return "no run_abi3_physical.py"
    s = f.read_text()
    msg = []
    if 'if _ot_rhc == "mm":' in s:
        msg.append("already supports OT_ROUTE_HOLD_CORNERS (hook-aware, mm)")
    elif MARK in s:                      # earlier patch generations / main before mm: replace the block
        i = s.index('    _ot_rhc = os.environ.get("OT_ROUTE_HOLD_CORNERS", "").strip()\n')
        j = s.index('            args.hold_corners = _ot_new\n', i) + len('            args.hold_corners = _ot_new\n') \
            if "kept {args.hold_corners}: step hook" in s else \
            s.index('        args.hold_corners = _ot_new\n', i) + len('        args.hold_corners = _ot_new\n')
        s = s[:i] + CODE + s[j:]
        msg.append(f"upgraded {f}")
    elif s.count(ANCHOR) != 1 or "\nimport os" not in s:
        return "anchor not found: not patched (route keeps its own hold corners)"
    else:
        if not f.with_suffix(".py.pre_holdcorners").exists():
            shutil.copy2(f, f.with_suffix(".py.pre_holdcorners"))
        s = s.replace(ANCHOR, ANCHOR + CODE)
        msg.append(f"patched {f}")
    # the flow container patch (inert unless the config exports OT_HOLD_MM=1)
    if "orfs_hold_mm.py /OpenROAD-flow-scripts" not in s:
        if s.count(DOCKER_ANCHOR) == 1:
            s = s.replace(DOCKER_ANCHOR, DOCKER_MM + DOCKER_ANCHOR)
            msg.append("container hook orfs_hold_mm.py added")
        else:
            msg.append("NO container anchor: OT_ROUTE_HOLD_CORNERS=mm unavailable in this snapshot")
    f.write_text(s)
    here = Path(__file__).resolve().parent
    for h in ("orfs_hold_mm.py", "orfs_hold_mm.tcl"):
        for cand in (here / h, here.parent / h):
            if cand.is_file() and not (Path(src) / "tools" / h).is_file():
                shutil.copy2(cand, Path(src) / "tools" / h)
                msg.append(f"shipped tools/{h}")
                break
    return "; ".join(msg)


if __name__ == "__main__":
    print("hold_corners_patch:", patch(sys.argv[1]))
