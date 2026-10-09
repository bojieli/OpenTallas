#!/usr/bin/env python3
"""Unified candidate composition and cost/evidence ledger for the three targets (2026-10-07).

Targets: Qwen3-8B ROM (8K, TP4), DeepSeek-V4.1 ROM S81 array (1M) and the HBM accelerator (DeepSeek 1M).
Every ledger line carries
  status  measured | priced-candidate | gated-unknown
  effect  its cost on the single-user token (cycles at 1.2 GHz or us), or None when gated
  source  the committed file (+ JSON pointer) and the commit that last touched it
and each target exposes named compositions that sum ONLY the lines they declare.  Gated lines never enter a sum
(they are never zero-filled): a composition that depends on one says so in `gated_by`.

A numerical component PASS is not physical adoption; none of the compositions below is a physically closed product
rate.  The published headline records (results/arch/three_machine_compose/compose.json, the HBM r23 closure headline,
the DS closure-cost ledger) are read, not rewritten; this tool reconciles them on one basis.

    python3 tools/unified_composition.py           # write results/arch/unified_composition_20261007/ledger.json
    python3 tools/unified_composition.py --check   # fail if the committed ledger is stale

Accessors (import tools/unified_composition as U):
    U.ledger()                     the whole record (dict)
    U.target('qwen_rom')           one target: lines, compositions, gates
    U.composition('hbm_ds', 'unified_candidate')
    U.line('ds_rom', 'bf_half_rate_doubling')
    U.lines(status='gated-unknown')
"""
from __future__ import annotations

import argparse
import functools
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results/arch/unified_composition_20261007"
CLK = 1.2e9
STATUSES = ("measured", "priced-candidate", "gated-unknown")

# ---- committed inputs ---------------------------------------------------------------------------------------------
CMP = "results/arch/three_machine_compose/compose.json"
Q_RELAY = "results/rtl/qwen_rom_die_r17_20261005/relays_r21/relay_token_cost.json"
Q_DSPARK = "results/rtl/qwen_rom_die_r17_20261005/relays_r21/dspark_verdict_relays.json"
Q_DSPARK_RE = "results/arch/unified_composition_20261007/qwen_dspark/dspark_ctrlshift_candidate.json"
Q_CLOSURE = "results/rtl/qwen_rom_closed_20261006/closure.json"
Q_FWD = "results/uarch/qwen_link_forwarded_graph_20261007/graph_prebuild_model.json"
Q_FWD_VAL = "results/uarch/qwen_link_forwarded_graph_20261007/validation.json"
Q_CTRL = "results/rtl/qwen_ctrl_shift_20261007/model.json"
Q_CTRL_Q = "results/rtl/qwen_ctrl_shift_20261007/qualification.json"
Q_CTRL_P = "results/rtl/qwen_ctrl_shift_20261007/runtime_protection_gate.json"
Q_VM_ME = "results/uarch/qwen_rom_vm_me_service_20261007/model.json"
Q_VM_SU = "results/uarch/qwen_rom_vm_su_service_20261007/model.json"
Q_VM_REC = "results/uarch/qwen_rom_vm_recovery_20261007/disposition.json"
Q_SPINE_P = "results/rtl/qwen_spine_lane_20261007/mutable_protection_blocker.json"
Q_LINKFR = "results/rtl/qwen_contracts_20261007/link_credit_rtt/bench_gate/result.json"   # full-rate hub gate
Q_LINKFR_P = "results/rtl/qwen_contracts_20261007/link_credit_rtt/pricing.json"            # area + cycle pricing
Q_KV_DECISION = "results/rtl/qwen_contracts_20261007/protected_kv_transport/decision.json"
Q_VM_CHK = "results/rtl/qwen_contracts_20261007/vm_contract_checks/summary.json"            # 9-package re-check
Q_STATION = "results/uarch/qwen_station_fullwidth_r22_20261007/model_dual_fault_r1.json"
DS_LEDGER = "results/rtl/dsrom_closure_cost_ledger_20261007/ledger.json"
DS_LINKS = "results/rtl/dsrom_1m_allmeasured_20261004/links_full_fec.json"
DS_RACK = "results/arch/dsrom_s81_rack_20261006/rack.json"
DS_MAP = "results/uarch/dsrom_s81_mixed1792_mapping_20261007"   # hash-bound complete mappings, 2d811aafb
DS_GEOM = "results/uarch/dsrom_s81_mixed_geometry_20261007/model.json"   # legal mixed geometry sizing, 77ffa0428
DS_RET = "results/uarch/dsrom_spine_return_station_20261007/sensitivity.json"
DS_BFROOT = "physical/s81_bf_root_phase/model.json"
DS_BFFAIL = "results/rtl/s81_bf_root_phase_hierarchy_fix_20261007"
DS_HBMB = "results/physical/hbm_die_abstracts_20261006/integration/consumer_binding_20261006.json"
H_MATCHED = "results/rtl/dshbm_matched_reference_20261005/composition.json"
H_LEDGER = "results/rtl/hbm_accel_die_views_20261006/closure_cost_ledger.md"
H_R23 = "results/rtl/hbm_accel_die_views_20261006/headline_with_closure_r23.json"
H_TC = "results/uarch/ha2_truecredit_20261007/model_measured_endpoint.json"
H_SRAM = "results/rtl/hbm_collective_full_20261007/storage_model.json"
H_CLKIN = "results/uarch/hbm_die_clock_inputs_20261007/model.json"
H_CLKENT = "results/uarch/hbm_collective_clock_entry_20261007/model.json"
FULLSYS = "results/rtl/fullsys_recheck_20261007/status.json"
# Since the merge of origin/main 54ff3c0af into this branch, every record below is in the tree; values are READ from it
# and commits come from git history (commit_of).  Branch-only items are named as such.
_J = lambda rel: json.loads((Path(__file__).resolve().parents[1] / rel).read_text())
# CDC design v1 (on main at 8b7f55b31; originally b49366616): packet-SRAM receive queue / protected CDC drain at II=3
H_CDC = "results/rtl/hbm_collective_cdc_design_20261007/options.json"
H_CDC_COMMIT = None
# II1 refill (B prime): on main at 9ead91a15
H_REFILL = "results/rtl/hbm_collective_cdc_20261007/refill_model.json"
H_REFILL_PASS = "results/rtl/hbm_collective_cdc_20261007/final_pass/record.json"
H_REFILL_COMMIT = None
# CDC design v2 recommending the refill (on main at 092c84e1d; originally 2ae0d7d33)
H_CDC2 = "results/rtl/hbm_collective_cdc_design_20261007/comparison_refill.json"
H_CDC2_COMMIT = None
# SM -> SU result-contract audit (on main at 10989fac4; originally 8c8bb2af2)
H_SMSU = "results/rtl/hbm_sm_su_result_contract_20261007/contract.json"
H_SMSU_COMMIT = None
_s = _J(H_SMSU)["summary"]
H_SMSU_V = dict(published=_s["published_cycles"], native=_s["native_cycles"], store_forward=_s["store_forward_floor_cycles"])
_o = _J(H_CDC)
_a = _o["options"]["A_credit_bound"]
H_CDC_V = dict(ii3_AR_us=_a["cost_serialisation"]["AR_us"], ii3_MTP_us=_a["cost_serialisation"]["MTP_step_us"],
               ii3_AR_pct=_a["cost_serialisation"]["AR_pct"], ii3_MTP_pct=_a["cost_serialisation"]["MTP_step_pct"],
               ser_AR=int(_o["workload"]["matched_P1"]["serialisation_cycles"]), ser_MTP=int(_o["workload"]["matched_P6"]["serialisation_cycles"]),
               lat_us=_a["cost_latency"]["AR_us"], lat_cycles=_a["cost_latency"]["AR_cycles"],
               rot_area_um2=_o["options"]["B_rotated_II1"]["area_um2_added"])
BF_BRANCH = "origin/claude/dsrom-bf-double-20261007"
BF_BRANCH_COMMIT = "a30252b68"   # ledger.md bf_merge_ksplit row; released binding 332983233; both on that branch only
# BF option records (on main at ece40d827)
BFA_FILE = "results/rtl/dsrom_bf_double_20261007/recovery_provenance.json"
BFA_COMMIT = None
_bf = _J(BFA_FILE)
BFA = dict(AR=_bf["options"]["A_f198_2048"]["AR"], MTP=_bf["options"]["A_f198_2048"]["MTP"],
           base_AR=_bf["options"]["base_f198_2050"]["AR"], base_MTP=_bf["options"]["base_f198_2050"]["MTP"],
           stages=_bf["options"]["A_f198_2048"]["stages"], regions=_bf["regions"]["A_f198_2048"]["region_runs"],
           base_regions=_bf["regions"]["base_f198_2050"]["region_runs"])
# option B: numbers in the same main record; its "DS ADOPT" label commit 505a9b484 is on branch
# origin/codex/restore-bf-pairs-20261007 only (verified not an ancestor of origin/main 54ff3c0af)
BFB_COMMIT = None
GEO_B = None
BFB = dict(AR=_bf["options"]["B_mixed_2304"]["AR"], MTP=_bf["options"]["B_mixed_2304"]["MTP"], base_AR=1603.3, base_MTP=4717.7,
           stages=_bf["options"]["B_mixed_2304"]["stages"], pairs=2304, layer_dies=340, regions=_bf["regions"]["B_mixed_2304"]["region_runs"],
           label="DS ADOPT bf_merge_ksplit on the mixed-slot S81 die: AR 1,603.3 -> 1,754.3 (+9.42 %), MTP 4,717.7 -> 5,098.3 (+8.07 %), MEASURED full field (commit 505a9b484, branch origin/codex/restore-bf-pairs-20261007 only)",
           physical=_bf["physical_status"], wire=_bf["wire_status"])
# S81 full-shape PQ partition v2 (Claude design, branch claude/s81-pq-fullshape-design-v2-20261007 @ 9a8c86255 ONLY; main
# carries the earlier version of the same record at 738ddfbc2 with +15 cycles / 0.47 %).  Branch values pinned here.
FP_FILE = "results/uarch/dsrom_s81_field_phases_1792_20261007/composition.json"   # s81-fieldphase, main abc13767e
FP = _J(FP_FILE)
PQ_FILE = "results/uarch/dsrom_s81_pq_fullshape_design_20261007/current_main/comparison_current_main.json"
PQ_ROOT = "results/uarch/dsrom_s81_pq_fullshape_design_20261007/current_main/root_contract/root_contract.json"
PQ_COMMIT = "9a8c86255 (branch origin/claude/s81-pq-fullshape-design-v2-20261007 only; main 738ddfbc2 has the earlier +15 / 0.47 % version)"
PQ = dict(cycles_per_phase=18, ar_loss_frac=0.00564, roots_mm2_per_die=3.0, core_mm2=0.32, rwb_mm2=0.40,
          design_cam_cycles=4, design_station_cycles=2, root_row_um=164.16)
# Native PQ root CAM (on main at 4251eb216): MEASURED latency deltas incl. publication; protection storage sizing
PQ_CAM_REC = "results/rtl/s81_pq_root_cam_20261007/record.json"
PQ_CAM_MODEL = "results/uarch/s81_pq_root_cam_20261007/model.json"
_pc = _J(PQ_CAM_REC)
PQ_CAM = dict(isolated=_pc["measured_delta_cycles"]["complete"], two_leaf=_pc["measured_delta_cycles"]["two_leaf"],
              eight_leaf=_pc["measured_delta_cycles"]["eight_leaf"], exact_roots=_pc["exact_roots"],
              bits_per_root=_J(PQ_CAM_MODEL)["incremental_state_bits"]["total_per_root"],
              bits_total=_J(PQ_CAM_MODEL)["incremental_state_bits"]["total_128_roots"])

def load(rel):
    return json.loads((ROOT / rel).read_text())


@functools.lru_cache(maxsize=None)
def commit_of(rel):
    """Last commit that touched `rel` (repository history, not the working tree)."""
    try:
        out = subprocess.check_output(["git", "log", "-1", "--format=%h", "--", rel], cwd=ROOT, text=True,
                                      stderr=subprocess.DEVNULL).strip()
    except (subprocess.CalledProcessError, OSError):
        out = ""
    return out or _ledger_commit(rel) or "uncommitted (this delivery)"


@functools.lru_cache(maxsize=1)
def _ledger_commits():
    """file -> commit from the committed ledger, used when git history is unavailable (e.g. a `git archive` export)."""
    try:
        rec = json.loads((OUT / "ledger.json").read_text())
    except (OSError, ValueError):
        return {}
    found = {}

    def walk(x):
        if isinstance(x, dict):
            if "file" in x and "commit" in x and isinstance(x["file"], str):
                found.setdefault(x["file"], x["commit"])
            for v in x.values():
                walk(v)
        elif isinstance(x, list):
            for v in x:
                walk(v)
    walk(rec)
    return found


def _ledger_commit(rel):
    return _ledger_commits().get(rel)


def src(rel, pointer=None, commit=None):
    return dict(file=rel, pointer=pointer, commit=commit or commit_of(rel))


def L(id, item, status, effect, source, note, role):
    """One ledger line.  effect: dict(unit='cycles'|'us', AR=..., MTP_step=...) or None (gated).
    role: base | published | candidate | conditional | alternative | gate | info."""
    assert status in STATUSES, status
    assert (effect is None) == (status == "gated-unknown") or role == "info", (id, status, effect)
    return dict(id=id, item=item, status=status, effect=effect, role=role,
                source=source if isinstance(source, list) else [source], note=note)


def tok_s_cycles(c):
    return round(CLK / c, 1)


def tok_s_us(us, tau=1.0):
    return round(tau * 1e6 / us, 1)


# ===================================================================================================== Qwen ROM 8K
def _link_credit_line(fwd):
    """Gate link_credit_rtt.  Before the full-rate hub (claude/qwen-contracts-20261007) this was gated-unknown: 4 link
    credits against the measured 117/119-cycle credit round trip.  The successor sizes credits to the round trip; the
    exact gate measures the rate, and the pricing record carries the routed area (or the analytic flop estimate while
    the routes are pending)."""
    g, pr = load(Q_LINKFR), load(Q_LINKFR_P)
    by = {(c["case"], c["sim"]): c for c in g["cases"]}
    pos = [by[("pos_h54_cr128", "verilator")]["epochs"][0], by[("pos_h55_cr128", "verilator")]["epochs"][0]]
    cr4 = by[("sweep_h54_cr4", "verilator")]["epochs"][0]
    assert g["pass_all"]
    return L("link_credit_rtt", "Link credit capacity vs the forwarded-path transport round trip", "priced-candidate",
             dict(unit="cycles", AR=pr["token_cycles_added"]), [src(Q_LINKFR, "cases"), src(Q_LINKFR_P), src(Q_FWD, "paths[].transport_credit_roundtrip_cycles")],
             "full-rate hub successor ot_qwen_die_hub_fr: CR=%d link credits >= the measured credit round trip %s cycles "
             "(54/55 stations); exact gate (Verilator + Icarus): rate %.3f / %.3f words a cycle, 0 credit stalls, "
             "%d checks a case, 4 negatives end in the named native fault; the predecessor's 4-credit window measures "
             "%.3f (credit-starved). Token: +%d cycles (same registered stations; the %d-sector-a-layer posted KV-new "
             "write-back serialises at 1 word a cycle, off the token path: measured STREAM4 stall_drain = stall_retire = 0). "
             "Area: %s. Physical: %s"
             % (pr["credits"], [p["credit_rtt_a"] for p in pos], pos[0]["rate_milli_a"] / 1000, pos[1]["rate_milli_a"] / 1000,
                4 * by[("pos_h54_cr128", "verilator")]["params"]["N"], cr4["rate_milli_a"] / 1000, pr["token_cycles_added"],
                pr["kv_new_sectors_per_layer"], pr["area"]["summary"], pr["physical"]["summary"]), "candidate")


def _protected_kv_line():
    """Gate protected_kv_transport: owner decision 2026-10-06 (not shipped), recorded with its evidence."""
    d = load(Q_KV_DECISION)
    return L("protected_kv_transport", "Protected KV transport (HBM->die landing)", "measured",
             dict(unit="cycles", AR=0), [src(Q_KV_DECISION), src(Q_CLOSURE, "kv_path.protected_full_width_transport"),
                                        src("results/rtl/qwen_plain_ar_stream4_P8191_20261005/terminal.json")],
             d["ledger_note"], "info")


def qwen():
    q = load(CMP)["qwen_rom"]
    lv = q["levers"]
    rel = load(Q_RELAY)
    ctrl, ctrlq = load(Q_CTRL), load(Q_CTRL_Q)
    fwd, fwdv = load(Q_FWD), load(Q_FWD_VAL)
    me = load(Q_VM_ME)
    vmc = load(Q_VM_CHK)
    rq = vmc["service_requirement"]["me_operation"]
    vm_chk_note = ("Contract re-check 2026-10-07 (qwen-contracts, %s): %d/%d component packages reproduce, incl. the known "
                   "publication-storage coverage failures; demand per ME operation: %d seats on each of %d consecutive edges "
                   "(%d unique scalars, fanout %d); no VM organisation serving it exists in RTL, so no token cost is composable. "
                   "Protected bank element routed for measurement: qfd_vm_bank_checked (loop)"
                   % (vmc["source_commit"][:9], sum(p["rc"] == 0 for p in vmc["packages"]), len(vmc["packages"]),
                      rq["seats_per_read_edge"], rq["consecutive_read_cycles"], rq["unique_scalars_per_edge"], rq["fanout"]))
    lines = [
        L("stream4_token", "Measured STREAM4 full token at P8191 (36 layers + head, 4 ranks, all 576 MiB FP8 KV landed)",
          "measured", dict(unit="cycles", AR=q["token_cycles_measured"]),
          src("results/rtl/qwen_plain_ar_stream4_P8191_20261005/terminal.json"),
          "RTL token; KV transport unprotected (see no-ECC inventory)", "base"),
        L("core_context", "Decode core r5_f2ba in die context", "measured", dict(unit="cycles", AR=lv["core_context"]["delta"]["cycles"]),
          src(lv["core_context"]["record"]), "closed under the prior Qwen bar (SS60/FF25 >= 0), not re-qualified at the 10-07 rule", "published"),
        L("slab_mul_lat7", "Slab MUL_LAT 7 (217 matrix ops a token)", "measured", dict(unit="cycles", AR=lv["slab_mul_lat7"]["delta"]["cycles"]),
          src(lv["slab_mul_lat7"]["record"]), lv["slab_mul_lat7"]["verdict"], "published"),
        L("kv_map_m", "KV landing Option M (KV_MAP=1), cold-layer KV-ready", "measured", dict(unit="cycles", AR=lv["kv_map_m"]["delta"]["cycles"]),
          src(lv["kv_map_m"]["record"]), "isolated P8191 bench, exact 15/15", "published"),
        L("die_relays_430um", "r21 die relay stations at the measured 430.56 um reach (8,965 relays)", "priced-candidate",
          dict(unit="cycles", AR=rel["cycles_per_ar_token"]), src(Q_RELAY, "cycles_per_ar_token"),
          "owner-approved 2026-10-07; priced as +%d per ME op x %d ops + %d per link traversal on the measured token; "
          "r21 floorplan stage counts, not a routed die" % (rel["delta_per_me_op"], rel["me_ops_per_ar_token"],
                                                             rel["delta_link_per_traversal"]), "published"),
        L("kv_crossbar_model", "Option M die crossbar (cycle model on the measured landing trace)", "priced-candidate",
          dict(unit="cycles", AR=lv["kv_map_m"]["modelled_not_composed"]["cycles"]), src(CMP, "qwen_rom.levers.kv_map_m.modelled_not_composed"),
          "modelled, not RTL", "candidate"),
        L("ctrl_shift", "Controller SHIFT successor (oldest-first write queue, registered bank eligibility)", "priced-candidate",
          dict(unit="cycles", AR=ctrl["latency"]["composed_worst_case_token_cycles"]),
          [src(Q_CTRL, "latency.composed_worst_case_token_cycles"), src(Q_CTRL_Q, "status")],
          "%s: exact all 32 PCs; worst-case +%d cycles a token (3 request->PHY edges); predecessor SS %.2f / FF %.2f ps; "
          "physical unmeasured; added mutable state unprotected (blocks production adoption). Protected successor "
          "(duplicated state, results/rtl/qwen_ctrl_protected_20261007/routed150, main 72bfeccb1): mapped-state retention PASS, "
          "routed physical status not_met, so no cycle or closure credit"
          % (ctrlq["status"], ctrl["latency"]["composed_worst_case_token_cycles"],
             ctrlq["predecessor_measurement"]["ss_ps"], ctrlq["predecessor_measurement"]["ff_ps"]), "candidate"),
        L("forwarded_clocks", "Direction-owned forwarded link clocks (217 primitives, 442 directional clock nets)", "priced-candidate",
          dict(unit="cycles", AR=fwd["latency"]["replacement_added_single_user_token_cycles"]), src(Q_FWD, "latency"),
          "same registered-hop count as r21 (0 added stage cycles); area proxy %.0f um2; active graph simulated=%s, adopted=%s; "
          "the protected-reset (TMR) successor graph r23 on main (8f68043a0) also adds 0 token cycles and is not adopted"
          % (fwd["area_proxy_um2"], fwdv["active_graph_simulated"], fwdv["adopted"]), "candidate"),
        _link_credit_line(fwd),
        L("vm_me_service", "Native VM ME bank service (captured W1 source slots, protected bank)", "gated-unknown", None,
          [src(Q_VM_ME, "serialized_reference"), src(Q_VM_CHK, "service_requirement")],
          "full_token_extra=null; the only priced reference is the serialized four-bank walker: +%s engine edges for the "
          "264 captured edges of ONE component (not a token cost, not composable; %.1fx the whole measured token); "
          "ready_for_new_bank_RTL=%s. %s" % (format(me["serialized_reference"]["conditional_extra_engine_edges"], ","),
                                             vmc["only_priced_service"]["ratio"], me["ready_for_new_bank_RTL"], vm_chk_note), "gate"),
        L("vm_su_service", "VM SU/reducer bank service obligations", "gated-unknown", None, [src(Q_VM_SU, "scope"), src(Q_VM_CHK, "packages")],
          "service quanta are not clock cycles; SRAM, protection, write completion, mux, fanout, capture unbound. " + vm_chk_note, "gate"),
        L("vm_recovery", "Qwen VM bank recovery / native schedule binding", "gated-unknown", None, [src(Q_VM_REC, "status"), src(Q_VM_CHK, "verdict")],
          load(Q_VM_REC)["status"] + "; one dynamic writer unresolved. " + vm_chk_note, "gate"),
        L("die_top_route", "Full-die detailed route, SS/FF, DRC and IR of the reopened Qwen die (directive 14)", "gated-unknown", None,
          src(Q_CLOSURE, "physical"), "die-top route not done; r18g bound (+13,305..16,268 cycles) is history, not composed. "
          "Owner: stream qwen-dietop (branch claude/qwen-dietop-20261007; academic-validation method: full-die GRT overflow 0, "
          "GRT-parasitic SS/FF STA, CTS clock plan, IR, representative-region DRT). The full-rate link (gate link_credit_rtt) "
          "grows the qfd_hub frame and adds a 128-word receive buffer at each strip endpoint", "gate"),
        L("routed_masters", "Real routed views for previously assumed masters", "gated-unknown", None,
          src("docs/OWNER_DIRECTIVES_2026_10_07.md"), "interim views cannot establish closure; relay masters qfd_cst / qfd_chead "
          "closed at 833 ps (+57.00/+17.75, +37.93/+17.62) carry no cycle change. Owner: stream qwen-blocks (branch "
          "claude/qwen-blocks-20261007); the full-rate hub qfd_hub_fr and the strip receive buffer qfd_link_rx128 are routed "
          "by stream qwen-contracts (gate link_credit_rtt)", "gate"),
        _protected_kv_line(),
        L("qwen_closure_cost_candidates", "Qwen closure-cost ledger candidates (tile ROM pipe, spine lane stations, lane credit, hub, "
          "IO CDC, collective, ctrl domain, CDC m2), upper bound", "priced-candidate", dict(unit="cycles", AR=3464),
          src("results/rtl/qwen_closure_cost_ledger_20261007/ledger.json", "total_cycles_upper_bound",
              commit="fd6f7805d (branch claude/qwen-blocks-20261007 only)"),
          "upper bound -1.75 %% AR on the 194,226-cycle base: every added cycle assumed exposed on every op; it assumes 325 "
          "ME ops a token where the relay record measures 217, so the per-op terms are overstated; nothing adopted until "
          "the routes close and the benches pass", "closure"),
    ]
    pub = q["token_cycles"]
    published_sum = sum(x["effect"]["AR"] for x in lines if x["role"] in ("base", "published"))
    assert published_sum == pub, (published_sum, pub)
    measured_only = sum(x["effect"]["AR"] for x in lines if x["role"] in ("base", "published") and x["status"] == "measured")
    cand = pub + sum(x["effect"]["AR"] for x in lines if x["role"] == "candidate")
    gates = [x["id"] for x in lines if x["status"] == "gated-unknown"]
    comps = dict(
        measured_lines_only=dict(cycles=measured_only, AR_tok_s=tok_s_cycles(measured_only),
                                 status="measured", note="measured token + measured levers, no die relay stations (not a design point)"),
        published=dict(cycles=pub, AR_tok_s=tok_s_cycles(pub), status="priced-candidate", record=src(CMP, "qwen_rom.token_cycles"),
                       note="three_machine_compose headline: measured lines + owner-adopted priced relays; physical closure "
                            "reopened 2026-10-07, so this is a candidate composition, not a closed rate"),
        unified_candidate=dict(cycles=cand, AR_tok_s=tok_s_cycles(cand), status="priced-candidate", gated_by=gates,
                               note="published + every priced candidate cost (crossbar model, controller SHIFT worst case, "
                                    "forwarded clocks 0)"),
    )
    clo = sum(x["effect"]["AR"] for x in lines if x["role"] == "closure")
    comps["unified_candidate_with_closure_upper"] = dict(
        cycles=cand + clo, AR_tok_s=tok_s_cycles(cand + clo), status="priced-candidate", gated_by=gates,
        note="unified_candidate + the Qwen closure-cost ledger upper bound (+%d cycles; per-op terms overstated)" % clo)
    # ---- DSpark re-evaluation
    old, new = load(Q_DSPARK), load(Q_DSPARK_RE)
    b = old["variants"]["baseline_np4"]
    ar_link = (rel["cycles_per_ar_token"] - rel["delta_per_me_op"] * rel["me_ops_per_ar_token"]) // rel["delta_link_per_traversal"]
    step, tau, step_links, step_ops = b["step_upper"], b["tau"], b["relay_upper"]["link_traversals"], b["relay_upper"]["me_ops"]
    # equal per-traversal stall x on AR and on a verify step: AR(pub + ar_link*x) vs step(step + step_links*x)/tau
    x_eq = (step / tau - pub) / (ar_link - step_links / tau)
    # verify traversals carry np positions: if a stall scales with payload, the step pays np*x each traversal
    np_ = b["np"]
    den = ar_link - np_ * step_links / tau
    dspark = dict(
        published=dict(record=src(Q_DSPARK), tok_s=b["tok_s_upper"], speedup_vs_ar=b["speedup_vs_ar_upper"],
                       verdict=old["verdict"], ar_cycles=old["ar"]["token_cycles"], status="priced-candidate",
                       note="RTL verify/draft stages + r21 relay stages priced on 1,003 ME ops / 96 link traversals; tau "
                            "third-party 3.1445"),
        reevaluated=dict(record=src(Q_DSPARK_RE), tok_s=new["variants"]["baseline_np4"]["tok_s_upper"],
                         speedup_vs_ar=new["variants"]["baseline_np4"]["speedup_vs_ar_upper"],
                         best=dict((k, new["best"][k]) for k in ("np", "tok_s_lower", "tok_s_upper", "speedup_vs_ar_lower", "speedup_vs_ar_upper")),
                         verdict=new["verdict"], ar_cycles=new["ar"]["token_cycles"], ar_tok_s=new["ar"]["tok_s"],
                         status="priced-candidate",
                         inputs_changed=["controller SHIFT worst case +144 on AR and +144 per DSpark step (charged once a step, "
                                         "like Option M's +54)", "forwarded clocks: 0 added stage cycles (same relay hops)"],
                         command="same as dspark_verdict_relays.sh with --ar-cycles 216857 --extra-per-step 198"),
        gated_inputs=dict(
            vm_service=("gated: per-ME-op cost unknown.  Any per-ME-op addition y lowers the DSpark ratio, because a step "
                        "issues %d ME ops for %.4f tokens (%.0f a token) against %d a token for AR; the AR_MODE verdict is "
                        "robust to it" % (step_ops, tau, step_ops / tau, rel["me_ops_per_ar_token"])),
            link_credit=dict(note=("resolved (gate link_credit_rtt, full-rate hub CR=128): measured 0 credit stalls a traversal, "
                                   "so x = 0 and the break-even below is not reached.  AR crosses the link %d times a token, a "
                                   "step %d times for %.4f tokens, so a link stall would hurt AR more per token" % (ar_link, step_links, tau)),
                             break_even_stall_cycles_per_traversal_equal_payload=round(x_eq),
                             break_even_if_verify_stall_scales_with_np=(round((step / tau - pub) / den) if den > 0 else None),
                             reading=("DSpark reaches AR only if each link traversal stalls >= %d cycles and the verify "
                                      "traversal (np=%d positions) stalls no more than an AR one; if the stall scales "
                                      "with payload the threshold %s" % (round(x_eq), np_,
                                      "is %d" % round((step / tau - pub) / den) if den > 0 else "is never reached"))),
            die_route_and_masters="gated: affects AR and the step through the same ME-op and link counts",
            tau="third-party 3.1445 (no Qwen DSpark acceptance measured on the target workload mix)"),
        verdict=("AR_MODE holds: the re-evaluation with the newer priced inputs gives %.1f tok/s (%.3fx); every gated "
                 "per-ME-op cost moves the ratio down; a link-credit stall above ~%d cycles a traversal could have moved it "
                 "up, but the full-rate hub measures 0 credit stalls" % (new["variants"]["baseline_np4"]["tok_s_upper"],
                                      new["variants"]["baseline_np4"]["speedup_vs_ar_upper"], round(x_eq))),
    )
    return dict(clock_hz=CLK, context="P8191, TP4, 4 dies, STREAM4 KV", lines=lines, compositions=comps, gates=gates,
                dspark=dspark, physical_status="REOPENED 2026-10-07 (owner directive 14): no full-die route, SS/FF, DRC or IR")


# ===================================================================================================== DS ROM S81 1M
def ds_rom():
    c = load(CMP)["ds_rom"]
    led = load(DS_LEDGER)
    links = load(DS_LINKS)
    rack = load(DS_RACK)
    tau = c["tau"]
    hop_us = links["hop"]["us"] + c["link_fec"]["full_fec"]["ii_hop_cable_us"]
    lines = [L("recovery_composition", "Recovery all-measured composition (adopted levers, full RS(544,514) FEC) before S81 closure costs",
               "measured", dict(unit="us", AR=round(1e6 / led["baseline"]["ar_tok_s"], 3), MTP_step=round(tau * 1e6 / led["baseline"]["mtp_tok_s"], 3)),
               src(DS_LEDGER, "baseline"), "rounded tok/s basis; measured share %.4f" % c["measured_share"], "base")]
    prev_ar, prev_mtp = led["baseline"]["ar_tok_s"], led["baseline"]["mtp_tok_s"]
    for it in led["items"]:
        st = "priced-candidate" if it["item"] in ("s81_die", "pq_qelem", "link_split") else "measured"
        lines.append(L("closure_" + it["item"], it["description"][:160], st,
                       dict(unit="us", AR=round(1e6 / it["ar_tok_s"] - 1e6 / prev_ar, 3),
                            MTP_step=round(tau * 1e6 / it["mtp_tok_s"] - tau * 1e6 / prev_mtp, 3)),
                       src(DS_LEDGER, "items[%s]" % it["item"]),
                       "block-measured cycles x op counts" if st == "measured" else "die/geometry pricing; DRT/SS/FF pending",
                       "published"))
        prev_ar, prev_mtp = it["ar_tok_s"], it["mtp_tok_s"]
    cand = {x["item"]: x for x in led["candidates"]}
    bf = cand["bf_half"]
    bf_ar = round(1e6 / bf["ar_tok_s"] - 1e6 / c["AR_tok_s"], 3)
    bf_mtp = round(tau * 1e6 / bf["mtp_tok_s"] - tau * 1e6 / c["MTP_tok_s"], 3)
    geo = rack["geometry"]
    var = {}
    for name in ("half_dedicated", "full_shared"):
        inv = load(f"{DS_MAP}/{name}/inventory.json")
        var[name] = dict(stages=inv["stages"], bf_stages=inv["bf_stages"], q_stages=inv["q_stages"],
                         layer_dies=inv["layer_dies"], BF_dedicated=inv["BF_dedicated"], ROM_ECC=inv["ROM_ECC"],
                         extra_hops_vs_composed=inv["stages"] - geo["stages"])
    ret = load(DS_RET)
    global GEO_B
    GEO_B = next(v for v in load(DS_GEOM)["variants"] if v["name"] == "mixed183")
    lines += [
        L("geometry_note", "Published composition geometry: f183.60 (%d stages, %d layer dies, %d dies total)"
          % (geo["stages"], geo["layer"] if "layer" in geo else rack["counts"]["layer"], rack["counts"]["dies"]),
          "measured", None, src(DS_RACK, "geometry"), "the historical S81 geometry with full-rate BF; NOT the actual 1792 mapping (the current physical integration basis); no token headline is adopted", "info"),
        L("actual1792_half_dedicated_hops", "Actual 1792 mapping, BF-dedicated half-rate (%d stages: %d BF + %d q): +%d stage hops [SUPERSEDED by the measured fieldphase compositions]"
          % (var["half_dedicated"]["stages"], var["half_dedicated"]["bf_stages"], var["half_dedicated"]["q_stages"],
             var["half_dedicated"]["extra_hops_vs_composed"]),
          "priced-candidate", dict(unit="us", AR=round(var["half_dedicated"]["extra_hops_vs_composed"] * hop_us, 3),
                                   MTP_step=round(var["half_dedicated"]["extra_hops_vs_composed"] * hop_us, 3)),
          [src(f"{DS_MAP}/half_dedicated/inventory.json", "stages"), src(DS_LINKS, "hop.us")],
          "each added stage = one measured full-FEC board hop %.4f us + %.4f us cable; capacity PASS, metadata only" % (links["hop"]["us"], hop_us - links["hop"]["us"]),
          "alternative"),
        L("actual1792_full_shared_hops", "Actual 1792 mapping, shared BF pairs (%d stages, gate K-split alias): +%d stage hops [SUPERSEDED by the measured fieldphase compositions]"
          % (var["full_shared"]["stages"], var["full_shared"]["extra_hops_vs_composed"]),
          "priced-candidate", dict(unit="us", AR=round(var["full_shared"]["extra_hops_vs_composed"] * hop_us, 3),
                                   MTP_step=round(var["full_shared"]["extra_hops_vs_composed"] * hop_us, 3)),
          [src(f"{DS_MAP}/full_shared/inventory.json", "stages"), src(DS_LINKS, "hop.us")], "as above", "alternative"),
        L("bf_half_rate_doubling", "BF half-rate (owner 2026-10-07): BF16 field phases doubled [SUPERSEDED by the measured fieldphase compositions]", "priced-candidate",
          dict(unit="us", AR=bf_ar, MTP_step=bf_mtp), src(DS_LEDGER, "candidates[bf_half]"),
          "priced BF16-phase doubling only (q phases on q pairs unchanged); on shared pairs the q words on BF pairs (20.6 %%) "
          "would also halve and are not priced. With the field phases of the 1792 geometry unmeasured, this proves no "
          "overall bound in either direction; zero added logic cycles (%s)" % DS_BFROOT, "alternative"),
        L("return_station_plus1", "Spine return station +1 cycle a return crossing (sensitivity)", "priced-candidate",
          dict(unit="us", AR=round(max(v["conditional_AR_latency_delta_ns"] for v in ret["variants"]) / 1000, 3),
               MTP_step=round(max(tau * 1e6 / v["conditional_MTP_tok_s"] - tau * 1e6 / v["baseline_MTP_tok_s"] for v in ret["variants"]), 3)),
          src(DS_RET, "variants"), "historical phase schedules; not the 1792 geometry", "candidate"),
        L("bf_merge_ksplit", "BF16 phase merges + router K split, option A (f198.72, 2,048 pairs, 96 reprice stages): "
          "full-field same-frame measurement", "measured",
          dict(unit="us", AR=round(1e6 / BFA["AR"] - 1e6 / BFA["base_AR"], 3),
               MTP_step=round(tau * 1e6 / BFA["MTP"] - tau * 1e6 / BFA["base_MTP"], 3)),
          src(BFA_FILE, "options.A_f198_2048 vs options.base_f198_2050", commit=BFA_COMMIT),
          "measured exact (option A %s/%s region runs, base_f198 %s/%s, both bit-exact), UNADOPTED, FULL-RATE BF: AR %.1f vs base_f198 %.1f "
          "(+%.2f %%), MTP %.1f vs %.1f (+%.2f %%). Supersedes the +7.82 %% figure (BF16-phase-only, ledger.md on %s). "
          "Option B (2,304 pairs) failed legal fit: see bf_merge_ksplit_option_B. Under the half-rate 1792 geometry its gain "
          "is unmeasured, so it is listed, never summed"
          % (format(BFA["regions"], ","), format(BFA["regions"], ","), format(BFA["base_regions"], ","), format(BFA["base_regions"], ","),
             BFA["AR"], BFA["base_AR"], 100 * (BFA["AR"] / BFA["base_AR"] - 1), BFA["MTP"], BFA["base_MTP"],
             100 * (BFA["MTP"] / BFA["base_MTP"] - 1), BF_BRANCH), "info"),
        L("bf_merge_ksplit_option_B", "Option B (historical/numerical): BF16 phase merges + router K split on mixed slots, %d pairs "
          "(18 a region, 512 BF), %d reprice stages, %d layer dies, full-rate BF" % (BFB["pairs"], BFB["stages"], BFB["layer_dies"]),
          "gated-unknown", None,
          [src(BFA_FILE, "options.B_mixed_2304", commit=BFB_COMMIT), src(DS_GEOM, "variants[name=mixed183].requested_fits")],
          "NUMERICAL, LEGAL-FIT FAILED, NOT PHYSICALLY QUALIFIED. Field vehicle bit-exact %s/%s regions (a numerical result, "
          "not measured silicon); its 1,754.3 AR is a field-vehicle composition on the pre-su_meso base %.1f, never a "
          "qualified rate. The mixed183 geometry requests 2,304 pairs but the legal maximum at that geometry is %d "
          "(requested_fits=false, %s). Codex's branch label is quoted for history only, not promoted: '%s'"
          % (format(BFB["regions"], ","), format(BFB["regions"], ","), BFB["base_AR"], GEO_B["maximum_pairs_at_this_geometry"],
             DS_GEOM, BFB["label"]), "info"),
        L("pq_fullshape_partition", "Full-shape PQ partition: %d non-CAM cycles a field phase (design v2) + the MEASURED native root "
          "CAM delta (+%d isolated / +%d two-leaf / +%d eight-leaf) = +%d..+%d" % (
              PQ["cycles_per_phase"] - PQ["design_cam_cycles"], PQ_CAM["isolated"], PQ_CAM["two_leaf"], PQ_CAM["eight_leaf"],
              PQ["cycles_per_phase"] - PQ["design_cam_cycles"] + PQ_CAM["isolated"], PQ["cycles_per_phase"] - PQ["design_cam_cycles"] + PQ_CAM["eight_leaf"]),
          "priced-candidate", dict(unit="us", AR=round(PQ["ar_loss_frac"] / PQ["cycles_per_phase"]
                                                        * (PQ["cycles_per_phase"] - PQ["design_cam_cycles"] + PQ_CAM["eight_leaf"]) * c["AR_us"], 3),
                                   MTP_step=None),
          [src(PQ_CAM_REC, "measured_delta_cycles"), src(PQ_CAM_MODEL, "latency, incremental_state_bits"),
           src(PQ_FILE, "changes[item=added cycles per phase (vs the native production parent)].current", commit=PQ_COMMIT)],
          "PARTIAL-PRICED CANDIDATE. The root CAM term uses the measured native CAM (main 4251eb216; %d exact roots; "
          "isolated +%d, two-leaf +%d, eight-leaf +%d incl. publication; one real ROOTD128 component, no parity, full-parent "
          "or physical qualification), not the design's +1/pass model; the effect shown is the eight-leaf case, about %.2f %% AR "
          "(%.2f %% isolated), via the historical per-cycle sensitivity. The per-token critical phases on the 1,792 mapping "
          "are not composed; MTP not priced. Geometry provisional: roots in the new %.2f um row, core %.2f mm2 in the "
          "449 x 1,728 um slot, return write-back blocks %.2f mm2, roots about %.1f mm2 a die. Protection storage +%d bits a "
          "root (%s for 128 roots, main model) -- sizing only; the protected root face is an unestablished contract with no "
          "credit. Non-CAM cycles from the design v2 record %s; main's 738ddfbc2 (+15 / 0.47 %%) is superseded"
          % (PQ_CAM["exact_roots"], PQ_CAM["isolated"], PQ_CAM["two_leaf"], PQ_CAM["eight_leaf"],
             100 * PQ["ar_loss_frac"] / PQ["cycles_per_phase"] * (PQ["cycles_per_phase"] - PQ["design_cam_cycles"] + PQ_CAM["eight_leaf"]),
             100 * PQ["ar_loss_frac"] / PQ["cycles_per_phase"] * (PQ["cycles_per_phase"] - PQ["design_cam_cycles"] + PQ_CAM["isolated"]),
             PQ["root_row_um"], PQ["core_mm2"], PQ["rwb_mm2"], PQ["roots_mm2_per_die"], PQ_CAM["bits_per_root"],
             format(PQ_CAM["bits_total"], ","), PQ_COMMIT), "candidate"),
        L("pq_root_protected_face", "PQ root protected 140/141-pin face (parity)", "gated-unknown", None,
          [src(PQ_CAM_MODEL, "mutable_state_protection"), src(PQ_ROOT, "parity", commit=PQ_COMMIT)],
          "OPEN: the native root interface lacks the proposed parity; no implicit parity or protection qualification", "gate"),
        L("pq_stage_b_timing", "PQ CAM stage-B timing", "gated-unknown", None, src(PQ_CAM_MODEL, "physical_gate"),
          "not measured. Stage-C fallback (OPC=1) RTL committed at 36b7a0452 (branch claude/s81-blocks-20261007), default-off; "
          "s81-blocks.log reports it exact at +3 two-leaf / +7 eight-leaf vs native (stage B +2 / +4) but no result record is "
          "committed; routes launched in the reserved 132 x 134 um slot. No credit until a stage closes", "gate"),
        L("pq_half_serial_lane_exactness", "HALF serial-lane exactness for a beat shift of <= 2 cycles", "gated-unknown", None,
          src(PQ_FILE, "changes", commit=PQ_COMMIT), "exactness of the HALF (BF-dedicated) serial lane under the <= 2-cycle beat shift not shown", "gate"),
        L("selector_selt_c_cuts", "Selector selt_c structural cuts (MRG_PIPE + RQPIPE): +22 cycles a segment vs the ledger's +20",
          "gated-unknown", None, src("rtl/dsrom_sys/s81_ph/ot_s81ph_sel_tile.sv", "MRG_PIPE, RQPIPE", commit="b17a8dda2 (branch claude/s81-blocks-20261007 only)"),
          "RTL committed; s81-blocks.log reports bench PASS (tail mean 129 vs 127) but no result record is committed. If it "
          "closes it adds +2 cycles a selector segment over the ledger's selector item; not composed", "info"),
        L("bf_halfphl_price", "BF HALF_PHL half-rate on dedicated BF pairs, priced on the measured 1,792 fieldphase (HALF + router K split)",
          "priced-candidate", dict(unit="us", AR=round(1e6 / 1467.6 - 1e6 / 1593.7, 3), MTP_step=round(tau * 1e6 / 4403.0 - tau * 1e6 / 4694.7, 3)),
          [src("results/rtl/dsrom_closure_cost_ledger_20261007/ledger.json", "candidates[bf_halfphl]"),
           src("results/uarch/dsrom_s81_field_phases_1792_20261007/composition_basis_39e424990.json", "variants.half_dedicated_ksplit.compositions.half_rate",
               commit="f42b1eb76 (branch claude/s81-fieldphase-20261007 only)")],
          "CORRECTED price: AR -7.91 %% / MTP -6.21 %% (1,593.7 / 4,694.7 -> 1,467.6 / 4,403.0, half-rate BF upper bound), "
          "confirmed by s81-bf (main 31f23a48a); the earlier -7.68 %% / -6.31 %% on the legal-fit-failed option-B base "
          "(5a07bf71d) and 16584ae76 are superseded. Optional full-rate recut at TT in flight (full-rate BF on the same "
          "mapping: 1,577.1 / 4,674.3)", "info"),
        L("s81_die_m221pq", "S81 die re-priced on the m221pq layer1 die: +28 cycles a field phase (round trip 167 + 2 PQ "
          "root-row stations = 169 vs 137, less meso 4; was +27)", "priced-candidate",
          dict(unit="us", AR=round(1e6 / 1593.7 - 1e6 / c["AR_tok_s"], 3), MTP_step=round(tau * 1e6 / 4694.7 - tau * 1e6 / c["MTP_tok_s"], 3)),
          src("results/rtl/dsrom_closure_cost_ledger_20261007/ledger.json", "items[s81_die]",
              commit="39e424990 (branch claude/s81-die-20261007 only)"),
          "composed ledger TOTAL AR 1,593.7 (-4.85 %%) / MTP 4,694.7 on the published basis; see composition "
          "published_m221pq_die", "info"),
        L("wfc_die150_ff", "WFC (wavefront controller) source block: die150 FF hold closed", "measured", None,
          src("results/rtl/dsrom_wfc_split_20261006/closure.json", "src r24", commit="dc8570b5d (branch claude/s81-die-20261007 only)"),
          "src r24: SS +31.5 ps (all modes) / FF +22.7 ps in incontext/die150/region/reg2reg, DRC / antenna / DRV 0, RTL "
          "unchanged (hold-ECO IO model at 150 ps on every port, slew margin 30); meets the closure line; not yet on main", "info"),
        L("field_phases_1792", "Field phase timings of the 1792 geometry: MEASURED (s81-fieldphase)", "measured", None,
          src(FP_FILE, "variants.*.nodes, phase_ledger"),
          "qelem10 field vehicle on every region of every stage of both 1,792 mappings, 7 representative layers: %s + %s "
          "region runs, all exact; actual mixed221 die wire, per-phase block adders; BF half rate a composed upper bound "
          "(phase ledger: measured / composed / model-only). Feeds the actual1792 compositions"
          % (format(FP["variants"]["half_dedicated"]["region_runs"], ","), format(FP["variants"]["full_shared"]["region_runs"], ",")), "info"),
        L("bf_half_physical", "BF half-rate clock root qualification (current exact BF closure path)", "gated-unknown", None,
          [src(DS_BFROOT, "physical_obligations"), src(DS_BFFAIL + "/record.json"), src(DS_BFFAIL + "/actual_calibration_failure.json")],
          "half-rate BF is the current exact BF closure path, not an immutable requirement: full rate may return if it meets "
          "the correctness and physical gates. The 449ebc571 root-phase failure was a script hierarchy failure (not an "
          "arithmetic rejection), fixed in 7990dfdbf and now calibrating; SS/FF >= +15 ps, DRC 0 still to be shown. HALF route limiter "
          "(ph -> ICG enable, -474.7 ps): structural HALF_PHL fix exact PASS (456 partials, negatives FAIL) on branch "
          "claude/s81-bf-20261007 6d26df595; routes running (s81-bf)", "gate"),
        L("s81_die_closure", "S81 die DRT / SS / FF / IR at the final mixed-BF/PQ geometry", "gated-unknown", None,
          src(DS_LEDGER, "items[s81_die].description"), "global-route feasibility only", "gate"),
        L("native_token", "Native end-to-end S81 token (connected RTL)", "gated-unknown", None,
          src("docs/PROGRAM_PLAN_2026_10_05.md"), "no native end-to-end S81 token yet", "gate"),
        L("mtp_physical", "MTP path physical qualification", "gated-unknown", None, src(CMP, "ds_rom.MTP_physical_qualified"),
          "MTP_physical_qualified=false", "gate"),
        L("fused_head_half", "Fused-head half-rate domain (fh_half)", "gated-unknown", None, src(DS_LEDGER, "unpriced_candidates"),
          "whole-domain clock/CDC contract and full-shape composition missing", "gate"),
    ]
    pub_ar, pub_mtp = c["AR_us"], c["MTP_step_us"]
    gates = [x["id"] for x in lines if x["status"] == "gated-unknown" and x["role"] != "info"]
    comps = dict(published=dict(AR_us=pub_ar, MTP_step_us=pub_mtp, AR_tok_s=c["AR_tok_s"], MTP_tok_s=c["MTP_tok_s"], tau=tau,
                                geometry="f183.60, %d stages, %d dies" % (geo["stages"], rack["counts"]["dies"]),
                                status="priced-candidate", record=src(CMP, "ds_rom"),
                                note="closure-cost ledger TOTAL on the historical 85-stage full-rate-BF geometry"))
    for name in ("half_dedicated", "full_shared"):
        v = var[name]
        fc = FP["variants"][name]["compositions"]
        hr, fr = fc["half_rate"], fc["full_rate_bf"]
        comps["actual1792_" + name] = dict(
            AR_us=hr["AR_us"], MTP_step_us=hr["MTP_step_us"], AR_tok_s=hr["AR_tok_s"], MTP_tok_s=hr["MTP_tok_s"], tau=tau,
            stages=v["stages"], dies=v["layer_dies"], pairs_per_layer_die=1792, bf_rate="half",
            dies_note="layer dies (Codex basis, 2d811aafb inventory); head / table / draft dies are outside the 1,792 mapping",
            basis=[src(DS_GEOM, "variants[name=mixed221]", commit="77ffa0428"), src(f"{DS_MAP}/{name}/inventory.json", "stages, layer_dies", commit="2d811aafb"),
                   src(FP_FILE, f"variants.{name}.compositions.half_rate")],
            adopted=False, closure=False,
            status="measured field phases + composed (current physical integration basis; not an adopted rate)",
            label="measured-field composition; BF half rate composed as an upper bound on latency",
            bound="half-rate BF: latency upper bound (rate lower bound) for the BF term only",
            full_rate_bf=dict(AR_tok_s=fr["AR_tok_s"], MTP_tok_s=fr["MTP_tok_s"], note="sensitivity if full-rate BF closes (recut at TT in flight)"),
            serial_substages=dict(AR_tok_s=fc["half_rate_serial"]["AR_tok_s"], MTP_tok_s=fc["half_rate_serial"]["MTP_tok_s"]),
            region_runs=FP["variants"][name]["region_runs"], all_exact=FP["variants"][name]["all_exact"],
            gated_by=[g for g in gates if g != "field_phases_1792"],
            note="s81-fieldphase: every region of every stage measured exact on the field vehicle; composed with the actual "
                 "mixed221 die wire and per-phase block adders on the published ledger basis; replaces the earlier "
                 "partial-priced sensitivity")
    pp = FP["variants"]["half_dedicated"]["compositions"]["published_per_phase"]
    comps["published_per_phase_rebased"] = dict(
        AR_tok_s=pp["AR_tok_s"], MTP_tok_s=pp["MTP_tok_s"], AR_us=pp["AR_us"], MTP_step_us=pp["MTP_step_us"], tau=tau,
        status="measured field phases + composed (85-stage historical geometry)", record=src(FP_FILE, "variants.half_dedicated.compositions.published_per_phase"),
        note="FINDING (s81-fieldphase): the published composition is about 2.6 %% optimistic -- re-based with the per-phase "
             "wire and block adders it is %.1f / %.1f instead of %.1f / %.1f" % (pp["AR_tok_s"], pp["MTP_tok_s"],
             FP["basis"]["published_AR_tok_s"], FP["basis"]["published_MTP_tok_s"]))
    comps["published_m221pq_die"] = dict(
        AR_tok_s=1593.7, MTP_tok_s=4694.7, AR_us=round(1e6 / 1593.7, 3), MTP_step_us=round(tau * 1e6 / 4694.7, 3), tau=tau,
        status="priced-candidate", record=src("results/rtl/dsrom_closure_cost_ledger_20261007/ledger.json", "total"),
        note="the DS closure-cost ledger TOTAL with s81_die re-priced on the m221pq layer1 die (+28 a field phase); "
             "85-stage historical geometry, same basis as 'published'")
    comps["option_B_2304_historical"] = dict(
        AR_tok_s=BFB["AR"], MTP_tok_s=BFB["MTP"], tau=tau, stages=BFB["stages"], pairs_per_layer_die=BFB["pairs"],
        dies=BFB["layer_dies"], bf_rate="full",
        status="numerical, legal-fit failed, not physically qualified (historical/competing numerical candidate)",
        codex_branch_label_quoted=BFB["label"], record=src(BFA_FILE, "options.B_mixed_2304", commit=BFB_COMMIT),
        legal_fit=src(DS_GEOM, "variants[name=mixed183].requested_fits", commit="77ffa0428"),
        note="field-vehicle numbers only: never measured silicon, never a qualified or adopted rate")
    comps["geometry_conflict"] = dict(
        status="ANSWERED by Codex root 2026-10-07",
        answer=("The current physical integration basis is the actual legal 1,792-pair mixed geometry (77ffa0428) with the "
                "hash-bound complete mappings (2d811aafb): HALF dedicated 120 stages / 480 dies and FULL shared 98 / 392. "
                "Neither is a final adopted rate or closure. The 2,304-pair option B failed legal fit and stays a "
                "historical numerical candidate. Half-rate BF is the current exact closure path, not an immutable "
                "requirement. No token headline is adopted"),
        basis=[dict(name="actual1792_half_dedicated", commits=["77ffa0428", "2d811aafb"], stages=var["half_dedicated"]["stages"],
                    dies=var["half_dedicated"]["layer_dies"], pairs_per_layer_die=1792, bf_rate="half",
                    AR_tok_s=comps["actual1792_half_dedicated"]["AR_tok_s"], MTP_tok_s=comps["actual1792_half_dedicated"]["MTP_tok_s"],
                    status="partial-priced sensitivity (unmeasured field phases), not an adopted or guaranteed bound", bound="none proven"),
               dict(name="actual1792_full_shared", commits=["77ffa0428", "2d811aafb"], stages=var["full_shared"]["stages"],
                    dies=var["full_shared"]["layer_dies"], pairs_per_layer_die=1792, bf_rate="half",
                    AR_tok_s=comps["actual1792_full_shared"]["AR_tok_s"], MTP_tok_s=comps["actual1792_full_shared"]["MTP_tok_s"],
                    status="partial-priced sensitivity (unmeasured field phases), not an adopted or guaranteed bound", bound="none proven")],
        not_basis=[dict(name="option_B_2304 (505a9b484)", status="numerical, legal-fit failed, not physically qualified"),
                   dict(name="option_A_2048 (f198.72)", status="numerical field measurement, unadopted, full-rate BF")])
    return dict(context="DeepSeek-V4.1 1M, S81 array, TP4", tau=tau, lines=lines, compositions=comps, gates=gates,
                mapping_1792=var, physical_status="not closed; numerical component PASS is not physical adoption")


# ===================================================================================================== HBM accel DS 1M
def hbm_ds():
    m = load(H_MATCHED)["gate"]
    r23 = load(H_R23)
    cm = load(CMP)["hbm_ds"]
    tau = m["tau"]
    rows, after_total = [], False   # rows below the first "TOTAL at r23:" line are not in the r23 headline
    for l in (ROOT / H_LEDGER).read_text().splitlines():
        if l.startswith("TOTAL at r23:"):
            after_total = True
        mm = re.match(r"\| (.+?) \| (\d+) \| ([\d.]+) \| ([\d.]+) \|$", l)
        if mm:
            rows.append((mm.group(1), int(mm.group(2)), after_total))
    pre = r23["pre_closure"]["AR_us"]
    lines = [
        L("matched_gate", "Matched reference gate (measured RTL nodes, light-FEC TU budget)", "measured",
          dict(unit="us", AR=m["AR_us"], MTP_step=m["MTP_step_us"]), src(H_MATCHED, "gate"), m["AR_row"], "base"),
        L("die_wire_r16j", "Die wire stages, r16j wire-priced (r13 GRT wire record)", "priced-candidate",
          dict(unit="us", AR=round(pre - m["AR_us"], 3), MTP_step=round(pre - m["AR_us"], 3)),
          src(H_R23, "pre_closure"), "same die traversals on the AR walk and the verify walk", "published"),
    ]
    for i, (name, cyc, beyond) in enumerate(rows):
        us = round(cyc / CLK * 1e6, 3)
        lines.append(L("closure_%02d" % i, name[:170], "priced-candidate", dict(unit="us", AR=us, MTP_step=us),
                       src(H_LEDGER, "row %d" % i), "die closure cost (stations / faces / splits / SM m2+m3 / relays / 2x hub)",
                       "candidate" if beyond else "published"))
    fec = cm["full_fec"]
    lines.append(L("full_fec", "Full RS(544,514) FEC on every switch crossing (owner 2026-10-06)", "priced-candidate",
                   dict(unit="us", AR=fec["AR_us"], MTP_step=fec["MTP_step_us"]), src(CMP, "hbm_ds.full_fec"),
                   "%d crossings x %.1f ns; NOT in the r23 closure headline; draft crossings not charged (HBM-favourable)"
                   % (fec["crossings_AR"], fec["per_crossing_ns"]), "candidate"))
    for k, v in cm["levers"].items():
        lines.append(L("lever_" + k, "Exact HBM lever " + k, "priced-candidate",
                       dict(unit="us", AR=v["delta"]["AR_us"], MTP_step=v["delta"]["MTP_step_us"]), src(v["record"]),
                       "exact on minimum components (%s); SS/FF not admitted" % v["scope"], "lever"))
    tc = load(H_TC)["endpoint_measurement"]
    n_red = 265      # exposed owner reductions a token (closure ledger HA2 convention: collective terms)
    tc_us = round(tc["measured_increment_cycles"] * n_red / CLK * 1e6, 3)
    sram = load(H_SRAM)["timing"]["added_queue_latency_vs_async_head_cycles"]
    sram_us = round(sram * n_red / CLK * 1e6, 3)
    lines += [
        L("ha2_truecredit", "HA2 true-credit endpoint (measured +%d cycles a transaction, 7+7 hops)" % tc["measured_increment_cycles"],
          "priced-candidate", dict(unit="us", AR=tc_us, MTP_step=tc_us), src(H_TC, "endpoint_measurement"),
          "x %d exposed owner reductions a token (ledger convention); composed_token_latency_cycles=null in the record; "
          "parametric hops, not placed pins" % n_red, "candidate"),
        L("collective_sram_protected", "Full-depth protected collective packet SRAM (+%d queue cycles vs async head)" % sram,
          "priced-candidate", dict(unit="us", AR=sram_us, MTP_step=sram_us), src(H_SRAM, "timing"),
          "x %d collective terms (assumption); default-off candidate" % n_red, "candidate"),
        L("ha2_half_rate_credit", "HA2 half-rate own-partial credit (alternative if it is the variant that closes)", "priced-candidate",
          dict(unit="us", AR=10.16, MTP_step=10.16), src(H_LEDGER, "Conditional"), "+46 cycles x 265; not summed", "alternative"),
        L("cdc_refill_ii1", "Protected CDC II=1 refill (B prime): full line rate, +2 empty-start cycles a pass x 610 passes",
          "priced-candidate", dict(unit="us", AR=H_CDC_V["lat_us"], MTP_step=H_CDC_V["lat_us"]),
          [src(H_REFILL, "status, normal_timing", commit=H_REFILL_COMMIT), src(H_REFILL_PASS, "passed", commit=H_REFILL_COMMIT),
           src(H_CDC2, "comparison.Bprime_refill_II1", commit=H_CDC2_COMMIT)],
          "RESOLVES the CDC rate cap: measured RTL on main (one full 545x64 protected CDC with the actual die reset entry, "
          "final_pass passed; status II1_REFILL_CANDIDATE_NOT_ADOPTED); recommended by the v2 design over the 3-bank rotation "
          "(0 added state bits, ~60-100 um2 of logic vs +12,093 um2). Latency +%.3f us a token. SS timing unmeasured (see "
          "cdc_refill_ss_timing); replaces the +2 x 265 collective_sram_protected term in the CDC compositions" % H_CDC_V["lat_us"],
          "alternative"),
        L("cdc_refill_ss_timing", "SS/FF timing of the CDC refill", "gated-unknown", None,
          src(H_REFILL, "physical_risk", commit=H_REFILL_COMMIT),
          "unmeasured; estimated risk on the 64:1 x 648-bit encoded read-mux / capture-address path; a function-preserving "
          "fix (registered head-pointer address) has been proposed (v2 design %s)" % H_CDC2, "gate"),
        L("cdc_frequency_lock", "PHY/core frequency lock for the II=1 CDC drain", "gated-unknown", None,
          src(H_CDC2, "contracts.frequency"),
          "hardware contract to be established, not an assumption: drain II=1 >= arrival only if Tw == Tr (same reference) "
          "or a rate-matcher leaves >= 1 idle per M flits; a faster write clock overflows a gap-free stream", "gate"),
        L("packet_sram_ii3_rate_cap", "Packet-SRAM receive queue still drains at II=3 (1/3 line rate per port)",
          "gated-unknown", None, src(H_CDC, "options.A_credit_bound.cost_serialisation", commit=H_CDC_COMMIT),
          "GATED until the same II=1 refill is applied to the packet SRAM: while it stays at II=3 the port is capped at a third "
          "of line rate even with the CDC refilled, +%.2f us AR / +%.0f us MTP on the measured receive streaming (%s cycles a "
          "AR token, %s a MTP step; +%.2f %% AR, +%.2f %% MTP step on the gate)"
          % (H_CDC_V["ii3_AR_us"], H_CDC_V["ii3_MTP_us"], format(H_CDC_V["ser_AR"], ","), format(H_CDC_V["ser_MTP"], ","),
             H_CDC_V["ii3_AR_pct"], H_CDC_V["ii3_MTP_pct"])
          + ". Progress: the packet-SRAM II=1 refill queue RTL (opt-in ENABLE_SRAM=2) is committed at 8bd16b9e0 (branch "
            "claude/hbm-contracts-20261007, not on main); its bench PASS is reported in hbm-contracts.log but no result "
            "record is committed; physical closure and integration pending, so no credit", "gate"),
        L("credit_producer_native", "Native credit producer for the full-rate credit contract", "gated-unknown", None,
          src(H_REFILL, "actual_credit_producer", commit=H_REFILL_COMMIT),
          "missing in the native RTL (today a testbench preload); full rate needs >= %d credits in flight against the "
          "159-cycle credit round trip, with an acknowledged grant/retirement protocol. The full-rate contract is gated "
          "on it" % 159, "gate"),
        L("cdc_sram_ii1_rotation", "3-bank rotation (II=1), fallback only", "priced-candidate",
          dict(unit="us", AR=H_CDC_V["lat_us"], MTP_step=H_CDC_V["lat_us"]), src(H_CDC, "options.B_rotated_II1", commit=H_CDC_COMMIT),
          "v1 design (historical record kept); same latency, +%s um2; the v2 design keeps it only if the refill cannot close SS "
          "after the registered-address fix" % format(H_CDC_V["rot_area_um2"], ",.1f"), "alternative"),
        L("sm_su_result_edge_native", "SM -> SU result handoff as a native edge (published as 343 cycles a token: hidden wire + 'stations gather a2 +1')",
          "gated-unknown", None, src(H_SMSU, "summary", commit=H_SMSU_COMMIT),
          "NOT a native edge today: in the die view the result tree ends in hfd_su's XOR exercise envelope, and in RTL the path "
          "runs through the GPU-comparator memory model. Every HBM DS row is a die-view-only result edge until this gate "
          "closes. HBM service bf801c49a and the native collective 7a60962c0 are integrated on main, but the actual consumer "
          "work is ongoing: no row takes native credit for the 343-cycle path. Alternatives: sm_su_native_edge_proposed / "
          "sm_su_store_forward_floor", "gate"),
        L("sm_su_native_edge_proposed", "Proposed native SM -> SU edge (SU ingress FIFOs + relay slices): %s cycles a token" % format(H_SMSU_V["native"], ","),
          "priced-candidate", dict(unit="us", AR=round((H_SMSU_V["native"] - H_SMSU_V["published"]) / CLK * 1e6, 3),
                                   MTP_step=round((H_SMSU_V["native"] - H_SMSU_V["published"]) / CLK * 1e6, 3)),
          src(H_SMSU, "summary.native_cycles", commit=H_SMSU_COMMIT),
          "increment over the published 343 cycles (+0.10 %% AR / +0.05 %% MTP step on the unified candidate); not summed (alternative)", "alternative"),
        L("sm_su_store_forward_floor", "RTL-implemented store-and-forward floor through the GPU-comparator memory system: >= %s cycles a token" % format(H_SMSU_V["store_forward"], ","),
          "priced-candidate", dict(unit="us", AR=round((H_SMSU_V["store_forward"] - H_SMSU_V["published"]) / CLK * 1e6, 3),
                                   MTP_step=round((H_SMSU_V["store_forward"] - H_SMSU_V["published"]) / CLK * 1e6, 3)),
          src(H_SMSU, "summary.store_forward_floor_cycles", commit=H_SMSU_COMMIT),
          "ESTIMATE (floor) that applies if no native edge is built; effect = increment over the published 343 cycles (+19.63 %% AR / "
          "+9.99 %% MTP step on the unified candidate; the full 132,520 cycles are 19.68 %% / 10.02 %%, contract.json impact); not summed (alternative)", "alternative"),
        L("su_reducer_safe", "SU reducer SAFE (+4 per reduction at 0.9 GHz)", "gated-unknown", None, src(H_LEDGER, "Pending"),
          "occurrences per token not bound", "gate"),
        L("su_c12_margin", "SU CP+c12 margin stage (+30 DS1M, measured exact) / RHALF (+176)", "gated-unknown", None,
          src(FULLSYS, "results[3..5]"), "per-stage cost measured; stages per token not composed; RHPAR 0 Qwen8K contract fault retained", "gate"),
        L("su_full_ddiv31", "su_full DDIV 31 (+10 per divide-class op)", "gated-unknown", None, src(H_LEDGER, "Conditional"),
          "only if hbm_su_full31 is the closing route; op count not composed", "gate"),
        L("vm_alignment", "VM write alignment / real publication path", "gated-unknown", None,
          src("results/rtl/hbm_accel_die_views_20261006/coordinator_r19c/audit.json", "VM_write_alignment"), "BLOCKED in the r19c audit", "gate"),
        L("die_clock_plan", "Die clock inputs, CTS and shared clock corridors", "gated-unknown", None, src(H_CLKIN, "entry_routing"),
          "candidate structural wiring only; collective reset entry adds 0 cycles a token (%s)" % H_CLKENT, "gate"),
        L("hbm_full_die", "Full-die detailed route / SS / FF / IR", "gated-unknown", None, src(H_R23), "die views only", "gate"),
    ]
    gates = [x["id"] for x in lines if x["status"] == "gated-unknown"]

    def ssum(roles):
        return (round(sum(x["effect"]["AR"] for x in lines if x["role"] in roles and x["effect"]), 3),
                round(sum(x["effect"]["MTP_step"] for x in lines if x["role"] in roles and x["effect"]), 3))
    ar_pub, mtp_pub = ssum(("base", "published"))
    assert abs(ar_pub - r23["with_closure"]["AR_us"]) < 0.02, (ar_pub, r23["with_closure"]["AR_us"])
    comps = dict(
        three_machine_published=dict(AR_us=cm["rows"]["median"]["AR_us"], AR_tok_s=cm["rows"]["median"]["AR_tok_s"],
                                     MTP_tok_s=cm["rows"]["median"]["MTP_tok_s"], record=src(CMP, "hbm_ds.rows.median"),
                                     status="priced-candidate", note="STALE as a headline: gate + exact levers + full FEC + r05 "
                                     "floorplan wire, but NO die closure costs"),
        r23_closure_published=dict(AR_us=r23["with_closure"]["AR_us"], AR_tok_s=r23["with_closure"]["AR_tok_s"],
                                   MTP_tok_s=r23["with_closure"]["MTP_tok_s"], record=src(H_R23, "with_closure"),
                                   status="priced-candidate", note="closure-inclusive but light FEC and no lever credit"),
    )
    ar, mtp = ssum(("base", "published", "candidate"))
    comps["closure_fec_no_lever_credit"] = dict(AR_us=ar, MTP_step_us=mtp, AR_tok_s=tok_s_us(ar), MTP_tok_s=tok_s_us(mtp, tau),
                                                status="priced-candidate", gated_by=gates,
                                                note="conservative: r23 closure + r23 attention tile + full FEC + priced credit/SRAM costs")
    ar2, mtp2 = ssum(("base", "published", "candidate", "lever"))
    comps["unified_candidate"] = dict(AR_us=ar2, MTP_step_us=mtp2, AR_tok_s=tok_s_us(ar2), MTP_tok_s=tok_s_us(mtp2, tau), tau=tau,
                                      status="priced-candidate", gated_by=gates,
                                      note="as above + the exact HBM levers (minimum-component exactness, SS/FF not admitted)")
    sram = next(x for x in lines if x["id"] == "collective_sram_protected")["effect"]
    for cname, (dar, dmtp, label) in dict(
            unified_candidate_refill_cdc_only=(H_CDC_V["lat_us"] + H_CDC_V["ii3_AR_us"], H_CDC_V["lat_us"] + H_CDC_V["ii3_MTP_us"],
                                               "refill lands for the CDC only; the packet SRAM stays at II=3 and caps the port"),
            unified_candidate_refill_both=(H_CDC_V["lat_us"], H_CDC_V["lat_us"],
                                           "refill lands for both the CDC and the packet SRAM (full line rate)")).items():
        a_ = round(ar2 - sram["AR"] + dar, 3); m_ = round(mtp2 - sram["MTP_step"] + dmtp, 3)
        comps[cname] = dict(AR_us=a_, MTP_step_us=m_, AR_tok_s=tok_s_us(a_), MTP_tok_s=tok_s_us(m_, tau), tau=tau,
                            status="priced-candidate", case=label,
                            gated_by=[g for g in gates if not (g == "packet_sram_ii3_rate_cap" and cname.endswith("both"))],
                            conditional_on_unestablished_contracts=(["cdc_frequency_lock", "credit_producer_native", "packet_sram_refill", "sm_su_native_edge"]
                                                                    if cname.endswith("both") else ["cdc_frequency_lock", "credit_producer_native", "sm_su_native_edge"]),
                            note="CONDITIONAL sensitivity, zero credit until its contracts are established. unified_candidate with the +2 x 265 SRAM term replaced by the refill's +2 cycles x 610 passes"
                                 + (" plus the packet-SRAM II=3 serialisation cost" if cname.endswith("cdc_only") else
                                    "; full rate also requires the native credit producer (gated)"),
                            record=[src(H_REFILL, "status", commit=H_REFILL_COMMIT), src(H_CDC2, "comparison", commit=H_CDC2_COMMIT)])
    alt = {x["id"]: x["effect"] for x in lines if x["id"] in ("sm_su_native_edge_proposed", "sm_su_store_forward_floor")}
    rb = comps["unified_candidate_refill_both"]
    a_ = round(rb["AR_us"] + alt["sm_su_native_edge_proposed"]["AR"], 3); m_ = round(rb["MTP_step_us"] + alt["sm_su_native_edge_proposed"]["MTP_step"], 3)
    comps["unified_candidate_contracts_rtl"] = dict(
        AR_us=a_, MTP_step_us=m_, AR_tok_s=tok_s_us(a_), MTP_tok_s=tok_s_us(m_, tau), tau=tau, status="priced-candidate",
        case="CDC + packet-SRAM II=1 refill, native credit producer, clock-lock idle insertion and the native SM -> SU edge "
             "(1,029 cycles a token) -- all four established at RTL + bench level (444859f1d gate_all PASS)",
        gated_by=[g for g in gates if g not in ("packet_sram_ii3_rate_cap", "credit_producer_native", "cdc_frequency_lock",
                                                 "sm_su_result_edge_native")],
        result_edge="native SM -> SU edge RTL + bench (444859f1d); physical screen pending",
        record=[src(HBM_GATE, "status, cases"), src(H_REFILL, "status", commit=H_REFILL_COMMIT)],
        note="refill_both + the native-edge increment (+686 cycles over the published 343); RTL-level credit only: the four "
             "contracts' physical screens, die integration and the CDC refill SS timing remain open")
    for cname, c_ in comps.items():
        if cname == "unified_candidate_contracts_rtl":
            continue
        c_["result_edge"] = "die-view-only result edge until gate sm_su_result_edge_native closes"
        gb = c_.setdefault("gated_by", [])
        if "sm_su_result_edge_native" not in gb:
            gb.append("sm_su_result_edge_native")
    for cname in ("unified_candidate",):
        c_ = comps[cname]
        c_["sm_su_alternatives"] = {}
        for k, e in alt.items():
            a_, m_ = c_["AR_us"] + e["AR"], c_["MTP_step_us"] + e["MTP_step"]
            c_["sm_su_alternatives"][k] = dict(AR_tok_s=tok_s_us(a_), MTP_tok_s=tok_s_us(m_, tau),
                                              AR_pct=round(100 * e["AR"] / c_["AR_us"], 2),
                                              MTP_step_pct=round(100 * e["MTP_step"] / c_["MTP_step_us"], 2))
    return dict(context="DeepSeek-V4.1 1M, HBM accelerator", tau=tau, lines=lines, compositions=comps, gates=gates,
                physical_status="die views priced; no full-die closure")


# ===================================================================================================== no-ECC inventory
def no_ecc():
    s = lambda f, p=None: src(f, p)
    return [
        dict(target="qwen_rom", item="Weight and configuration ROM", protection="none", policy="compliant (owner 2026-10-02 ROM no-ECC)", source=s("AGENTS.md")),
        dict(target="ds_rom", item="Weight ROM (4096-row macros, 1792-pair mapping)", protection="none (ROM_ECC=false)", policy="compliant", source=s(f"{DS_MAP}/half_dedicated/inventory.json", "ROM_ECC")),
        dict(target="qwen_rom", item="STREAM4 KV transport, 128 pseudo-channel parallel landing (HBM -> die)", protection="none", policy="GAP: HBM/link protection is retained by policy; protected full-width transport not adopted", source=s(Q_CLOSURE, "kv_path.shipped")),
        dict(target="qwen_rom", item="Spine lane: 32x1536 payload FIFO, 32x32 tag FIFO, split/tag/valid pipeline, pointers/credits, fault/commit registers", protection="none (fault-free bench only)", policy="GAP: mutable state", source=s(Q_SPINE_P, "unprotected")),
        dict(target="qwen_rom", item="Controller SHIFT added state (FIFO head 32, bank eligibility 32, write-queue one-hot 128 bits per PC; 128 PCs)", protection="none in SHIFT; protected successor (duplicated state) routed on main at 72bfeccb1: retention PASS, physical not_met", policy="GAP: blocks production adoption", source=s(Q_CTRL_P, "state_breakdown")),
        dict(target="qwen_rom", item="Finite VM banks (ME/SU service)", protection="excluded from the service models (owner tags, protection/checks not sized)", policy="GAP: protected bank not bound", source=s(Q_VM_SU, "source_frame_storage_lower_bound_bits.excluded")),
        dict(target="qwen_rom", item="Forwarded-link opaque 16 control bits per stream", protection="integrity binding missing", policy="GAP (adoption gate)", source=s(Q_FWD, "endpoint_adoption_gates")),
        dict(target="qwen_rom", item="Relay stations (1,536) and column heads (64), 508-bit payload", protection="dual-fault replicas, default off", policy="candidate", source=s(Q_STATION, "replicas")),
        dict(target="ds_rom", item="S81 VM raw macro backend", protection="none (64 empty protection slots reserved, not RTL)", policy="GAP: mutable SRAM", source=s(DS_HBMB, "S81_r8_superseding_physical_binding.VM")),
        dict(target="ds_rom", item="S81 PQ root CAM state (+387 bits a root, 49,536 for 128 roots) and the root face", protection="none: native interface lacks the proposed parity; protected 140/141-pin face OPEN", policy="GAP: mutable state, unestablished contract", source=s(PQ_CAM_MODEL, "mutable_state_protection")),
        dict(target="hbm_ds", item="Collective packet SRAM", protection="protected full-depth candidate (default off, +2 queue cycles)", policy="candidate", source=s(H_SRAM, "queues")),
        dict(target="hbm_ds", item="SM serial command/record path", protection="protected successor (preserved duplicate state + fault gating) committed on origin/main at 65988656b; minimum-parent gate passed, selected=false", policy="GAP until selected and physically integrated", source=src("results/rtl/hbm_sm_command_20261007/protected_component.json", "passed, selected")),
        dict(target="all", item="Off-package links", protection="full RS(544,514) FEC", policy="compliant (owner 2026-10-06)", source=s(DS_LINKS, "decision")),
    ]


# ===================================================================================================== publication audit
STALE = [
    dict(file="docs/INTEGRATED_PHYSICAL_PLAN.md", claim="'Qwen ROM CLOSED (owner decision, 2026-10-06)' with 5,537.3 tok/s as a closed headline",
         why="Qwen ROM reopened 2026-10-07 (directive 14); 216,713 includes priced (not routed) relays", action="relabelled as a candidate composition; history kept"),
    dict(file="docs/PROGRAM_PLAN_2026_10_05.md", claim="Qwen row 'CLOSED'; DS 1,675.0 / 4,895.0 'all measured'; HBM 2,173.7 / 4,683.2; ratios 0.77x / 1.05x / 1.24x / 2.49-2.57x",
         why="DS pre-closure and on the 85-stage geometry; HBM before die closure costs; Qwen reopened", action="2026-10-07 status note added above the table; rows kept as dated history"),
    dict(file="docs/ARCHITECTURE_ATLAS.html", claim="'Qwen ROM headline - closed configuration' (sec. 1 list, sec. 8 finding, Table 8-4 'composed from measured')",
         why="reopened; relay term priced", action="relabelled 'candidate configuration'; relay row already says priced"),
    dict(file="docs/ANALYTICAL_REPORT.md", claim="'Qwen ROM closed headline' 5,537.3 in sec. Qwen; DS/HBM ratio text",
         why="reopened; candidate", action="qualified as candidate; unified ledger cited; DSpark re-evaluation added"),
    dict(file="tools/chip_explorer_build.py", claim="Qwen AR status 'measured'; HBM DS cards show 1,948.8 / 3,944.2 (no die closure costs); DS without 1792 caveat",
         why="mislabelled status; stale HBM headline", action="Qwen AR -> analytical candidate; HBM cards show the unified closure-inclusive candidate; pre-closure kept for the waterfall"),
    dict(file="results/arch/energy_silicon_measured/README.md", claim="DS ROM 1,603.3 / 4,717.7 rows (record STALE vs the scoreboard on main)",
         why="--check failed at 449ebc571", action="regenerated (1,596.7 / 4,702.0) with a scope note on the 85-stage geometry and Qwen reopen"),
    dict(file="results/rtl/dsrom_closure_cost_ledger_20261007/ledger.md (branch claude/dsrom-bf-double-20261007)",
         claim="bf_merge_ksplit AR 1,728.6 (+7.82 %), MTP +6.43 %", why="BF16-phase-only figure; the full-field same-frame "
         "measurement is +2.33 % AR / +1.63 % MTP (option A, 1,645.8 vs base_f198 1,608.4)", action="ledger line uses the full-field figure; +7.8 % marked superseded"),
    dict(file="results/arch/three_machine_compose/table.txt", claim="DS ROM / HBM AR 0.8193x MTP 1.1921x",
         why="HBM side excludes die closure costs", action="not rewritten (pinned record); superseded by unified ledger ratios"),
]


UNESTABLISHED = [
    ("pq_root_protected_face", "ds_rom", "Protected PQ root 140/141-pin face and parity", "pq_root_protected_face",
     "native root interface lacks the proposed parity (main 4251eb216 model: mutable_state_protection)"),
    ("pq_stage_b_timing", "ds_rom", "PQ CAM stage-B timing", "pq_stage_b_timing", "not measured; stage-C fallback modelled, default-off"),
    ("half_serial_lane_beat_shift", "ds_rom", "HALF serial-lane exactness for a <= 2-cycle beat shift", "pq_half_serial_lane_exactness",
     "not shown"),
]


# Die-level evidence (OWNER STEER 2026-10-07 ~19:00 PT: academic validation, not tape-out). Hierarchical sign-off:
# blocks at full rigor; per die: GRT overflow 0, die SS/FF STA on GRT parasitics, CTS-validated clock plan, IR, and
# detail route of REPRESENTATIVE REGIONS with the GRT-vs-DRT error bar. NO flat full-die DRT, by design.
# status: done | in progress | missing.  "in progress" names live work from the stream logs (no credit until committed).
# Contracts established at RTL + bench level (committed gate records). Credit only in the compositions that name them;
# physical screens and die integration remain open, so no physical credit.
HBM_GATE = "results/rtl/hbm_contracts_20261007/gate_all/record.json"   # 444859f1d: 12 positives / 20 negatives PASS
ESTABLISHED_RTL = [
    ("sm_su_native_edge", "hbm_ds", "SM -> SU native result edge (1,029 cycles a token priced; bench latency within it)",
     "sm_su_result_edge_native", HBM_GATE, "smsu_edge_* + 5 negatives; 12/12 golden composed cases (sm_su_composed)"),
    ("credit_producer_native", "hbm_ds", "Native credit producer (registered allow / can_send; D_tx >= 27)",
     "credit_producer_native", HBM_GATE, "credit_* 2 positives / 8 negatives; 0 cycles a token, +3 at link-up"),
    ("packet_sram_refill", "hbm_ds", "Packet-SRAM II=1 refill (ENABLE_SRAM=2)", "packet_sram_ii3_rate_cap", HBM_GATE,
     "pkt_ii1_* 4 positives / 3 negatives"),
    ("cdc_frequency_lock", "hbm_ds", "Clock lock via idle insertion (+-200 ppm, M <= 4,999)", "cdc_frequency_lock", HBM_GATE,
     "idle_* 4 positives / 4 negatives; 0 cycles for bursts <= 1,024 flits, worst 0.098 % of TX slots"),
    ("link_credit_rtt", "qwen_rom", "Qwen hub link credits CR=128 >= measured 117/119-cycle RTT", "link_credit_rtt", None,
     "exact gate rate 1.000 at 54/55 hops, 4 negatives; +0 token cycles (qwen-contracts)"),
]


DIE_ITEMS = ("grt_overflow", "die_sta_grt_parasitics", "cts_skew_plan", "ir", "region_drt_and_error_bar")


def die_level_evidence():
    Q = "results/rtl/qwen_rom_closed_20261006/closure.json"
    QIR = "results/rtl/qwen_rom_die_r17_20261005/ir/ir_record.json"
    S = "results/rtl/dsrom_s81_fulldie_20261004"
    B = "results/rtl/budgets_20261006/README.md"
    H = "results/rtl/hbm_accel_die_views_20261006/die_r10.json"
    HF = "results/rtl/hbm_accel_die_floorplan_20261005/feasibility.json"
    q = _J(Q)["physical"]["die_r20c"]
    s9 = {v: _J(f"{S}/{v}/feasibility.json")["cases"] for v in ("v9d", "v9e")}
    ov = lambda c: sum(l.get("overflow_total", 0) for l in c["grt"]["layers"].values())
    hir = _J(HF)["ir_summary"]
    ir_last = max((k for k in hir if k.startswith("ir1")), key=lambda k: int("".join(ch for ch in k[2:] if ch.isdigit()) or 0))
    E = dict(policy="no flat full-die detail route, by design (owner steer 2026-10-07); representative regions only",
             qwen_rom=dict(
                 grt_overflow=dict(status="in progress", evidence=src(Q, "physical.die_r20c.grt_i50"),
                     note="last committed full-die GRT r20c i50 overflow %s (NOT CLOSED); r21 GRT overflow 71,398 traced to the "
                          "PDN being counted twice (grt.tcl PG-proxy on a PDN odb). qwen-dietop.log 19:32 reports full-die GRT overflow 0 "
                          "(adjfix_t4p8, M4-M9, 8,057,897 nets) on the r21 PDN floorplan; no committed record yet, so not done" % format(q["grt_i50"]["overflow"], ",")),
                 die_sta_grt_parasitics=dict(status="in progress", evidence=src("tools/qwen_die_sta_classes.py", "r21 pre-DRT die STA", commit="a9bf510a0"),
                     note="committed: r21 die STA on placement parasitics fails every relay / station hop (SS -287 ps worst; closed "
                          "station views were routed at 3.9 fF, re-route kit at 80 fF committed a9bf510a0). Reported in qwen-dietop.log, "
                          "not committed: on the overflow-0 full-die GRT (adjfix_t4p8, estimate_parasitics -global_routing, signoff833 "
                          "ETMs) SS WNS -90.23 ps / TNS -8.69 us (1,124,207 endpoints, almost all relay hops; chead -37.95, cst -20.02) "
                          "and FF worst -5.50 ps (qfd_tile assumed views); with every die hop on M8 the placement-length STA gives "
                          "+71.45 ps. Under owner option B the closing setup corner is TT; these SS figures are a sensitivity"),
                 cts_skew_plan=dict(status="missing", evidence=None,
                     note="the CTS-validated die clock plan (budgets_20261006) covers S81 and HBM only; Qwen forwarded-clock graph "
                          "is a candidate without CTS validation"),
                 ir=dict(status="done", evidence=src(QIR),
                     note="r19 frame: worst interior %.2f mV vs 35 mV budget (window-edge maxima exceed 35 mV); frame predates r21/r22"
                          % q["ir"]["worst_interior_mv"]),
                 region_drt_and_error_bar=dict(status="missing", evidence=src(Q, "physical.die_r20c.die_top_route"),
                     note="the r20c representative-region pilot (66.6 mm2) was killed in CUGR maze routing; no region DRT and no "
                          "GRT-vs-DRT error bar")),
             ds_rom=dict(
                 grt_overflow=dict(status="done", evidence=[src(f"{S}/v9d/feasibility.json", "cases.*_k16_i50"), src(f"{S}/v9e/feasibility.json", "cases.hb_k16_i50")],
                     note="bundled full-die GRT i50 overflow: scan %d, layer1 %d (v9d, 2,048 pairs), head %d (v9e); pin access + "
                          "legality 0. On the previous geometry: the actual 1,792 mixed geometry has no full-die GRT yet"
                          % (ov(s9["v9d"]["sb_k16_i50"]), ov(s9["v9d"]["l1b_k16_i50"]), ov(s9["v9e"]["hb_k16_i50"]))),
                 die_sta_grt_parasitics=dict(status="missing", evidence=None,
                     note="no die SS/FF STA on GRT parasitics (frame-block / macro-context vehicles only)"),
                 cts_skew_plan=dict(status="done", evidence=src(B, "section 1 table"),
                     note="clock-only CTS validates the plan for scan/layer, layer1 and head (trunk bound 45-50 ps, columns <= 37.9 ps, "
                          "meso wander 384-386 ps < 417 ps, tight) on r9m215_v4, not on the 1,792 geometry"),
                 ir=dict(status="done", evidence=src(f"{S}/STATUS.md", "PSM IR table"),
                     note="PSM rail-to-rail interior 28.6-32.2 mV (r5/r7 frames, before the recovery levers) and 13.3 mV interior on "
                          "r9m215 v3; not re-run on the 1,792 geometry"),
                 region_drt_and_error_bar=dict(status="missing", evidence=None,
                     note="no representative-region DRT or GRT-vs-DRT error bar; the v9b_r1 die-top DRT resume on EPYC3 (s81-die) "
                          "is a flat run, outside the steer")),
             hbm_ds=dict(
                 grt_overflow=dict(status="in progress", evidence=src(H, "overflow"),
                     note="last committed full-die GRT record r10 overflow 371 (i5) / 454 (i50); later rounds (r14b/r16g 'routes "
                          "clean', r23c wire record) have no committed overflow record in the tree; hbm-die owns the r23 die"),
                 die_sta_grt_parasitics=dict(status="in progress", evidence=None,
                     note="relay-die STA r23_rly1 (1,056 relays, clock-plan entry per pin, placement RC) SS+FF running on EPYC2 "
                          "(hbm-die); not yet GRT parasitics, not committed"),
                 cts_skew_plan=dict(status="done", evidence=src(B, "section 1 table"),
                     note="clock-only CTS validates the r16j plan: 34 regions, intra bound max 56.7 ps (budget 29-90), meso wander "
                          "270 ps < 417 ps; the r23 die and the explicit clock inputs (148467f54) are not re-validated"),
                 ir=dict(status="done", evidence=src("results/physical/hbm_die_20261007/ir_r23/feasibility_r23.json", "ir_summary.r23",
                                                     commit="55e136da6 (branch claude/hbm-die-20261007)"),
                     note="r23 die: PSM on every window, 125/125 load windows PASS, worst interior 33.26 mV (budget 35; 18 no-load "
                          "windows). Earlier rounds on main: %s all_pass=%s, %.2f mV"
                          % (ir_last, hir[ir_last]["all_pass"], hir[ir_last]["worst_interior_rail_to_rail_mv"])),
                 region_drt_and_error_bar=dict(status="missing", evidence=None,
                     note="the r23c die-top DRT (flat) was killed after 11 h (25,785 violations, 10 % of iteration 0); no region "
                          "DRT or error bar yet")))
    geo = dict(qwen_rom=dict(grt_overflow="r20c", ir="r19 frame"),
               ds_rom=dict(grt_overflow="v9d/v9e (2,048 pairs), not the 1,792 basis", cts_skew_plan="r9m215_v4, not the 1,792 basis",
                           ir="r5/r7 and r9m215 v3, not the 1,792 basis"),
               hbm_ds=dict(grt_overflow="r10", cts_skew_plan="r16j, not r23", ir="r23"))
    for t_, items in geo.items():
        for k, g in items.items():
            E[t_][k]["geometry"] = g
    return E


LB_FILE = "results/arch/unified_composition_20261007/link_budget_restatus_20261007.json"


def _link_budget_summary():
    """Consistent die-link budget applied to every closed block job (coordinator decision 2026-10-07)."""
    d = _J(LB_FILE)
    by = {}
    for r in d["rows"]:
        ss = r.get("period_correction", r["link_budget_ss_ps"])
        v = "NOT CHECKED" if r["verdict"] == "NOT CHECKED" else ("HOLDS" if ss >= 0 else "REVOKED")
        by.setdefault(v, []).append(dict(job=r["job"], block=r["block"], closed_ss_ps=r["closed_ss_ps"],
                                                    link_budget_ss_ps=r.get("period_correction", r["link_budget_ss_ps"])))
    return dict(closure_line="OWNER DECISION 2026-10-07: SS >= 0 ps / FF >= 0 ps / DRC 0 at 833.333 ps sign-off (+15 ps is a "
                             "design target only); consistent die-link budget and rule H1 still apply",
                rule=d["rule"], method=d["method"], record=src(LB_FILE),
                counts_at_re_sta=d["counts"], counts_under_closure_line={k: len(v) for k, v in by.items()},
                holds=by.get("HOLDS", []),
                revoked=dict(label="revoked: link budget", jobs=by.get("REVOKED", [])),
                unverified=dict(label="unverified (needs a per-link model)", reason=d["unchecked_reason"], jobs=by.get("NOT CHECKED", [])),
                requeued=d["requeued"],
                option_b_status=dict(record=src("results/closure_loop/option_b_status_20261007/status.json", "counts"),
                                     counts=_J("results/closure_loop/option_b_status_20261007/status.json")["counts"],
                                     note="AUTHORITATIVE under owner option B: TT setup >= 0 under the consistent link budget, FF >= 0, "
                                          "DRC 0 (TT re-STA of the final routes, 614782370). Supersedes the SS re-STA counts above; "
                                          "13 previously closed blocks fail TT under the budget (may change: setup-triage is checking "
                                          "a possible reset-path artifact)"),
                reclosed=[dict(job="qfd_lst_h-5a3bb1721-lbc", block="qfd_lst_h", ss_ps=244.84, ff_ps=42.17, drc=0,
                               record=src("results/rtl/qwen_die_masters_20261006", "closure-loop verdict",
                                          commit="a95df3ae1 (branch claude/setup-triage-20261007; routed at 387a4d2ac with the link-budget hook)"))],
                consequence="a job counts as closed only if its link-budget SS is >= 0 (closure line); revoked and unverified "
                            "jobs carry no closure credit until their re-routes re-close under the consistent budget")


def _pins(rec):
    """sha256 of every cited source file present in this tree (immutable evidence pin)."""
    files = set()

    def walk(x):
        if isinstance(x, dict):
            if isinstance(x.get("file"), str):
                files.add((x["file"], "branch" in str(x.get("commit", ""))))
            for v in x.values():
                walk(v)
        elif isinstance(x, list):
            for v in x:
                walk(v)
    walk(rec)
    out = {}
    for f, branch_only in sorted(files):
        path = ROOT / f
        if branch_only:
            out.setdefault(f, "branch-only citation: pinned by the commit cited at the line, not by this tree's copy")
        else:
            out[f] = hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else "not in this tree (pinned by the commit cited at the line)"
    return out


def ledger():
    q, d, h = qwen(), ds_rom(), hbm_ds()
    hu = h["compositions"]["unified_candidate"]
    ratios = dict(
        basis="per user, same tau on both sides; both sides priced-candidate",
        ds_rom_published_over_hbm_unified=dict(AR=round(d["compositions"]["published"]["AR_tok_s"] / hu["AR_tok_s"], 4),
                                               MTP=round(d["compositions"]["published"]["MTP_tok_s"] / hu["MTP_tok_s"], 4)),
        ds_rom_1792_half_dedicated_over_hbm_unified=dict(note="measured-field 1,792 HALF composition (half-rate BF upper bound) over the HBM unified candidate",
            AR=round(d["compositions"]["actual1792_half_dedicated"]["AR_tok_s"] / hu["AR_tok_s"], 4),
            MTP=round(d["compositions"]["actual1792_half_dedicated"]["MTP_tok_s"] / hu["MTP_tok_s"], 4)),
        stale=dict(record=src(CMP, "ratios"), AR=load(CMP)["ratios"]["ds_rom_over_hbm_ar"], MTP=load(CMP)["ratios"]["ds_rom_over_hbm_mtp"],
                   why="HBM side without die closure costs"))
    rec = dict(schema="opentallas.unified-composition.v1", date="2026-10-07",
               rule=("status: measured = committed RTL/physical measurement composed as recorded; priced-candidate = an analytic "
                     "price of a committed design/candidate (or a measured component not admitted at SS/FF); gated-unknown = a "
                     "cost that is not bound and is never summed. A numerical component PASS is not physical adoption."),
               targets=dict(qwen_rom=q, ds_rom=d, hbm_ds=h), ratios=ratios, no_ecc_inventory=no_ecc(), stale_claims=STALE,
               die_level_evidence=die_level_evidence(),
               block_signoff_link_budget=_link_budget_summary(),
               established_contracts_rtl_bench=[dict(id=i, target=tg, contract=nm, ledger_line=ln, evidence=(src(ev) if ev else
                                                     next(x for x in dict(qwen_rom=q, ds_rom=d, hbm_ds=h)[tg]["lines"] if x["id"] == ln)["source"]),
                                                     bench=bn, level="RTL + bench (exact, negatives detected)",
                                                     performance_credit="only in compositions that name it; physical screen / die integration pending")
                                                for i, tg, nm, ln, ev, bn in ESTABLISHED_RTL],
               unestablished_contracts=[dict(id=i, target=tg, contract=nm, ledger_line=ln, state=st, performance_credit=0,
                                             source=next(x for x in dict(qwen_rom=q, ds_rom=d, hbm_ds=h)[tg]["lines"] if x["id"] == ln)["source"])
                                        for i, tg, nm, ln, st in UNESTABLISHED],
               tool=dict(file="tools/unified_composition.py",
                         sha256=hashlib.sha256((ROOT / "tools/unified_composition.py").read_bytes()).hexdigest()))
    rec["source_sha256"] = _pins(rec)
    return rec


def _commitless(x):
    """--check ignores commit hashes (they change when this record itself is committed)."""
    if isinstance(x, dict):
        return {k: _commitless(v) for k, v in x.items() if k != "commit"}
    if isinstance(x, list):
        return [_commitless(v) for v in x]
    return x


@functools.lru_cache(maxsize=1)
def _committed():
    return json.loads((OUT / "ledger.json").read_text())


def target(name, rec=None):
    return (rec or _committed())["targets"][name]


def composition(tname, cname, rec=None):
    return target(tname, rec)["compositions"][cname]


def line(tname, lid, rec=None):
    return next(x for x in target(tname, rec)["lines"] if x["id"] == lid)


def lines(status=None, rec=None):
    r = rec or _committed()
    return [dict(x, target=t) for t, v in r["targets"].items() for x in v["lines"] if status in (None, x["status"])]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args(argv)
    rec = ledger()
    text = json.dumps(rec, indent=1) + "\n"
    if a.check:
        old = json.loads((OUT / "ledger.json").read_text())
        if _commitless(old) != _commitless(rec):
            print("unified_composition: STALE: re-run tools/unified_composition.py")
            return 1
        print("unified_composition: current")
        return 0
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "ledger.json").write_text(text)
    for t, v in rec["targets"].items():
        for c, x in v["compositions"].items():
            print("%-8s %-34s AR %8s tok/s  MTP %8s  %s" % (t, c, x.get("AR_tok_s"), x.get("MTP_tok_s", "-"), x["status"]))
        print("%-8s gates: %s" % (t, ", ".join(v["gates"])))
    print("ratios", json.dumps(rec["ratios"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
