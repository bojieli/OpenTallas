#!/usr/bin/env python3
"""Matched DS recovery DAG pricing; conditional measurements never adopt hardware.

Uses dsrom_1m_allmeasured.compose, including S81 WINDOW, head, draft, CDC,
wavefront busy times and the unchanged reduction/dependency graph. --su accepts
an exact full-shape node replacement record when the SU owner publishes it.
"""
from __future__ import annotations

import argparse
from collections import Counter
import copy
import hashlib
import json
import subprocess
from pathlib import Path
from types import SimpleNamespace

import dsrom_1m_allmeasured as A
import dsrom_1m_allmeasured_adapters as AD

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results/rtl/dsrom_recovery_20261004/decision_gate"


def load(p):
    return json.loads(Path(p).read_text())


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def summary(r):
    return dict(AR_us=r["AR_us"], AR_tok_s=r["AR_tok_s"], MTP=r["MTP"],
                cdc_on_path_us=r["cdc_on_path_us"],
                still_modelled=r["still_modelled"], hardware_qualified=False)


def replay(candidates=(), mutate=None):
    saved = {}
    def hook(g, p, base, info):
        if mutate:
            mutate(g, p)
        saved.update(graph=g, patches=p.rows)
    args = SimpleNamespace(rec=A.REC, out=None, baseline="recovery", recovery=A.RECOVERY,
                           window="s81", hop_tier="full_fec")
    record = A.compose(args, excluded_levers=("field", "su", "su_chains"),
                       candidates=candidates, graph_hook=hook, write_output=False)
    return record, saved["graph"], saved["patches"]


def field_evidence(candidate, measurement):
    """Historical contrast is deliberately separate from matched admission gain."""
    exact = measurement.get("status") == "pass" and all(x.get("exact") is True for x in measurement["nodes"])
    return dict(verdict="UNRESOLVED", exact_rows=exact, physical_verdict=candidate.get("ss_ff"),
        isolated_overlap_gain_us=None,
        experiment="serialization vs overlap on shared final2 candidate hardware",
        matched_required=dict(serialized_offer="top.idle", overlap_offer="top.ready",
            invariant="same binary/archive, PHW3, VAW17, R93/BF520, inputs, ordered phases and golden",
            terminal="actual last destination write / consumer-ready, not unit drain alone"),
        historical_confounders=["PHW2 -> PHW3", "VAW16 -> VAW17", "BF519 -> BF520/R93",
                                 "candidate tags/configuration shadow/context/walker"],
        minimum_physical_inputs=["candidate-context/shadow/walker cost vs the actual historical netlist",
            "R93 one Q-to-BF conversion and legal escape/placement cost separately",
            "pair and full-size spine SS60/FF25 in-context terminal; pair alone is insufficient"],
        adoption=False)


def dag_edges(g, patches):
    g.solve(True)
    sink = "token.return"
    rows = []
    for name in g.path(sink):
        node = g.nodes[name]
        critical = g.crit[name]
        times = {d: g.fin[d] * 1e6 for d in node["deps"]}
        rows.append(dict(node=name, kind=node["kind"], deps=node["deps"],
            critical_predecessor=critical, dependency_finish_us=times,
            finish_us=g.fin[name]*1e6, exposed_us=sum(g.contrib[name].values())*1e6,
            dependency_slack_us={d:(g.fin[critical]-g.fin[d])*1e6 for d in node["deps"]},
            source=patches.get(name, {}).get("source", node.get("desc")),
            payload_bytes=node.get("payload"), resource=node.get("resource")))
    return rows


def anatomy_by_node(g):
    """Project the measured anatomy by representative node, retaining .9 GHz.

    No FLOORS or 1.2 GHz hypothetical fused pipelines enter the composition.
    Only nodes whose measured base increment matches this graph are attributed.
    """
    d = load(A.RECOVERY / "su_chains/anatomy.json")
    table = {}
    categories = ("setup", "issue_barrier", "stream", "wire", "vm_round_trip", "arith",
                  "passthrough", "reduction", "cdc", "serial_select")
    for chain in d["chains"]:
        for row in chain["nodes"]:
            table[row["node"]] = {k:row.get(k, 0)/900 for k in categories}
    result, unmatched = {}, []
    for name, node in g.nodes.items():
        pre, _, suf = name.partition(".")
        if not (pre.startswith("L") and pre[1:].isdigit()):
            continue
        key = f"{AD.rep_layer(int(pre[1:]), None)}.{suf}"
        row = table.get(key) or table.get(f"L20.{suf}")
        if row is None:
            continue
        # Independent CDC is a separate charge; arithmetic/VM categories stay raw.
        value = sum(row.values())
        actual = node["issue"] + node["depth"] + node["ctrl"]
        if actual*1e6 < value-0.001:
            unmatched.append(name)  # a successor may have replaced this increment
        else:
            result[name] = row
    return result, unmatched


def attribution(record, g, patches):
    anat, unmatched = anatomy_by_node(g)
    families, buckets, su = Counter(), Counter(), Counter()
    edges = dag_edges(g, patches)
    for e in edges:
        n, v = e["node"], e["exposed_us"]
        families[n.partition(".")[2] or n] += v
        src = e["source"] or ""
        if "ROM field:" in src or "conditional field:" in src:
            bucket = "weight_field_read_compute_reduction_delivery_COMPOSITE"
        elif e["kind"] == "hop":
            bucket = "hops_measured_endpoint_plus_vendor_PHY_and_wire"
        elif e["kind"] == "collective":
            bucket = "collectives"
        elif n in anat:
            bucket = "SU_chain"
            for key, value in anat[n].items():
                su[key] += min(value, v)
        elif "own_row_write" in n:
            bucket = "current_KV_publication_NOT_generic_VM_roundtrip"
        elif "window" in n or "window" in src.lower():
            bucket = "KV_window_source_delivery"
        else:
            bucket = "other_measured_or_modelled"
        buckets[bucket] += v
    buckets["extra_S81_stage_hops"] += record["critical_path_us_by_class"]["extra_S81_hops"]
    return dict(families_us=dict(families.most_common()), buckets_us=dict(buckets),
        SU_measured_categories_us=dict(su), SU_unmatched_successor_nodes=unmatched,
        field_note="Field node cost includes read/issue/reduction/control/return/wire; never label all wo_a as arithmetic.",
        publication_note="Source current-row publication is mandatory KV state; no removal credited.",
        edges=edges)


def capacity_census():
    d = load(A.REC / "field.json")
    out = []
    for phase in d["phases"]:
        w = phase["worst_region_detail"]
        out.append(dict(phase=phase["phase"], node=f"L{phase['layer']}.{phase['node']}",
            die_stage=phase["die_stage"], formats=phase["fmts"], K=phase["K"],
            regions=phase["regions"], rows_checked=phase["rows_checked"],
            worst_region=phase["worst_region"], region_pairs=w["pairs"], active_pairs=w["busy_pairs"],
            active_pair_fraction_in_that_region=w["busy_pairs"]/w["pairs"],
            region_BF_pairs=w["bf_pairs"], native_weight_read_words_per_busiest_pair=w["t_read"],
            offered_beats=w["nbeat"], accept_to_last_row_cycles=phase["go_to_last_row_cycles"],
            installed_pair_fraction_all_die=None,
            scope="worst latency region only; not an all-region utilization sum"))
    return dict(installed=dict(stages=81, TP=4, layer_rank_dies=324, pairs_per_rank_die=2417,
                BF_capability_pairs=519, Q_or_dual_pairs=2417, physical_ROM_leaves_per_rank_die=9668),
        R93=dict(BF_capability_pairs=520, complete_pair_count_delta=0,
                 conversion_site=1773, conversion_region=93, area_delta_mm2=None),
        format_word_capacity=dict(physical_bits=274, fp4_MACs_per_word=64,
                                  fp8_MACs_per_word=32, bf16_MACs_per_word=16),
        actual_phase_rates=out,
        temporal_utilization="Fixed installed weights are resident; only selected layer/expert owners execute. Installed capacity is not active MACs on the single-token dependency path.",
        full_die_active_MACs_per_cycle=None,
        missing="Rawls all-region active MAC/read-port census; cannot extrapolate busiest-region ratio to all 2417 pairs.")


def exposure_bounds(candidates):
    field = load(A.REC / "field.json")
    def no_field(g, p):
        keys = set(AD.field_rows(g, field))
        keys.update(n for n,v in g.nodes.items() if v.get("kind") == "matvec")
        keys.add("head.lm_head")
        for candidate in candidates:
            if candidate["lever"] == "field":
                keys.update(candidate["nodes"])
        for name in keys:
            if name in g.nodes:
                g.nodes[name].update(issue=p.rows.get(name, {}).get("cdc_measured_us",0.)*1e-6,
                                     depth=0., ctrl=0.)
                g.nodes[name].pop("wire_in", None)
                g.nodes[name].pop("wire_out", None)
    eliminated, _, _ = replay(candidates, no_field)
    links = load(A.REC / "links.json")
    cuts = []
    def streaming_collective(g, p):
        for name, nd in g.nodes.items():
            suffix = name.partition(".")[2]
            if suffix not in ("attn.out_allreduce", "ffn.combine_allreduce"):
                continue
            measured = links["collectives"][suffix]
            # Optimistic only: hide input serialization, keep the measured tail.
            # Real first-root/beat timings may expose some/all of this prefix.
            remove = measured["words_per_rank"] / A.CLK
            nd["issue"] = max(0., nd["issue"] - remove)
            cuts.append(dict(node=name, input_bytes=measured["payload_B"],
                input_words=measured["words_per_rank"], port_bytes_per_fast_edge=64,
                measured_total_edges=measured["cycles"], retained_tail_edges=measured["cycles"]-measured["words_per_rank"],
                additional_protected_buffer_FF_floor=184320,
                additional_buffer_area_mm2_at_50pct=184320*.2916*2/1e6,
                first_producer_beat_edge=None, accepted_overlap_gain_us=None))
    coll, _, _ = replay(candidates, streaming_collective)
    return dict(full_field_elimination=summary(eliminated),
        full_field_elimination_claim="Impossible zero-field-cost AR Amdahl upper bound only, including head weight sweep; same KV, SU, collectives, hops, CDC and golden dependency graph retained. Composite delivery/control also erased, so this is more generous than removing arithmetic alone. MTP head occupancy remains its measured floor. Not a proposal.",
        top_follow_on=dict(name="Arriving-stream TP4 all-reduce on native field results", approved_levels=[2,3,5],
            optimistic_prefix_hidden_projection=summary(coll), cut_nodes=cuts,
            actual_gain_us=None, owner=None, RTL_admitted=False,
            prerequisites=["actual producer first/last beat and accepted collective ports",
                "same golden reduction tree and rounding per word; no norm algebra",
                "finite retained credit/buffer and cross-position owner",
                "priced incremental endpoint/control/clock/route and actual in-context SS60/FF25"],
            note="At most 320 source input edges hidden per 20KiB collective; full 590-edge measured tail is not erased. No free increase in ports or remote bandwidth."),
        not_selected=[dict(name="SU straight-to-lane forwarding", reason="Within current SU-owner fusion scope; no second credit beyond that candidate. Match actual last write, not observer HUB_OUT23."),
            dict(name="independent HC chain interleave", reason="Current DAG already computes HC beside the body; no second blanket gain."),
            dict(name="redundant field replay removal", reason="R93 wo_a phase removal is already in preliminary field contrast; no double count."),
            dict(name="cut-through hop", reason="Measured physical REJECT remains; no rescue or new clock/partition." )])


def norm_subset():
    """Only the actually exercised L20 chain; no all-layer extrapolation."""
    prefix = A.RECOVERY / "su_chains/takeover"
    join, transport = load(prefix/"norm_join.json"), load(prefix/"transport_result.json")
    actual = join["actual_registered_transport"]
    if transport.get("pass") is not True or transport.get("fault") != 0:
        raise ValueError("norm registered transport must have a functional PASS")
    import re
    events = {}
    for line in transport["boundary_events"]:
        m = re.fullmatch(r"SU_BOUNDARY (\w+) cycle=(\d+)(?: vector=\d+)?", line)
        if not m:
            raise ValueError("unrecognized norm event")
        events.setdefault(m[1], []).append(int(m[2]))
    first, go, landing = min(events["gain_load"]), events["go"][0], max(events["consumer_q"])
    hz = transport["source"]["clock_hz"]
    if landing-first != actual["gain_first_to_output_cycles"]:
        raise ValueError("cold endpoint disagrees with source-bound events")
    rows = {}
    for index, row in enumerate(actual["nodes"]):
        cycles = row["candidate_cycles"] + (go-first if index == 0 else 0)
        rows[row["node"]] = dict(us=cycles/hz*1e6, kind="fused_fast",
            source="actual L20 norm registered transport; cold gain included; consumer credits unqualified")
    return dict(lever="su_norm_measured_subset", exact=True, nodes=rows), dict(
        scope="Only L20.attn.hc_pre_norm actually exercised; no all-layer/case gain extrapolation",
        component_verdict="FUNCTIONAL_REGISTERED_TRANSPORT_PASS", adoption=False,
        first_gain_cycle=first, gain_cycles=events["gain_load"], go_cycle=go,
        final_registered_landing_cycle=landing, cold_cycles=landing-first,
        cold_us=(landing-first)/hz*1e6, warm_cycles=landing-go,
        warm_us=(landing-go)/hz*1e6, baseline_chain_us=actual["wall_us"]["baseline_component"],
        measured_component_delta_us=actual["wall_us"]["baseline_component"]-(landing-first)/hz*1e6,
        physical_SS_FF=None, finite_consumer_credits=None, VM_publication_lease=None,
        storage_bits_estimate=2080373, loaded_area_mm2=None,
        CDC="Existing graph crossings retained once; component bench is not CDC qualification")


def build(su_path=None, field_path=None):
    field_path = Path(field_path) if field_path else OUT / "inputs/field_preliminary.json"
    field = load(field_path)
    subset, norm = norm_subset()
    su = load(su_path) if su_path else subset
    if su_path and su.get("latency_boundary") != "last_actual_write_or_consumer_ready":
        raise ValueError("SU candidate must bind last actual write/consumer-ready, not unit drain")
    selected_physical = load(OUT/"inputs/rt_m5a4.corner.json")
    alternative_physical = load(OUT/"inputs/rt_m6a5.corner.json")
    rejection = dict(candidate="HCPOST M5A4", verdict="REJECT_SS",
        SS_setup_ps=selected_physical["setup_ss"]["worst_slack_ps"],
        FF_hold_ps=selected_physical["hold_ff"]["worst_slack_ps"],
        alternative=dict(candidate="M6A5 lane only", selected=False,
            SS_setup_ps=alternative_physical["setup_ss"]["worst_slack_ps"],
            FF_hold_ps=alternative_physical["hold_ff"]["worst_slack_ps"],
            qualifies_selected_M5A4_or_full_NG256=False), adoption=False)
    if rejection["SS_setup_ps"] >= 0:
        raise ValueError("selected rejection evidence no longer matches")
    result, graphs, records = {}, {}, {}
    for name, selections in [("baseline", []), ("field_only", [field]),
                              ("SU_only", [su] if su else []), ("both", [field,su] if su else [field])]:
        known = [r for r in selections if r]
        rec, g, patches = replay(known)
        complete = not (name in ("SU_only", "both") and su_path is None)
        result[name] = dict(verdict=("BASELINE_REFERENCE" if name == "baseline" else
                "REJECT_SELECTED_HCPOST_SS" if name in ("SU_only", "both") else "UNRESOLVED"),
            composition_complete=complete, adoption=False,
            conditional_cost=summary(rec) if complete else None,
            known_terms_projection=summary(rec), missing=[] if complete else ["Remaining SU chains, finite consumer credits/VM publication and loaded SS/FF; only L20 norm subset measured"],
            attribution=attribution(rec,g,patches))
        graphs[name], records[name] = g, rec
    base, f = records["baseline"], records["field_only"]
    hbm_path = ROOT / "results/rtl/dshbm_1m_allmeasured_20261004/composition.json"
    hbm = load(hbm_path)
    canonical_path = A.RECOVERY / "composition.json"
    canonical = load(canonical_path)
    if (base["context"], base["position"]) != (hbm["context"], hbm["position"]):
        raise ValueError("ROM and HBM workloads must match")
    if canonical["info"]["hop_tier"] != base["info"]["hop_tier"]:
        raise ValueError("decision gate must use the canonical full-FEC composition")
    target = 1e6/hbm["AR_tok_s"]
    inputs = dict(base["inputs"])
    inputs.update(base["tool_sha256"])
    for path in [field_path, OUT/"inputs/rt_m5a4.corner.json", OUT/"inputs/rt_m6a5.corner.json", OUT/"inputs/field_pq.json", OUT/"inputs/field_pq_variant_r93.json",
                 OUT/"inputs/field_WIP_composition.json", A.RECOVERY/"su_chains/anatomy.json", hbm_path, canonical_path,
                 A.FULL_FEC_LINKS, A.FULL_FEC_RACK,
                 ROOT/"tools/uarch_model.py",
                 A.RECOVERY/"su_chains/takeover/norm_join.json",
                 A.RECOVERY/"su_chains/takeover/transport_result.json",
                 ROOT/"results/uarch/ds_recovery_attribution_20261005/attribution.json", ROOT/"tools/dsrom_1m_allmeasured.py", ROOT/"tools/dsrom_recovery_decision_gate.py"]:
        inputs[str(path.relative_to(ROOT))] = sha(path)
    for name in ("dsrom_1m_allmeasured_adapters.py", "decode_critical_path.py", "arch_budget_v41.py",
                 "arch_lanes_v41.py", "third_party_tau.py"):
        inputs["tools/"+name] = sha(ROOT/"tools"/name)
    if su_path:
        inputs[str(Path(su_path).resolve().relative_to(ROOT))] = sha(su_path)
    fetch = [e for e in hbm["path"] if e["node"].startswith("hbm:expert_fetch")]
    return dict(schema="opentallas.dsrom-recovery.matched-decision-gate.v1", inputs=inputs,
        source_snapshot=f"{subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()}; current adopted levers, WINDOW=s81, hop full_fec",
        composition_sha256=sha(canonical_path),
        context=base["context"], position=base["position"],
        composition_contract=dict(canonical_source=str(canonical_path.relative_to(ROOT)),
            hop_tier=base["info"]["hop_tier"], window=base["info"]["window"]["mode"],
            full_fec=base["info"]["full_fec"], adopted_levers=base["info"]["levers"]["applied"]),
        scenarios=result, measured_norm_subset=norm, selected_SU_physical=rejection,
        installed_attribution=dict(source="results/uarch/ds_recovery_attribution_20261005/attribution.json",
            evidence=load(ROOT/"results/uarch/ds_recovery_attribution_20261005/attribution.json"),
            interpretation="Installed weight capacity is not a proved root cause; removable weight service and total current area are unknown (draft +52 dies ledger incomplete). No headline energy claim."),
        field=field_evidence(field,load(OUT/"inputs/field_pq.json")),
        historical_contrast=dict(AR_saved_us=base["AR_us"]-f["AR_us"],
            AR_rate_gain_fraction=base["AR_us"]/f["AR_us"]-1,
            label="Historical baseline vs preliminary shared-hardware PQ+R93 duration: NOT isolated scheduling gain"),
        hardware_build_admitted=False, full_die_trigger="real field adoption verdict and final selected-cost/objects; not preliminary ADOPT ss_ff null",
        matched_input_contract=dict(SU_tail="Actual last write/consumer-ready; no unimplemented HUB_OUT23 credit",
            CDC="Retain source domain and independently measured CDC; exactly once",
            topology="Same S81/TP4/4096-row weights and golden tree, no silent partition/clock changes"),
        capacity=capacity_census(),
        comparison=dict(HBM_AR_us=hbm["AR_us"], HBM_AR_tok_s=hbm["AR_tok_s"], HBM_MTP_tok_s=hbm["MTP_tok_s"],
            AR_equal_rate_target_us=target, baseline_extra_exposed_us=base["AR_us"]-target,
            after_preliminary_field_additional_exposed_us=f["AR_us"]-target,
            HBM_exposed_expert_weight_fetch_us=sum(x["us"] for x in fetch), HBM_by_term=hbm["AR_by_term"],
            note="Only exposed HBM fetch is charged; prefetched hidden weight traffic is not re-added. ROM weights do not remove long KV/index loads. Different TP/compute organisations, not a controlled weight-medium ablation.",
            compute_reuse="Weight nonreuse alone does not cause decode latency; physical residency spends area, while active owners, serial phase admission, port rates, reductions and movement determine critical time."),
        bounds_and_next=exposure_bounds([field]),
        interactions=dict(field_SU_interaction_us=None if su_path is None else
            records["both"]["AR_us"]-records["field_only"]["AR_us"]-records["SU_only"]["AR_us"]+base["AR_us"],
            method="Re-solve every DAG, then recompute worst-stage II, six-position verify, draft and commit. Never add percentages; AR gain need not equal MTP gain."))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--su", type=Path)
    parser.add_argument("--field", type=Path,
                        help="owner's measured node table; historical preliminary table is default")
    parser.add_argument("--out", type=Path, default=OUT/"model.json")
    args = parser.parse_args()
    result = build(args.su, args.field)
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(result,indent=1,sort_keys=True)+"\n")
    print(json.dumps({k:dict(verdict=v['verdict'],cost=v['conditional_cost']) for k,v in result['scenarios'].items()}))


if __name__ == "__main__":
    main()
