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
import re
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
# The corner block replacement spans the calibrate-only injection installed by
# hold_corners_patch. Keep it in the final block so either overlay order retains it.
CALIBRATION_CODE = r'''    if os.environ.get("OT_CAL_CTS_ONLY", "") == "1":
        args.orfs_var = list(args.orfs_var or []) + ["SKIP_CTS_REPAIR_TIMING=1"]
        print("OT_CAL_CTS_ONLY: calibrate run, SKIP_CTS_REPAIR_TIMING=1 (no CTS setup/hold repair)", file=sys.stderr)
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
    # Forward OT_SPINE_* / OT_CG_* job-shell knobs into the hook (main 225badfab): the hooks read ::env, which only
    # carries config.mk exports.  This backport REPLACES main's function, so without this block every overlaid job
    # silently dropped the knobs (w8c-a/b-225badfab: 'OT_SPINE skipped: no port ck[0]', plain TritonCTS, TT -1,8xx).
    knobs = sorted(k for k in os.environ if re.match(r"OT_(SPINE|CG)_[A-Z0-9_]+$", k))
    for k in knobs:
        v = os.environ[k].replace("\\", "\\\\").replace("{", "\\{").replace("}", "\\}")
        body.append(f"if {{![info exists ::env({k})] || $::env({k}) eq \"\"}} {{ set ::env({k}) {{{v}}} }}")
    if orig:
        body.append(f"source {orig}")
    record = []
    for i, fix in enumerate(fixes):
        source = Path(fix)
        if not source.is_absolute():
            # tt_overlay: recipes that run from a reduced context copy (route_core.sh context_src) lack common_flow:
            # fall back to the job snapshot this function was patched into
            source = next((r / fix for r in (ROOT, Path("@TTB_SRC@")) if (r / fix).is_file()), ROOT / fix)
        if not source.is_file():
            raise ValueError(f"OT_CTS_FIX_HOOKS: no such file {source}")
        name = f"ot_cts_fix_{i}_{source.name}"
        shutil.copy2(source, hooks_dir / name)
        for sib in ("link_budget_consistent.sdc",):   # sourced by link_budget_hook.tcl from its own directory
            if source.name == "link_budget_hook.tcl" and (source.parent / sib).is_file():
                shutil.copy2(source.parent / sib, hooks_dir / sib)
        body.append(f"source /work/hooks/{name}")
        record.append({"path": fix, "name": name, "sha256": _h.sha256(source.read_bytes()).hexdigest()})
    (hooks_dir / "pre_cts_ot_cts_fix.tcl").write_text("\n".join(body) + "\n", encoding="utf-8")
    (hooks_dir / "ot_cts_fix.json").write_text(json.dumps({"pre_cts_orig": orig, "fixes": record, "env_knobs": {k: os.environ[k] for k in knobs}}, indent=1) + "\n",
                                               encoding="utf-8")
    kept.append("export PRE_CTS_TCL = /work/hooks/pre_cts_ot_cts_fix.tcl")
    return kept
'''
CFG_ANCHOR = '    (case / "config.mk").write_text("\\n".join(config) + "\\n", encoding="utf-8")\n'
FN_ANCHOR = "\ndef io_constraints_tcl("
COMMON = ["cg_pushdown.tcl", "clk_net_protect.tcl", "link_budget_hook.tcl", "link_budget_consistent.sdc",
          "nbr_clk_measured_ttb.sdc"]


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
    if seg == CORNER_CODE + CALIBRATION_CODE:
        return s, msg, True
    if seg.strip() and "CORNER" not in seg:
        return s, [f"unexpected code between parse_args and the hold-corner block ({len(seg)} chars)"], False
    s = s[:a] + CORNER_CODE + CALIBRATION_CODE + s[b:]
    msg.append("corner block v2 (WC reads TT)" + (" replaced a rename block" if seg.strip() else " added"))
    return s, msg, True


# LOOP-LVT 2026-10-10: the WC-reads-TT var alone is not enough for multi-VT routes.  The asap7 platform config.mk
# (included after the design config) appends each OTHER_VT with `WC_NLDM_LIB_FILES += $(subst PLACEHOLDER,<vt>,
# $(WC_NLDM_LIB_FILES_T))` -- the SS template, which the design config cannot override (the platform re-assigns it) --
# so OT_MULTI_VT routes repaired setup against LVT/SLVT SS cells (qfd sys_v lvt r3).  `override` makes that += a no-op.
LIBOV_FN = r'''def ot_tt_lib_override(config):
    """LOOP-LVT (tt_overlay backport): `override export WC_NLDM_LIB_FILES = $(TC_NLDM_LIB_FILES)` so the asap7
    platform's OTHER_VT `+=` (SS template) cannot add LVT/SLVT SS libraries to the TT-reading WC corner."""
    return [("override " + line) if re.fullmatch(r"export WC_NLDM_LIB_FILES\s*=\s*\$\(TC_NLDM_LIB_FILES\)\s*", line)
            else line for line in config]


'''
LIBOV_CALL = "    config = ot_tt_lib_override(config)\n"
HOOKS_CALL = "    config = apply_cts_fix_hooks(config, case)\n"
DIRECT_OVERRIDE = ("# tt_overlay LOOP-LVT: no OTHER_VT SS append into the TT-reading WC corner\n"
                   "override export WC_NLDM_LIB_FILES = $(TC_NLDM_LIB_FILES)")


def ensure_lib_override(s):
    """(text, msgs, ok): run_abi3_physical writes `override export WC_NLDM_LIB_FILES = ...` (main has it since
    LOOP-LVT; older snapshots get the function + call).  Needs ensure_hooks' call anchor."""
    if "def ot_tt_lib_override" in s and LIBOV_CALL in s:
        return s, [], True
    if s.count(HOOKS_CALL) != 1 or s.count("\ndef apply_cts_fix_hooks") != 1:
        return s, ["NO anchor for the WC TT lib override (LOOP-LVT)"], False
    if "def ot_tt_lib_override" not in s:
        i = s.index("\ndef apply_cts_fix_hooks") + 1
        s = s[:i] + LIBOV_FN + s[i:]
    if LIBOV_CALL not in s:
        s = s.replace(HOOKS_CALL, HOOKS_CALL + LIBOV_CALL)
    return s, ["WC TT lib override (multi-VT) added"], True


def ensure_hooks(s, src):
    fn = HOOKS_FN.replace("@TTB_SRC@", str(src.resolve()))
    if fn in s:
        return s, [], True
    if "def apply_cts_fix_hooks" in s:
        # replace main's / an older overlay's version (no context-copy fallback, no sibling SDC copy)
        a = s.index("\n\ndef apply_cts_fix_hooks")
        # end of the function = the first top-level line after it (2026-10-15: searching for the next "\ndef " also
        # cut module-level statements between the two defs -- main 65529c027's GRT183_HOOK constant -> NameError in
        # every TT-overlaid route)
        b = re.compile(r"\n(?=\S)").search(s, s.index("\n", a + 5) + 1).start()
        s = s[:a] + fn.rstrip("\n") + "\n\n" + s[b:]
        return s, ["OT_CTS_FIX_HOOKS function replaced (context fallback)"], True
    if s.count(CFG_ANCHOR) != 1 or s.count(FN_ANCHOR) != 1:
        return s, ["NO anchor for OT_CTS_FIX_HOOKS"], False
    s = s.replace(CFG_ANCHOR, "    config = apply_cts_fix_hooks(config, case)\n" + CFG_ANCHOR)
    s = s.replace(FN_ANCHOR, fn + FN_ANCHOR)
    return s, ["OT_CTS_FIX_HOOKS added"], True


SMH_OLD = 'f"export WC_LIB_FILES = $(WC_NLDM_LIB_FILES) {lib_ss}"'
SMH_NEW = 'f"export WC_LIB_FILES = $(TC_NLDM_LIB_FILES) {lib_ss.replace(\'_ss.lib\', \'_tt.lib\')}"'
# v2 first deploy appended an inline comment that swallowed the list comma (strings concatenated -> "export" read as a lib)
SMH_BAD = SMH_NEW + '  # tt_overlay v2: corner WC reads the TT liberties (option B)'


SMH_CORNER_LINE = '  echo "corner_rc=$?" >> $W/status\n'
SMH_NBR = (SMH_CORNER_LINE +
           "  # tt_overlay: setup corners re-timed with nbr_clk at the measured insertion (hbm-blocks 9e81f6c70 semantics);\n"
           "  # the loop's tt_resta.sh re-times this tcl at TT; FF hold (w18_sta_ff.tcl) keeps the generator model\n"
           "  if [ -f $W/w18_sta_ss.tcl ] && ! grep -q OT_NBR_MEASURED_TTB $W/w18_sta_ss.tcl; then "
           "cp $W/w18_sta_ss.tcl $W/w18_sta_ss.planning.tcl && cp $S/physical/common_flow/nbr_clk_measured_ttb.sdc $W/ && "
           "sed -i 's#^set_propagated_clock \\[all_clocks\\]$#&\\nsource /work/nbr_clk_measured_ttb.sdc ;\\# OT_NBR_MEASURED_TTB#' "
           "$W/w18_sta_ss.tcl; echo \"nbr_measured_rc=$?\" >> $W/status; fi\n")


# LOOP-CORNER 2026-10-10: since c10b5fc9a the generator names the corner by OT_SMH_CORNER ({_SC}); it honours ONLY that
# variable, so a recipe with OT_ORFS_CORNER(_OVERRIDE)=TC routed at SS -- and 48c78e37f's "no WC_LIB_FILES line" skip
# read this form as "predates corner libs" and left it unpatched (hbm_smh_tile_{wg,eg}_cg hold floods, CLOSED at SS).
SMH_SC_LIB = 'lib_su = lib_ss if _SC == "WC" else " ".join(f"/src/{m}/{Path(m).name}_tt.lib" for m in macros)\n'
SMH_SC_LIB_NEW = ('lib_su = " ".join(f"/src/{m}/{Path(m).name}_tt.lib" for m in macros)'
                  '  # tt_overlay LOOP-CORNER: TC route stage reads TT\n')
SMH_SC_LINE = 'f"export {_SC}_LIB_FILES = $({_SC}_NLDM_LIB_FILES) {lib_su}"'
SMH_SC_LINE_NEW = 'f"export {_SC}_LIB_FILES = $(TC_NLDM_LIB_FILES) {lib_su}"'
SMH_HONOURS = "LOOP-CORNER (2026-10-10): the closure loop's option-B route env"


def _smh_sc_form(s):
    """(text, msg): patch a c10b5fc9a..LOOP-CORNER generator ({_SC} corner) so corner WC reads the TT liberties;
    msg None when this is not that form."""
    if SMH_HONOURS in s:
        return s, "SMH flow: generator honours OT_ORFS_CORNER (no patch)"
    if SMH_SC_LIB_NEW in s and SMH_SC_LINE_NEW in s:
        return s, "SMH flow ({_SC} form): WC reads TT"
    if SMH_SC_LINE not in s and SMH_SC_LIB not in s:
        return s, None
    if s.count(SMH_SC_LIB) != 1 or s.count(SMH_SC_LINE) != 1:
        return s, "SMH: {_SC} corner-lib anchor missing"
    return s.replace(SMH_SC_LIB, SMH_SC_LIB_NEW).replace(SMH_SC_LINE, SMH_SC_LINE_NEW), "SMH flow ({_SC} form): WC reads TT"


def _smh_mark():
    if os.environ.get("OT_TTB_CORNER_MARK"):
        with open(os.environ["OT_TTB_CORNER_MARK"], "a") as m:
            m.write(f"TC {os.getpid()} smh_config wc_reads_tt\n")


def ensure_smh(src):
    """SM piece flow (tools/hbm_accel_smh_physical.py writes its own config.mk, not through run_abi3_physical): in a
    TC route stage, corner WC reads the TT std-cell + macro liberties; the mark is written here."""
    f = src / "tools/hbm_accel_smh_physical.py"
    tc = (os.environ.get("OT_ORFS_CORNER", "") or os.environ.get("OT_ORFS_CORNER_OVERRIDE", "")).strip().upper() == "TC"
    if not f.is_file() or not tc:
        return []
    s = f.read_text()
    s2, msg = _smh_sc_form(s)
    if msg is not None:
        if "missing" in msg:
            return [msg]
        if s2 != s:
            f.write_text(s2)
        _smh_mark()
        return [msg]
    if "WC_LIB_FILES" not in s:
        # 2026-10-08 drive-0502: commits predating the SM generator's corner-lib line (e.g. 4b111850a) have nothing to
        # patch; a non-SM route (Qwen die masters) on such a snapshot must not fail the overlay on it
        return ["SMH: generator has no WC_LIB_FILES line (predates corner libs; not patched)"]
    s = s.replace(SMH_BAD, SMH_NEW)
    if SMH_NEW not in s:
        if s.count(SMH_OLD) != 1:
            return ["SMH: WC_LIB_FILES anchor missing"]
        s = s.replace(SMH_OLD, SMH_NEW)
    if "OT_NBR_MEASURED_TTB" not in s and "OT_SMH_POST_SDC" not in s:
        if s.count(SMH_CORNER_LINE) != 1:
            return ["SMH: corner_rc anchor missing"]
        s = s.replace(SMH_CORNER_LINE, SMH_NBR)
    f.write_text(s)
    _smh_mark()
    return ["SMH flow: WC reads TT"]


def ensure_direct_configs(src):
    """Recipes that drive ORFS directly with a checked-in config.mk (ha2 relay / h2 fixedpins style): in a TC route stage
    the WC_LIB_FILES line reads the TT std-cell libraries and macro _tt.lib (corner names kept)."""
    tc = (os.environ.get("OT_ORFS_CORNER", "") or os.environ.get("OT_ORFS_CORNER_OVERRIDE", "")).strip().upper() == "TC"
    if not tc:
        return []
    n = 0
    for f in (src / "physical").rglob("config.mk"):
        t = f.read_text(errors="replace")
        u = "\n".join((l.replace("$(WC_NLDM_LIB_FILES)", "$(TC_NLDM_LIB_FILES)").replace("_ss.lib", "_tt.lib")
                       if re.match(r"\s*export\s+WC_LIB_FILES\s*=", l) else l) for l in t.split("\n"))
        if re.search(r"^\s*export\s+WC_LIB_FILES\s*=", u, re.M) and DIRECT_OVERRIDE not in u:
            # LOOP-LVT: a single-corner stage (LIB_FILES += $(WC_NLDM_LIB_FILES)) and any OTHER_VT append read TT too
            u = u.rstrip("\n") + "\n" + DIRECT_OVERRIDE + "\n"
        if u != t:
            f.write_text(u)
            n += 1
    if n and os.environ.get("OT_TTB_CORNER_MARK"):
        with open(os.environ["OT_TTB_CORNER_MARK"], "a") as m:
            m.write(f"TC {os.getpid()} direct_config_mk x{n} wc_reads_tt\n")
    return [f"direct config.mk WC->TT x{n}"] if n else []


CTX_CP = "cp $S/tools/orfs_allcorner_spef.py $R/context_src/tools/"
CTX_CP_NEW = (CTX_CP + "; cp $S/tools/orfs_hold_mm.py $S/tools/orfs_hold_mm.tcl $R/context_src/tools/ 2>/dev/null; "
              "mkdir -p $R/context_src/physical/common_flow; cp $S/physical/common_flow/* $R/context_src/physical/common_flow/"
              "  # tt_overlay: mm hold helpers + CTS hooks in the context copy")
CTX_ADD = "add rtl/control_context.v physical/qwen_core_ctx tools/orfs_allcorner_spef.py"
CTX_ADD_NEW = "add rtl/control_context.v physical/qwen_core_ctx tools physical/common_flow"


def ensure_context_copies(src):
    """Qwen route_core*.sh run ORFS from a reduced context copy: ship the mm hold helpers and common_flow into it."""
    n = 0
    for f in (src / "physical/qwen_die_masters/jobs").glob("route_core*.sh"):
        t = f.read_text()
        u = t.replace(CTX_CP + "\n", CTX_CP_NEW + "\n") if CTX_CP_NEW not in t else t
        u = u.replace(CTX_ADD, CTX_ADD_NEW)
        if u != t:
            f.write_text(u)
            n += 1
    return [f"context copy helpers x{n}"] if n else []


def main():
    src = Path(sys.argv[1])
    f = src / "tools/run_abi3_physical.py"
    out, ok = [], True
    if f.is_file():
        s0 = s = f.read_text()
        s, m1, ok1 = ensure_corner(s)
        s, m2, ok2 = ensure_hooks(s, src)
        s, m3, ok3 = ensure_lib_override(s) if ok2 else (s, [], False)
        out += m1 + m2 + m3
        ok = ok1 and ok2 and ok3
        if s != s0:
            if not f.with_suffix(".py.pre_ttb").exists():
                shutil.copy2(f, f.with_suffix(".py.pre_ttb"))
            f.write_text(s)
    else:
        out.append("no tools/run_abi3_physical.py")
        ok = (src / "tools/hbm_accel_smh_physical.py").is_file() or any((src / "physical").rglob("config.mk"))
    out += ensure_direct_configs(src)
    out += ensure_context_copies(src)
    sm = ensure_smh(src)
    out += sm
    ok = ok and not any("missing" in x for x in sm)
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
