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
BF_BRANCH = "origin/claude/dsrom-bf-double-20261007"
BF_BRANCH_COMMIT = "332983233"
# bf_merge_ksplit full-field same-frame measurement (coordinator correction 2026-10-07); record not on main
BFA_FILE = "results/rtl/dsrom_bf_double_20261007/recovery_provenance.json"
BFA_COMMIT = "4534a8e5f (origin/codex/bf-evidence-only-20261007, BF agent records of claude/dsrom-bf-double-20261007; not on main)"
BFA = dict(AR=1645.8, MTP=4841.9, base_AR=1608.4, base_MTP=4764.3, stages=96)
# option B (mixed 2,304 pairs, 85 stages), Codex "DS ADOPT" 505a9b484 on origin/codex/restore-bf-pairs-20261007; not on main
BFB_COMMIT = "52f5f1963 (origin/codex/restore-bf-pairs-20261007; adoption commit 505a9b484; not on main)"
GEO_B = None
BFB = dict(AR=1754.3, MTP=5098.3, base_AR=1603.3, base_MTP=4717.7, stages=85, pairs=2304, layer_dies=340, regions=18288,
           label="DS ADOPT bf_merge_ksplit on the mixed-slot S81 die: AR 1,603.3 -> 1,754.3 (+9.42 %), MTP 4,717.7 -> 5,098.3 (+8.07 %), MEASURED full field",
           physical="PENDING: mixed 2304-pair geometry not routed; uniform 2048-pair S81 v9d is different. Final PQ/BF footprints and die station cycles must be priced before physical adoption.",
           wire="ESTIMATED f183.60 round trips for mixed slot option")


def load(rel):
    return json.loads((ROOT / rel).read_text())


@functools.lru_cache(maxsize=None)
def commit_of(rel):
    """Last commit that touched `rel` (repository history, not the working tree)."""
    try:
        out = subprocess.check_output(["git", "log", "-1", "--format=%h", "--", rel], cwd=ROOT, text=True,
                                      stderr=subprocess.DEVNULL).strip()
    except subprocess.CalledProcessError:
        out = ""
    return out or "uncommitted (this delivery)"


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
def qwen():
    q = load(CMP)["qwen_rom"]
    lv = q["levers"]
    rel = load(Q_RELAY)
    ctrl, ctrlq = load(Q_CTRL), load(Q_CTRL_Q)
    fwd, fwdv = load(Q_FWD), load(Q_FWD_VAL)
    me = load(Q_VM_ME)
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
          "physical unmeasured; added mutable state unprotected (blocks production adoption)"
          % (ctrlq["status"], ctrl["latency"]["composed_worst_case_token_cycles"],
             ctrlq["predecessor_measurement"]["ss_ps"], ctrlq["predecessor_measurement"]["ff_ps"]), "candidate"),
        L("forwarded_clocks", "Direction-owned forwarded link clocks (217 primitives, 442 directional clock nets)", "priced-candidate",
          dict(unit="cycles", AR=fwd["latency"]["replacement_added_single_user_token_cycles"]), src(Q_FWD, "latency"),
          "same registered-hop count as r21 (0 added stage cycles); area proxy %.0f um2; active graph simulated=%s, adopted=%s"
          % (fwd["area_proxy_um2"], fwdv["active_graph_simulated"], fwdv["adopted"]), "candidate"),
        L("link_credit_rtt", "Link credit capacity vs the forwarded-path transport round trip", "gated-unknown", None,
          src(Q_FWD, "paths[].transport_credit_roundtrip_cycles"),
          "registered path %s stations, credit RTT %s cycles; the historical 8-credit abstract does not sustain it. "
          "Per-traversal stall unknown until endpoint credit capacity/service is composed"
          % (sorted({p["registered_stations"] for p in fwd["paths"]}), sorted({p["transport_credit_roundtrip_cycles"] for p in fwd["paths"]})), "gate"),
        L("vm_me_service", "Native VM ME bank service (captured W1 source slots, protected bank)", "gated-unknown", None,
          src(Q_VM_ME, "serialized_reference"),
          "full_token_extra=null; the only priced reference is the serialized four-bank walker: +%s engine edges for the "
          "264 captured edges of ONE component (not a token cost, not composable); ready_for_new_bank_RTL=%s"
          % (format(me["serialized_reference"]["conditional_extra_engine_edges"], ","), me["ready_for_new_bank_RTL"]), "gate"),
        L("vm_su_service", "VM SU/reducer bank service obligations", "gated-unknown", None, src(Q_VM_SU, "scope"),
          "service quanta are not clock cycles; SRAM, protection, write completion, mux, fanout, capture unbound", "gate"),
        L("vm_recovery", "Qwen VM bank recovery / native schedule binding", "gated-unknown", None, src(Q_VM_REC, "status"),
          load(Q_VM_REC)["status"] + "; one dynamic writer unresolved", "gate"),
        L("die_top_route", "Full-die detailed route, SS/FF, DRC and IR of the reopened Qwen die (directive 14)", "gated-unknown", None,
          src(Q_CLOSURE, "physical"), "die-top route not done; r18g bound (+13,305..16,268 cycles) is history, not composed", "gate"),
        L("routed_masters", "Real routed views for previously assumed masters", "gated-unknown", None,
          src("docs/OWNER_DIRECTIVES_2026_10_07.md"), "interim views cannot establish closure; relay masters qfd_cst / qfd_chead "
          "closed at 833 ps (+57.00/+17.75, +37.93/+17.62) carry no cycle change", "gate"),
        L("protected_kv_transport", "Protected KV transport (HBM->die landing)", "gated-unknown", None,
          src(Q_CLOSURE, "kv_path.protected_full_width_transport"),
          "shipped STREAM4 landing has no transport protection; protected full-width path has no full token (full36_r1 FAIL "
          "retained); cost unknown", "gate"),
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
            link_credit=dict(note=("gated: per-traversal credit stall x unknown.  AR crosses the link %d times a token, a step %d "
                                   "times for %.4f tokens, so link stalls hurt AR more per token" % (ar_link, step_links, tau)),
                             break_even_stall_cycles_per_traversal_equal_payload=round(x_eq),
                             break_even_if_verify_stall_scales_with_np=(round((step / tau - pub) / den) if den > 0 else None),
                             reading=("DSpark reaches AR only if each link traversal stalls >= %d cycles and the verify "
                                      "traversal (np=%d positions) stalls no more than an AR one; if the stall scales "
                                      "with payload the threshold %s" % (round(x_eq), np_,
                                      "is %d" % round((step / tau - pub) / den) if den > 0 else "is never reached"))),
            die_route_and_masters="gated: affects AR and the step through the same ME-op and link counts",
            tau="third-party 3.1445 (no Qwen DSpark acceptance measured on the target workload mix)"),
        verdict=("AR_MODE holds: the re-evaluation with the newer priced inputs gives %.1f tok/s (%.3fx); every gated "
                 "per-ME-op cost moves the ratio down; only an unmeasured link-credit stall above ~%d cycles a traversal "
                 "could move it up" % (new["variants"]["baseline_np4"]["tok_s_upper"],
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
        L("actual1792_half_dedicated_hops", "Actual 1792 mapping, BF-dedicated half-rate (%d stages: %d BF + %d q): +%d stage hops"
          % (var["half_dedicated"]["stages"], var["half_dedicated"]["bf_stages"], var["half_dedicated"]["q_stages"],
             var["half_dedicated"]["extra_hops_vs_composed"]),
          "priced-candidate", dict(unit="us", AR=round(var["half_dedicated"]["extra_hops_vs_composed"] * hop_us, 3),
                                   MTP_step=round(var["half_dedicated"]["extra_hops_vs_composed"] * hop_us, 3)),
          [src(f"{DS_MAP}/half_dedicated/inventory.json", "stages"), src(DS_LINKS, "hop.us")],
          "each added stage = one measured full-FEC board hop %.4f us + %.4f us cable; capacity PASS, metadata only" % (links["hop"]["us"], hop_us - links["hop"]["us"]),
          "alternative"),
        L("actual1792_full_shared_hops", "Actual 1792 mapping, shared BF pairs (%d stages, gate K-split alias): +%d stage hops"
          % (var["full_shared"]["stages"], var["full_shared"]["extra_hops_vs_composed"]),
          "priced-candidate", dict(unit="us", AR=round(var["full_shared"]["extra_hops_vs_composed"] * hop_us, 3),
                                   MTP_step=round(var["full_shared"]["extra_hops_vs_composed"] * hop_us, 3)),
          [src(f"{DS_MAP}/full_shared/inventory.json", "stages"), src(DS_LINKS, "hop.us")], "as above", "alternative"),
        L("bf_half_rate_doubling", "BF half-rate (owner 2026-10-07): BF16 field phases doubled", "priced-candidate",
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
          "measured exact (19,056/19,056 regions, both runs bit-exact), UNADOPTED, FULL-RATE BF: AR %.1f vs base_f198 %.1f "
          "(+%.2f %%), MTP %.1f vs %.1f (+%.2f %%). Supersedes the +7.82 %% figure (BF16-phase-only, ledger.md on %s). "
          "Option B (2,304 pairs) failed legal fit: see bf_merge_ksplit_option_B. Under the half-rate 1792 geometry its gain "
          "is unmeasured, so it is listed, never summed"
          % (BFA["AR"], BFA["base_AR"], 100 * (BFA["AR"] / BFA["base_AR"] - 1), BFA["MTP"], BFA["base_MTP"],
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
        L("field_phases_1792", "Field phase timings of the 1792 geometry (remapped regions, BF/q stage split)", "gated-unknown", None,
          src(f"{DS_MAP}/provenance.json", "variants.*.full_token_latency"), "'unpriced until matching field phase measurements and new geometry timing are composed'", "gate"),
        L("bf_half_physical", "BF half-rate clock root qualification (current exact BF closure path)", "gated-unknown", None,
          [src(DS_BFROOT, "physical_obligations"), src(DS_BFFAIL + "/record.json"), src(DS_BFFAIL + "/actual_calibration_failure.json")],
          "half-rate BF is the current exact BF closure path, not an immutable requirement: full rate may return if it meets "
          "the correctness and physical gates. The 449ebc571 root-phase failure was a script hierarchy failure (not an "
          "arithmetic rejection), fixed in 7990dfdbf and now calibrating; SS/FF >= +15 ps, DRC 0 still to be shown", "gate"),
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
    for name, hops in (("half_dedicated", "actual1792_half_dedicated_hops"), ("full_shared", "actual1792_full_shared_hops")):
        h = next(x for x in lines if x["id"] == hops)["effect"]
        ar, mtp = pub_ar + h["AR"] + bf_ar, pub_mtp + h["MTP_step"] + bf_mtp
        v = var[name]
        comps["actual1792_" + name] = dict(
            AR_us=round(ar, 3), MTP_step_us=round(mtp, 3), AR_tok_s=tok_s_us(ar), MTP_tok_s=tok_s_us(mtp, tau), tau=tau,
            stages=v["stages"], dies=v["layer_dies"], pairs_per_layer_die=1792, bf_rate="half",
            dies_note=("%d = layer dies, the Codex basis (2d811aafb inventory layer_dies). An earlier revision of this ledger "
                       "printed %d by also counting the %d head + %d table + %d draft dies of the 85-stage rack record; those "
                       "are outside the 1792 mapping and not re-sized for it" % (v["layer_dies"], v["layer_dies"] + rack["counts"]["head"]
                       + rack["counts"]["table"] + rack["counts"]["draft"], rack["counts"]["head"], rack["counts"]["table"], rack["counts"]["draft"])),
            basis=[src(DS_GEOM, "variants[name=mixed221]", commit="77ffa0428"), src(f"{DS_MAP}/{name}/inventory.json", "stages, layer_dies", commit="2d811aafb")],
            adopted=False, closure=False,
            status="priced-candidate (current physical integration basis; not an adopted rate)",
            label="partial-priced sensitivity (unmeasured field phases), not an adopted or guaranteed bound",
            bound="none proven",
            caveat=("BF16 doubling priced; field phases at this geometry unmeasured" if name == "half_dedicated" else
                    "BF16 doubling priced; shared-pair q-phase halving NOT priced (undercount); field phases unmeasured"),
            gated_by=gates, lines=[hops, "bf_half_rate_doubling"],
            note="published composition + extra stage hops + BF half-rate doubling; field phases at this geometry unmeasured")
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
    rows = []
    for l in (ROOT / H_LEDGER).read_text().splitlines():
        mm = re.match(r"\| (.+?) \| (\d+) \| ([\d.]+) \| ([\d.]+) \|$", l)
        if mm:
            rows.append((mm.group(1), int(mm.group(2))))
    pre = r23["pre_closure"]["AR_us"]
    lines = [
        L("matched_gate", "Matched reference gate (measured RTL nodes, light-FEC TU budget)", "measured",
          dict(unit="us", AR=m["AR_us"], MTP_step=m["MTP_step_us"]), src(H_MATCHED, "gate"), m["AR_row"], "base"),
        L("die_wire_r16j", "Die wire stages, r16j wire-priced (r13 GRT wire record)", "priced-candidate",
          dict(unit="us", AR=round(pre - m["AR_us"], 3), MTP_step=round(pre - m["AR_us"], 3)),
          src(H_R23, "pre_closure"), "same die traversals on the AR walk and the verify walk", "published"),
    ]
    for i, (name, cyc) in enumerate(rows):
        us = round(cyc / CLK * 1e6, 3)
        lines.append(L("closure_%02d" % i, name[:170], "priced-candidate", dict(unit="us", AR=us, MTP_step=us),
                       src(H_LEDGER, "row %d" % i), "die closure cost (stations / faces / splits / SM m2+m3 / relays / 2x hub)",
                       "published" if i < len(rows) - 1 else "candidate"))
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
        dict(target="qwen_rom", item="Controller SHIFT added state (FIFO head 32, bank eligibility 32, write-queue one-hot 128 bits per PC; 128 PCs)", protection="none", policy="GAP: blocks production adoption", source=s(Q_CTRL_P, "state_breakdown")),
        dict(target="qwen_rom", item="Finite VM banks (ME/SU service)", protection="excluded from the service models (owner tags, protection/checks not sized)", policy="GAP: protected bank not bound", source=s(Q_VM_SU, "source_frame_storage_lower_bound_bits.excluded")),
        dict(target="qwen_rom", item="Forwarded-link opaque 16 control bits per stream", protection="integrity binding missing", policy="GAP (adoption gate)", source=s(Q_FWD, "endpoint_adoption_gates")),
        dict(target="qwen_rom", item="Relay stations (1,536) and column heads (64), 508-bit payload", protection="dual-fault replicas, default off", policy="candidate", source=s(Q_STATION, "replicas")),
        dict(target="ds_rom", item="S81 VM raw macro backend", protection="none (64 empty protection slots reserved, not RTL)", policy="GAP: mutable SRAM", source=s(DS_HBMB, "S81_r8_superseding_physical_binding.VM")),
        dict(target="hbm_ds", item="Collective packet SRAM", protection="protected full-depth candidate (default off, +2 queue cycles)", policy="candidate", source=s(H_SRAM, "queues")),
        dict(target="hbm_ds", item="SM serial command/record path", protection="protection build in progress (uncommitted Codex work in the central checkout)", policy="GAP until committed", source=dict(file="tools/hbm_sm_serial_protection_model.py", pointer=None, commit="uncommitted (central checkout, Codex)")),
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


def ledger():
    q, d, h = qwen(), ds_rom(), hbm_ds()
    hu = h["compositions"]["unified_candidate"]
    ratios = dict(
        basis="per user, same tau on both sides; both sides priced-candidate",
        ds_rom_published_over_hbm_unified=dict(AR=round(d["compositions"]["published"]["AR_tok_s"] / hu["AR_tok_s"], 4),
                                               MTP=round(d["compositions"]["published"]["MTP_tok_s"] / hu["MTP_tok_s"], 4)),
        ds_rom_1792_half_dedicated_over_hbm_unified=dict(note="partial-priced sensitivity (unmeasured field phases), no bound proven",
            AR=round(d["compositions"]["actual1792_half_dedicated"]["AR_tok_s"] / hu["AR_tok_s"], 4),
            MTP=round(d["compositions"]["actual1792_half_dedicated"]["MTP_tok_s"] / hu["MTP_tok_s"], 4)),
        stale=dict(record=src(CMP, "ratios"), AR=load(CMP)["ratios"]["ds_rom_over_hbm_ar"], MTP=load(CMP)["ratios"]["ds_rom_over_hbm_mtp"],
                   why="HBM side without die closure costs"))
    rec = dict(schema="opentallas.unified-composition.v1", date="2026-10-07",
               rule=("status: measured = committed RTL/physical measurement composed as recorded; priced-candidate = an analytic "
                     "price of a committed design/candidate (or a measured component not admitted at SS/FF); gated-unknown = a "
                     "cost that is not bound and is never summed. A numerical component PASS is not physical adoption."),
               targets=dict(qwen_rom=q, ds_rom=d, hbm_ds=h), ratios=ratios, no_ecc_inventory=no_ecc(), stale_claims=STALE,
               tool=dict(file="tools/unified_composition.py",
                         sha256=hashlib.sha256((ROOT / "tools/unified_composition.py").read_bytes()).hexdigest()))
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
