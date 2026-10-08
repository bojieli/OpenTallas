#!/usr/bin/env python3
"""TT-BATCH overlay (2026-10-07, owner option B): make a job's ORIGINAL-commit source snapshot route under the current
closure flow without moving the job to a newer commit (its RTL and benches stay exactly as they were).

   tt_overlay.py <snapshot root> [--no-link-budget]        (idempotent; run in the calibrate and route commands)

1. CORNER (option B), v2: with OT_ORFS_CORNER=TC (loop route env) or OT_ORFS_CORNER_OVERRIDE=TC, corner WC reads the
   TT liberties (std cells + macro _tt.lib) and keeps its NAME (hbm-blocks 4aadc92bc; a TC rename dies at floorplan with
   STA-0102 under the loop's WC-scene mm session).  Any older rename block (main 852d9b461, c10b5fc9a, v1) is replaced.  Each application of a corner appends
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
CORNER_CODE = r'''    # TTB-CORNER-BEGIN (tt_overlay v2 = hbm-blocks 4aadc92bc semantics): OWNER OPTION B, setup repair at TT.  Keep the
    # WC/BC corner NAMES (the loop's mm hold session builds scene WC; renaming the corner to TC died in floorplan
    # report_metrics, STA-0102) and make corner WC READ the TT liberties: WC_NLDM_LIB_FILES = $(TC_NLDM_LIB_FILES), every
    # macro's WC view = its _tt.lib.  Hold stays at BC (FF).
    _ot_tc = (os.environ.get("OT_ORFS_CORNER", "") or os.environ.get("OT_ORFS_CORNER_OVERRIDE", "")).strip().upper()
    if _ot_tc == "TC":
        ORFS_CORNER_MACRO_TAG["WC"] = "tt"
        args.orfs_var = list(args.orfs_var or []) + ["WC_NLDM_LIB_FILES=$(TC_NLDM_LIB_FILES)"]
        print(f"OT_ORFS_CORNER=TC (tt_overlay v2): corner WC reads the TT liberties (std cells + macro _tt.lib); "
              f"orfs corner {args.orfs_corner}, hold corners {args.hold_corners}", file=sys.stderr)
        if os.environ.get("OT_TTB_CORNER_MARK"):
            with open(os.environ["OT_TTB_CORNER_MARK"], "a") as _ot_mf:
                _ot_mf.write(f"TC {os.getpid()} wc_reads_tt orfs_corner={args.orfs_corner} hold={args.hold_corners}\n")
    # TTB-CORNER-END
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
    """(text, messages, ok): replace whatever corner code sits between parse_args and the hold-corner block (main
    852d9b461 rename, hbm-blocks c10b5fc9a v1 rename / 4aadc92bc v2, tt_overlay v1) with the v2 WC-reads-TT block."""
    msg = []
    if "ORFS_CORNER_MACRO_TAG = " not in s or "ORFS_LIB_CORNERS = " not in s:
        return s, ["snapshot predates per-corner macro views (ORFS_CORNER_MACRO_TAG)"], False
    if s.count(PARSE_ANCHOR) != 1:
        return s, ["NO parse_args anchor"], False
    a = s.index(PARSE_ANCHOR) + len(PARSE_ANCHOR)
    b = s.index(RHC_ANCHOR, a) if RHC_ANCHOR in s[a:] else a
    seg = s[a:b]
    if seg == CORNER_CODE:
        return s, msg, True
    if seg.strip() and "CORNER" not in seg:
        return s, [f"unexpected code between parse_args and the hold-corner block ({len(seg)} chars)"], False
    s = s[:a] + CORNER_CODE + s[b:]
    msg.append("corner block v2 (WC reads TT)" + (" replaced a rename block" if seg.strip() else " added"))
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
