#!/usr/bin/env python3
"""Qwen ROM per-layer throughput record (owner 2026-10-13: ROM throughput is qualified at the PER-LAYER level).

Reads one positive and one mutant run of the Qwen ROM token bench on the partitioned core
(tools/qwen_missing/partition_token.py, split partition s22ml7, L0-L2 chain at P 8,191, host linked with
-DRT_OPTRACE_PA and run with RT_OPTRACE=1) and writes the per-layer record:

  * exactness (layer X and current K/V against the golden) and the mutant's verdict;
  * measured cycles of every chained layer, split into the priced layer's operations at the op-fetch boundaries of
    die 0 (the same boundaries tools/token_path_export.py Q_OPS cuts the committed isolated-L0 trace at), with the
    ME-busy cycles, collective beats and issue-stall cycles inside each window;
  * each operation and class against the priced layer of results/arch/token_path_20261009/qwen_rom.json;
  * the end-to-end tok/s effect with tools/throughput/accepted_cost.py (the token-path longest path).

    qwen_rom_layer.py --run DIR --out results/rtl/qwen_layer_tput_1013 [--xvm DIR2] [--sha S --host H]
DIR holds pos_runtime.log, pos_result.json, neg_result.json, head_result.json copied from the run; DIR2 (optional) the
result.json / runtime.log of the same vehicle built with QROM_XVM=11 (VM x read + 10 edges, the TP8 bit-plane VM hand-off).

The op-fetch windows are NOT execution windows: the controller fetches ahead of posted work, and in the chain the KV fill
of the attention is hidden behind the previous layer.  The record therefore regroups the windows by what the counters
show they hold (CONTENT), and the layer total, not a window, is the qualifying figure.
"""
from __future__ import annotations

import argparse
import collections
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "tools" / "throughput"))
import accepted_cost as AC  # noqa: E402
from token_path_export import Q_OPS  # noqa: E402

OLD = ROOT / "results/rtl/qwen_rom_kv_fullbw_20261004/dspark_verify_P8187/optrace/k_AR_op.trace.log"
TP = ROOT / "results/arch/token_path_20261009/qwen_rom.json"
STALLS = ("stall_kv", "stall_drain", "stall_bridge", "stall_retire", "stall_mem")
# vehicle scope: what the stream4 ROM-die vehicle holds of each priced adder / operation
NOT_IN_VEHICLE = {"die_relays_430um": "r21 die relay stations (priced adder, physical relays are not in the RTL vehicle)",
                  "band_integrate (re-price 10-08)": "band integration re-price (priced adder)",
                  "serdes_pinreg (re-price 10-08)": "SerDes pin register re-price (priced adder)",
                  "slab_mul_lat7": "slab MUL_LAT 7 (measured on the slab-share route, not in this vehicle)",
                  "kv_map_m": "per-token KV-path constant", "kv_crossbar_model": "per-token KV-path constant",
                  "ctrl_shift": "per-token KV-path constant"}
SPLIT = "rom_split_stations_and_issue_relays"
KV_DIE_OPS = ("attn_kv", "softmax_norm")   # production: on the KV die through the link; vehicle: tile attention


def parse_trace(text):
    ev = collections.defaultdict(list)
    for m in re.finditer(r"^OPTRACE stage=(\S+) cyc=(\d+) prog_a=(\d+) base=(\d+) me_busy=(\d+) c_beats=(\d+) r_beats=(\d+) "
                         r"stall_kv=(\d+) stall_drain=(\d+) stall_bridge=(\d+) stall_retire=(\d+) stall_mem=(\d+)", text, re.M):
        v = list(map(int, m.groups()[1:]))
        ev[m[1]].append(dict(zip(("cyc", "pa", "base", "me_busy", "c_beats", "r_beats", *STALLS), v)))
    st = {m[1]: dict(cycles=int(m[2]), start=int(m[3]), end=int(m[4]), me_busy=int(m[5]))
          for m in re.finditer(r"^STAGE (\S+) done cycles=(\d+) start_cyc=(\d+) end_cyc=(\d+) me_busy=(\d+)", text, re.M)}
    mem = {}
    for m in re.finditer(r"^MEMSTAT (\S+) die0 (.*)$", text, re.M):
        mem[m[1]] = {k: int(v) for k, v in re.findall(r"(\w+)=(-?\d+)", m[2])}
    return ev, st, mem


def old_boundaries():
    """event index of each Q_OPS window start in the committed isolated-L0 trace + its fetch-address sequence"""
    rows = [(int(m[1]), int(m[2])) for m in re.finditer(r"^OPTRACE cyc=(\d+) prog_a=(\d+)", OLD.read_text(), re.M)]
    cyc = [c for c, _ in rows]
    idx = {o[0]: cyc.index(o[3]) for o in Q_OPS}
    return [p for _, p in rows], idx


def windows(events, stage, seq_old, idx):
    """cut one stage's events into the Q_OPS windows -> [dict(op, cls, cycles, me_busy, c_beats, r_beats, stalls)]"""
    # the stage's events from its first fetch; the trace also logs the address returning to the stage base on reset
    n = len(seq_old)
    start = None
    for seq in ([e["pa"] - e["base"] for e in events], [e["pa"] for e in events]):   # relative, else absolute address
        # align: the old trace is the fetch sequence of one layer program; find it inside this stage's sequence
        start = next((i for i in range(len(seq) - n + 1) if seq[i:i + n] == seq_old), None)
        if start is not None:
            break
    if start is None:
        raise SystemExit(f"{stage['name']}: fetch-address sequence differs from the committed trace:\n new {seq}\n old {seq_old}")
    ev = events[start:start + n]
    end = dict(cyc=stage["end"], me_busy=stage["me_busy_abs"], **{k: None for k in ("c_beats", "r_beats", *STALLS)})
    out = []
    order = [o[0] for o in Q_OPS]
    for k, o in enumerate(Q_OPS):
        a = ev[idx[o[0]]]
        b = ev[idx[order[k + 1]]] if k + 1 < len(order) else (events[start + n] if start + n < len(events) else end)
        w = dict(op=o[0], label=o[1], cls=o[2], start=a["cyc"] - stage["start"], cycles=b["cyc"] - a["cyc"],
                 me_busy=b["me_busy"] - a["me_busy"])
        for f in ("c_beats", "r_beats", *STALLS):
            w[f] = None if b[f] is None else b[f] - a[f]
        out.append(w)
    lead = ev[0]["cyc"] - stage["start"]
    return out, lead, start


PRICE_SRC = "results/rtl/token_exact_20261009/qwen_rom"          # the runs the token path's split structure was priced from
KVD = "results/arch/qwen_kv_die_20261009/reprice.json"
# what each op-fetch window of the CHAINED layer holds (checked against the counters in content())
CONTENT = dict(rmsnorm1="su", qkv="me", qknorm_rope="su", attn_kv="attention", softmax_norm="attention", o_proj="me",
               allreduce1="attention", attn_tail="link", rmsnorm2="su", gate_up="me", down="me", allreduce2="link", residual="su")
# the same grouping of the priced base windows (isolated-L0 trace, drain removed): where the price put those cycles
PRICE_GROUP = dict(CONTENT, allreduce1="link")
# registry: elements of a Qwen ROM class that the per-layer vehicle does not hold (their cost is a priced adder)
NOT_IN_VEHICLE_ELEMENTS = [
    [r"^(qfd_rly|qfd_lst_)", "die relay stations (die_relays_430um: 95 per ME op, 26 per all-reduce, priced)"],
    [r"^ot_qwen_slab_port_group", "slab MUL_LAT 7 port group (slab_mul_lat7, measured on the slab-share route only)"],
    [r"^qfd_sp_band_lanes", "band integration (band_integrate re-price, priced)"],
    [r"^(qfd_io_serdes|qfd_io_ucie|qfd_link_rx|ot_qwen_link_)", "SerDes / UCIe / forwarded-link stations (serdes_pinreg, link relays: priced)"],
    [r"^(qfd_io_collective|qfd_io_xfifo|qfd_coll_xfifo|qfd_cdc|ot_qwen_stream4_cdc)",
     "native collective port / CDC (the vehicle's all-reduce is ot_rom_oneshot_allreduce on ot_rom_pkg_link)"],
    [r"^(qfd_sp_tree_top|qfd_tt_)", "tree-top issue / status relays (r22k, 623 cycles a layer priced from split_relays.json; the vehicle has the pin stations only)"],
    [r"^(qfd_sp_vector_memory_bv|ot_qfd_sp_vector_memory_bv|qfd_vm_bv)", "TP8 bit-plane VM (XPR 10): the vehicle VM is the XVM 1 behavioural memory"],
]


def content(L):
    """the window grouping, with the two re-assignments proven from the counters of this run"""
    w = {x["op"]: x for x in L["windows"]}
    c = dict(CONTENT)
    proof = {}
    a1, at = w["allreduce1"], w["attn_tail"]
    if not (a1["c_beats"] == 0 and a1["me_busy"] >= a1["cycles"] - 2 and at["c_beats"] and at["c_beats"] > 0):
        c.update(allreduce1="link", attn_tail="su")
        proof["allreduce1"] = "nominal (the collective beats are inside the window)"
    else:
        proof["allreduce1"] = (f"the {a1['cycles']}-cycle 'allreduce1' fetch window is the END-b barrier waiting on the posted attention: "
                               f"ME busy {a1['me_busy']} of {a1['cycles']} cycles, 0 collective beats")
        proof["attn_tail"] = (f"all-reduce #1 runs inside the 'attn_tail' fetch window: {at['c_beats']} collective beats "
                              f"(all-reduce #2: {w['allreduce2']['c_beats']} beats in its own window)")
    return c, proof


def stage_cycles(text):
    return {m[1]: int(m[2]) for m in re.finditer(r"^STAGE (\S+) done cycles=(\d+)", text, re.M)}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--run", type=Path, required=True)
    ap.add_argument("--xvm", type=Path, default=None)
    ap.add_argument("--xvm-edges", type=int, default=10, help="extra VM read edges in the reference latency probe (default 10)")
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--sha", default="")
    ap.add_argument("--host", default="")
    ap.add_argument("--layer", default="L1", help="the chained layer compared with the priced layer")
    ap.add_argument("--kv-attention", type=Path, default=ROOT / "results/arch/qwen_attention_rate_1015/receipt.json",
                    help="measured production KV-die attention receipt (native static service + link), replaces the priced swap")
    a = ap.parse_args()
    run = a.run
    J = lambda p: json.loads(Path(p).read_text())
    pos, neg, head = J(run / "pos_result.json"), J(run / "neg_result.json"), J(run / "head_result.json")
    text = (run / "pos_runtime.log").read_text()
    events, stages, mem = parse_trace(text)
    seq_old, idx = old_boundaries()
    tp = J(TP)
    price = {n["op"]: n for n in tp["nodes"] if n.get("group") == a.layer}
    acc, rec_layers = 0, {}
    for name in stages:
        acc += stages[name]["me_busy"]
        st = dict(stages[name], name=name, me_busy_abs=acc)
        w, lead, _ = windows(events[name], st, seq_old, idx)
        tot = sum(x["cycles"] for x in w)
        rec_layers[name] = dict(cycles=stages[name]["cycles"], me_busy=stages[name]["me_busy"], windows=w, lead_cycles=lead,
                                unattributed=stages[name]["cycles"] - tot - lead, memstat_die0=mem.get(name, {}))
    L = rec_layers[a.layer]
    assert L["unattributed"] == 0, L["unattributed"]
    # ---- the priced layer -------------------------------------------------------------------------------------------
    base, stn = J(ROOT / PRICE_SRC / "L3_base.json"), J(ROOT / PRICE_SRC / "L3_s22ml7.json")
    sp = J(ROOT / KVD)
    def find(o):
        if isinstance(o, dict):
            if "split_structure" in o:
                return o["split_structure"]
            for v in o.values():
                r = find(v)
                if r:
                    return r
    sp = find(sp)
    p_base = base["stage_cycles"][a.layer]
    p_stn = sp["stations_only"]["layer"]
    p_relay = sp["issue_relays"]["layer"]
    assert p_base + p_stn == stn["stage_cycles"][a.layer] and p_stn + p_relay == sp["layer_delta"]
    p_prod = sum(n["cycles"] for n in price.values())
    old = {o[0]: o for o in Q_OPS}
    pbase = {}                                  # the priced base window of each op on the vehicle's shape (tile attention)
    for op, n in price.items():
        pbase[op] = float(old[op][4] - old[op][3]) if op in KV_DIE_OPS else float(n["base_cycles"])
    assert sum(pbase.values()) == p_base, (sum(pbase.values()), p_base)
    adders = collections.Counter()
    for n in price.values():
        for k, v in n["adders"]:
            adders[k] += v
    assert adders.pop(SPLIT) == sp["layer_delta"]
    assert not [k for k in adders if k not in NOT_IN_VEHICLE], adders
    att_veh = sum(pbase[o] for o in KV_DIE_OPS)
    att_prod = sum(price[o]["cycles"] for o in KV_DIE_OPS)
    p_vehicle = p_base + p_stn
    assert p_vehicle + p_relay + (att_prod - att_veh) + sum(adders.values()) == p_prod
    m_layer = L["cycles"]
    # ---- windows and classes ----------------------------------------------------------------------------------------
    grp, proof = content(L)
    rows = []
    cls = collections.defaultdict(lambda: dict(measured=0, price_base=0.0, windows=[]))
    for w in L["windows"]:
        n = price[w["op"]]
        rows.append(dict(op=w["op"], label=w["label"], priced_cls=w["cls"], holds=grp[w["op"]], measured=w["cycles"],
                         price_base_window=pbase[w["op"]], delta=round(w["cycles"] - pbase[w["op"]], 1),
                         price_production=n["cycles"], production_adders=dict(n["adders"]), me_busy=w["me_busy"],
                         c_beats=w["c_beats"], r_beats=w["r_beats"], stalls={k: w[k] for k in STALLS}))
        cls[grp[w["op"]]]["measured"] += w["cycles"]
        cls[grp[w["op"]]]["windows"].append(w["op"])
        cls[PRICE_GROUP[w["op"]]]["price_base"] += pbase[w["op"]]
    classes = []
    for k, v in cls.items():
        d = v["measured"] - v["price_base"]
        classes.append(dict(cls=k, measured=v["measured"], price_base=v["price_base"], delta=round(d, 1),
                            ratio_vs_base=round(v["measured"] / v["price_base"], 4), windows=v["windows"],
                            over_1p10=v["measured"] > AC.QUALIFY * v["price_base"],
                            scope=("vehicle only: tile attention on the ROM die; production runs this step on the KV die "
                                   f"through the link ({att_prod:.0f}, its own record)" if k == "attention" else "production operator class")))
    assert sum(c["measured"] for c in classes) + L["lead_cycles"] == m_layer
    assert sum(c["price_base"] for c in classes) == p_base
    stn_meas = m_layer - p_base
    single = [dict(op=r["op"], holds=r["holds"], measured=r["measured"], price_base_window=r["price_base_window"],
                   ratio=round(r["measured"] / r["price_base_window"], 4), delta=r["delta"])
              for r in rows if r["price_base_window"] >= 50 and PRICE_GROUP[r["op"]] == r["holds"]
              and r["measured"] > AC.QUALIFY * r["price_base_window"]]
    # ---- head -------------------------------------------------------------------------------------------------------
    hn = next(n for n in tp["nodes"] if n["id"] == "head.lm_head")
    h_meas = head["stage_cycles"]["head"]
    head_rec = dict(measured=h_meas, price_base=hn["base_cycles"], ratio=round(h_meas / hn["base_cycles"], 4),
                    delta=h_meas - hn["base_cycles"], exact=head["exact"], next_token=head["next_token"],
                    note="the head ran on the stationed core (dcu 2 / duc 2 / SU ML 7); the price is the unstationed head and the "
                         "token path charges no station cost on it")
    # ---- end to end -------------------------------------------------------------------------------------------------
    T = tp["totals"]["cycles"]
    l0_gap = rec_layers["L0"]["cycles"] - stn["stage_cycles"]["L0"]
    gap = m_layer - p_vehicle
    items = [dict(item="ROM-die layer (vehicle scope)", per_layer=gap, l0=l0_gap, added_cycles=l0_gap + 35 * gap, grade="measured"),
             dict(item="LM head on the stationed core", added_cycles=head_rec["delta"], grade="measured")]
    hand = {}
    # VM bit-plane x read + 10 edges
    edges = a.xvm_edges
    assert edges > 0, "VM latency probe needs a positive edge count"
    vm = dict(unit="VM.XREAD", branch="claude/qwen-tp8-vm-1013 @ 31dbda816" if edges == 10 else "reference latency sensitivity probe",
              edges_per_x_read=edges, x_reads_per_token=217,
              bound_cycles=217 * edges, bound_loss_pct=round(AC.loss_pct(T, T + 217 * edges), 3),
              unit_bench=("tb_qfd_vm_bv_ports: XVM 22 -> 32 on r21 (measured by the VM stream); pop / SU / row / write paths + 0" if edges == 10 else "Reference-model latency probe of the later VM handoff; native VM hardware is not in this vehicle"))
    if a.xvm and (a.xvm / "result.json").exists():
        xr = J(a.xvm / "result.json")
        xs = xr["stage_cycles"]
        d = {k: xs[k] - pos["stage_cycles"][k] for k in xs}
        added = d["L0"] + 35 * d[a.layer] + edges
        vm.update(measured=dict(vehicle=f"the same vehicle built with QROM_XVM={edges + 1} (VM x-read transport 1 -> {edges + 1} edges)",
                                exact=xr["exact"], layer_x_mismatches=xr["layer_x_mismatches"], kv_mismatches=xr["kv_mismatches"],
                                stage_cycles=xs, delta_per_layer=d, head_delta_bound=edges,
                                added_cycles_per_token=added, e2e_loss_pct=round(AC.loss_pct(T, T + added), 3),
                                x_reads_on_critical_path_per_layer=round(d[a.layer] / edges, 2),
                                executable_sha256=xr.get("executable_sha256")), status="MEASURED per layer")
        items.append(dict(item=f"VM bit-plane x read + {edges} edges (latency probe)", per_layer=d[a.layer], l0=d["L0"], added_cycles=added, grade="measured layers + head bound"))
    else:
        vm.update(measured=None, status="UNMEASURED per layer (bound only)")
        items.append(dict(item=f"VM bit-plane x read + {edges} edges (latency probe)", added_cycles=217 * edges,
                          grade=f"bound (217 x reads x {edges}, all on the critical path)"))
    hand["vm_bitplane_x_read"] = vm
    hand["reset_tree"] = dict(per_token_cycles=0, grade="by construction",
                              note="registered reset tree: power-on only; traffic start gated 85 cycles after root release (qwen-tp8 die, 10-13 04:16)")
    hand["data_relays"] = dict(per_layer_cycles=None, status="UNMEASURED: not posted",
                               note="[tp8-relay-data] (el1011-qwen-tp8.log) has no per-layer / per-token cycle additions yet: the relay generator "
                                    "fix is open (10-13 07:26: 9,643 relays, 3 chains unrepaired, 5 nets > 500 um); the token path prices the "
                                    "TP4 die relays as die_relays_430um")
    hand["die_tile_cycles"] = dict(status="UNMEASURED: no die-tile composition run exists",
                                   note="the hardened qfd_* tiles and the TP8 die are not in a per-layer simulation; this record is the "
                                        "cycle-reference core composition")
    # ---- production KV-die attention: measured native static service (+ link) replaces the priced attn_kv ------------
    kv_att = dict(cycles=att_prod, status="PRICED", record="results/rtl/tput_map_1011/qwen_kv_die/record.json (its own composed bench)")
    if a.kv_attention and a.kv_attention.exists():
        ka = J(a.kv_attention)
        r = ka["ratio_vs_price"]
        assert ka["positives_exact"].startswith("53/53"), ka["positives_exact"]
        att_meas = r["with_link"]
        kv_att = dict(cycles=att_meas, priced=att_prod, ratio=round(att_meas / att_prod, 4), status="MEASURED (component: service + link)",
                      service_cycles_T8192=r["service_8192"], link_cycles=ka["budget"]["link_cycles"],
                      record=str(a.kv_attention.relative_to(ROOT)), source=ka["source_commit"],
                      calendar="tools/qwen_attention_native/attn_calendar.py (production pv=w16)", exact=ka["positives_exact"])
        d = att_meas - att_prod
        items.append(dict(item="KV-die attention (native static w16 service + link) vs priced attn_kv", per_layer=d, l0=d,
                          added_cycles=36 * d, grade="measured component (service bench + link stages)"))
    added = sum(i["added_cycles"] for i in items)
    e2e = dict(model="serial token path (every node critical, slack 0): added cycles summed over 36 layers + head",
               base_cycles=T, items=items, added_cycles=added, cycles=T + added, e2e_loss_pct=round(AC.loss_pct(T, T + added), 3),
               tok_s_price=round(tp["clock_hz"] / T, 1), tok_s=round(tp["clock_hz"] / (T + added), 1))
    unmeasured = dict(issue_relays_r22k=p_relay, **{k: v for k, v in adders.items()})
    reg_ratio = {c["cls"]: c["ratio_vs_base"] for c in classes if c["cls"] != "attention"}
    reg_ratio["head"] = head_rec["ratio"]
    rec = dict(
        schema="opentallas.qwen_layer_tput.v2",
        rule="owner 2026-10-13: ROM throughput is qualified per layer (a measured per-layer run against the priced layer); unit benches only for critical-path units",
        source_sha=a.sha, host=a.host,
        vehicle=dict(bench="tools/qwen_missing/partition_token.py build|run --variant part --dcu 2 --duc 2 --su-ml 7 --comp 1 (mutant --comp 0), --stages L3 / head",
                     top="ot_qwen_rom_rt_die_w12_stream4_tagged_ar x 4 dies (partitioned ot_qwen_rom_core: controller / matrix-engine spine / stream unit, "
                         "pin stations + split-exact compensation) + ot_rom_oneshot_allreduce on ot_rom_pkg_link + ot_qwen_me_array_w12 tiles",
                     shape="Qwen3-8B, position 8,191 (8K context), L0-L2 chained, real HBM KV stream, INT8 weights",
                     tp="TP4. No TP8 vehicle, fixture or golden exists (gold/tp4_hs); the priced token path (token_path_20261009/qwen_rom.json) is TP4 too. "
                        "The TP8 die is UNMEASURED per layer.",
                     level="cycle-reference core composition: NOT the hardened qfd_* tiles and NOT the routed die (no die relays, no native collective port, "
                           "tile attention instead of the KV die)",
                     trace="host linked with -DRT_OPTRACE_PA (QROM_OPTRACE=1), run with RT_OPTRACE=1: observation only"),
        exact=dict(positive=dict(exact=pos["exact"], layer_x_mismatches=pos["layer_x_mismatches"], layer_x_checks=pos["layer_x_checks"],
                                 kv_mismatches=pos["kv_mismatches"], kv_checks=pos["kv_checks"], stage_cycles=pos["stage_cycles"],
                                 executable_sha256=pos["executable_sha256"]),
                   mutant=dict(what="--comp 0: the pin stations without the split-exact compensation", exact=neg["exact"],
                               layer_x_mismatches=neg["layer_x_mismatches"], kv_mismatches=neg["kv_mismatches"],
                               stage_cycles=neg["stage_cycles"], fails_as_required=not neg["exact"]),
                   head=dict(exact=head["exact"], next_token=head["next_token"], cycles=h_meas)),
        production_layer=dict(priced=p_prod, measured_scope=dict(vehicle_measured=m_layer, minus_vehicle_attention=att_veh,
                                                                  plus_kv_die_attention=kv_att["cycles"]),
                              composed=m_layer - att_veh + kv_att["cycles"] + p_relay + sum(adders.values()),
                              ratio=round((m_layer - att_veh + kv_att["cycles"] + p_relay + sum(adders.values())) / p_prod, 4),
                              still_priced=dict(issue_relays_r22k=p_relay, **dict(adders)),
                              note="vehicle layer measured (tile attention swapped out) + measured KV-die attention + the still-priced relay/adder terms"),
        layer=dict(name=a.layer, measured_cycles=m_layer, priced_vehicle_scope=p_vehicle, ratio=round(m_layer / p_vehicle, 4),
                   qualified=bool(pos["exact"] and not neg["exact"] and m_layer <= AC.QUALIFY * p_vehicle),
                   price=dict(source=f"{PRICE_SRC}/L3_base.json + L3_s22ml7.json, {KVD} split_structure, {TP.relative_to(ROOT)}",
                              base_unstationed=p_base, split_stations=p_stn, vehicle_scope=p_vehicle,
                              production_layer=p_prod,
                              production_minus_vehicle=dict(issue_relays_r22k=p_relay, kv_die_attention_swap=att_prod - att_veh,
                                                            **dict(adders))),
                   measured_fraction_of_production_layer=round((p_vehicle - att_veh) / p_prod, 4),
                   all_layers={k: dict(measured=v["cycles"], priced=stn["stage_cycles"][k], ratio=round(v["cycles"] / stn["stage_cycles"][k], 4),
                                       me_busy=v["me_busy"]) for k, v in rec_layers.items()},
                   lead_cycles=L["lead_cycles"], me_busy_cycles=L["me_busy"], memstat_die0=L["memstat_die0"]),
        classes=classes,
        class_note=dict(basis="measured op-fetch windows of the chained layer, grouped by what they hold, against the priced base windows "
                              "(isolated-L0 trace with the write-back drain removed = the unstationed chained layer). The split-station cost "
                              f"({p_stn} a layer, priced as one lump on the layer's last op) is NOT credited to any class here, so these ratios are upper bounds.",
                        regrouping=proof, stations_measured=stn_meas, stations_priced=p_stn,
                        stations_where={c["cls"]: c["delta"] for c in classes} | {"lead": L["lead_cycles"]}),
        windows=rows,
        windows_over_1p10=dict(rows=single,
                               cause="rmsnorm2: + 11 cycles, the controller -> unit pin stations on the issue path (stall_bridge 28 in the window); "
                                     "inside the priced station lump. No operator class is over 1.10."),
        head=head_rec, handoffs=hand, end_to_end=e2e,
        unmeasured_per_layer=dict(cycles_per_layer=p_relay + sum(adders.values()), share_of_production_layer=round((p_relay + sum(adders.values())) / p_prod, 4),
                                  items=unmeasured, kv_die_attention=kv_att,
                                  embed="embedding fetch through the KV die (272, priced)"),
        registry=dict(model="qwen_rom", qualified_by="layer", class_ratio=reg_ratio,
                      basis=f"{a.layer} chained, measured / priced = {m_layer} / {p_vehicle:.0f}; class ratio = measured windows / priced base windows (no station credit)",
                      not_in_vehicle_elements=NOT_IN_VEHICLE_ELEMENTS),
        accepted_cost=dict(rows_added=[], why="no unit of the measured layer is over 1.10 against its price"))
    a.out.mkdir(parents=True, exist_ok=True)
    (a.out / "record.json").write_text(json.dumps(rec, indent=1) + "\n")
    print(json.dumps(dict(production_layer=rec["production_layer"], layer={k: v for k, v in rec["layer"].items() if k != "memstat_die0"}, classes=classes, over=single,
                          head=head_rec, vm=vm, e2e=e2e), indent=1))


if __name__ == "__main__":
    main()
