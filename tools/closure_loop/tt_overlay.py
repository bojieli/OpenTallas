#!/usr/bin/env python3
"""TT-BATCH overlay (2026-10-07, owner option B): make a job's ORIGINAL-commit source snapshot route under the current
closure flow without moving the job to a newer commit (its RTL and benches stay exactly as they were).

   tt_overlay.py <snapshot root> [--no-link-budget]        (idempotent; run in the calibrate and route commands)

1. CORNER (option B): tools/run_abi3_physical.py honours OT_ORFS_CORNER (the loop exports TC for every route launched
   from OPTB_SINCE; OT_ORFS_CORNER_OVERRIDE of claude/hbm-blocks-tt c10b5fc9a is read too) and passes OT_MM_SETUP_CORNER to the flow-hold mm session, exactly as main 852d9b461 does.  Snapshots
   pinned before 852d9b461 ignore OT_ORFS_CORNER and silently route at WC (SS).  Each application of a corner appends
   '<corner> <pid>' to $OT_TTB_CORNER_MARK so a verdict check can prove the route ran at TC.
2. CTS FIX HOOKS (setup-triage df37bfa4e / 387a4d2ac): run_abi3_physical honours OT_CTS_FIX_HOOKS (PRE_CTS chain), and
   physical/common_flow/{cg_pushdown,clk_net_protect,link_budget_hook}.tcl + link_budget_consistent.sdc are refreshed
   from this overlay's copy (the consistent die-link budget, applied at route time after CTS and carried into
   6_final.sdc, hence into the TT / SS / FF sign-off STA).
3. RULE H1 (flow-hold): tools/closure_loop/h1_patch.py of this overlay.
The loop's own hold_corners_patch.py (mm hold repair, RSZ-0060 tolerance, helpers) runs before this, from the job env.
Fails (exit 2) when the corner support cannot be installed: the job must not route at SS under a TT name."""
import hashlib
import os
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent            # <overlay>/tools/closure_loop
OVL = HERE.parent.parent                          # <overlay> root (holds physical/common_flow)

RHC_ANCHOR = '    _ot_rhc = os.environ.get("OT_ROUTE_HOLD_CORNERS", "").strip()\n'
PARSE_ANCHOR = "    args = build_parser().parse_args(argv)\n"
CORNER_CODE = r'''    _ot_oc = (os.environ.get("OT_ORFS_CORNER", "") or os.environ.get("OT_ORFS_CORNER_OVERRIDE", "")).strip().upper()
    if _ot_oc:
        # OWNER OPTION B (2026-10-07): the closure loop routes with CORNER=TC (setup repair at TT; hold at FF via mm)
        # (tt_overlay.py: snapshot pinned before main 852d9b461)
        if _ot_oc not in ORFS_LIB_CORNERS:
            raise SystemExit(f"OT_ORFS_CORNER={_ot_oc}: unknown ORFS corner; known {sorted(ORFS_LIB_CORNERS)}")
        if args.orfs_corner != _ot_oc:
            print(f"OT_ORFS_CORNER={_ot_oc}: primary corner {args.orfs_corner} -> {_ot_oc}", file=sys.stderr)
        if args.hold_corners:
            args.hold_corners = ",".join(_ot_oc if c.strip() == (args.orfs_corner or "WC") else c.strip()
                                         for c in args.hold_corners.split(","))
        args.orfs_corner = _ot_oc
        if os.environ.get("OT_TTB_CORNER_MARK"):
            with open(os.environ["OT_TTB_CORNER_MARK"], "a") as _ot_mf:
                _ot_mf.write(f"{_ot_oc} {os.getpid()} hold_corners={args.hold_corners}\n")
'''
MARK_CODE = r'''        if os.environ.get("OT_TTB_CORNER_MARK"):
            with open(os.environ["OT_TTB_CORNER_MARK"], "a") as _ot_mf:
                _ot_mf.write(f"{_ot_oc} {os.getpid()} hold_corners={args.hold_corners}\n")
'''
MAIN_CORNER_TAIL = "        args.orfs_corner = _ot_oc\n"
MM_OLD = 'args.orfs_var = list(args.orfs_var or []) + ["OT_HOLD_MM=1"]'
MM_NEW = 'args.orfs_var = list(args.orfs_var or []) + ["OT_HOLD_MM=1", f"OT_MM_SETUP_CORNER={_ot_p}"]'

HOOKS_FN = r'''

def apply_cts_fix_hooks(config, case):
    """Opt-in flow fixes chained after the block's own PRE_CTS hook (setup-triage 2026-10-07; tt_overlay.py backport).
    OT_CTS_FIX_HOOKS = space-separated Tcl files (repo-relative or absolute).  Unset: config unchanged."""
    import hashlib as _h
    fixes = os.environ.get("OT_CTS_FIX_HOOKS", "").split()
    if not fixes:
        return config
    hooks_dir = case / "hooks"
    hooks_dir.mkdir(exist_ok=True)
    orig, kept = None, []
    for line in config:
        m = re.match(r"\s*export\s+PRE_CTS_TCL\s*=\s*(.*)$", line)
        if m:
            orig = m.group(1).strip()
            continue
        kept.append(line)
    body = ["# Written by tools/run_abi3_physical.py (OT_CTS_FIX_HOOKS, tt_overlay backport)."]
    if orig:
        body.append(f"source {orig}")
    record = []
    for i, fix in enumerate(fixes):
        source = Path(fix)
        if not source.is_absolute():
            source = ROOT / source
        if not source.is_file():
            raise ValueError(f"OT_CTS_FIX_HOOKS: no such file {source}")
        name = f"ot_cts_fix_{i}_{source.name}"
        shutil.copy2(source, hooks_dir / name)
        body.append(f"source /work/hooks/{name}")
        record.append({"path": fix, "name": name, "sha256": _h.sha256(source.read_bytes()).hexdigest()})
    (hooks_dir / "pre_cts_ot_cts_fix.tcl").write_text("\n".join(body) + "\n", encoding="utf-8")
    (hooks_dir / "ot_cts_fix.json").write_text(json.dumps({"pre_cts_orig": orig, "fixes": record}, indent=1) + "\n",
                                               encoding="utf-8")
    kept.append("export PRE_CTS_TCL = /work/hooks/pre_cts_ot_cts_fix.tcl")
    return kept
'''
CFG_ANCHOR = '    (case / "config.mk").write_text("\\n".join(config) + "\\n", encoding="utf-8")\n'
FN_ANCHOR = "\ndef io_constraints_tcl("
COMMON = ["cg_pushdown.tcl", "clk_net_protect.tcl", "link_budget_hook.tcl", "link_budget_consistent.sdc"]


def ensure_corner(s):
    """(text, messages, ok): OT_ORFS_CORNER + OT_MM_SETUP_CORNER + the corner mark in a run_abi3_physical.py text."""
    msg = []
    if 'os.environ.get("OT_ORFS_CORNER", "")' not in s:
        if s.count(RHC_ANCHOR) == 1:
            s = s.replace(RHC_ANCHOR, CORNER_CODE + RHC_ANCHOR)
        elif s.count(PARSE_ANCHOR) == 1:
            s = s.replace(PARSE_ANCHOR, PARSE_ANCHOR + CORNER_CODE)
        else:
            return s, ["NO anchor for OT_ORFS_CORNER"], False
        msg.append("OT_ORFS_CORNER added")
    elif "OT_TTB_CORNER_MARK" not in s:
        if s.count(MAIN_CORNER_TAIL) != 1:
            return s, ["OT_ORFS_CORNER present but no mark anchor"], False
        s = s.replace(MAIN_CORNER_TAIL, MAIN_CORNER_TAIL + MARK_CODE)
        msg.append("corner mark added")
    if MM_OLD in s:
        s = s.replace(MM_OLD, MM_NEW)
        msg.append("OT_MM_SETUP_CORNER added")
    if "OT_HOLD_MM=1" in s and "OT_MM_SETUP_CORNER" not in s:
        return s, msg + ["mm session without OT_MM_SETUP_CORNER (unknown mm form)"], False
    if "ORFS_LIB_CORNERS = " not in s:
        return s, msg + ["no ORFS_LIB_CORNERS (snapshot predates --orfs-corner)"], False
    return s, msg, True


def ensure_hooks(s):
    if "def apply_cts_fix_hooks" in s:
        return s, [], True
    if s.count(CFG_ANCHOR) != 1 or s.count(FN_ANCHOR) != 1:
        return s, ["NO anchor for OT_CTS_FIX_HOOKS"], False
    s = s.replace(CFG_ANCHOR, "    config = apply_cts_fix_hooks(config, case)\n" + CFG_ANCHOR)
    s = s.replace(FN_ANCHOR, HOOKS_FN + FN_ANCHOR)
    return s, ["OT_CTS_FIX_HOOKS added"], True


def main():
    src = Path(sys.argv[1])
    f = src / "tools/run_abi3_physical.py"
    out, ok = [], True
    if f.is_file():
        s0 = s = f.read_text()
        s, m1, ok1 = ensure_corner(s)
        s, m2, ok2 = ensure_hooks(s)
        out += m1 + m2
        ok = ok1 and ok2
        if s != s0:
            if not f.with_suffix(".py.pre_ttb").exists():
                shutil.copy2(f, f.with_suffix(".py.pre_ttb"))
            f.write_text(s)
    else:
        out.append("no tools/run_abi3_physical.py")
        ok = False
    d = src / "physical/common_flow"
    d.mkdir(parents=True, exist_ok=True)
    for n in COMMON:
        a = OVL / "physical/common_flow" / n
        b = d / n
        if not b.is_file() or b.read_bytes() != a.read_bytes():
            shutil.copy2(a, b)
            out.append(f"shipped common_flow/{n}")
    h1 = subprocess.run([sys.executable, str(HERE / "h1_patch.py"), str(src)], capture_output=True, text=True)
    out.append(h1.stdout.strip() or h1.stderr.strip()[-200:])
    digest = hashlib.sha256(f.read_bytes()).hexdigest()[:12] if f.is_file() else "-"
    print(f"tt_overlay: {'OK' if ok else 'FAIL'} run_abi3_physical {digest}: " + "; ".join(x for x in out if x))
    sys.exit(0 if ok else 2)


if __name__ == "__main__":
    main()
