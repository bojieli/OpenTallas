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
              "../../physical/common_flow/native_pg_binding.tcl",
              "../../physical/common_flow/native_pg_bootstrap.tcl")

HELPERS = ("m6_stub_config.py", "eco_recovery.py", "path_summary.py", "macro_views.py", "ck_insertion.py", "hold_eco.sh", "hold_eco.tcl", "hold_eco_corner.tcl",
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
