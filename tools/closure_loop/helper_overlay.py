"""One effective helper resolver and immutable content plans for gates and routes."""
from __future__ import annotations
import hashlib
import threading
import json
import os
import re
import stat
import subprocess
from pathlib import Path

PG_HELPERS = ("pg_receipt.py", "../../physical/common_flow/audit_native_pg.tcl",
              "../../physical/common_flow/native_pg_bootstrap.tcl")

HELPERS = ("../../physical/common_flow/native_pg_binding.tcl", "m6_stub_config.py", "eco_recovery.py", "path_summary.py", "macro_views.py", "ck_insertion.py", "hold_eco.sh", "hold_eco.tcl", "hold_eco_corner.tcl",
           "hold_eco_sdc.py", "hold_eco_window.tcl", "hold_corners_patch.py", "h1_patch.py", "cal_classify.sh", "resume_patch.py", "resume_check.sh",
           "../orfs_hold_mm.py", "../orfs_hold_mm.tcl", "tt_resta.sh", "meas_resta.py", "lane_kh_overlay.py",
           "../../physical/common_flow/io_ref_routed.sdc", "../../physical/common_flow/clock_family.tcl", "../fp_margin_lint.py", "../fp_margin_lint.tcl",
           "../preroute_gate.py", "../preroute_gate.tcl", "../textbook_lint.py", "tt_overlay.py", "vtswap_eco.sh", "vtswap_eco.tcl",
           "pinflop_overlay.py", "../../physical/qwen_die_masters/pinflop_ref.tcl", "../w18/corner_sta.py", "route_corner_check.py", "../hier_contract/child_lint.py",
           "../hier_contract/abstract_pin_stub.py", "../hier_contract/m6_pin_grant.py", "../../physical/common_flow/grt_macro_top_layer.tcl", "../../physical/common_flow/m6_pin_access.tcl",
           "../tt_views/view_export.py",
           "../../physical/common_flow/grt_macro_top_layer_post.tcl",
           *(f"../../physical/common_flow/{n}" for n in ("cg_pushdown.tcl", "clk_net_protect.tcl", "link_budget_hook.tcl",
                                                          "link_budget_consistent.sdc", "nbr_clk_measured_ttb.sdc",
                                                          "macro_sliver_block.tcl", "edge_sliver_block.tcl",
                                                          "macro_cts_cluster.tcl")))

SCHEMA = "opentallas.closure_loop.helper_overlay_plan.v1"


def blob_id(data):
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()


def main_head(repo):
    p = subprocess.run(["git", "-C", str(repo), "rev-parse", "refs/remotes/origin/main"], capture_output=True, text=True)
    return p.stdout.strip() if not p.returncode else None


def resolve_bytes(daemon, repo, rel, head, cache=None, local_bytes=None):
    """Preserve closure-loop's existing same/stale/daemon-only resolution rules."""
    cache = {} if cache is None else cache
    local = (Path(daemon) / rel).read_bytes() if local_bytes is None else local_bytes
    if not head:
        return local, "no_git"
    key = (rel, head)
    if key not in cache:
        p = subprocess.run(["git", "-C", str(repo), "rev-parse", f"{head}:{rel}"], capture_output=True, text=True, timeout=60)
        cache[key] = p.stdout.strip() if not p.returncode else None
    tip = cache[key]
    lid = blob_id(local)
    if tip is None:
        return local, "not_on_main"
    if lid == tip:
        return local, "same"
    hk = ("inhist", rel, lid)
    if not cache.get(hk):
        p = subprocess.run(["git", "-C", str(repo), "log", "--format=", "--raw", "--no-abbrev", "--no-renames", head, "--", rel],
                           capture_output=True, text=True, timeout=180)
        cache[hk] = not p.returncode and lid in {ln.split()[3] for ln in p.stdout.splitlines()
                                               if ln.startswith(":") and len(ln.split()) >= 5}
    if cache[hk]:
        p = subprocess.run(["git", "-C", str(repo), "cat-file", "blob", tip], capture_output=True, timeout=60)
        if not p.returncode:
            return p.stdout, "stale"
        return local, "no_git"
    return local, "daemon_only"


def helper_paths(helpers=None):
    return sorted({os.path.normpath("tools/closure_loop/" + h) for h in (HELPERS if helpers is None else helpers)})


def pg_strict(spec):
    """The job/spec is authoritative; environment variables never admit strict jobs."""
    value = spec.get("pg_strict", False)
    if type(value) is not bool:
        raise ValueError("pg_strict must be a boolean")
    return value


def validate_pg_policy(plan, pg_strict=False):
    """Refuse policy drift; never retrofit PG dependencies into historical plans."""
    if type(pg_strict) is not bool:
        raise ValueError("pg_strict must be a boolean")
    if not isinstance(plan, dict):
        if pg_strict:
            raise ValueError("strict PG job requires a strict frozen helper plan")
        return
    if type(plan.get("pg_strict", False)) is not bool or plan.get("pg_strict", False) != pg_strict:
        raise ValueError("strict PG policy differs from frozen helper plan")
    pg_paths = set(helper_paths(PG_HELPERS))
    paths = {r.get("path") for r in plan.get("files", []) if isinstance(r, dict)}
    if not pg_strict and pg_paths & paths:
        raise ValueError("default frozen helper plan unexpectedly carries strict PG dependencies")
    if pg_strict:
        rows = frozen_rows(plan)
        if not pg_paths <= {r["path"] for r in rows}:
            raise ValueError("strict frozen helper plan lacks PG dependencies")


def content_rows(files):
    return sorted([{k: f[k] for k in ("path", "sha256", "git_blob", "mode")} for f in files], key=lambda f: f["path"])


def digest(files):
    return hashlib.sha256(json.dumps(content_rows(files), sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def capture_plan(daemon, repo, paths=None, head=None, cache=None, pg_strict=False):
    """Freeze one origin ref and the actual effective bytes; HEAD is provenance only."""
    if type(pg_strict) is not bool:
        raise ValueError("pg_strict must be a boolean")
    paths = set(helper_paths() if paths is None else paths)
    if pg_strict:
        paths.update(helper_paths(PG_HELPERS))
    head = main_head(repo) if head is None else head
    files, payloads = [], {}
    for rel in sorted(paths):
        literal = (Path(daemon) / rel).read_bytes()
        data, state = resolve_bytes(daemon, repo, rel, head, cache, local_bytes=literal)
        payloads[rel] = data
        files.append({"path": rel, "sha256": hashlib.sha256(data).hexdigest(), "git_blob": blob_id(data),
                      "mode": (Path(daemon) / rel).stat().st_mode & 0o777, "resolution": state,
                      "literal_git_blob": blob_id(literal)})
    plan = {"schema": SCHEMA, "origin_main": head, "content_sha256": digest(files), "files": files}
    if pg_strict:
        plan["pg_strict"] = True
    return plan, payloads


def compare_plans(frozen, effective):
    if not isinstance(frozen, dict) or frozen.get("schema") != SCHEMA:
        return False, "missing frozen effective helper plan"
    try:
        validate_pg_policy(effective, pg_strict=effective.get("pg_strict", False))
        validate_pg_policy(frozen, pg_strict=effective.get("pg_strict", False))
        if digest(frozen["files"]) != frozen.get("content_sha256"):
            return False, "frozen helper plan digest mismatch"
        old = {f["path"]: f for f in content_rows(frozen["files"])}
        new = {f["path"]: f for f in content_rows(effective["files"])}
    except (KeyError, TypeError, ValueError):
        return False, "malformed frozen helper plan"
    for rel in sorted(set(old) | set(new)):
        if old.get(rel) != new.get(rel):
            return False, f"effective route helper drift: {rel} (frozen {old.get(rel)}, current {new.get(rel)})"
    return True, "effective route helper bytes and modes match frozen plan"


# FLEET-RUN HELPERS (ROOT 2026-10-16): helpers a route does NOT execute from its frozen cl/ copy but from the fleet
# snapshot kept at main on every loop host (closure_loop.tt_overlay_fallback runs the fleet copy FIRST since 00cbddaea;
# snapshot_refresh keeps it at main).  A frozen plan row for such a path records what the daemon resolved at submit,
# not what the route runs, so drift there is SANCTIONED when the effective bytes are exactly origin/main's blob for the
# path and the frozen blob is an earlier main revision of the same path (never a daemon-only or foreign blob, never a
# mode change).  The caller records both shas and re-freezes the plan to the executed bytes.  Every other helper keeps
# the strict guard.  (s81net_sstn_e0c0sinf-n6-790b63257: frozen ba24e51 pre-3c31fb285, fleet/main 8c1b35bb.)
FLEET_RUN = ("tools/closure_loop/tt_overlay.py",)

# POST-ROUTE PUBLISH HELPERS (RLYH0-NE 2026-10-19): the view exporter runs only in collect / re-export, after the
# route's verdict, and never changes routed geometry or timing (its sessions are checked against the verdict).  It is
# the loop's publish step (EXPORT-SDC: every collect runs the loop's copy), so a fix there must reach routes already
# closed: qfwd_rlyh0_128_ne_65x30-f1-fc2236d82 lost a CLOSED result to the default abstract's merged pin-column OBS
# and its frozen exporter would replay the same failure on every re-collect.  Same rule as FLEET_RUN: drift sanctioned
# only to exactly origin/main's blob from an earlier main revision; the current bytes ship.
PUBLISH_ONLY = ("tools/tt_views/view_export.py",)


# LINT-ONLY HELPERS (ROOT 2026-10-16 URGENT, 9 jobs NEEDS_HUMAN after 2c5779073 added the native_capture CLOSED-STANDS kind):
# textbook_lint.py holds lint/gate constants and rule text; it never changes routed geometry or timing.  A frozen plan
# whose ONLY drift is such a path, from one main revision to a later main revision (same mode), is not a source change:
# the route runs with its FROZEN bytes (recovered exactly from the plan's committed origin tree), so the execution is the
# original one and the frozen plan stays valid.
LINT_ONLY = ("tools/textbook_lint.py",)


# RULE-COMMIT CLASSIFICATION (GATE-FRICTION 2026-10-18, owner 0eg; generalises ROOT-0040's relaxing-only allowlist,
# owner 10-17: "rules exist to close the die ASAP, never to delay it").  A gate executed with an older overlay / gate tool
# stays valid unless a commit that changed the file since is STRICTER for this tile.  Every commit on the file's blob
# chain (gate blob -> today's blob) is classified, first match wins:
#   1. RULE_COMMITS below (full sha): kind "relaxing" (a FAIL became a WARN / a limit loosened), "neutral" (no gate
#      verdict can change: refactor, report text, WARN-only check, submit-only constants) or "tightening" (a new FAIL /
#      stricter limit).  Optional: requires=<condition judged from the existing gate report>, applies_to=(tile/kit/top
#      name prefixes; a tightening outside them does not touch this tile).
#   2. a "Gate-Rule:" trailer in the commit message, same vocabulary:
#        Gate-Rule: relaxing requires=clock_pin_spread
#        Gate-Rule: neutral
#        Gate-Rule: tightening applies-to=qfd_,hbm_sfu_
#   3. automatic: the change is comments / docstrings / blank lines only (.py by AST; .tcl/.sdc/.sh/.json by lines), or a
#      LINT_ONLY path's submit-only constants -> neutral.
#   4. anything else is UNCLASSIFIED and keeps the strict refusal (named, with how to classify it).
# relaxing / neutral keep the gate; a tightening keeps it only when it does not apply to the tile, or its "requires" is
# met by the gate report.  Add an entry only with a reason a reviewer can check.
RULE_COMMITS = {
    # ROOT-MERGE 10-25 (codex/integrate-1025): f991d663c is the KIT-CENSUS hold-stop (owner 10-25): inside P&R hold
    # repair, a run whose synchronized FF scene shows hold WNS < -100 ps or > 2000 true failing endpoints stops before
    # repair_timing.  It is P&R flow behaviour only: no pre-route gate check reads orfs_hold_mm.tcl's new proc, so no
    # gate verdict can change; a routed run is still judged by its own sign-off report.
    "f991d663cf5f126f244bbf8b25de902d6ac266b5": dict(
        kind="neutral", rule="hold-structural-stop", paths=("tools/orfs_hold_mm.tcl",),
        what="orfs_hold_mm: stop structural FF hold failures before repair_timing (flow stop, no gate verdict)"),
    # ROOT-MERGE2 10-23 batch 15: claude/tile-flow2-1023 @6f0229425 (COORD 03:26 approved, condition: in-flight recipe-5
    # kits must not change silently).  Every planner change is behind tile_plan.planner_version 2: a kit generated before
    # this merge (kit.env present, no version in its spec) regenerates with the frozen tile_plan_v1 planner, 3 pins/um, no
    # implied pin_balance -> byte-identical kit files (measured: rg3b xm6/xmh0u/xmh1u, hr_core_prompt_tf1, lep_tf1; only
    # spec.json gains planner_version 1 / pin_density 3 / pin_balance false).  New kits take version 2.
    "1c53dcf809907d4e1b5f5aa04660184d6bf2a5dc": dict(
        kind="neutral", paths=('tools/ref_tile/tile_plan.py',),
        what="TILE-FLOW2 dual-face macro columns (plan_macros, version 2 only)"),
    "980a5d3b443960d457b2dc171b8bbaf861160814": dict(
        kind="neutral", paths=('tools/ref_tile/tie_audit.py',),
        what="TILE-FLOW2 tie_audit.py new report tool + opt-in SKIP_REPAIR_TIE_FANOUT (spec opt-in only)"),
    "1e63ff060d5487b0b306a36bddc477036a92363e": dict(
        kind="neutral", paths=('tools/ref_tile/ref_tile.py',),
        what="TILE-FLOW2 pin_balance default layers kept under a lowered signal cap (only kits with signal cap < M5 and pin_balance without h/v; old default was above the cap)"),
    "a415508d2b62d70667fbf6c2ec3cda39dcc1eb8b": dict(
        kind="neutral", paths=('tools/ref_tile/tile_plan.py',),
        what="TILE-FLOW2 mixed-column per-macro pin sum (plan_macros, version 2 only)"),
    "528708dbc611f143b4a2a5b51e19d1b929133aaa": dict(
        kind="neutral", paths=('tools/ref_tile/tile_plan.py',),
        what="TILE-FLOW2 FFD height-capped columns (plan_macros, version 2 only)"),
    "da7f261378cace6cf26af3a129b38edb38682be1": dict(
        kind="neutral", paths=('tools/ref_tile/ref_tile.py', 'tools/ref_tile/tile_plan.py'),
        what="TILE-FLOW2 tied macro pins ignored by the planner (version 2 only)"),
    "c094f6cee0b6c7eac0d388aa271e50644eb9c712": dict(
        kind="neutral", paths=('tools/ref_tile/ref_tile.py', 'tools/ref_tile/tile_plan.py'),
        what="TILE-FLOW2 logic_face over-macro back-face reach (version 2 only)"),
    "4ad9f0de4ca301b47510ad9e6e768ac7b7727ab1": dict(
        kind="neutral", paths=('tools/ref_tile/ref_tile.py',),
        what="TILE-FLOW2 face-fence orfs_vars re-derived every gen (version 2 only; version 1 keeps setdefault)"),
    "da5561a4627864abaf267e6b50f55ac56743d392": dict(
        kind="neutral", paths=('tools/ref_tile/outline_audit.py', 'tools/ref_tile/ref_tile.py', 'tools/ref_tile/tile_plan.py'),
        what="TILE-FLOW2 6 pins/um on two layers + pin-density FAIL + fixed-block macro area (version 2 only) + outline_audit report"),
    # ROOT-MERGE-1023 10-23 batch 14: claude/gate-layout-review-1023 (COORD batch 14; OWNER 10-23 tile visual review).
    # The gate now FAILs std-cell fill < 20 % of free area / pin->register p90 > 150 um (layout_review) -> a real
    # TIGHTENING for every kit: a gate run before it carries no review.png / review_stats.json and is re-gated (the
    # owner wants every unclosed tile rendered and judged).  0cf7fc33f relaxes parents to macro packing; cc59663f0 lets a
    # GEOM-REVIEW PASS excuse fill (relaxing) but no longer lets fill reasons excuse far pin registers (tightening).
    "52ac3504776512d603f25edc462ba58f07a34839": dict(
        kind="tightening", rule="layout-review",
        paths=('tools/ref_tile/layout_review.py', 'tools/ref_tile/layout_review.tcl', 'tools/ref_tile/pre_route_gate.py',
               'tools/ref_tile/layout_dump.tcl'),
        what="layout_review FAIL on low std fill / far pin registers + mandatory review render (new FAIL, all kits)"),
    "0cf7fc33ffe923df8d16d9772fdc1fd58a6cffd2": dict(
        kind="relaxing", paths=('tools/ref_tile/layout_review.py', 'tools/ref_tile/pre_route_gate.py'),
        what="layout_review: parents/clusters judged by macro packing, not std-cell fill (relative to 52ac35047)"),
    "cc59663f0755702f133bd72229f81516d3f7929e": dict(
        kind="tightening", rule="layout-review",
        paths=('tools/ref_tile/layout_review.py', 'tools/ref_tile/pre_route_gate.py'),
        what="layout_review: fill reasons no longer excuse pin-register p90 > 150 um; GEOM FAIL revokes parent fill reasons"),
    # ROOT-MERGE-1023 10-23 batch 13: claude/ft-qc-1023 (COORD 02:35 approved).  Both changes act only on a spec with
    # pg_contract == "m7_passthrough" (new opt-in, first used by the do-not-bind pilot qfd_c_b8_ft1); default contract,
    # PDN text and gate layer audit unchanged for every older kit.
    "db3885a1d0a9f2c9c894d70cb6c89c36aa158fc0": dict(
        kind="neutral", paths=('tools/ref_tile/pre_route_gate.py',),
        what="pre_route_gate layer audit: want_pg M7 only for opt-in pg_contract m7_passthrough clusters"),
    "0d25e46372e3bd0117c24752ba398169ba0ee3ad": dict(
        kind="neutral", paths=('tools/ref_tile/ref_tile.py',),
        what="ref_tile layer_contract/gen_pdn m7_passthrough branch (opt-in pg_contract only)"),
    # ROOT-MERGE-1023 10-23 batch 13: claude/tile-flow-1023 (COORD 02:33 approved).  Every new rule (content outline,
    # face fence, outline_ratio FAIL, pin_regs wrapper refusal, macro array plan) is behind tile_plan_on(spec): recipe 5
    # leaf tiles or an explicit "tile_plan" opt-in.  No kit gated before this merge has either (RECIPE_LATEST was 4),
    # and test_tile_plan_off_keeps_recipe_4_behaviour pins the legacy path -> no older gate verdict can change.
    "867781db8cfa5e9c87f418b6361e2d37738f3e8e": dict(
        kind="neutral", paths=('physical/common_flow/pin_reg_face_fence.tcl', 'tools/ref_tile/outline_audit.py',
                               'tools/ref_tile/ref_tile.py', 'tools/ref_tile/tile_plan.py'),
        what="TILE-FLOW recipe 5 / tile_plan (opt-in, new kits only); legacy recipe <= 4 kits unchanged"),
    "c861553eb5133e82baac953f5ad790722797fe28": dict(
        kind="neutral", paths=('tools/ref_tile/ref_tile.py',),
        what="TILE-FLOW tile_plan macro column abutment + outline reason (tile_plan kits only)"),
    "59174ca777cae5c92619b66679f2958469c36cc5": dict(
        kind="neutral", paths=('physical/common_flow/pin_reg_face_fence_after.tcl',),
        what="TILE-FLOW face fence chaining hook (sourced only by tile_plan kits)"),
    "a786d230d791823dfe8fa15ac08e50c8aabd6506": dict(
        kind="neutral", paths=('physical/common_flow/pin_reg_face_fence.tcl', 'tools/ref_tile/outline_audit.py'),
        what="TILE-FLOW face fence globals (tile_plan kits only) + audit report tool"),
    "2a1910a6233bc25a40124aee4b16ffd45bcd548a": dict(
        kind="neutral", paths=('physical/common_flow/pin_reg_face_fence.tcl',),
        what="TILE-FLOW face fence keeps FIRM pin flops (tile_plan kits only)"),
    # ROOT-MERGE-1023 10-23 batch 12: claude/geom-review-gate-1023 (COORD 02:02/02:15 approved, enforcing).  The GEOM-REVIEW
    # intake check is a separate submit-time policy keyed on review verdicts + kit content hash, judged by the CURRENT
    # code at every intake; it changes no pre_route_gate verdict, so an older gate stays as valid as before.
    "bfc589005a25959d56e7646c8da5c7f314a6ea9b": dict(
        kind="neutral", paths=('tools/closure_loop/closure_loop.py', 'tools/closure_loop/geom_review_gate.py'),
        what="GEOM-REVIEW route intake gate (new module + intake/validate hook); no gate report verdict changes"),
    "99d25d3f279399b207389f9a52df85178a479052": dict(
        kind="neutral", paths=('tools/closure_loop/geom_review_gate.py',),
        what="GEOM-REVIEW PASS-CONDITIONAL verdict class (intake only); no gate report verdict changes"),
    # ROOT-MERGE-1022 10-22 batch 9: STW-S81c-TOK5 20:38 + STEWARD-S81c 20:05 GATE_RULE_GUARD asks (collect auto-merge refusals)
    "127356adf225c23173c42e606c0215e7a041af36": dict(
        kind="neutral", paths=('tools/ref_tile/specs_pl_gunit/respec_lp4.py',),
        what="S81 gunit lp kit spec generator respec_lp4.py (pin_balance / peak_ram / spec keys of dsdv_gunit_lp kits); kit specs + kit files + the unit's own RTL/benches; no shared gate rule"),
    "687be27a4d389446033506b2ae9cddf5df7e6db3": dict(
        kind="neutral", paths=('tools/ref_tile/specs_pl_gunit/respec_lp4.py',),
        what="S81 gunit lp kit spec generator respec_lp4.py (pin_balance / peak_ram / spec keys of dsdv_gunit_lp kits); kit specs + kit files + the unit's own RTL/benches; no shared gate rule"),
    "3b8b264472a25910b43c69117603bfa0ff0122b2": dict(
        kind="neutral", paths=('tools/ref_tile/specs_pl_gunit/respec_lp4.py',),
        what="S81 gunit lp kit spec generator respec_lp4.py (pin_balance / peak_ram / spec keys of dsdv_gunit_lp kits); kit specs + kit files + the unit's own RTL/benches; no shared gate rule"),
    "676085b635759a98630c0df247be24351a29a09a": dict(
        kind="neutral", paths=('tools/ref_tile/specs_pl_gunit/respec_lp4.py',),
        what="S81 gunit lp kit spec generator respec_lp4.py (pin_balance / peak_ram / spec keys of dsdv_gunit_lp kits); kit specs + kit files + the unit's own RTL/benches; no shared gate rule"),
    "60db766f669b64af32828cca95aec0cba5d2a618": dict(
        kind="neutral", paths=('physical/common_flow/macro_pin_flops.tcl',),
        what="macro_pin_flops.tcl opt-in placement hook (kits with pin_hook_before_flops only): globals -> upvar 1 crash fix; places flops, judges nothing"),
    "b80342fea3727b0d7f8e779f45b79fa364871551": dict(
        kind="neutral", paths=('physical/common_flow/macro_pin_flops.tcl', 'physical/common_flow/macro_pin_flops_release.tcl'),
        what="new opt-in macro-pin flop placement hooks (PRE_GLOBAL_PLACE / PRE_DETAIL_PLACE) used only by s81dv_idxtx* kits listing pin_hook_before_flops; no check, SDC template or netlist change"),
    # ROOT-MERGE-1022 10-22: s81-reftile-pin-boundary
    "d3dddf08fb1f43cbcab1aadadfd4925d9f25d3ad": dict(
        kind="neutral",
        what="ref_tile _child_insertion: pin-mode multiple_cts_roots child without clock_measurements targets insertion tt.boundary.mean (kit generator spine target; no gate check change; no-op on main specs)"),
    # ROOT-MERGE-1022 10-22: tokc-sparse-keep2
    "fd50f64dbbfa30e99b39f83fab582b5ec5d7d01b": dict(
        kind="neutral",
        what="sparse_keep.py v2: append-only sparse list edits, refuses before any removal; no gate check"),
    # ROOT-MERGE-1022 10-22: tokc-sparse-keep (new files only)
    "cc298a6f04b3bc417d29076a8e70783653af108d": dict(
        kind="neutral",
        what="sparse_keep.py new helper: widens a sparse worktree without deleting on-disk kits; no gate check"),
    # ROOT-MERGE-1022 10-22: claude/sqc-slice16-1022 lineage fbee65bf2 touches only qw2 slice2 kit files under
    # tools/ref_tile/specs_qw2_slice2_native|tall (plus tools/qwen_dv generators); no shared gate/helper rule changes.
    "fbee65bf263e7e0275ccd3bf695cb3f21be8b05b": dict(
        kind="neutral",
        what="qw2 slice2 kit spec/pin/fence files only (specs_qw2_slice2_*); shared gate unchanged"),
    # ROOT-MERGE-1022 10-22: claude/sqc-slice16-1022 lineage e3f6a40a7 touches only qw2 slice2 kit files under
    # tools/ref_tile/specs_qw2_slice2_native|tall (plus tools/qwen_dv generators); no shared gate/helper rule changes.
    "e3f6a40a762c486fe2316db4a8547962437eb622": dict(
        kind="neutral",
        what="qw2 slice2 kit spec/pin/fence files only (specs_qw2_slice2_*); shared gate unchanged"),
    # ROOT-MERGE-1022 10-22: claude/sqc-slice16-1022 lineage ca722a3b6 touches only qw2 slice2 kit files under
    # tools/ref_tile/specs_qw2_slice2_native|tall (plus tools/qwen_dv generators); no shared gate/helper rule changes.
    "ca722a3b69f19d725dabda9eb4e618fcd43a928a": dict(
        kind="neutral",
        what="qw2 slice2 kit spec/pin/fence files only (specs_qw2_slice2_*); shared gate unchanged"),
    # ROOT-MERGE-1022 10-22: claude/sqc-slice16-1022 lineage 1d121e084 touches only qw2 slice2 kit files under
    # tools/ref_tile/specs_qw2_slice2_native|tall (plus tools/qwen_dv generators); no shared gate/helper rule changes.
    "1d121e0847501049f73943e7d06836592f496352": dict(
        kind="neutral",
        what="qw2 slice2 kit spec/pin/fence files only (specs_qw2_slice2_*); shared gate unchanged"),
    # ROOT-MERGE-1022 10-22: 497ebf9c7 changes helper_overlay.py only by adding the RULE_COMMITS entry for 522f36523
    # (plus new seq (B) parent kit files) -> no gate behaviour changes.
    "497ebf9c7533848ddbc0e797a5bc0df69e0e16a7": dict(
        kind="neutral",
        what="helper_overlay: adds the 522f36523 RULE_COMMITS entry only; seq (B) kit files"),
    # ROOT-MERGE-1022 10-22: claude/s81-seq-b1-1022 lineage ba140fd98 (S81-ELEM2-SEQ) only edits the dsdv_seq_host
    # kit spec generators under tools/ref_tile/specs_pl_seq; no shared gate or helper rule changes.
    "ba140fd98883fbc99cae1066757fa98f32be77d4": dict(
        kind="neutral",
        what="seq host kit spec generators (mk_dsdv_seq_host_gh/hw) only; shared gate unchanged"),
    # ROOT-MERGE-1022 10-22: claude/tokc-oomadj-1022 ded87247b (URGENT TOKc-OOM). closure_loop.py only changes the die
    # job OOM probe/adjust value (-1000 -> -999, -1000 processes left untouched); no gate verdict or route helper changes.
    "ded87247b93bc390636bc661eaec6ecbdcb198d7": dict(
        kind="neutral",
        what="closure_loop die OOM adjust moved to -999 (was minus one thousand); process protection only, no gate check"),
    # STW-S81c-COLLA2 10-22 (STEWARD-S81c decision (A), seq (B) parents): clock_entry_constraints multi_root_children is
    # opt-in through the spec key (absent = byte-identical SDC: 34/34 landed specs on origin/main regenerate identical);
    # it only lifts the one-child-one-root ownership assertion for declared CLOSED children -> no older gate changes.
    "522f365238e6aac3090324d750c1c6f323979b34": dict(
        kind="neutral",
        what="seq (B): opt-in multi_root_children in clock_entry_constraints; default SDC identical"),
    # ROOT-MERGE-1022 10-22: 0c6c603fa (same branch): clock_entry_constraints landed_band record type + half-landing port
    # multicycles, only through a spec's landed_band key (absent = lp-record SDC sha identical) -> no older gate changes.
    "0c6c603fa825799b1ffaf8c66292016122daed92": dict(
        kind="neutral",
        what="frame: opt-in landed_band record in clock_entry_constraints; default SDC identical"),
    # ROOT-MERGE-1022 10-22: claude/s81c-frame-1022 7fa6e9622 (STW-S81c-DIE-FRAME). pre_route_gate cross_region_links
    # now ACCEPTS an ot_reset_sync reset landing into a forwarded clock (net only on async_rst_n, all other members on one
    # root) that it used to report as unlanded -> a FAIL can only become a PASS.  lp.py landing_vector_group and the
    # landed_band record are opt-in (absent = byte-identical output).
    "7fa6e96222a7fedc6b29534becc713e96910463e": dict(
        kind="relaxing",
        what="frame: reset-sync landing into a forwarded clock accepted; lp/clock-entry additions opt-in"),
    # ROOT-MERGE-1022 10-22: claude/hbm-pslice-lp15-1021 b6940eee2 (HBMb/IDXSU-PS15). Its child_centre_tap.tcl r15 was
    # resolved to main's copy (58622b026, Gate-Rule: neutral), which already carries the r15 child-scoped corner fix
    # and the per-mode propagation; the rest are NEW pgcol_l r6a/r6b and pslice_c5_r15 kit files.
    "b6940eee26c1db9b96ffca27e11586cb54093df4": dict(
        kind="neutral",
        what="pslice lp15: new kit files; child_centre_tap.tcl = main's copy (58622b026)"),
    # ROOT-MERGE-1022 10-22: claude/hbm-pslice-lp14-1021 17f38120b (HBM-ELEM13/SU-PSLICE14). The merge resolved
    # physical/common_flow/child_centre_tap.tcl to main's newer copy (58622b026, Gate-Rule: neutral), its ref_tile.py
    # hunk is byte-identical to main's, and the rest are NEW pslice_c5 lp14a/b kit spec/pin/fence files -> no gate rule
    # an older gate blob saw changes.
    "17f38120bb4a6dce5f38384bbed1a80d2bb276dd": dict(
        kind="neutral",
        what="pslice lp14: new kit files; cct + ref_tile.py identical to main's copies"),
    # START-NONFAIL/HBM-CANC 10-21: claude/hbm-ks13-agtool-1021. async_gray SDC applies every bounded pair's
    # set_max/min_delay first and proves each pair's finite max/min path in one ot_ag_verify pass (was one
    # find_timing_paths re-search per pair).  Same exceptions/checks/errors/PATH_DEFERRED texts; ASAP7 equivalence on
    # the 10-18 kshare netlist BOUNDED 12,576 = 12,576, 0 extra/missing, ownership identical -> no verdict changes.
    "a7bc197f096b54b49b908549e2369bbc58baae8e": dict(
        kind="neutral", paths=("tools/ref_tile/async_gray_fifo_constraints.py",),
        what="async_gray: one-pass ot_ag_verify of bounded pairs; identical exceptions (EQUIV 12,576=12,576)"),
    # MERGE-1200 10-21: SQK-INGEST OT_GF fixes (claude/sqk-ingest-1021). db8d8c63d: a hard-macro output in a storage-gating
    # cone is a free-variable leaf in _bdd_of (as _cone_cut already did; it crashed before) -> only cones that used to
    # error now evaluate.  a3aafacd6: reset-bank copy flops named ot_rrs__<fam>__c<k> alias to their own reviewed leaf
    # role (no new role) -> a refusal becomes a pass for exactly those copies.  Neither tightens any gate.
    "db8d8c63d661ec74102231f0afb5963238223459": dict(
        kind="relaxing", paths=("tools/ref_tile/gray_fifo_cdc_constraints.py",),
        what="OT_GF: macro output is a free BDD leaf (was a crash)"),
    "a3aafacd6cfb91e0704eda7825c4e619fc3043b0": dict(
        kind="relaxing", paths=("tools/ref_tile/gray_fifo_cdc_constraints.py",),
        what="OT_GF: reset-bank copy names alias to the reviewed leaf role"),
    # MERGE-1200 10-21: SCRATCH2-1021 run_base() falls back to the last good host probe when the probe cache was just
    # dropped (run-dir placement on the freest scratch base only); no gate check or route helper behaviour changes.
    "0f20951a3b233134e8b8e7b38c60a2541117d871": dict(
        kind="neutral", paths=("tools/closure_loop/closure_loop.py",),
        what="run_base scratch-base selection uses last good probe; placement only, gates unchanged"),
    # ROOT 10-21: a kit-specific generator under the broad tools/ref_tile prefix; it creates only the new
    # xhead3/xhead3b specs, with no change to shared gate checks or pre-existing kit generation.
    "b9e2576f31ef0a5ff404bbb4693f04c0295bd173": dict(
        kind="neutral", paths=("tools/ref_tile/specs_qw_s5_xhead/gen_xhead3_specs.py",),
        what="new xhead3/xhead3b kit generator; shared gate and route helpers unchanged"),
    # ROOT-1021 10-21: da435c6ac / 712ed0fe8 are claude/drives81-l1f-1020 lineage commits (S81-GUSEQ / PL-GULEAF) whose
    # helper hunks are origin/main tool content carried into the branch (its later 'sync ... from origin/main
    # (byte-identical)' commits d5427b883 / 5858e903d prove the copies).  The ROOT merge resolved every helper file to
    # main's own content, so these commits bring no rule onto main that an older gate blob did not already have.
    "da435c6ace7434f910b524da6698802e1cd41274": dict(
        kind="neutral", paths=("tools/closure_loop/ck_insertion.py", "tools/ref_tile/pre_route_gate.py",
                               "tools/ref_tile/source_binding.py"),
        what="drives81-l1f lineage: main helper content carried into the branch; ROOT merge kept main's files"),
    "712ed0fe86cb946c41f4643e1f84642e8b2d17ac": dict(
        kind="neutral", paths=("tools/closure_loop/helper_overlay.py", "tools/ref_tile/pre_route_gate.py",
                               "tools/ref_tile/source_binding.py"),
        what="drives81-l1f lineage: main helper content carried into the branch; ROOT merge kept main's files"),
    # KV-PVFIN17 10-20 21:40: 13a502b48 ("scoped cap binds to the gated tile") carries a bare 'Gate-Rule: tightening'
    # (no applies-to), so every gate made before it was refused at submit (s81sl_ve_r5, PVFIN R15c, ...).  It only adds
    # "scoped waiver S does not apply to tile T" when a spec's clock_rule_waiver names scope S != its block T; the scoped
    # caps it narrows were added by its parent 3969f6fb4 (relaxing applies-to=qkd_pv_fin_s32) and both reached main in
    # the same merge (first main commit containing either: cd50a961a), so no gate ever ran with 3969f6fb4 alone and no
    # gate verdict relative to an older blob becomes stricter for any tile.  pre_route_gate.py only passes spec["block"].
    "13a502b48ca210cbc317a4834ec48a7173f9ce05": dict(
        kind="neutral", paths=("tools/textbook_lint.py", "tools/ref_tile/pre_route_gate.py"),
        what="scoped clock-waiver cap bound to its own tile; landed on main together with the cap (3969f6fb4)"),
    # e7358eb66 (same pattern for the MC3c7 census waiver of 0b6052c50): the new refusal fires only for the two MC3c7
    # kits' scoped waiver -> tightening scoped to them.
    "e7358eb6681cca4d302824840bb13c034f7ad0dd": dict(
        kind="tightening", applies_to=("hdie_pc_ctrl_mc3c7_wel", "hdie_pc_ctrl_mc3c7_cts"),
        paths=("tools/ref_tile/pre_route_gate.py",),
        what="MC3c7 scoped census waiver bound to the gated kit's spec; only those two kits"),
    # ROOT11 10-20: XS bay record merge (f61a12bcc lineage). 9a21b1c63 only re-synced main's CX-IJ cross-clock gate
    # (check_cross_clock, tightening, multi-clock kits only) into the HF-5 branch; the merged tree keeps main's file.
    "9a21b1c6382c404f803e8f954db08024701dcb23": dict(
        kind="tightening", paths=("tools/ref_tile/pre_route_gate.py",),
        what="branch re-sync of main's CX-IJ cross-clock gate (multi-clock kits only); no new rule"),

    # QW STREAM: the only guarded path is a NEW, tile-specific spec generator.
    # It adds no gate/submit/route validator code and changes no existing helper.
    "6ebf7706a64edfe81bfbde75defed9c374c5bfd8": dict(
        kind="neutral", paths=("tools/ref_tile/specs_qw_stream_1019/mk_specs.py",),
        what="new Qwen stream kit-spec generator only; no existing gate-rule or shared helper changes"),

    "ef6a3af26513c90c8af5d553c7238276df905848": dict(
        kind="relaxing", rule="0dq", requires="clock_pin_spread",
        what="clock rule 0dq (owner 10-17): insertion > 300 ps / > 15k sinks FAIL -> WARN; FAIL only on pin-flop "
             "spread > 80 ps at TT or FF"),
    "58a346a8ef042c634b3f368b265ddd96ae6004be": dict(
        kind="neutral", rule="util-density",
        what="textbook_lint util_channel is WARN-only (not in REFUSE_CHECKS/HARD_CHECKS): std-cell density over the "
             "placeable area for macro kits changes WARN text, never a gate FAIL; no-macro kits unchanged"),
    "98474c45ee3474d9198f521060af91e2c2bc416d": dict(
        kind="neutral", rule="closed-stands-native-capture",
        what="CLOSED_STANDS native_capture admission: submit-time CLOSED-STANDS lint only, never read by the pre-route gate"),
    "2c5779073788dca0d09b65bc8150f0006d9326c6": dict(
        kind="neutral", rule="closed-stands-native-capture",
        what="CLOSED_STANDS reroute kind native_capture: submit-time lint only"),
    # ROOT-0330 10-18: KV die planner changes without a trailer (inputs of ~180 gates).  Only kv_die.py and
    # kv_pin_repair.py are classified (paths=): the same commits' pv_trunk_gen.py / kv_static_die.py / kv_expand.py
    # changes are not.  With every new switch at its default the plan is byte-identical for every kit that built before.
    "76f68cefa8ae97296b8c1f07eab9801c47aaac70": dict(
        kind="neutral", rule="kv-die-opt-in", paths=("tools/qwen_kv_die/kv_die.py", "tools/qwen_kv_die/kv_pin_repair.py"),
        what="KV-PLAN3: OT_KV_CTL_BAND (default 0 = old sy), OT_KV_FAIL_JSON (dump on the raise path only), "
             "KSD.face_order only under OT_KV_STATIC_DIE=1, pin_reach report gains an 'all' list (report text); "
             "kv_pin_repair attempt 0 = the old loop verbatim, attempt 1 runs only for a hop the old code left "
             "unresolved, which made the old build raise (default OT_KV_HOP=0) -> every previously built plan unchanged"),
    "8a83ec822056192aa6c6c49940974ebe062e734b": dict(
        kind="neutral", rule="kv-die-opt-in", paths=("tools/qwen_kv_die/kv_die.py",),
        what="KV-RTRUNK: PV_RS = OT_KV_PV_T=1 (default 0) AND a pv_trunk_t plan carrying result_trunk; only then the "
             "qkd_pvw_* masters gain port bundle pr and its strip-face pin (the plan.json is its own bound input)"),
    # ROOT-0630 10-18 (0gi): the three older kv_die.py commits without a trailer (kv_die.py only, paths=).
    "283be4b3ab79bd9bfe26093d72e1c826c8748cea": dict(
        kind="neutral", rule="kv-die-opt-in", paths=("tools/qwen_kv_die/kv_die.py",),
        what="KV-PLAN2: OT_KV_SN_LIFT (default 0; band_shift['N'] += 0, Hk + 0, geo.sn_lift only when set) -> every "
             "plan built without the switch is byte-identical"),
    "482e947cb6ca1f3577a511962446e8e593e9b8d6": dict(
        kind="tightening", rule="kv-ahub-one-clock", paths=("tools/qwen_kv_die/kv_die.py",),
        applies_to=("qkd_ahub", "ot_qkd_ahub", "qkd_die", "qwen_kv_die"),
        what="KV-AHUB hp4: AHUB_CLK 14 per-child entries -> one entry ck (SPLIT_BINDINGS ahub ck_c=['ck']); changes only "
             "the attention-hub block's clock pins / binding and the die nets to it -> ahub kits and the KV die top"),
    "50747106abfceb433fb03d3e3fdf96846bba6f41": dict(
        kind="tightening", rule="kv-host-clock-family", paths=("tools/qwen_kv_die/kv_die.py",),
        applies_to=("qkd_host", "qkd_hr", "qkd_die", "qwen_kv_die"),
        what="KVJ-A3 D2: HOST_CLK_INFERRED ck_peer / ck_root_mux host -> core family (die clk_core_c / clk_host nets to "
             "the host block); changes only the HOST block's clock trunks -> host / host-root-cluster kits and the KV "
             "die top"),
    # ROOT-0615 10-18: dcd8111e5 (SM-RP4 CHILD-FLOP, coordinator 0gd) had no trailer.  ck_insertion now adds a per-corner
    # child_flop {boundary, all} record (a block-master clock pin counted at arrival + R, R = that view's insertion.json
    # boundary mean, else its lib max_clock_tree_path, else 0) and pre_route_gate.corner_spreads judges it.  Verdict-
    # neutral for: wires-only parents (with_child_flops overwrites the record; child_pair basis), kits with no macros,
    # and kits whose macros carry no R (plain SRAM / ROM libs: R = 0, identical stats).  It CAN change the pin-flop
    # spread either way for (a) clusters whose boundary also holds glue registers, with hard children that have
    # insertion.json / max_clock_tree_path, and (b) leaf tiles using a macro lib with max_clock_tree_path
    # (ot_rom_4096x266_m8_skew*, any ETM view used as a macro).  requires= judges that from the kit (source_binding).
    "dcd8111e54a033d01ffd6e3d58ec91b6f070bb27": dict(
        kind="tightening", rule="child-flop-basis", requires="child_flop_basis",
        what="ck_insertion/pre_route_gate CHILD-FLOP: hard-child / referenced-macro clock pins judged at arrival + R; "
             "applies to clusters with glue boundary registers + referenced children, and tiles with "
             "max_clock_tree_path macros; wires-only parents and R-less macro kits unchanged"),
    # ROOT-0920 10-18: two tool-lane commits merged without a trailer.
    "6d18d818a48d030788f6762e4f5f653fd4a4f935": dict(
        kind="neutral", rule="landed-cluster-kit",
        what="PL-KIT: ref_tile accepts kind cluster + multiple_cts_roots only with landed_record + children (a form it "
             "refused before, so no earlier gate exists for it); every new SDC/TCL/hook line is behind "
             "landed_cluster(s) / ::ot_ce_landed_cluster; LEAF_BODY/BODY bytes unchanged -> non-landed kits identical"),
    "41f49ef5bb30d8e277d2a7281b8b93e50db57905": dict(
        kind="neutral", rule="cdc-lint-receipt",
        what="ROOT-LINT: CDC/gray-fifo kit lint reuses a content-keyed receipt or runs the same lint on the fleet; same "
             "lint, same generated bytes, same verdict; submit_exact ignores an untracked lint_receipt.json"),
    # ROOT-0945 10-18: S81-QNT3 merged without a trailer on the branch commit.
    "6d627c6feee72e058f22f2ef3f9f3fdbf24ac4b0": dict(
        kind="neutral", rule="bench-input-path",
        what="S81-QNT3: SU/HC composition gates + 3 kit specs read the committed tools/s81_suhc/fixtures/"
             "su_cases_v2_ildr.pkl (same bytes, sha 8c18c0655ccf) instead of a /srv path; regexes and checks unchanged"),
    "3dd60bc0f0617cfaae3db5f77870c267195e76a8": dict(
        kind="tightening", rule="pin-geometry",
        what="fp_margin_lint: actual pin rectangles inside the die with track data (new FAIL)"),
    "53efc860bda4dc258b0ec9f229d1b6a9b89d05ff": dict(
        kind="tightening", rule="pin-track-access",
        what="fp_margin_lint: IO pins without actual routing-track access FAIL"),
    # ROOT-UNBLOCK 10-19: two main commits without a trailer refused every older gate (unclassified).
    # 96f1d6e0d (RC-IOREF): ot_rc_cal_hold now re-syncs the numeric FF I/O references (ot_mm_unsync; ot_mm_sync) after
    # applying and after restoring the calibrated hold RC.  It acts only when RC-CAL changes something AND the MM scene
    # was already synced (OT_HOLD_MM).  No gate FAIL rule reads it (gate hold is WARN-only; the clock tree is not touched),
    # but it changes the hold-repair targets: stale platform-RC references were pessimistic for outputs and optimistic
    # for inputs (rc_ioref_capc_1019: out_hold 30.3 -> 111.6 ps, refmax 605 -> 522 ps), so repair buffers can move either
    # way.  At gate CTS (placement mode) the hold RC applies only with a spine (ot_rc_cal_spine), so the gate's CTS ODB
    # can differ only for spine clusters -> tightening scoped by requires=rc_cal_spine_hold (spine cluster: re-gate).
    "96f1d6e0d0577256388fba8ae81830b4c80f4284": dict(
        kind="tightening", rule="rc-ioref-refresh", requires="rc_cal_spine_hold", paths=("tools/orfs_hold_mm.tcl",),
        what="RC-IOREF: FF I/O references re-measured under the calibrated hold RC (and again after restore) inside "
             "ot_rc_cal_hold; gate CTS hold repair differs only for spine clusters under OT_HOLD_MM; never a gate FAIL "
             "rule; route hold repair targets change in either direction"),
    # e03b80922 (SINGLE-CLOCK BW contract): ot_mm_sync_link_periods now calls ot_single_clock_check, a proc that exists
    # only in kits whose spec carries single_clock_contract (single_clock_contract.guard); it can raise (wrong root,
    # unowned virtual clock, period mismatch), never relax -> tightening scoped by requires=single_clock_contract.
    "e03b80922d812ab1d803f3c4c9313e74f5eeba9b": dict(
        kind="tightening", rule="single-clock-contract", requires="single_clock_contract", paths=("tools/orfs_hold_mm.tcl",),
        what="SINGLE-CLOCK: MM link-period sync runs ot_single_clock_check when the kit defines it (spec "
             "single_clock_contract); other kits never define the proc -> unchanged"),
    "c0b7b4d66a11c2125ad0d1ecac53454604b54cc6": dict(
        kind="tightening", rule="single-clock-contract", requires="single_clock_contract",
        paths=("physical/common_flow/io_ref_routed.sdc",),
        what="SINGLE-CLOCK: io_ref_routed.sdc runs ot_single_clock_check when the kit defines it (spec "
             "single_clock_contract); other kits never define the proc -> unchanged"),
    # b7aff0fb8 / a6dc6094a (CLOCK-FAMILY ordinary roots): with no generated clock family (ot_cf_master empty) the
    # family helpers fall back to the pre-family all_registers / legacy ot_ir_arr ownership query, which the strict
    # family query could refuse ('wrong/ambiguous clock ownership') on check-only macro entries; generated-family kits run
    # the same code.  a6dc6094a only makes that rename idempotent when the SDC is re-sourced after an RC refresh (the
    # second source used to raise).  ck_insertion: ot_cf_root is the identity for ordinary roots.  -> relaxing.
    "b7aff0fb8961b5ac15a3ea8d8551aa62db9facd9": dict(
        kind="relaxing", rule="clock-family-ordinary",
        paths=("physical/common_flow/clock_family.tcl", "physical/common_flow/io_ref_routed.sdc",
               "tools/closure_loop/ck_insertion.py"),
        what="CLOCK-FAMILY: ordinary roots (no generated family) use the pre-family all_registers ownership query "
             "again; generated families unchanged; an ownership FAIL can only disappear"),
    "a6dc6094abd587d675adc438a0247d115bd63862": dict(
        kind="relaxing", rule="clock-family-ordinary", paths=("physical/common_flow/io_ref_routed.sdc",),
        what="CLOCK-FAMILY: re-sourcing io_ref_routed.sdc after an RC refresh no longer raises on the legacy rename"),
    # a6d33cc98 (BALANCED-RESET): textbook_lint gains balanced_reset_proof, active only with --balanced-reset-profile,
    # which pre_route_gate passes only when spec.reset_landing.first_copies is set.  For such a kit a proved two-edge
    # landing skips the rst_land_max FAIL (relaxing) but a refused proof is a new FAIL (tightening); every kit without
    # first_copies runs byte-identical checks -> tightening scoped by requires=balanced_reset_profile.
    "a6d33cc985d3a0d686ba2b1d94930b3350b5de14": dict(
        kind="tightening", rule="balanced-reset-proof", requires="balanced_reset_profile", paths=("tools/textbook_lint.py",),
        what="BALANCED-RESET: opt-in mapped two-edge reset proof for kits with reset_landing.first_copies (proof replaces "
             "the rst_land_max sink limit, refusal is a FAIL); kits without first_copies unchanged"),
    # ROOT-RULETAG 10-19: the six remaining helper-chain commits without a (valid) trailer.
    # 03c544ca1 (DAEMON-FIX2): abstract_pin_stub.move_stubs pin index = same hits in the same order (randomised
    # equivalence test vs the all-pairs scan); the closure_loop.py part is daemon restart-drain / checkpoint plumbing.
    "03c544ca1ab6f68f0d2a94bb2e7fb43751eedce7": dict(
        kind="neutral", rule="pin-stub-index",
        what="DAEMON-FIX2: abstract_pin_stub binned pin index (identical output, faster); daemon SIGTERM drain + "
             "write-ahead checkpoint + staged helper ship; no gate check or limit changes"),
    # b7918e979 (KV-ECTL5): child_lint (i) pin access is a new FAIL on hard-child views (the pre-route gate lints spec
    # "children" only) and ref_tile gen refuses such a view; abstract_pin_stub's wider pin keep-out only shrinks the
    # pocket set child_lint (h) can see.  -> tightening, judged per kit by requires=child_pin_access (no children, or no
    # child view LEF with a violation: gate kept).
    "b7918e97926daf87d0edfee3e62f07322d62e96b": dict(
        kind="tightening", rule="child-pin-access", requires="child_pin_access",
        what="KV-ECTL5: child_lint (i) FAILs a hard-child pin with a same-layer OBS closer than the wide-metal spacing; "
             "ref_tile gen refuses such a child view; pin keep-out >= wide spacing (pockets can only shrink)"),
    # view_export.py (PUBLISH_ONLY): runs only in collect / re-export after the route verdict; no pre-route gate reads it.
    # bb5e443cd's trailer "Gate-Rule: export-session reproduces verdict" is not in the vocabulary, so it read unclassified.
    "bb5e443cdb8423c7b3ad4fab6961c201bfeb9e1b": dict(
        kind="neutral", rule="export-replays-verdict",
        what="PF-HARDCHILD-EXPORT: the export session replays the verdict's OT_PF_MACRO_LIBS line, so export slack = "
             "verdict slack; no rule or limit changes"),
    "b8fa05678b7e74d2549d37a0d6c8a7608abc6731": dict(
        kind="relaxing", rule="exact-abstract-fallback",
        what="RLYH0-NE: export publishes the exact-shape abstract only when the default abstract has child_lint (i) "
             "pin-access violations and the exact one has fewer (a collect FAIL can only disappear); PUBLISH_ONLY "
             "drift sanction; identical export-lint FAIL stops at the first repeat (retry count, not a verdict)"),
    "cdd8d92a84daa2bf1d60a08d9d8ba97be64c1488": dict(
        kind="relaxing", rule="exact-abstract-fallback", paths=("tools/tt_views/view_export.py",),
        what="view_export judges pin access on the finalized LEF too, so the exact-shape fallback also runs when the "
             "published LEF would fail child_lint (i); a collect FAIL can only disappear"),
    "ff7aa2deb861035c309af48249284018f40718b0": dict(
        kind="relaxing", rule="exact-abstract-fallback", paths=("tools/tt_views/view_export.py",),
        what="TW3-LGTAP: exact shapes only inside pin windows when the exact abstract is > 200k rects; published only "
             "when it has fewer pin-access violations than the default; a collect FAIL can only disappear"),
    # ROOT3 10-19 (merge note, history not rewritten): KV-PC 96ac666e1 changed ot_rst_copies.py/.tcl without a trailer.
    # Strided families apply only to (* ot_rst_split = W *) with an integer W >= 2 (1 / binary 1 -> the old family) and
    # --wide / opt_dff run only under OT_RST_COPIES_WIDE=1 -> every existing kit's prep and split are unchanged.
    # ROOT3 10-19 (merge note): KV-RELAYGEN 1d4c26cb4 (inherited by claude/kv-attn2b-1019) added ot_rst_split.py/.tcl without
    # a trailer; both were removed again on that branch (superseded by ot_rst_copies) and are absent from main's tree ->
    # no gate ever reads them.
    "1d4c26cb409c792c175b54cba00d45da36e773b6": dict(
        kind="neutral", rule="rst-copies-opt-in",
        paths=("physical/common_flow/ot_rst_split.py", "physical/common_flow/ot_rst_split.tcl"),
        what="ot_rst_split.py/.tcl (OT_RST_SPLIT_MAX opt-in), removed again before the merge: not in any merged tree"),
    "96ac666e1019437db6b9c723cf9059aa9884a314": dict(
        kind="neutral", rule="rst-copies-opt-in",
        paths=("physical/common_flow/ot_rst_copies.py", "physical/common_flow/ot_rst_copies.tcl"),
        what="ot_rst_copies: strided copy families only for ot_rst_split = W >= 2, OT_RST_COPIES_WIDE=1 opt-in "
             "(opt_dff + memory/coarse-cell maps); default prep/split byte-identical for every existing kit"),
    # ROOT4-QWMERGE 10-19 (merge note, history not rewritten): the Qwen branches qw-slice3 / toksim-qw-stg / toksim-qw-link
    # (base 9cba02d14) inherited helper commits without a trailer.  In the merged tree every one of these paths is main's
    # blob (the copy-of-main / RLYH0-EN / SLICE-E content is already on main under its own classified commits); none of
    # the branch blobs below is read by a main gate.
    "16cfc00b6091057abf89debd8c49372d436ef69c": dict(
        kind="neutral", rule="copy-of-main",
        paths=("tools/closure_loop/ck_insertion.py", "tools/ref_tile/pre_route_gate.py", "tools/ref_tile/source_binding.py"),
        what="QK-SLICE: tools/closure_loop + tools/ref_tile copied from origin/main (an intermediate main state)"),
    "516b68f312152d7a8e0281fcfa45ad8171f0dde9": dict(
        kind="neutral", rule="copy-of-main", paths=("tools/ref_tile/clock_entry_constraints.py",),
        what="MU-DQ-DHUSER: tools/ref_tile copied from origin/main (an intermediate main state)"),
    "5972dd261119d646c106fc414b78e3bb53fc20de": dict(
        kind="neutral", rule="copy-of-main", paths=("tools/ref_tile/ref_tile.py",),
        what="MU-DQ-SLICEKC: tools/ref_tile copied from origin/main (an intermediate main state)"),
    "d3cf669e3a78eb68520be5d61e78d6968d89e0c6": dict(
        kind="neutral", rule="copy-of-main", paths=("tools/ref_tile/ref_tile.py",),
        what="MU-SLICE-GATE: tools/closure_loop + tools/ref_tile carried from origin/main onto the SLICE-E tree"),
    "70d2a74d202f0483728a983ad0a06682d4ad1382": dict(
        kind="neutral", rule="duplicate-of-main",
        paths=("tools/ref_tile/pre_route_gate.py", "tools/ref_tile/ref_tile.py"),
        what="RLYH0-EN reset-landing / face_land helpers: the same content reached main separately; merged tree = main's"),
    "c7be255085b0c640a08d3262d1041108dc65f729": dict(
        kind="neutral", rule="duplicate-of-main",
        paths=("tools/ref_tile/pre_route_gate.py", "tools/ref_tile/ref_tile.py"),
        what="OWN-QWEN/SLICE-E landed-parent ref_tile / pre_route_gate support: on main already; merged tree = main's"),
    "ea5b57e3bcc2758d66b52e44b0cb8e746bc0f479": dict(
        kind="relaxing", rule="literal-pin-no-m6", paths=("tools/ref_tile/ref_tile.py",),
        what="QK-SLICE: a literal pin plan with no M6 pin needed no M6 grant (qfd_xs_leaf_w130m5 stand-in); NOT kept by "
             "the ROOT4 merge -- main's check (io_tcl + m6_pin_grant required) stands"),
}
# ROOT-0040 name, kept for callers / tests: the relaxing entries
RELAXING_RULE_COMMITS = {c: e for c, e in RULE_COMMITS.items() if e.get("kind") == "relaxing"}
RULE_KINDS = ("relaxing", "neutral", "tightening")
TRAILER_RE = re.compile(r"^Gate-Rule:\s*(relaxing|neutral|tightening)\b(.*)$", re.M | re.I)


def parse_rule_trailer(message):
    """{"kind", "requires"?, "applies_to"?} from a commit message's Gate-Rule trailer, else None"""
    m = TRAILER_RE.search(message or "")
    if not m:
        return None
    out = dict(kind=m.group(1).lower(), rule="trailer", what=m.group(0).strip()[:200])
    for k, v in re.findall(r"([\w-]+)=(\S+)", m.group(2)):
        k = k.lower().replace("-", "_")
        if k == "requires":
            out["requires"] = v
        elif k == "applies_to":
            out["applies_to"] = tuple(x for x in v.split(",") if x)
        elif k == "rule":
            out["rule"] = v
    return out


def change_is_comment_only(rel, old, new):
    """True when two versions of a tool file differ only in comments / docstrings / blank lines / trailing spaces"""
    import ast
    if old == new:
        return True
    try:
        a, b = (x.decode() if isinstance(x, bytes) else x for x in (old, new))
    except UnicodeDecodeError:
        return False
    if rel.endswith(".py"):
        def norm(t):
            tree = ast.parse(t)
            for node in ast.walk(tree):
                body = getattr(node, "body", None)
                if isinstance(body, list) and body and isinstance(body[0], ast.Expr) \
                        and isinstance(getattr(body[0], "value", None), ast.Constant) and isinstance(body[0].value.value, str):
                    node.body = body[1:] or [ast.Pass()]
            return ast.dump(tree, include_attributes=False)
        try:
            return norm(a) == norm(b)
        except (SyntaxError, ValueError):
            return False
    if rel.endswith((".tcl", ".sdc", ".sh")):
        def lines(t):
            return [ln.rstrip() for ln in t.splitlines() if ln.strip() and not ln.lstrip().startswith("#")]
        return lines(a) == lines(b)
    if rel.endswith(".json"):
        try:
            return json.loads(a) == json.loads(b)
        except ValueError:
            return False
    return False


def tile_matches(applies_to, tile):
    if not applies_to:
        return True                        # no scope: applies to every tile
    names = [t for t in (tile or ()) if t]
    if not names:
        return True                        # unknown tile: assume it applies (strict)
    return any(str(n).startswith(p) for n in names for p in applies_to)


def _blob(repo, sha):
    p = subprocess.run(["git", "-C", str(repo), "cat-file", "blob", sha], capture_output=True, timeout=60)
    return None if p.returncode else p.stdout


def classify_commit(repo, commit, rel, pre, post, registry=None, cache=None):
    """{"commit", "kind" (relaxing|neutral|tightening|unclassified), "source" (registry|trailer|auto), ...}"""
    if registry is None:
        reg = {**{c: dict(e, kind=e.get("kind", "relaxing")) for c, e in RELAXING_RULE_COMMITS.items()}, **RULE_COMMITS}
    else:
        reg = registry
    if commit in reg and (not reg[commit].get("paths") or rel in reg[commit]["paths"]):
        # optional "paths": the entry classifies only those files of the commit (its other files fall through)
        return dict(reg[commit], commit=commit, source="registry")
    cache = {} if cache is None else cache
    if ("msg", commit) not in cache:
        p = subprocess.run(["git", "-C", str(repo), "log", "-1", "--format=%B", commit], capture_output=True, text=True,
                           timeout=60)
        cache[("msg", commit)] = p.stdout if not p.returncode else ""
    t = parse_rule_trailer(cache[("msg", commit)])
    if t:
        return dict(t, commit=commit, source="trailer")
    a, b = _blob(repo, pre), _blob(repo, post)
    if a is not None and b is not None:
        if change_is_comment_only(rel, a, b):
            return dict(kind="neutral", rule="comment-only", what="comments / docstrings only", commit=commit, source="auto")
        if rel in LINT_ONLY and lint_change_is_submit_only(a, b):
            return dict(kind="neutral", rule="submit-only-lint", what="submit-only lint constants", commit=commit,
                        source="auto")
    return dict(kind="unclassified", commit=commit, source="none",
                what="no RULE_COMMITS entry, no 'Gate-Rule:' trailer, not comment-only")


def _merge_is_clean(repo, rel, parents, result_blob, cache):
    """(ok, parent_blobs, base_blob): a two-parent merge whose rel is exactly git merge-file's conflict-free merge of
    the parents' blobs over their merge base's blob -- the merge adds nothing beyond its parents' commits."""
    if len(parents) != 2:
        return False, [], None
    def rp(rev):
        q = subprocess.run(["git", "-C", str(repo), "rev-parse", "--verify", "-q", f"{rev}:{rel}"], capture_output=True,
                           text=True, timeout=60)
        return q.stdout.strip() if not q.returncode else None
    mb = subprocess.run(["git", "-C", str(repo), "merge-base", *parents], capture_output=True, text=True, timeout=120)
    if mb.returncode:
        return False, [], None
    pb, base = [rp(x) for x in parents], rp(mb.stdout.split()[0])
    if None in pb or base is None:
        return False, pb, base
    datas = [_blob(repo, b) for b in (pb[0], base, pb[1])]
    if any(d is None for d in datas):
        return False, pb, base
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        fs = []
        for k, d in zip(("ours", "base", "theirs"), datas):
            f = Path(td) / k
            f.write_bytes(d)
            fs.append(str(f))
        q = subprocess.run(["git", "merge-file", "-p", "-q", *fs], capture_output=True, timeout=120)
    return (q.returncode == 0 and q.stdout == _blob(repo, result_blob)), pb, base


def _copy_of_main(repo, c, e, info, span, main):
    """main commit M (in span, on main) whose post blob equals c's post, when c is NOT on main and c's pre blob is the
    post of a main commit that is an ancestor of M (or the gate side); else None."""
    def on_main(x):
        return subprocess.run(["git", "-C", str(repo), "merge-base", "--is-ancestor", x, main], capture_output=True,
                              timeout=60).returncode == 0
    if not main or len(e["parents"]) != 1 or not e["pre"] or on_main(c):
        return None
    pre = e["pre"][0]
    for m in span:
        if m == c or info[m]["post"] != e["post"] or not on_main(m):
            continue
        for a, ea in info.items():
            if ea["post"] == pre and on_main(a) and subprocess.run(
                    ["git", "-C", str(repo), "merge-base", "--is-ancestor", a, m], capture_output=True,
                    timeout=60).returncode == 0:
                return m
    return None


def rule_span(repo, rel, old_blob, new_blob, heads, tile=None, registry=None, max_steps=64):
    """(ok, rows, why): classify every commit that changed rel between the gate's revision (the commits whose rel blob
    is old_blob) and the current one (commits whose rel blob is new_blob), all reachable from heads (origin/main plus the
    route commit).  ok when no commit is stricter for the tile: every row is relaxing / neutral, or a tightening outside
    the tile's scope, or a tightening whose "requires" the caller then judges.  rows newest first, each with "applies"
    (bool).  why: the first blocking commit, else None.
    ROOT-0330 10-18: commit-set walk (git rev-list NEW ^OLD -- rel), not a single blob chain, so a file changed on two
    branches and merged (kv_die.py 76f68cefa || 8a83ec822 -> bb834a0fb) is classified: every non-merge commit on either
    side is classified, and a merge that changed rel against EVERY parent must be clean (git merge-file of its parents
    over their merge base reproduces it byte-exactly), i.e. it adds nothing of its own."""
    if not old_blob or not new_blob:
        return False, [], "blob unknown"
    if old_blob == new_blob:
        return True, [], None
    heads = [h for h in heads if h]
    if not heads:
        return False, [], "no history head"
    p = subprocess.run(["git", "-C", str(repo), "log", "-m", "--format=C %H %P", "--raw", "--no-abbrev", "--no-renames",
                        *heads, "--", rel], capture_output=True, text=True, timeout=180)
    if p.returncode:
        return False, [], "git log failed"
    info, cur = {}, None            # commit -> dict(parents, pre=[blobs], post)
    for ln in p.stdout.splitlines():
        if ln.startswith("C "):
            f = ln[2:].split()
            cur = f[0] if f else None
            if cur:
                info.setdefault(cur, dict(parents=f[1:], pre=[], post=None))
        elif ln.startswith(":") and cur:
            f = ln.split()
            if len(f) >= 5:
                info[cur]["pre"].append(f[2])
                info[cur]["post"] = f[3]
    olds = [c for c, e in info.items() if e["post"] == old_blob]
    news = [c for c, e in info.items() if e["post"] == new_blob]
    gate_ref = f"{rel}: gate blob {old_blob[:9]} is not an ancestor revision of {new_blob[:9]} on main"
    if not olds or not news:
        return False, [], gate_ref
    if not any(subprocess.run(["git", "-C", str(repo), "merge-base", "--is-ancestor", o, n], capture_output=True,
                              timeout=60).returncode == 0 for o in olds for n in news):
        return False, [], gate_ref
    q = subprocess.run(["git", "-C", str(repo), "rev-list", "--full-history", *news, *[f"^{o}" for o in olds], "--", rel],
                       capture_output=True, text=True, timeout=180)
    if q.returncode:
        return False, [], "git rev-list failed"
    span = [c for c in q.stdout.split() if c in info]
    rows, cache = [], {}
    for c in span:
        e = info[c]
        if len(e["parents"]) > 1:
            if len(e["pre"]) < len(e["parents"]):
                continue                 # rel equals one parent's: the merge adds nothing to that parent's commits
            clean, _, _ = _merge_is_clean(repo, rel, e["parents"], e["post"], cache)
            if not clean:
                rows.append(dict(kind="unclassified", commit=c, source="none", applies=False,
                                 what="merge with its own changes to the file (not a clean merge of its parents)"))
                return False, rows, (f"{rel}: merge {c[:9]} is not a clean merge of its parents (classify it with a "
                                     f"helper_overlay.RULE_COMMITS entry)")
            continue                     # clean merges are not listed: their parents' commits are
        if len(rows) >= max_steps:
            return False, rows, f"{rel}: blob chain longer than {max_steps} commits"
        cp = _copy_of_main(repo, c, e, info, span, heads[0])
        if cp:
            # ROOT-0615 10-18: a branch commit that took the file from main ("git checkout origin/main -- tools/..."):
            # its pre and post blobs are both revisions on main, and main's own commits between them are in this span
            # and classified here; the copy adds nothing of its own
            rows.append(dict(kind="neutral", rule="copy-of-main", commit=c, source="auto", applies=False,
                             what=f"blob {e['post'][:9]} copied from main {cp[:9]}"))
            continue
        r = classify_commit(repo, c, rel, e["pre"][0] if e["pre"] else None, e["post"], registry, cache)
        r["applies"] = r["kind"] == "tightening" and tile_matches(r.get("applies_to"), tile)
        rows.append(r)
        if r["kind"] == "unclassified":
            return False, rows, (f"{rel}: commit {c[:9]} is not a relaxing-only rule change (unclassified: add a "
                                 f"'Gate-Rule: relaxing|neutral|tightening' trailer or a helper_overlay.RULE_COMMITS entry)")
        if r["applies"] and not r.get("requires"):
            return False, rows, f"{rel}: commit {c[:9]} TIGHTENS rule {r.get('rule')} for this tile ({r.get('what', '')[:120]})"
    return True, rows, None


def relaxing_only_span(repo, rel, old_blob, new_blob, heads, allow=None, max_steps=64):
    """ROOT-0040 interface: (ok, commits) -- rule_span with no tile scope; commits newest first, the blocking one last."""
    reg = None if allow is None else {c: dict(e, kind=e.get("kind", "relaxing")) for c, e in allow.items()}
    ok, rows, _ = rule_span(repo, rel, old_blob, new_blob, heads, registry=reg, max_steps=max_steps)
    return ok, [r["commit"] for r in rows]


# SUBMIT-ONLY lint names (ROOT 2026-10-16, coordinator): constants of tools/textbook_lint.py read only by the submit-time
# CLOSED-STANDS lint, never by the pre-route gate.  A textbook_lint change confined to them (and to comments / docstrings)
# leaves every gate verdict valid.
SUBMIT_ONLY_LINT_NAMES = ("CLOSED_STANDS_KINDS", "CLOSED_STANDS_INSTEAD", "DIE_WINDOW_CUT_MIN")


def lint_change_is_submit_only(old, new, names=SUBMIT_ONLY_LINT_NAMES):
    """True when two textbook_lint.py versions differ only in comments/docstrings or in assignments to `names`."""
    import ast

    def norm(data):
        tree = ast.parse(data.decode() if isinstance(data, bytes) else data)
        body = []
        for node in tree.body:
            if isinstance(node, ast.Expr) and isinstance(getattr(node, "value", None), ast.Constant) \
                    and isinstance(node.value.value, str):
                continue                                                   # module / stray docstrings
            if isinstance(node, (ast.Assign, ast.AnnAssign)):
                targets = node.targets if isinstance(node, ast.Assign) else [node.target]
                if all(isinstance(t, ast.Name) and t.id in names for t in targets):
                    continue
            body.append(ast.dump(node, include_attributes=False))
        return body
    try:
        return norm(old) == norm(new)
    except (SyntaxError, ValueError, UnicodeDecodeError):
        return False


def _main_blobs(repo, head, rel):
    p = subprocess.run(["git", "-C", str(repo), "log", "--format=", "--raw", "--no-abbrev", "--no-renames", head, "--", rel],
                       capture_output=True, text=True, timeout=180)
    if p.returncode:
        return set()
    return {ln.split()[3] for ln in p.stdout.splitlines() if ln.startswith(":") and len(ln.split()) >= 5}


def compare_plans_sanctioned(frozen, effective, repo, head=None):
    """compare_plans, except that drift on FLEET_RUN paths is accepted when the effective blob is origin/main's and the
    frozen blob is an earlier main revision of that path.  Returns (ok, why, sanctioned_rows)."""
    ok, why = compare_plans(frozen, effective)
    if ok or why.startswith(("missing", "frozen helper plan digest", "malformed")):
        return ok, why, []
    old = {f["path"]: f for f in content_rows(frozen["files"])}
    new = {f["path"]: f for f in content_rows(effective["files"])}
    head = head or effective.get("origin_main") or main_head(repo)
    sanctioned = []
    for rel in sorted(set(old) | set(new)):
        o, n = old.get(rel), new.get(rel)
        if o == n:
            continue
        if rel in LINT_ONLY and o is not None and n is not None and head and o["mode"] == n["mode"]:
            hist = _main_blobs(repo, head, rel)
            if o["git_blob"] in hist and n["git_blob"] in hist:
                sanctioned.append(dict(path=rel, kind="lint_frozen", frozen_git_blob=o["git_blob"],
                                       frozen_sha256=o["sha256"], current_git_blob=n["git_blob"],
                                       current_sha256=n["sha256"], origin_main=head))
                continue
        if rel not in FLEET_RUN + PUBLISH_ONLY or o is None or n is None or not head:
            return False, f"effective route helper drift: {rel} (frozen {o}, current {n})", []
        p = subprocess.run(["git", "-C", str(repo), "rev-parse", f"{head}:{rel}"], capture_output=True, text=True, timeout=60)
        tip = p.stdout.strip() if not p.returncode else None
        if n["git_blob"] != tip or o["mode"] != n["mode"] or o["git_blob"] not in _main_blobs(repo, head, rel):
            return False, (f"effective route helper drift: {rel} (frozen {o}, current {n}; fleet-run path, but current is "
                           f"not origin/main {str(tip)[:9]} or frozen is not an earlier main revision)"), []
        sanctioned.append(dict(path=rel, kind="publish" if rel in PUBLISH_ONLY else "fleet_run",
                               frozen_git_blob=o["git_blob"], frozen_sha256=o["sha256"],
                               current_git_blob=n["git_blob"], current_sha256=n["sha256"], origin_main=head))
    return True, "helper bytes match the frozen plan except sanctioned fleet-run / lint-only paths", sanctioned


def frozen_rows(plan):
    """Validate the recorded plan without consulting today's helper resolution."""
    if not isinstance(plan, dict) or plan.get("schema") != SCHEMA:
        raise ValueError("missing frozen effective helper plan")
    try:
        rows = content_rows(plan["files"])
        if not rows or digest(rows) != plan.get("content_sha256"):
            raise ValueError("frozen helper plan digest mismatch")
        paths, names = set(), set()
        for row in rows:
            path = Path(row["path"])
            if path.is_absolute() or ".." in path.parts or str(path) != row["path"]:
                raise ValueError("unsafe frozen helper path")
            if row["path"] in paths or path.name in names:
                raise ValueError("duplicate frozen helper path or transport basename")
            paths.add(row["path"])
            names.add(path.name)
            if not re.fullmatch(r"[0-9a-f]{64}", row["sha256"]) or not re.fullmatch(r"[0-9a-f]{40}", row["git_blob"]):
                raise ValueError("invalid frozen helper hash")
            if type(row["mode"]) is not int or not 0 <= row["mode"] <= 0o777:
                raise ValueError("invalid frozen helper mode")
        return rows
    except (KeyError, TypeError, AttributeError) as ex:
        raise ValueError("malformed frozen helper plan") from ex


def committed_frozen_payloads(repo, plan, only=None):
    """Recover only bytes committed at each original path in the recorded tree.

    Git records the executable bit; the plan records the full transported POSIX
    mode (e.g. 0664). Both are checked independently of current main or daemon.
    Daemon-only/uncommitted content cannot enter this recovery path.
    """
    rows = frozen_rows(plan)
    head = plan.get("origin_main")
    if not isinstance(head, str) or not re.fullmatch(r"[0-9a-f]{40}", head):
        raise ValueError("frozen helper origin must be an explicit committed tree")
    kind = subprocess.run(["git", "-C", str(repo), "cat-file", "-t", head], capture_output=True, timeout=60)
    if kind.returncode or kind.stdout.strip() != b"commit":
        raise ValueError("frozen helper committed tree unavailable")
    lineage = subprocess.run(["git", "-C", str(repo), "merge-base", "--is-ancestor", head,
                              "refs/remotes/origin/main"], capture_output=True, timeout=60)
    if lineage.returncode:
        raise ValueError("frozen helper origin is not retained main history")
    tree = subprocess.run(["git", "-C", str(repo), "ls-tree", "-rz", head], capture_output=True, timeout=60)
    if tree.returncode:
        raise ValueError("frozen helper committed tree unavailable")
    entries = {}
    for item in tree.stdout.split(b"\0"):
        if item:
            meta, path = item.split(b"\t", 1)
            entries[path.decode()] = meta.decode().split()
    payloads = {}
    for row in rows:
        if only is not None and row["path"] not in only:
            continue
        mode, kind, blob = entries.get(row["path"], (None, None, None))
        if kind != "blob" or mode not in ("100644", "100755") or blob != row["git_blob"]:
            raise ValueError(f"frozen helper committed tree mismatch: {row['path']}")
        if bool(row["mode"] & 0o111) != (mode == "100755"):
            raise ValueError(f"frozen helper committed executable mode mismatch: {row['path']}")
        data = subprocess.run(["git", "-C", str(repo), "cat-file", "blob", blob], capture_output=True, timeout=60)
        if data.returncode or blob_id(data.stdout) != blob or hashlib.sha256(data.stdout).hexdigest() != row["sha256"]:
            raise ValueError(f"frozen helper committed bytes missing or tampered: {row['path']}")
        payloads[row["path"]] = data.stdout
    return payloads


def store_payloads(store, plan, payloads):
    """Keep every frozen helper byte-string in a content-addressed store (one file per sha256).

    The store lives in the loop's state directory (~/.local/state/closure_loop/frozen_helpers), which no run-root,
    scratch or worktree cleanup touches; run directories (where helpers execute) are disposable copies of it.
    """
    store = Path(store)
    store.mkdir(parents=True, exist_ok=True)
    for row in frozen_rows(plan):
        data = payloads[row["path"]]
        if hashlib.sha256(data).hexdigest() != row["sha256"] or blob_id(data) != row["git_blob"]:
            raise ValueError(f"frozen helper payload differs from plan: {row['path']}")
        dest = store / row["sha256"]
        if dest.exists() and hashlib.sha256(dest.read_bytes()).hexdigest() == row["sha256"]:
            continue
        # per-thread temp name: the daemon steps jobs in parallel threads of ONE process, and two jobs freezing the same
        # helper blob raced on a pid-only name (FileNotFoundError at os.replace, qfd_xcst_s_m5 17:12 10-15)
        tmp = store / f".{row['sha256']}.{os.getpid()}.{threading.get_ident()}.tmp"
        tmp.write_bytes(data)
        os.replace(tmp, dest)


def stored_frozen_payloads(store, plan, only=None):
    """Recover the exact frozen bytes from the content store; every file re-verified against the plan."""
    payloads = {}
    for row in frozen_rows(plan):
        if only is not None and row["path"] not in only:
            continue
        try:
            data = (Path(store) / row["sha256"]).read_bytes()
        except OSError as ex:
            raise ValueError(f"frozen helper not in content store: {row['path']}") from ex
        if hashlib.sha256(data).hexdigest() != row["sha256"] or blob_id(data) != row["git_blob"]:
            raise ValueError(f"frozen helper content store bytes tampered: {row['path']}")
        payloads[row["path"]] = data
    return payloads


UNCOMMITTED_RESOLUTIONS = ("daemon_only", "not_on_main", "no_git")
# rows whose bytes come from the content store on a reinstall: uncommitted at freeze, or a PUBLISH_ONLY row refreshed
# to a later origin/main blob on an installed run (closure_loop._publish_refresh; the plan keeps its original origin tree)
STORE_RESOLUTIONS = UNCOMMITTED_RESOLUTIONS + ("publish_refresh",)


def recover_frozen_payloads(repo, store, plan):
    """Exact frozen bytes for a reinstall.  Returns (payloads, source).

    Rows frozen from committed main (resolution same/stale) come ONLY from the plan's committed origin tree, so a
    forged origin or a tree mismatch still refuses.  Rows that were legally uncommitted when frozen (daemon_only /
    not_on_main / no_git) come from the content-addressed store.  Every byte is verified (sha256 + git blob id)
    against the job's frozen plan, so a reinstall is identical to the original install or it does not happen.
    """
    rows = frozen_rows(plan)
    resolution = {f.get("path"): f.get("resolution") for f in plan.get("files", []) if isinstance(f, dict)}
    loose = {r["path"] for r in rows if resolution.get(r["path"]) in STORE_RESOLUTIONS}
    if not loose:
        return committed_frozen_payloads(repo, plan), "committed_origin"
    if store is None:
        raise ValueError("uncommitted frozen helpers need the content store")
    committed = {r["path"] for r in rows} - loose
    payloads = committed_frozen_payloads(repo, plan, only=committed) if committed else {}
    payloads.update(stored_frozen_payloads(store, plan, only=loose))
    return payloads, ("committed_origin+content_store" if committed else "content_store")


def verify_installed_plan(directory, plan):
    """Read-only verification of the original flattened route helper directory."""
    rows = frozen_rows(plan)
    directory = Path(directory)
    sidecar = directory / "helper_overlay_plan.json"
    if not sidecar.exists():
        if any((directory / Path(row["path"]).name).exists() for row in rows):
            raise ValueError("original helper files exist but frozen sidecar is missing")
        return {"status": "not_installed"}
    if not stat.S_ISREG(sidecar.lstat().st_mode):
        raise ValueError("original helper sidecar is not a regular file")
    if json.loads(sidecar.read_text()) != plan:
        raise ValueError("original helper sidecar differs from job frozen plan")
    for row in rows:
        path = directory / Path(row["path"]).name
        try:
            info = path.lstat()
            if not stat.S_ISREG(info.st_mode):
                raise ValueError(f"original helper is not a regular file: {row['path']}")
            if stat.S_IMODE(info.st_mode) != row["mode"]:
                raise ValueError(f"original helper mode mismatch: {row['path']}")
            data = path.read_bytes()
        except OSError as ex:
            raise ValueError(f"original helper missing: {row['path']}") from ex
        if hashlib.sha256(data).hexdigest() != row["sha256"] or blob_id(data) != row["git_blob"]:
            raise ValueError(f"original helper bytes mismatch: {row['path']}")
    return {"status": "verified_original", "origin_main": plan["origin_main"],
            "content_sha256": plan["content_sha256"], "files": len(rows)}


def publish_only_pair(a, b):
    """True when plans a and b (both self-consistent) differ ONLY in PUBLISH_ONLY rows of the same mode: one is a
    publish refresh of the other (closure_loop._publish_refresh)."""
    try:
        ra = {r["path"]: r for r in frozen_rows(a)}
        rb = {r["path"]: r for r in frozen_rows(b)}
    except ValueError:
        return False
    if set(ra) != set(rb) or a.get("origin_main") != b.get("origin_main"):
        return False
    diff = [p for p in ra if ra[p] != rb[p]]
    return bool(diff) and all(p in PUBLISH_ONLY and ra[p]["mode"] == rb[p]["mode"] for p in diff)


def installed_plan_receipt(directory, plan):
    """verify_installed_plan, except that an installed sidecar which is a PUBLISH_ONLY refresh of the job's plan (or the
    reverse) is verified on its own rows and returned as receipt["installed_plan"] for the caller to sanction and adopt.

    QXPQ-UNSTICK 2026-10-19: a publish refresh rewrites cl/ (view_export.py + sidecar) on the host BEFORE the daemon saves
    the job; the daemon restarted at 06:25 between the two, so dsrom-qelem-qs5f-ob2-tc-hm25-cl-4b2f835cb kept the old plan
    while its routed run held the refreshed one, and every later step failed 'sidecar differs' -> NEEDS_HUMAN."""
    try:
        return verify_installed_plan(directory, plan)
    except ValueError as ex:
        if "sidecar differs" not in str(ex):
            raise
        sidecar = Path(directory) / "helper_overlay_plan.json"
        try:
            installed = json.loads(sidecar.read_text())
        except (OSError, ValueError):
            raise ex
        if not publish_only_pair(plan, installed):
            raise
        receipt = verify_installed_plan(directory, installed)
        return dict(receipt, installed_plan=installed, sidecar_mismatch="publish_only")


def verify_staged_helpers(directory, plan, paths):
    """Verify the helpers actually shipped into an immutable gate source tree."""
    rows = {row["path"]: row for row in frozen_rows(plan)}
    if not paths or len(set(paths)) != len(paths) or any(path not in rows for path in paths):
        raise ValueError("gate executed helper paths missing or outside frozen plan")
    for rel in paths:
        row = rows[rel]
        path = Path(directory) / rel
        try:
            info = path.lstat()
            if not stat.S_ISREG(info.st_mode) or stat.S_IMODE(info.st_mode) != row["mode"]:
                raise ValueError(f"original gate helper kind/mode mismatch: {rel}")
            data = path.read_bytes()
        except OSError as ex:
            raise ValueError(f"original gate helper missing: {rel}") from ex
        if hashlib.sha256(data).hexdigest() != row["sha256"] or blob_id(data) != row["git_blob"]:
            raise ValueError(f"original gate helper bytes mismatch: {rel}")
    return {"status": "verified_original_gate", "origin_main": plan["origin_main"],
            "content_sha256": plan["content_sha256"], "executed_paths": sorted(paths)}
