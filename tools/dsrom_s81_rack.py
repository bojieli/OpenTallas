#!/usr/bin/env python3
"""DeepSeek-V4.1 ROM S81: rack packing, link classes and HBM stack allocation (one record, 2026-10-06).

Resolves three data conflicts the Chip Explorer rack view exposed (CLAUDE DS-RACK):

 1. LINKS.  OWNER 2026-10-06: full RS(544,514) FEC on every link that leaves the package (board / in-tray, in-rack
    cable, rack to rack), for the DS ROM array and the HBM accelerator; light FEC is dropped everywhere.  In-package
    UCIe keeps its own spec.  Every off-package hop therefore pays the measured full-KP4 hop
    (results/rtl/dsrom_1m_allmeasured_20261004/links_full_fec.json, RTL with the 209 ns channel, ~0.3 m of flight
    inside); the classes differ only by the flight beyond 0.3 m (twinax 4.6 ns/m, Broadcom SUE RM104) and, past the
    2 m passive-DAC reach (IEEE 802.3ck CR), an AEC retimer (3 ns analog, results/arch/v41_rack.json).
    The packing minimises cable hops: two consecutive stages share a tray (board link), the stage chain runs as a
    U across two racks (down R1, across at the bottom, up R2), the head trays sit beside stage 0 so the 8-traversal
    token return stays on the shortest cable, and the draft trays sit beside the head trays.  With 2 stages a 1 OU
    tray (4 two-die packages, the rack study's liquid tray), 81 stages need 41 trays, so 40 board hops and 40 cable
    hops is the minimum; the chain crosses racks exactly once (a cycle head -> S0 .. S80 -> head over two racks crosses
    twice: the stage crossing at the bottom and the head hop).

 2. HBM STACKS (owner decisions 'KV lives in HBM' and 'DS ROM scenario C: KV stacks sized to need',
    results/uarch/dsrom_return_storage_hbm_20261003/HANDOFF_SCENARIO_C.md): 4 stacks on the 32 index-scanning rank
    dies (scan layers 2, 8, ..., 36 at their S81 scan stages, canonical stage_map.json), 1 on every other rank die,
    4 on each head die, 0 on Engram table dies and on the DP1-EP5 expert-replica draft dies (no per-user state).
    The S81 die generator draws the SCAN die (four stacks): right for 32 dies, not for the other 292.  The power
    model's 452 = 4S + 128 is the same rule at 8 head dies; at the adopted 12 head dies it is 468.

 3. HEAD / TABLE: 12 head + 36 Engram table dies (results/uarch/dsrom_l2_head_mac_20261004/model.json verdict
    recommended_head_dies 12, head_groups['12'].total_dies 372 = 324 + 12 + 36; head lever levers/head.json prices
    'per head die (1 of 12)'), + 52 draft dies (levers/draft.json dies_added).  '8 + 36' (C1 ledger, 368 dies) and
    '12 + 32' (explorer, 44 kept) are both stale.

STAGE COUNT (CLAUDE DS-RACK85 2026-10-06).  The adopted DS ROM headline uses the closed QX 10 q-element frame
(default QELEM, owner go 3661e31c6; tools/dsrom_1m_allmeasured_adapters.FIELD_GEOM).  Its taller element frame holds
fewer pairs a die, so the array needs more layer dies: the r8 re-price record gives the stage and layer-die count of
each frame (results/rtl/dsrom_field_reprice_r8_20261006/reprice.json geoms[FIELD_GEOM]: f183.60 = 85 stages, 340
layer dies, +16 / +4 stage hops over S81).  This record packs THAT count; the head / Engram table counts are the head
model's (unchanged: table = head model total - its 324 S81 layer dies - 12 head).  The extra stages are matrix stages
(the S81 binding has 74 matrix stages and 7 tail stages); the scan dies' stage homes are the S81 provisional homes
scaled to the 78 matrix stages (still provisional: the count, 32 dies, is what the stacks need).

    python3 tools/dsrom_s81_rack.py            # writes results/arch/dsrom_s81_rack_20261006/rack.json
"""
from __future__ import annotations

import hashlib
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results/arch/dsrom_s81_rack_20261006/rack.json"
RACK = "results/arch/v41_rack.json"
STAGE_MAP = "results/uarch/dsrom_s81_released_binding_20261004/canonical/stage_map.json"
S81FP = "results/rtl/dsrom_s81_fulldie_20261004/floorplan.json"
HEADREC = "results/uarch/dsrom_l2_head_mac_20261004/model.json"
HEADLEV = "results/rtl/dsrom_recovery_20261004/levers/head.json"
DRAFTLEV = "results/rtl/dsrom_recovery_20261004/levers/draft.json"
SCEN_C = "results/uarch/dsrom_return_storage_hbm_20261003/HANDOFF_SCENARIO_C.md"
LFF = "results/rtl/dsrom_1m_allmeasured_20261004/links_full_fec.json"
RECHECK = "tools/dsrom_c_recheck.py"
REPRICE = "results/rtl/dsrom_field_reprice_r8_20261006/reprice.json"
CLK = 1.2e9
RANKS = 4
S81_STAGES = 81                  # the S81 binding (stage_map.json) and the head model's layer-die base
sys.path.insert(0, str(ROOT / "tools"))
import dsrom_1m_allmeasured_adapters as _AD  # noqa: E402  (FIELD_GEOM: the adopted element frame)
GEOM = _AD.FIELD_GEOM
_G = json.loads((ROOT / REPRICE).read_text())["geoms"][GEOM] if GEOM else {}
STAGES = _G.get("stages", S81_STAGES)
assert _G.get("layer_dies", STAGES * RANKS) == STAGES * RANKS, "re-price layer dies are not stages x TP4"
PKG_PER_TRAY = 4                 # rack study: 1 OU liquid tray of four two-die packages
RACK_PITCH_M = 0.6               # ORv3 frame width (Open Rack v3, 600 mm)
REAR_LEG_M = 0.4                 # tray rear edge to the cable channel, each end (rack study adjacent-tray 0.798 m)


def J(p):
    return json.loads((ROOT / p).read_text())


def sha(p):
    return hashlib.sha256((ROOT / p).read_bytes()).hexdigest()


def counts():
    hr = J(HEADREC)
    head = hr["verdict"]["recommended_head_dies"]
    total = next(v for v in hr["variants"] if v["NV"] == 5)["head_groups"][str(head)]["total_dies"]
    layer = STAGES * RANKS
    base_layer = len(J(STAGE_MAP)["rank_dies"])               # 324: the head model prices the S81 array
    assert base_layer == S81_STAGES * RANKS
    table = total - base_layer - head
    draft = J(DRAFTLEV)["dies_added"]
    assert "1 of 12" in json.dumps(J(HEADLEV)) and head == 12, "head lever no longer prices 12 head dies"
    return dict(stages=STAGES, layer=layer, head=head, table=table, draft=draft, dies=layer + head + table + draft,
                src=dict(head=f"{HEADREC} verdict.recommended_head_dies (owner-adopted 12, codex_notes 2026-10-04 "
                              f"'12 head dies / 372 total stay'); {HEADLEV} 'per head die (1 of 12)'",
                         stages=f"{REPRICE} geoms['{GEOM}'] stages / layer_dies (adopted element frame, "
                                f"tools/dsrom_1m_allmeasured_adapters.FIELD_GEOM; S81 = {S81_STAGES} stages)",
                         table=f"{HEADREC} head_groups['12'].total_dies {total} - {base_layer} S81 layer - {head} head",
                         draft=f"{DRAFTLEV} dies_added (DP1-EP5)"))


def stacks(c):
    sm = J(STAGE_MAP)
    s81_homes = sorted(set(sm["scan_service_homes"].values()))
    tail = sum(1 for x in sm["PHW_required_by_stage"] if x == 1)            # S81: 7 non-matrix tail stages
    m81 = S81_STAGES - tail
    m = STAGES - tail
    scan_stages = [round(h * m / m81) for h in s81_homes]                  # identity at S81
    assert len(set(scan_stages)) == len(s81_homes) and max(scan_stages) < m
    scan_dies = RANKS * len(scan_stages)
    per = dict(scan=4, layer=1, head=4, table=0, draft=0)
    tot = scan_dies * per["scan"] + (c["layer"] - scan_dies) * per["layer"] + c["head"] * per["head"]
    return dict(per_die=per, scan_stages=scan_stages, scan_dies=scan_dies, total=tot,
                rule_4S_plus_128_at_8_head=4 * STAGES + 3 * scan_dies + 4 * 8,
                src=f"{SCEN_C} line 17 (scenario C: 4 stacks on the 32 index-scanning rank dies, 1 on the other rank "
                    f"dies, 4 on each head die; tables none); scan stages {STAGE_MAP} scan_service_homes "
                    f"(provisional homes: the count, 32 dies, is what the stacks need); at {STAGES} stages the S81 "
                    f"homes {s81_homes} are scaled to the {STAGES - (S81_STAGES - m81)} matrix stages (provisional)",
                note="the power model's 452 (tools/dsrom_c_recheck.py stacks = 4S + 128) is this rule with 8 head "
                     "dies; draft expert replicas (DP1-EP5) hold no per-user state, the drafter's KV rides on the "
                     "head dies' stacks as in scenario C")


def link_classes():
    rk = J(RACK)["physical_constants"]
    lf = J(LFF)
    tw = rk["twinax_ns_per_m"]["value"]
    inc = rk["hop_flight_included_m"]["value"]
    dac = rk["dac_112g_reach_m"]["value"]
    aec = rk["aec_added_latency_ns"]["value"][0]
    hop_cyc = lf["hop"]["total_cycles"]

    def cls(name, length_m, what):
        fl = max(0.0, (length_m - inc) * tw)
        ret = aec if length_m > dac else 0.0
        extra_ns = fl + ret
        return dict(cls=name, what=what, length_m=round(length_m, 3), medium=(
            "board trace (<= 0.3 m, inside the 200 ns channel)" if name == "in-tray" else
            "passive twinax DAC" if length_m <= dac else "AEC (analog retimer)"),
            fec="RS(544,514) KP4 (full)", flight_extra_ns=round(fl, 2), retimer_ns=ret,
            extra_cycles=math.ceil(extra_ns * 1e-9 * CLK - 1e-9),
            hop_cycles=hop_cyc + math.ceil(extra_ns * 1e-9 * CLK - 1e-9))
    return cls, dict(twinax_ns_per_m=tw, flight_included_m=inc, dac_reach_m=dac, aec_ns=aec, hop_cycles=hop_cyc,
                     hop_us=lf["hop"]["us"], light_fec_hop_cycles_was=lf["hop"]["light_fec_cycles"],
                     src=f"{LFF} hop (RTL ot_dsrom_link_rt, board channel 251 cycles = 209 ns full KP4); {RACK} "
                         "physical_constants twinax_ns_per_m / hop_flight_included_m / dac_112g_reach_m / "
                         "aec_added_latency_ns")


def build():
    rk = J(RACK)
    pc, pw = rk["physical_constants"], rk["power"]
    OU_MM, USABLE = pc["orv3_ou_mm"]["value"], pc["orv3_usable_ou"]["value"]
    WALL, MARGIN, SHELF = pw["wall_factor"], pw["provision_margin"], pw["shelves"]["n_plus_1_w"]
    STACK_W, TRAY_KG = pc["hbm3e_stack_static_w"]["value"], pc["tray_mass_kg"]["value"]
    import dsrom_c_recheck as C
    LAYER_W = J(S81FP)["scan_die_power"]["total_saturated_w"]
    HT_W = (C.HEAD_W + C.TABLE_W) / C.HEAD_TABLE_DIES     # C1 ledger: the same W a head or table die
    c = counts()
    st = stacks(c)
    scan = set(st["scan_stages"])
    pid = [0]

    def pk(role, dies, s=None):
        p = dict(id=pid[0], r=role, d=dies)
        if s is not None:
            p["s"] = s
        pid[0] += 1
        return p

    def die_stacks(p):
        if p["r"] == "stage":
            return st["per_die"]["scan" if p["s"] in scan else "layer"]
        return st["per_die"][p["r"]]

    def die_w(p):
        return HT_W if p["r"] in ("head", "table") else LAYER_W

    def tray(kind, pks, label):
        for p in pks:
            p["k"] = die_stacks(p)            # HBM3E stacks on each die of this package
        n = sum(len(p["d"]) for p in pks)
        sk = sum(len(p["d"]) * die_stacks(p) for p in pks)
        return dict(ou=1, kind=kind, pk=pks, label=label, stacks=sk,
                    w=round(sum(len(p["d"]) * die_w(p) for p in pks) + sk * STACK_W, 1), dies=n)

    stage_pk = [[pk("stage", [f"s{s}r{2 * q}", f"s{s}r{2 * q + 1}"], s) for q in range(2)] for s in range(STAGES)]
    stage_trays = []
    for s in range(0, STAGES, 2):
        pks = stage_pk[s] + (stage_pk[s + 1] if s + 1 < STAGES else [])
        lab = f"stage tray S{s}" + (f" + S{s + 1}" if s + 1 < STAGES else "")
        sc = [x for x in (s, s + 1) if x in scan]
        stage_trays.append(tray("stage", pks, lab + (f" (scan die{'s' if len(sc) > 1 else ''}: S{', S'.join(map(str, sc))}, 4 stacks)" if sc else "")))
    head_pk = [pk("head", [f"h{2 * i}", f"h{2 * i + 1}"]) for i in range(c["head"] // 2)]
    table_pk = [pk("table", [f"t{2 * i}", f"t{2 * i + 1}"]) for i in range(c["table"] // 2)]
    draft_pk = [pk("draft", [f"d{2 * i}", f"d{2 * i + 1}"]) for i in range(c["draft"] // 2)]
    chunk = lambda L: [L[i:i + PKG_PER_TRAY] for i in range(0, len(L), PKG_PER_TRAY)]  # noqa: E731
    head_trays = [tray("head", g, f"head tray {i}: embed, LM head, norm") for i, g in enumerate(chunk(head_pk))]
    table_trays = [tray("table", g, f"Engram table tray {i}") for i, g in enumerate(chunk(table_pk))]
    draft_trays = [tray("draft", g, f"draft tray {i} (DP1-EP5 expert replicas)") for i, g in enumerate(chunk(draft_pk))]
    infra = [dict(h=1, kind="switch", label="Engram / host switch (51.2T class, 1 OU)", w=1500.0),
             dict(h=2, kind="host", label="host: 2-socket CPU + 2 x 400G NIC (prefill KV ingest) + BMC", w=900.0)]

    def shelves(prov):
        return 2 * max(1, -(-int(prov) // int(SHELF)))

    def prov_w(trs, inf):
        return sum(t["w"] for t in trs) * WALL * MARGIN + (sum(r["w"] for r in inf) + 100) * MARGIN

    def fits(trs, inf):
        return len(trs) + sum(r["h"] for r in inf) + shelves(prov_w(trs, inf)) + 1 <= USABLE

    # R1 (bottom -> top): shelves, stage trays S(2k)..S0 (descending, so the chain runs DOWN), head, draft, infra.
    # R2 (bottom -> top): shelves, the Engram table trays, then the stage trays continuing upward to S80: the tables
    # below lift S80 to the head trays' height, so both rack crossings (the stage hop and the head hop) stay inside
    # the 2 m passive-DAC reach (no AEC).
    k = len(stage_trays)
    while k and not fits(stage_trays[:k] + head_trays + draft_trays, infra):
        k -= 1
    r1_stage, r2_stage = stage_trays[:k], stage_trays[k:]
    assert r2_stage and fits(r2_stage + table_trays, []), f"S{STAGES} does not fit two racks in this template"

    def rack(name, trays_bottom_up, inf):
        prov = prov_w(trays_bottom_up, inf)
        ns = shelves(prov)
        rows, ou = [], 1
        for s in range(ns):
            rows.append(dict(ou=ou, h=1, kind="power", label=f"power shelf {'AB'[s % 2]}{s // 2 + 1} (33 kW, 6 x 5.5 kW PSU)"))
            ou += 1
        for t in trays_bottom_up:
            rows.append(dict(ou=ou, h=1, kind=t["kind"], label=t["label"], pk=t["pk"], w=t["w"], stacks=t["stacks"]))
            ou += 1
        for r in inf:
            rows.append(dict(ou=ou, h=r["h"], kind=r["kind"], label=r["label"]))
            ou += r["h"]
        rows.append(dict(ou=ou, h=1, kind="mgmt", label="management switch (1 GbE OOB) + leak detection"))
        ou += 1
        chips = sum(t["w"] for t in trays_bottom_up)
        infra_w = sum(r["w"] for r in inf) + 100
        kg = 170 + 60 + len(trays_bottom_up) * (TRAY_KG[0] + TRAY_KG[1]) / 2 + sum(r["h"] for r in inf) * 12 + ns * 8
        return dict(name=name, rows=rows, used_ou=ou - 1, dies=sum(t["dies"] for t in trays_bottom_up),
                    packages=sum(len(t["pk"]) for t in trays_bottom_up), trays=len(trays_bottom_up),
                    stacks=sum(t["stacks"] for t in trays_bottom_up), chips_kw=round(chips / 1e3, 2),
                    wall_kw=round((chips * WALL + infra_w) / 1e3, 2), prov_kw=round(prov / 1e3, 2), shelves=ns,
                    kg=round(kg))
    racks = [rack("R1", list(reversed(r1_stage)) + head_trays + draft_trays, infra),
             rack("R2", table_trays + r2_stage, [])]
    # positions: (rack index, OU) of every stage, head tray 0 and draft tray 0
    loc = {}
    for ri, r in enumerate(racks):
        for row in r["rows"]:
            for p in row.get("pk", []):
                key = ("s", p["s"]) if "s" in p else (p["r"], None)
                loc.setdefault(key, (ri, row["ou"]))
    cls, lk = link_classes()

    def hop(a, b, what):
        (ra, oa), (rb, ob) = loc[a], loc[b]
        if (ra, oa) == (rb, ob):
            return cls("in-tray", 0.3, what)
        dh = abs(oa - ob) * OU_MM / 1e3
        if ra == rb:
            return cls("in-rack", max(2 * REAR_LEG_M, dh + 2 * REAR_LEG_M), what)
        return cls("rack-to-rack", dh + 2 * REAR_LEG_M + RACK_PITCH_M * abs(ra - rb), what)
    stage_hops = [dict(src=f"S{s}", dst=f"S{s + 1}", **hop(("s", s), ("s", s + 1), "stage hop"))
                  for s in range(STAGES - 1)]
    head_hop = dict(src=f"S{STAGES - 1}", dst="head", **hop(("s", STAGES - 1), ("head", None), "head hop (last stage -> head dies)"))
    ret = dict(src="head", dst="S0", **hop(("head", None), ("s", 0), "token return (head -> stage 0)"))
    draft = dict(src="head", dst="draft", **hop(("head", None), ("draft", None), "draft seed / replica links (head and draft trays)"))
    summ = {}
    for h in stage_hops:
        summ[h["cls"]] = summ.get(h["cls"], 0) + 1
    extra = sum(h["extra_cycles"] for h in stage_hops)
    cross = [h for h in stage_hops if h["cls"] == "rack-to-rack"]
    tot_stacks = sum(r["stacks"] for r in racks)
    assert tot_stacks == st["total"], (tot_stacks, st["total"])
    return dict(
        schema="opentallas.dsrom-s81-rack.v1", tool="tools/dsrom_s81_rack.py",
        decision_links="OWNER 2026-10-06: full RS(544,514) FEC on every off-package link (board, in-rack cable, rack "
                       "to rack) for both the DS ROM array and the HBM accelerator; light FEC is not used anywhere. "
                       "In-package UCIe keeps its own spec.",
        geometry=dict(field_geom=GEOM, stages=STAGES, layer_dies=STAGES * RANKS, s81_stages=S81_STAGES,
                      extra_stages=STAGES - S81_STAGES, label=_G.get("label"),
                      pairs_per_layer_die=_G.get("pairs"),
                      src=f"{REPRICE} geoms['{GEOM}'] (default QELEM, owner go 3661e31c6)"),
        counts=c, stacks=st,
        die_w=dict(layer=LAYER_W, head_table=round(HT_W, 2), stack=STACK_W,
                   src=f"{S81FP} scan_die_power.total_saturated_w (busiest layer die, used for every layer and draft "
                       f"die); {RECHECK} (HEAD_W + TABLE_W) / HEAD_TABLE_DIES (C1 ledger: one W a head or table die); "
                       f"{RACK} hbm3e_stack_static_w"),
        packing=dict(rule="2 consecutive stages a 1 OU tray of 4 two-die packages (board link between them); the "
                          "stage chain is a U over two racks (R1 top -> bottom, across at the bottom, R2 bottom -> "
                          "top, above the Engram table trays); head trays beside S0 (8-traversal token return on the shortest cable), draft trays "
                          f"beside the head trays; Engram tables at the bottom of R2 (lifts S{STAGES - 1} to the head trays' height)",
                     minimum=f"{STAGES} stages at 2 a tray = {-(-STAGES // 2)} trays: {STAGES // 2} board hops + "
                             f"{STAGES - 1 - STAGES // 2} cable hops is the minimum; one stage hop crosses racks "
                             f"(S{STAGES} does not fit one 44 OU rack with its power shelves)",
                     r1_stages=[0, 2 * k - 1], r2_stages=[2 * k, STAGES - 1],
                     rack_crossing=dict(src=cross[0]["src"], dst=cross[0]["dst"], length_m=cross[0]["length_m"],
                                        medium=cross[0]["medium"]) if cross else None),
        racks=racks,
        link_basis=lk,
        link_classes=[
            dict(cls="in-package", what="die to die inside a two-die package (TP4 pair half)", medium="UCIe advanced package",
                 fec="none (UCIe CRC + retry)", ns=10.0, src="configs/hardware/technology.json links.rom_package_ucie"),
            dict(cls="in-tray", what="package to package on one tray board: TP4 collectives, stage hop between the "
                 "two stages of a tray", medium="112G PAM4 board trace <= 0.3 m", fec="RS(544,514) KP4 (full)",
                 ns=209.0, src="configs/hardware/technology.json links.rom_board_serdes full_kp4_fec_s; RTL hop "
                 f"{lk['hop_cycles']} cycles = {lk['hop_us']} us ({LFF})"),
            dict(cls="in-rack", what="tray to adjacent tray: stage hops, token return, draft links",
                 medium=f"passive twinax DAC ~{2 * REAR_LEG_M:.1f} m", fec="RS(544,514) KP4 (full)",
                 ns=round(209.0 + max(0, 2 * REAR_LEG_M - lk["flight_included_m"]) * lk["twinax_ns_per_m"], 1),
                 src="technology.json links.rom_rack_cable_serdes (209 ns) + flight beyond 0.3 m at 4.6 ns/m"),
            dict(cls="rack-to-rack", what="the one stage hop between racks and the head hop",
                 medium="passive twinax DAC <= 2 m (AEC past 2 m)", fec="RS(544,514) KP4 (full)",
                 ns=round(209.0 + (cross[0]["length_m"] - lk["flight_included_m"]) * lk["twinax_ns_per_m"], 1) if cross else None,
                 src=f"{RACK} dac_112g_reach_m 2 m (IEEE 802.3ck CR), twinax 4.6 ns/m; length from the packing"),
        ],
        stage_hops=stage_hops, head_hop=head_hop, token_return=ret, draft_links=draft,
        hop_summary=dict(stage_hops=summ, stage_hop_extra_cycles=extra,
                         head_hop_extra_cycles=head_hop["extra_cycles"],
                         token_return_extra_cycles_each=ret["extra_cycles"],
                         draft_link_extra_cycles_each=draft["extra_cycles"],
                         note="extra = flight beyond the 0.3 m inside the measured full-KP4 hop (+ AEC past 2 m); "
                              "the composition adds these to the measured hop"),
        inputs={p: sha(p) for p in (RACK, STAGE_MAP, S81FP, HEADREC, HEADLEV, DRAFTLEV, SCEN_C, LFF, RECHECK, REPRICE)},
        tool_sha256=sha("tools/dsrom_s81_rack.py"))


def main():
    rec = build()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(rec, indent=1) + "\n")
    c, s, h = rec["counts"], rec["stacks"], rec["hop_summary"]
    print(f"dies {c['dies']} (layer {c['layer']}, head {c['head']}, table {c['table']}, draft {c['draft']}); "
          f"stacks {s['total']} (rule at 8 head: {s['rule_4S_plus_128_at_8_head']})")
    print("racks", [(r["name"], r["used_ou"], r["trays"], r["dies"], r["stacks"], r["prov_kw"]) for r in rec["racks"]])
    print("stage hops", h["stage_hops"], "extra cyc", h["stage_hop_extra_cycles"], "head", rec["head_hop"]["cls"],
          rec["head_hop"]["length_m"], "return", rec["token_return"]["cls"], "crossing", rec["packing"]["rack_crossing"])
    print("->", OUT.relative_to(ROOT))


if __name__ == "__main__":
    main()
