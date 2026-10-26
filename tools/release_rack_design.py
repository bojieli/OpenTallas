#!/usr/bin/env python3
"""Release rack design and wiring plan (RACK-1021, OWNER request 2026-10-21).

Analytical design, no simulation.  Successor of tools/v41_rack_design.py (old V4.1: 188 dies, 2-die UCIe packages)
for the CURRENT release dies:

  S81 DeepSeek-V4.1 ROM array (first)  stage map -> TP4 groups -> 5-lane-pair rank dies (OWNER-approved 5th link)
  Qwen3-8B ROM                         compute + KV die pairs
  HBM accelerator                      DeepSeek and Qwen systems

For every system it writes
  (a) a connection list, one row per circuit (endpoint A die + SerDes macros, medium, endpoint B, length, reach,
      loss, latency, lanes, traffic), for OPTION D (direct: board traces + cables) and OPTION S (static circuits
      through the one-tier switch);
  (b) the tray / board plan (each TP group on one board, TP mesh as traces, trace length and loss vs KR 28 dB);
  (c) the rack elevation (folded serpentine pipeline order, power shelves, liquid cooling, switch trays for S);
  (d) power and thermal per tray and rack;
  (e) the sparing plan;
  (f) OPTION D vs OPTION S;
  (g) per-hop latency per circuit class (results/arch/release_rack_1021/hop_latency.json, read by the token-pass
      static schedule).

Every number carries a grade: published (vendor / standard), spec (this repo's committed records), MODEL
(allocator / analytical model or engineering estimate, unqualified) or derived (arithmetic on the others).
Physical constants and their sources are reused from tools/v41_rack_design.PHYS.

    python3 tools/release_rack_design.py          # writes results/arch/release_rack_1021/*
"""
from __future__ import annotations

import csv
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import v41_rack_design as V41  # noqa: E402  (PHYS constants, NVL72 / CM384 published figures)

OUT = ROOT / "results/arch/release_rack_1021"
S81_INPUT = OUT / "s81_stage_map_input.json"
CHAIN_PLAN = ROOT / "results/arch/mu_s81_1018/chain_plan.json"
F_CLK = 1.2e9

GRADE_MAP = {"published": "published", "spec": "spec", "derived": "derived", "measured": "spec",
             "estimate": "MODEL", "assumed": "MODEL", "published/estimate": "published"}


def P(key):
    """A PHYS constant from the V4.1 rack model with its grade mapped to the four report grades."""
    e = V41.PHYS[key]
    return dict(value=e["value"], grade=GRADE_MAP.get(e["grade"], "MODEL"), source=e["source"])


def N(value, grade, source):
    return dict(value=value, grade=grade, source=source)


# ---------------------------------------------------------------------------------------------------------------
# Constants new to the release design (the rest come from V41.PHYS)
# ---------------------------------------------------------------------------------------------------------------
C = dict(
    lane_bits=N(512, "spec", "reports/s81_links_1021.md s1: a lane carries 512 b/cycle at 1.2 GHz [RTL width x bench clock]"),
    lane_usable=N(0.764, "spec", "reports/s81_links_1021.md s1: compiler caps the off-die rate at 0.764 beats/cycle [RTL comment]"),
    macro_elec_lanes=N(6, "MODEL", "reports/s81_links_1021.md s1: the SerDes macro carries a 544-b KP4 word a cycle, ~6 x 112G-class lanes; macro abstract is a placeholder"),
    cable_lanes=N(8, "published", V41.PHYS["dac_800g_cr8"]["source"]),
    pcb_db_per_mm=N(0.0354, "MODEL", "ultra-low-loss stripline ~0.9 dB/in at 26.56 GHz (Megtron-7 / Tachyon-100G class laminate); engineering estimate, band 0.7-1.2 dB/in"),
    pkg_db=N(3.0, "MODEL", "package + BGA + via loss per end at 26.56 GHz; engineering estimate"),
    kr_budget_db=N(28.0, "published", V41.PHYS["dac_112g_reach_m"]["source"]),
    escape_mm=N(30.0, "MODEL", "package escape / via fan-out added to every board trace; estimate"),
    pkg_pitch_mm=N(70.0, "MODEL", "single-die package (25 x 32 mm die + 1 HBM3E 11 x 11 mm on a ~32 x 38 mm interposer, ~55 x 55 mm substrate) on a 70 mm pitch with VR and cold-plate keep-outs; estimate"),
    flyover_mm=N(0.45, "MODEL", "near-package flyover twinax from the package to the rear OSFP cage of a 1 OU tray (~800 mm deep): mean length per end, estimate"),
    cable_slack_m=N(0.35, "MODEL", "rear cable management: bend radius + service loop per external cable, estimate"),
    rack_pitch_m=N(0.6, "published", "Open Rack 24 in (610 mm) outside width; " + V41.PHYS["orv3_it_width_mm"]["source"]),
    switch_lanes=N(512, "derived", "Tomahawk Ultra 51.2 Tb/s / 100 Gb/s lanes = 512 lanes (" + V41.PHYS["switch_capacity_tbps"]["source"] + ")"),
    switch_phy_fec_ns=N(100.0, "spec", "tools/s81_dv/dv_mu_chain.py: switched crossing budget 377.6 ns = PHY/FEC 100 + switch 250 + cable 27.6 (lanes/TOKEN-XDIE-S81.md s2)"),
    switched_budget_ns=N(377.6, "spec", "same: the off-chip leg modelled at 453 cycles = 377.6 ns in the xdie co-sims (results/rtl/xdie_s81_1018/1019)"),
    aec_w=N(10.0, "published", V41.PHYS["aec_112g_reach_m"]["source"]),
    optic_w=N(16.0, "published", "800G OSFP DR8 / 2xFR4 transceiver ~14-17 W (vendor datasheets, e.g. Broadcom / Coherent 800G OSFP); one module per cable end"),
    tray_misc_w=N(60.0, "MODEL", "BMC, management NIC, pump / fan share and misc per 1 OU tray; estimate"),
    switch_asic_ou=N(1, "MODEL", "one 51.2T ASIC per 1 OU switch tray (NVL72 NVLink switch trays are 1 RU with 2 ASICs; estimate)"),
    mgmt_ou=N(1, "MODEL", "1 OU management switch per rack; estimate"),
    shelves_per_side=N(3, "MODEL", "2N power: side A carries the load on 3 shelves (N+1 inside each), side B mirrors (as tools/v41_rack_design.py)"),
    shelf_usable_kw=N(27.5, "published", V41.PHYS["power_shelf_kw"]["source"]),
    liquid_tray_kw_max=N(5.5, "published", "GB200 NVL72 compute tray: 4 B200 + 2 Grace ~5.4-5.7 kW in 1 RU, liquid cold plates (NVIDIA GB200 NVL72 / DGX guide)"),
    tray_swap_min=N(30, "MODEL", "tray swap with blind-mate liquid quick disconnects and rear re-plug of its cables; estimate"),
    repoint_s=N(1, "MODEL", "rewrite of a switch's static circuit table (cross-connect map) and link retrain; estimate"),
)


def v(k):
    return C[k]["value"] if k in C else V41.PHYS[k]["value"]


def ns_to_cycles(ns):
    return int(math.ceil(ns * 1e-9 * F_CLK))


# ---------------------------------------------------------------------------------------------------------------
# Link physics
# ---------------------------------------------------------------------------------------------------------------
_CUR = dict(lanes=12, macros_per_pair=2)   # set by each system builder


def circuit_lanes():
    """Electrical 112G lanes per direction a circuit (S81: lane pair = 2 SerDes macros x 6 lanes)."""
    return _CUR["lanes"]


def trace(length_mm):
    """A board trace circuit: KR channel check, latency = the full-KP4 hop (which includes 0.3 m of flight)."""
    loss = length_mm * v("pcb_db_per_mm") + 2 * v("pkg_db")
    extra_m = max(0.0, length_mm / 1000 - v("hop_flight_included_m"))
    ns = v("cable_hop_s") * 1e9 + extra_m * v("pcb_ns_per_m")
    return dict(medium="board trace", length_m=round(length_mm / 1000, 3), loss_db=round(loss, 1),
                reach_ok=loss <= v("kr_budget_db"), reach_limit="KR 28 dB bump to bump", latency_ns=round(ns, 1),
                cycles=ns_to_cycles(ns), cables=0, retimers=0)


def cable(length_m):
    """Off-board circuit: passive DAC <= 2 m, AEC <= 7 m, else optics.  Twinax flight beyond the 0.3 m the
    209 ns hop already carries; AEC adds its analog retimer (3 ns, published)."""
    if length_m <= v("dac_112g_reach_m"):
        med, extra, limit = "passive DAC", 0.0, "<= 2 m passive copper (802.3ck CR)"
    elif length_m <= v("aec_112g_reach_m"):
        med, extra, limit = "AEC", V41.PHYS["aec_added_latency_ns"]["value"][0], "<= 7 m active copper (Credo AEC)"
    else:
        med, extra, limit = "optics", 20.0, "optics (DSP module ~20 ns, MODEL)"
    ns = v("cable_hop_s") * 1e9 + max(0.0, length_m - v("hop_flight_included_m")) * v("twinax_ns_per_m") + extra
    return dict(medium=med, length_m=round(length_m, 2), loss_db=None, reach_ok=True, reach_limit=limit,
                latency_ns=round(ns, 1), cycles=ns_to_cycles(ns),
                cables=math.ceil(circuit_lanes() / v("cable_lanes")), retimers=0)


def switched(len_a_m, len_b_m):
    """OPTION S crossing: die -> switch port -> die.  Endpoint PHY/FEC 100 ns + Tomahawk-Ultra 250 ns + flight of
    both legs (+ AEC retimers past 2 m)."""
    legs = []
    extra = 0.0
    for L in (len_a_m, len_b_m):
        if L <= v("dac_112g_reach_m"):
            legs.append("passive DAC")
        elif L <= v("aec_112g_reach_m"):
            legs.append("AEC")
            extra += V41.PHYS["aec_added_latency_ns"]["value"][0]
        else:
            legs.append("optics")
            extra += 20.0
    ns = v("switch_phy_fec_ns") + v("switch_latency_s") * 1e9 + (len_a_m + len_b_m) * v("twinax_ns_per_m") + extra
    return dict(medium="switch port (%s / %s)" % tuple(legs), legs=legs, length_m=round(len_a_m + len_b_m, 2),
                reach_ok=True, latency_ns=round(ns, 1), cycles=ns_to_cycles(ns),
                within_budget=ns <= v("switched_budget_ns"))


# ---------------------------------------------------------------------------------------------------------------
# Geometry: 1 OU tray with four 2 x 2 package quads; folded serpentine over racks
# ---------------------------------------------------------------------------------------------------------------
QUAD_XY = {0: (140.0, 560.0), 1: (140.0, 330.0), 2: (393.0, 330.0), 3: (393.0, 560.0)}   # mm: x across, y from front
RANK_OFF = {0: (-0.5, -0.5), 1: (0.5, -0.5), 2: (0.5, 0.5), 3: (-0.5, 0.5)}                # ring order around the quad


def pkg_xy(quad, rank, slots=4):
    qx, qy = QUAD_XY[quad]
    ox, oy = RANK_OFF[rank % 4]
    p = v("pkg_pitch_mm")
    return qx + ox * p, qy + oy * p


def trace_mm(a, b):
    (ax, ay), (bx, by) = a, b
    return abs(ax - bx) + abs(ay - by) + v("escape_mm")


def fold(units, per_side=2):
    """Folded ring over trays: tray t holds out-going units 2t, 2t+1 (quads 0, 1) and the returning units (quads 2, 3).
    Every ring neighbour then sits in the same tray or the next one, and the ring closes inside tray 0."""
    n = len(units)
    half = (n + 1) // 2
    out, back = units[:half], units[half:][::-1]
    k = per_side
    ntray = math.ceil(half / k)
    trays = []
    for t in range(ntray):
        q = {}
        for i, u in enumerate(out[k * t:k * t + k]):
            q[i] = u
        for i, u in enumerate(back[k * t:k * t + k][::-1]):
            q[3 - i] = u    # back half runs the other way: quad 2 -> 3 inside a tray, 3 of tray t+1 -> 2 of tray t
        trays.append(q)
    return trays


def rack_slots(ntrays, per_rack, below=0):
    """Serpentine tray order over racks: R1 bottom -> top, R2 top -> bottom, ...  Returns [(rack, ou)] per tray,
    ou counted from the first compute OU (power shelves below)."""
    racks = math.ceil(ntrays / per_rack)
    per = math.ceil(ntrays / racks)
    slots = []
    for t in range(ntrays):
        r, k = divmod(t, per)
        ou = k if r % 2 == 0 else per - 1 - k
        slots.append((r, ou + below))
    return slots, racks, per


def tray_cable_m(sa, sb):
    """Length of an external tray-to-tray cable (rear cage to rear cage) plus both flyovers."""
    (ra, oa), (rb, ob) = sa, sb
    ext = abs(ra - rb) * v("rack_pitch_m") + abs(oa - ob) * v("orv3_ou_mm") / 1000 + v("cable_slack_m")
    if ra != rb:
        ext += 0.3      # over the rack side rails / through the cable manager between racks
    return ext + 2 * v("flyover_mm")


# ---------------------------------------------------------------------------------------------------------------
# S81 DeepSeek ROM array
# ---------------------------------------------------------------------------------------------------------------
S81_PAIRS = {
    # lane pair -> (SerDes macros, role).  5-circuit lane plan (lanes/S81-LINK5.md, OWNER 10-21 5th pair):
    # slice s_0S = W column S, s_7S = E column S, s_7N = E column N, s_0N = W column N; pair A = macros 0/1, B = 2/3
    "WS": ("lk_WS0+lk_WS1", "s_0S pair A: TP peer d-1"),
    "ES": ("lk_ES0+lk_ES1", "s_7S pair A: TP peer d+1"),
    "EN": ("lk_EN0+lk_EN1", "s_7N pair A: TP peer d+2 (one bidirectional circuit, EN<->EN)"),
    "WN": ("lk_WN0+lk_WN1", "s_0N pair A: stage NEXT (TX data to next stage, same rank)"),
    "W5": ("lk_WN2+lk_WN3", "s_0N pair B: stage PREV (RX data from previous stage, same rank; 5th pair, OWNER 10-21)"),
    "E6": ("lk_EN2+lk_EN3", "E column B: copy-A/B reserve (blockage on the G4 rank die; wired only on pre-group dies)"),
    "W6": ("lk_WS2+lk_WS3", "copy-A/B reserve: copy-B merge (post-group stage dies only)"),
    "HX": ("lk_HOST0+lk_HOST1", "host SerDes pair on head-die trays only (S81.HOST, direct cabling)"),
}
S81_HOST = dict(
    decision="S81.HOST (coordinator, 10-21, direct cabling): the host attaches only to the head dies (extra SerDes on "
             "head-die trays). Host traffic to stage dies (config, KV ingest, token in/out) rides in-band on the "
             "existing pipeline/stage circuits in calendar slots (20-30x bandwidth headroom). Stage dies have no host "
             "link: the s_7N host-plane port maps to the in-band route. Every tray carries a low-rate management "
             "sideband (boot/config: I2C/SMBus + 1GbE BMC class) to the rack management switch; it is not a SerDes.",
    mgmt_medium="mgmt sideband (I2C/SMBus + 1GbE BMC)",
    host_cable_m=1.5,
    grade="spec (coordinator decision); host NIC position and sideband lengths MODEL")


def s81_inputs():
    inp = json.loads(S81_INPUT.read_text())
    stages, layer_dies, src = inp["stages"], inp["layer_dies"], "MODEL allocator (input file)"
    if inp.get("stage_map_path"):
        p = Path(inp["stage_map_path"])
        p = p if p.is_absolute() else ROOT / p
        if p.exists():
            m = json.loads(p.read_text())
            stages = m.get("stages_count") or len(m["stages"])
            layer_dies = inp["tp"] * stages
            src = "stage map %s (%s)" % (p.relative_to(ROOT) if p.is_relative_to(ROOT) else p,
                                         "qualified" if inp.get("qualified") else "unqualified")
    plan = json.loads(CHAIN_PLAN.read_text())
    return inp, stages, layer_dies, src, plan


def s81_units():
    inp, stages, layer_dies, src, plan = s81_inputs()
    cb = inp["copy_b"]
    per_copy = round(layer_dies / cb["layers"])
    per_copy = 4 * math.ceil(per_copy / 4)                 # whole TP4 groups
    run = per_copy // 4                                     # stages in a duplicated group
    groups = []
    for name, layer in sorted(cb["groups_81map"].items(), key=lambda kv: kv[1]):
        s0 = round(int(name[1:]) * stages / cb["stages_81map"])
        groups.append(dict(group81=name, layer=layer, start=s0, stop=s0 + run, pre=s0 - 1, post=s0 + run))
    hd = inp["head"]["dies"]
    units, die = [], 0
    for h in range(hd // 4):
        units.append(dict(id="H%d" % h, kind="head", dies=list(range(die, die + 4)))); die += 4
    stage_unit = {}
    for s in range(stages):
        u = dict(id="S%03d" % s, kind="stage", dies=list(range(die, die + 4))); die += 4
        units.append(u); stage_unit[s] = u
        for g in groups:
            if s == g["stop"] - 1:          # copy B sits right after the copy-A run in rack order
                for k in range(run):
                    b = dict(id="B%d.%d" % (g["layer"], k), kind="copyB", group=g["layer"],
                             dies=list(range(die, die + 4))); die += 4
                    units.append(b)
    return dict(inp=inp, stages=stages, layer_dies=layer_dies, src=src, plan=plan, units=units, groups=groups,
                per_copy=per_copy, run=run, head_dies=hd, dies=die)


def s81_edges(S):
    """Logical circuits: (kind, unit_a, rank_a, pair_a, unit_b, rank_b, pair_b)."""
    U = {u["id"]: u for u in S["units"]}
    E = []
    for u in S["units"]:
        for r in range(4):                                  # TP4 full mesh: d+1 on S tier, d+2 on N tier
            E.append(("tp_mesh", u["id"], r, "ES", u["id"], (r + 1) % 4, "WS"))
        for r in range(2):                                  # TP d+2: s_7N pair A <-> s_7N pair A, one circuit
            E.append(("tp_mesh", u["id"], r, "EN", u["id"], r + 2, "EN"))
    chain = ["H%d" % h for h in range(S["head_dies"] // 4)] + ["S%03d" % s for s in range(S["stages"])]
    for i, a in enumerate(chain):
        b = chain[(i + 1) % len(chain)]
        kind = ("token_return" if a.startswith("H") and b == "S000" else "head_hop" if b.startswith("H")
                else "stage_hop")
        for r in range(4):                                  # stage hop: s_0N pair A -> next stage s_0N pair B
            E.append((kind, a, r, "WN", b, r, "W5"))
    for g in S["groups"]:
        bs = ["B%d.%d" % (g["layer"], k) for k in range(S["run"])]
        for r in range(4):
            E.append(("copyb_in", "S%03d" % g["pre"], r, "E6", bs[0], r, "W5"))
            for x, y in zip(bs, bs[1:]):
                E.append(("copyb_hop", x, r, "WN", y, r, "W5"))
            E.append(("copyb_out", bs[-1], r, "WN", "S%03d" % g["post"], r, "W6"))
    for h in range(S["head_dies"] // 4):                    # S81.HOST: host links on head dies only
        for r in range(4):
            E.append(("host", "H%d" % h, r, "HX", "host", 0, "NIC"))
    assert all(e[1] in U and (e[4] in U or e[4] == "host") for e in E)
    return E


TRAFFIC = {
    # per-circuit traffic, from reports/s81_links_1021.md and BAL195 link_check (source read + arithmetic)
    "tp_mesh": dict(beats_per_user_token=12500 / 3, grade="derived",
                    source="reports/s81_links_1021.md s4: a TP port carries ~12.5k beats a token, spread over its 3 TP circuits"),
    "stage_hop": dict(beats_per_user_token=652 * 2, grade="spec",
                      source="results/arch/mu_s81_1018/chain_plan.json links: h message 40,976 B a rank die = 652 cycles on a lane pair (2 lanes)"),
}
for k in ("head_hop", "token_return", "copyb_in", "copyb_out", "copyb_hop"):
    TRAFFIC[k] = TRAFFIC["stage_hop"]


def place(units, per_side=2):
    trays = fold(units, per_side)
    loc = {}
    for t, q in enumerate(trays):
        for quad, u in q.items():
            loc[u["id"]] = (t, quad)
    return trays, loc


def tray_power_w(dies_by_role, die_w, stack_w, stacks_by_role, serdes_macros):
    chip = sum(n * die_w[r] for r, n in dies_by_role.items())
    hbm = sum(n * stack_w for n in stacks_by_role.values())
    ser = serdes_macros * v("macro_elec_lanes") * v("lane_gbps") * 1e9 * v("serdes_pj_per_bit") * 1e-12
    it = chip + hbm + ser + v("tray_misc_w")
    return dict(die_w=round(chip, 1), hbm_w=round(hbm, 1), serdes_w=round(ser, 1), misc_w=v("tray_misc_w"),
                it_w=round(it, 1), dc_input_w=round(it / v("vr_efficiency"), 1))


def assemble(name, title, units, edges, pair_macros, die_w, stacks_per_die, traffic, spare_per_rack=1, units_fold=None,
             per_side=2):
    """Place units (TP groups, 4 dies a quad) on folded trays and serpentine racks, then size every circuit."""
    U = {u["id"]: u for u in units}
    trays, loc = place(units_fold or units, per_side)
    stack_w = v("hbm3e_stack_static_w")
    pairs_per_die = {}
    for e in edges:
        for (u, r, p) in ((e[1], e[2], e[3]), (e[4], e[5], e[6])):
            if u == "host":
                continue
            pairs_per_die.setdefault((u, r), set()).add(p)
    tray_rows = []
    for t, q in enumerate(trays):
        roles, stacks, macros = {}, {}, 0
        for quad, u in q.items():
            k = u["kind"]
            nd = len(u["dies"])
            roles[k] = roles.get(k, 0) + nd
            stacks[k] = stacks.get(k, 0) + nd * stacks_per_die[k]
            macros += sum(_CUR["macros_per_pair"] * len(pairs_per_die.get((u["id"], r), ())) for r in range(nd))
        pw = tray_power_w(roles, die_w, stack_w, stacks, macros)
        tray_rows.append(dict(tray=t, quads={k: u["id"] for k, u in q.items()}, dies=sum(roles.values()),
                              hbm_stacks=sum(stacks.values()), serdes_macros=macros, **pw))
    worst = max(r["dc_input_w"] for r in tray_rows)
    side_kw = v("shelves_per_side") * v("shelf_usable_kw")
    ou_free = v("orv3_usable_ou") - 2 * v("shelves_per_side") - v("mgmt_ou")
    per_rack = min(ou_free, int(side_kw * 1000 // worst)) - spare_per_rack
    slots, nracks, per = rack_slots(len(trays), per_rack, below=2 * v("shelves_per_side"))
    rows = []
    lanes = circuit_lanes()
    for i, (kind, ua, ra, pa, ub, rb, pb) in enumerate(edges):
        ta, qa = loc[ua]
        if ub == "host":                                    # host NIC beside the head-die tray (MODEL length)
            rows.append(dict(id="%s.%05d" % (name.lower(), i), system=name, cls=kind, a_unit=ua, a_die=U[ua]["dies"][ra],
                             a_rank=ra, a_pair=pa, a_macros=pair_macros[pa][0], b_unit="host", b_die=-1, b_rank=0,
                             b_pair=pb, b_macros="host NIC", a_tray=ta, b_tray=ta, lanes_per_dir=lanes,
                             D=cable(S81_HOST["host_cable_m"]), traffic=traffic.get(kind)))
            continue
        tb, qb = loc[ub]
        if ta == tb:
            D = trace(trace_mm(pkg_xy(qa, ra), pkg_xy(qb, rb)))
        else:
            D = cable(tray_cable_m(slots[ta], slots[tb]))
        rows.append(dict(id="%s.%05d" % (name.lower(), i), system=name, cls=kind, a_unit=ua, a_die=U[ua]["dies"][ra],
                         a_rank=ra, a_pair=pa, a_macros=pair_macros[pa][0], b_unit=ub, b_die=U[ub]["dies"][rb], b_rank=rb,
                         b_pair=pb, b_macros=pair_macros[pb][0], a_tray=ta, b_tray=tb, lanes_per_dir=lanes, D=D,
                         traffic=traffic.get(kind)))
    return rows, tray_rows, slots, nracks, per, spare_per_rack


def build_s81():
    _CUR.update(lanes=12, macros_per_pair=2)
    S = s81_units()
    E = s81_edges(S)
    die_w = dict(stage=84.1, copyB=84.1, head=92.34)
    stacks = dict(stage=1, copyB=1, head=S["inp"]["head"]["hbm_stacks_per_die"])
    rows, tray_rows, slots, nracks, per, spare = assemble("S81", "S81", S["units"], E, S81_PAIRS, die_w, stacks, TRAFFIC)
    rec = finish_system(
        name="S81", title="S81 DeepSeek-V4.1 ROM array", S=S, rows=rows, tray_rows=tray_rows, slots=slots,
        nracks=nracks, per_rack=per, spare_per_rack=spare, die_w=die_w, users=S["inp"]["users_ar"],
        token_cycles=S["inp"]["token_cycles_ar"], phases=S["inp"]["collective_phases_per_token"],
        counts=dict(stages=S["stages"], layer_dies=S["layer_dies"], copy_b_dies=S["per_copy"] * len(S["groups"]),
                    copy_b_groups=len(S["groups"]), copy_b_dies_per_group=S["per_copy"], head_dies=S["head_dies"],
                    total_dies=S["dies"], hbm_stacks=sum(t["hbm_stacks"] for t in tray_rows), stage_source=S["src"],
                    grade="MODEL" if not S["inp"].get("qualified") else "spec"),
        die_power_src=dict(rank=N(84.1, "spec", "results/rtl/dsrom_s81_fulldie_20261004/floorplan.json scan_die_power.total_saturated_w (old 10-04 S81 die report, busiest layer die; no 72-frame die power report yet) via results/arch/dsrom_s81_rack_20261006/rack.json die_w"),
                           head=N(92.34, "MODEL", "results/arch/dsrom_s81_rack_20261006/rack.json die_w.head_table (C1 ledger); not re-derived for the 4-die, HBM-free head (OWNER 2026-10-24)"),
                           stack=P("hbm3e_stack_static_w")),
        die_links=dict(rank=N(10, "spec", "OWNER-approved 5th link (10-21): 5 lane pairs = TP4 full mesh 3 + prev/next stage 2 (reports/s81_links_1021.md s2 option A)"),
                       copy_ab=N(12, "spec", "pre-/post-group rank dies carry a 6th pair (chain_plan extra_circuits_on_existing_dies; lep_mu_ab)"),
                       copy_b=N(10, "MODEL", "copy-B dies use the rank die master (chain_plan: same masks fabricated twice)"),
                       head=N(12, "spec", "head die plan physical/die_plan/s81_head (S81-HEAD 10-24): 12 SerDes = 5 lane pairs + the host pair lk_HOST0+1 (S81.HOST); no draft fan-out SerDes: the MTP composition of record uses no head-die draft link (OWNER 2026-10-24 lean: the draft rides copy-B; to confirm)")),
        extra=dict(host_plan=dict(S81_HOST, head_host_circuits=sum(1 for r in rows if r["cls"] == "host"),
                                  stage_die_host_circuits=0, mgmt_rows=len(tray_rows))))
    # per-tray management sideband (not a SerDes, not a circuit of the data plane): one row per tray to the rack mgmt switch
    for t in tray_rows:
        u0 = next(iter(t["quads"].values()))
        D = dict(medium=S81_HOST["mgmt_medium"], length_m=None, loss_db=None, reach_ok=True,
                 reach_limit="low-rate sideband, not a SerDes", latency_ns=None, cycles=None, cables=1, retimers=0)
        rec["_rows"].append(dict(id="s81.mgmt.%03d" % t["tray"], system="S81", cls="mgmt", a_unit="tray%d" % t["tray"],
                                 a_die=-1, a_rank=0, a_pair="MGMT", a_macros="tray BMC/I2C (all %d dies)" % t["dies"],
                                 b_unit="rack mgmt switch", b_die=-1, b_rank=0, b_pair="MGMT", b_macros="mgmt switch port",
                                 a_tray=t["tray"], b_tray=t["tray"], lanes_per_dir=0, D=D, S=dict(D), traffic=None))
    return rec


# ---------------------------------------------------------------------------------------------------------------
# HBM accelerator, DeepSeek system: 192 next-release dies (P=3), 2 HBM3E stacks each, 5 SerDes links a die
# ---------------------------------------------------------------------------------------------------------------
HBM_PAIRS = {
    "WS": ("lk_SW0", "quad peer d-1"), "ES": ("lk_SE0", "quad peer d+1"), "WN": ("lk_NW0", "quad peer d+2"),
    "EN": ("lk_NE0", "ring: next quad, same rank"), "W5": ("lk_SW1", "ring: previous quad, same rank"),
}
HBM_DIE_MM2 = 767.4
HBM_W_PER_MM2 = 0.5


def hbm_ds_units(dies=192):
    return [dict(id="D%02d" % g, kind="hbm", dies=list(range(4 * g, 4 * g + 4))) for g in range(dies // 4)]


def build_hbm_ds():
    _CUR.update(lanes=6, macros_per_pair=1)
    units = hbm_ds_units()
    E = []
    for u in units:
        for r in range(4):
            E.append(("quad_mesh", u["id"], r, "ES", u["id"], (r + 1) % 4, "WS"))
        for r in range(2):
            E.append(("quad_mesh", u["id"], r, "WN", u["id"], r + 2, "WN"))
    for i, u in enumerate(units):
        w = units[(i + 1) % len(units)]
        for r in range(4):
            E.append(("quad_ring", u["id"], r, "EN", w["id"], r, "W5"))
    die_w = dict(hbm=HBM_W_PER_MM2 * HBM_DIE_MM2)
    rows, tray_rows, slots, nracks, per, spare = assemble("HBM-DS", "", units, E, HBM_PAIRS, die_w, dict(hbm=2), {},
                                                          per_side=1)
    G = len(units)
    ring_hops = 2 * (G // 2)                     # bidirectional ring reduce + broadcast across G quads
    d_cyc = ns_to_cycles(max(r["D"]["latency_ns"] for r in rows if r["cls"] == "quad_ring"))
    s_cyc = ns_to_cycles(v("switched_budget_ns"))
    rec = finish_system(
        name="HBM-DS", title="HBM accelerator, DeepSeek (192 dies)", S=None, rows=rows, tray_rows=tray_rows, slots=slots,
        nracks=nracks, per_rack=per, spare_per_rack=spare, die_w=die_w, users=1, token_cycles=None, phases=None,
        counts=dict(total_dies=192, hbm_stacks=384, die_mm2=HBM_DIE_MM2, grade="spec",
                    source="lanes/HBM-NEXT-P3.md, HBM-NEXT-VEH.md (f4c_t9p3 767.41 mm2, OWNER 10-19 P=3); results/arch/s81_balance_1018/compute.py HBM rows (192 dies, 384 stacks)"),
        die_power_src=dict(hbm=N(round(HBM_W_PER_MM2 * HBM_DIE_MM2, 1), "MODEL",
                                 "results/arch/s81_balance_1018/compute.py HBM Qwen row rule 0.5 W/mm2 x 767.4 mm2 (no die power report; the DS row's 12,544 W / 192 = 65 W a die is inconsistent with it and is not used)"),
                           stack=P("hbm3e_stack_static_w")),
        die_links=dict(hbm=N(5, "spec", "lanes/TOKEN-XDIE-HBM.md:8: 5 ot_pdie_serdes links a d4g die (SW 2, SE/NW/NE 1); P=3 die assumed to inherit them (not confirmed)")),
        crossings=None,
        board="1 OU tray, 2 quads of 2 x 2 single-die packages (die + 2 HBM3E stacks): one quad of the outgoing ring "
              "half and one of the returning half; quad mesh as board traces")
    rec["collective_effect"] = dict(
        note="OPTION S is today's topology: one switch plane, every die reaches any die in one crossing (o-group reduce = "
             "2 crossings, measured 1,569 cycles / instance, lanes/TOKEN-XDIE-HBM.md). OPTION D with 5 links can only "
             "be a quad mesh + a ring of %d quads: an array-wide reduce + broadcast takes %d ring hops." % (G, ring_hops),
        array_reduce_cycles_D=ring_hops * d_cyc, array_reduce_cycles_S=2 * s_cyc,
        verdict="keep OPTION S for HBM-DS: its array collectives need any-to-any in one crossing; D is %0.0fx slower "
                "per array-wide collective" % (ring_hops * d_cyc / (2 * s_cyc)), grade="derived")
    return rec


# ---------------------------------------------------------------------------------------------------------------
# Single-tray systems: Qwen ROM (4 packages of 2 ROM + 2 KV dies) and HBM Qwen (one 8-die package)
# ---------------------------------------------------------------------------------------------------------------
def replica_rack(tray_dc_w, tray_ou, spare=1):
    side_kw = v("shelves_per_side") * v("shelf_usable_kw")
    ou_free = v("orv3_usable_ou") - 2 * v("shelves_per_side") - v("mgmt_ou")
    n = min(ou_free // tray_ou, int(side_kw * 1000 // tray_dc_w)) - spare
    return n


def build_qwen_rom():
    _CUR.update(lanes=12, macros_per_pair=2)
    pitch = 200.0
    pk_xy = {0: (166.0, 300.0), 1: (166.0 + pitch, 300.0), 2: (166.0 + pitch, 300.0 + pitch), 3: (166.0, 300.0 + pitch)}
    rows, n = [], 0
    die = lambda pk, k: 4 * pk + k          # k: 0, 1 = ROM compute dies, 2, 3 = KV dies
    mk = lambda cls, a, am, b, bm, D, tr=None: rows.append(dict(
        id="qwen-rom.%03d" % len(rows), system="Qwen-ROM", cls=cls, a_unit="P%d" % (a // 4), a_die=a, a_rank=a % 4,
        a_pair=am, a_macros=am, b_unit="P%d" % (b // 4) if b >= 0 else "host", b_die=b, b_rank=b % 4 if b >= 0 else 0,
        b_pair=bm, b_macros=bm, a_tray=0, b_tray=0, lanes_per_dir=12 if not D["medium"].startswith("UCIe") else 64,
        D=D, traffic=tr))
    ucie = lambda ns: dict(medium="UCIe (in package)", length_m=0.002, loss_db=None, reach_ok=True,
                           reach_limit="UCIe advanced <= 2 mm", latency_ns=ns, cycles=ns_to_cycles(ns), cables=0, retimers=0)
    tr_ar = dict(beats_per_user_token=36 * 2 * 8192 * 8 / 512, grade="derived",
                 source="results/arch/qwen_tp8_1012/SPEC.md s3: each die sends its 8 KiB owned half to the same-rank die of the 3 other packages, 2 all-reduces a layer, 36 layers")
    for pk in range(4):
        mk("ucie_rom_pair", die(pk, 0), "io_ucie", die(pk, 1), "io_ucie", ucie(3.5))
        for k in range(2):
            mk("ucie_rom_kv", die(pk, k), "ucie_kv", die(pk, 2 + k), "qkvd_ucie", ucie(4.2))
    port = {}
    for a in range(4):
        for b in range(a + 1, 4):
            (ax, ay), (bx, by) = pk_xy[a], pk_xy[b]
            L = abs(ax - bx) + abs(ay - by) + 2 * v("escape_mm") + 60.0    # + die-to-package-edge run inside the package
            for k in range(2):
                pa, pb = port.setdefault((a, k), 0), port.setdefault((b, k), 0)
                port[(a, k)] += 1
                port[(b, k)] += 1
                mk("tp8_allreduce", die(a, k), "io_serdes_%d" % pa, die(b, k), "io_serdes_%d" % pb, trace(L), tr_ar)
    mk("host", die(0, 2), "qkd_host", -1, "host NIC", cable(1.5))
    die_w = dict(compute=527.0, kv=round(527.0 * 377.6 / 841.0, 1))
    macros = 8 * 3 * 2 + 2          # 3 x12 SerDes a compute die (2 macro-equivalents each) + host port
    pw = tray_power_w(dict(compute=8, kv=8), die_w, v("hbm3e_stack_static_w"), dict(kv=32), macros)
    tray = dict(tray=0, quads={0: "P0", 1: "P1", 2: "P2", 3: "P3"}, dies=16, hbm_stacks=32, serdes_macros=macros,
                tray_ou=2, **pw)
    nrep = replica_rack(pw["dc_input_w"], 2)
    trays = [dict(tray, tray=i) for i in range(nrep)]
    slots = [(0, 2 * v("shelves_per_side") + 2 * i) for i in range(nrep)]
    rec = finish_system(
        name="Qwen-ROM", title="Qwen3-8B ROM (8 compute + 8 KV dies)", S=None, rows=rows, tray_rows=trays[:1],
        slots=slots[:1], nracks=1, per_rack=nrep, spare_per_rack=1, die_w=die_w, users=4, token_cycles=251615, phases=None,
        counts=dict(total_dies=16, compute_dies=8, kv_dies=8, hbm_stacks=32, packages=4, grade="spec",
                    source="results/arch/qwen_tp8_1012/SPEC.md track A (2 ROM + 2 KV dies + 8 stacks a package, K4 board); results/arch/s81_balance_1018/compute.py Q"),
        die_power_src=dict(compute=N(527.0, "MODEL", "results/arch/s81_balance_1018/compute.py Qwen ROM power row (no die report)"),
                           kv=N(die_w["kv"], "MODEL", "same row, area-scaled 527 x 377.6 / 841"), stack=P("hbm3e_stack_static_w")),
        die_links=dict(compute=N(5, "spec", "dv2f15r die plan: io_serdes x3 (112G x12, one per remote package) + io_ucie x1 (ROM pair) + ucie_kv x1 (lanes/DIE-QWEN-LEAD.md:7, dieplan2_1016)"),
                       kv=N(2, "spec", "UCIe to its compute die + host SerDes port qkd_host (tools/qwen_kv_die/contract.py:111)")),
        crossings=72, replicas=nrep,
        board="2 OU ORv3 tray holding one whole system: 4 CoWoS packages (2 ROM + 2 KV dies + 8 HBM3E each, ~110 x 110 mm, "
              "MODEL) on a 200 mm 2 x 2 pitch; the K4 package mesh (12 SerDes circuits) is board trace, ROM pair and "
              "ROM-KV are UCIe inside the package")
    rec["trays"]["tray_ou"] = 2
    rec["trays"]["liquid_limit_w"] = 2 * v("liquid_tray_kw_max") * 1000
    rec["token_effect"]["grade"] = ("derived: 36 layers x 2 TP8 all-reduces = 72 board crossings a token on the critical "
                                    "path; token = 251,615 cycles (compute.py Q.T). Qwen ROM is ALREADY option D (K4 "
                                    "board, SPEC.md s4); the gain is what option S would lose. The Qwen PHY model prices "
                                    "a crossing at 223 ns (198 KP4 + 25 PHY, tools/qwen_missing/link_phy_gen.py), this "
                                    "tool at 209 ns + flight")
    rec["racks"] = dict(count=1, trays_per_rack=nrep, systems_per_rack=nrep, slots=slots,
                        rows=[dict(rack="R1", trays=nrep, spare_trays=1,
                                   it_kw=round(nrep * pw["it_w"] / 1000, 1), dc_kw=round(nrep * pw["dc_input_w"] / 1000, 1),
                                   wall_kw=round(nrep * pw["dc_input_w"] / v("psu_efficiency") / 1000, 1),
                                   shelves="3 + 3 (2N)", cooling="direct liquid on every package")])
    rec["replica_note"] = "one system = one 2 OU tray; a rack holds %d systems (%d users) plus a spare slot" % (nrep, 4 * nrep)
    return rec


def build_hbm_qwen():
    _CUR.update(lanes=6, macros_per_pair=1)
    rows = []
    inp = lambda: dict(medium="in-package trace", length_m=0.03, loss_db=None, reach_ok=True,
                       reach_limit="in-package (organic / RDL) trace", latency_ns=3.3, cycles=ns_to_cycles(3.3), cables=0,
                       retimers=0)
    for a in range(8):
        for bit in range(3):
            b = a ^ (1 << bit)
            if a < b:
                rows.append(dict(id="hbm-qwen.%03d" % len(rows), system="HBM-Qwen", cls="hypercube", a_unit="pkg", a_die=a,
                                 a_rank=a, a_pair="L%d" % bit, a_macros="ot_pdie_serdes L%d" % bit, b_unit="pkg", b_die=b,
                                 b_rank=b, b_pair="L%d" % bit, b_macros="ot_pdie_serdes L%d" % bit, a_tray=0, b_tray=0,
                                 lanes_per_dir=6, D=inp(), traffic=None))
    rows.append(dict(id="hbm-qwen.%03d" % len(rows), system="HBM-Qwen", cls="host", a_unit="pkg", a_die=0, a_rank=0,
                     a_pair="L3", a_macros="ot_pdie_serdes L3", b_unit="host", b_die=-1, b_rank=0, b_pair="NIC",
                     b_macros="host NIC", a_tray=0, b_tray=0, lanes_per_dir=6, D=cable(1.5), traffic=None))
    die_w = dict(hbm=HBM_W_PER_MM2 * HBM_DIE_MM2)
    pw = tray_power_w(dict(hbm=8), die_w, v("hbm3e_stack_static_w"), dict(hbm=16), 8 * 5)
    nrep = replica_rack(pw["dc_input_w"], 1)
    tray = dict(tray=0, quads={0: "pkg"}, dies=8, hbm_stacks=16, serdes_macros=1, **pw)
    slots = [(0, 2 * v("shelves_per_side") + i) for i in range(nrep)]
    rec = finish_system(
        name="HBM-Qwen", title="HBM accelerator, Qwen (8 dies, one package)", S=None, rows=rows, tray_rows=[tray],
        slots=slots[:1], nracks=1, per_rack=nrep, spare_per_rack=1, die_w=die_w, users=1, token_cycles=None, phases=None,
        counts=dict(total_dies=8, hbm_stacks=16, packages=1, grade="spec",
                    source="results/arch/s81_balance_1018/compute.py HBM Qwen row (8 dies, 16 stacks); lanes/TOKEN-XDIE-HBM.md s3 (one package)"),
        die_power_src=dict(hbm=N(round(die_w["hbm"], 1), "MODEL", "0.5 W/mm2 x 767.4 mm2 (compute.py HBM Qwen rule)"),
                           stack=P("hbm3e_stack_static_w")),
        die_links=dict(hbm=N(5, "spec", "5 ot_pdie_serdes a die; hypercube uses 3 (lanes/TOKEN-XDIE-HBM.md s3: package topology is an open coordinator decision)")),
        crossings=None, replicas=nrep,
        board="1 OU tray with one 8-die package (16 HBM3E); the 3-link hypercube is in-package trace (3.3 ns, MODEL); "
              "only the host link leaves the package")
    rec["racks"] = dict(count=1, trays_per_rack=nrep, systems_per_rack=nrep, slots=slots,
                        rows=[dict(rack="R1", trays=nrep, spare_trays=1, it_kw=round(nrep * pw["it_w"] / 1000, 1),
                                   dc_kw=round(nrep * pw["dc_input_w"] / 1000, 1),
                                   wall_kw=round(nrep * pw["dc_input_w"] / v("psu_efficiency") / 1000, 1),
                                   shelves="3 + 3 (2N)", cooling="direct liquid")])
    rec["replica_note"] = ("one system = one 1 OU tray; a rack holds %d systems. OPTION S does not apply inside the "
                           "package; the open topology choice (hypercube vs in-package switch) is the coordinator's" % nrep)
    return rec


# ---------------------------------------------------------------------------------------------------------------
# Option S, comparison, sparing, power roll-up (shared by every system)
# ---------------------------------------------------------------------------------------------------------------
def option_s(rows, ndies_lanes, nracks, slots, replicas=1):
    """Static circuits through one-tier switch planes.  Every die-side lane lands on a switch port; a circuit's two
    ends must sit on the same switch chip (one crossing), so each plane is cut into chip domains of consecutive dies
    in pipeline order; circuits that straddle a domain boundary consume a port on both sides (MODEL: +10%)."""
    die_lanes = ndies_lanes
    chips_bw = math.ceil(replicas * die_lanes / v("switch_lanes"))
    chips_rack = math.ceil(chips_bw * 1.10)          # for single-tray systems: switch chips shared by a rack of replicas
    chips = chips_rack / replicas
    switch_racks = math.ceil(chips_rack * v("switch_asic_ou") / (v("orv3_usable_ou") - 2 * v("shelves_per_side") - v("mgmt_ou")))
    # cable legs: compute tray -> switch rack (switch racks interleaved between compute racks: mean 1 rack pitch,
    # half a rack height vertically)
    mean_leg = 1.0 * v("rack_pitch_m") + 0.5 * 36 * v("orv3_ou_mm") / 1000 + v("cable_slack_m") + v("flyover_mm") + 0.3
    near_leg = 0.5 * v("rack_pitch_m") + 0.25 * 36 * v("orv3_ou_mm") / 1000 + v("cable_slack_m") + v("flyover_mm") + 0.3
    sw = switched(mean_leg, mean_leg)
    cables = math.ceil(die_lanes / v("cable_lanes"))
    n_aec = cables if mean_leg > v("dac_112g_reach_m") else 0
    return dict(chips=round(chips, 2), chips_per_rack_of_replicas=chips_rack if replicas > 1 else None,
                chips_bandwidth_bound=chips_bw, switch_trays=chips_rack, switch_racks=switch_racks,
                cables=cables, aec_cables=n_aec, mean_leg_m=round(mean_leg, 2), near_leg_m=round(near_leg, 2),
                crossing=sw, crossing_best=switched(near_leg, near_leg),
                switch_w=chips * v("switch_tray_w"), aec_w=n_aec * v("aec_w"),
                grade="MODEL (chip domains +10% boundary overhead; switch racks interleaved with compute racks)")


def inpkg(r):
    return r["D"]["medium"].startswith(("UCIe", "in-package"))


def finish_system(name, title, S, rows, tray_rows, slots, nracks, per_rack, spare_per_rack, die_w, users,
                  token_cycles, phases, counts, die_power_src, die_links, extra=None, crossings=None, board=None,
                  replicas=1):
    lanes = circuit_lanes()
    # ---- option D roll-up
    by_med = {}
    for r in rows:
        m = r["D"]["medium"]
        d = by_med.setdefault(m, dict(circuits=0, cables=0, max_len_m=0.0, max_loss_db=0.0, all_reach_ok=True))
        d["circuits"] += 1
        d["cables"] += r["D"]["cables"]
        d["max_len_m"] = max(d["max_len_m"], r["D"]["length_m"])
        if r["D"]["loss_db"] is not None:
            d["max_loss_db"] = max(d["max_loss_db"], r["D"]["loss_db"])
        d["all_reach_ok"] &= r["D"]["reach_ok"]
    # cables are shared by the circuits of one tray boundary: pack lanes per (tray a, tray b) pair
    bundles = {}
    for r in rows:
        if r["D"]["medium"] != "board trace" and not inpkg(r):
            k = tuple(sorted((r["a_tray"], r["b_tray"])))
            bundles.setdefault(k, [0, r["D"]["medium"]])[0] += lanes
    cables_d = sum(math.ceil(l / v("cable_lanes")) for l, _ in bundles.values())
    aec_d = sum(math.ceil(l / v("cable_lanes")) for l, m in bundles.values() if m == "AEC")
    opt_d = sum(math.ceil(l / v("cable_lanes")) for l, m in bundles.values() if m == "optics")
    die_lanes = sum(t["serdes_macros"] for t in tray_rows) * v("macro_elec_lanes")
    S_ = option_s(rows, die_lanes, nracks, slots, replicas)
    for r in rows:
        r["S"] = (dict(r["D"]) if inpkg(r) else
                  dict(medium=S_["crossing"]["medium"], length_m=S_["crossing"]["length_m"],
                       latency_ns=S_["crossing"]["latency_ns"], cycles=S_["crossing"]["cycles"]))
    # ---- hop latency per class
    classes = {}
    for r in rows:
        c = classes.setdefault(r["cls"], dict(circuits=0, D_ns=[], D_media=set(), S_ns=r["S"]["latency_ns"]))
        c["circuits"] += 1
        c["D_ns"].append(r["D"]["latency_ns"])
        c["D_media"].add(r["D"]["medium"])
    hop = {}
    for k, c in classes.items():
        hop[k] = dict(circuits=c["circuits"], D_media=sorted(c["D_media"]),
                      D_ns_max=max(c["D_ns"]), D_cycles_max=ns_to_cycles(max(c["D_ns"])),
                      D_ns_min=min(c["D_ns"]), D_cycles_min=ns_to_cycles(min(c["D_ns"])),
                      S_ns=c["S_ns"], S_cycles=ns_to_cycles(c["S_ns"]),
                      S_budget_ns=None if c["S_ns"] < 100 else v("switched_budget_ns"),
                      S_budget_cycles=None if c["S_ns"] < 100 else ns_to_cycles(v("switched_budget_ns")),
                      saved_cycles_D_vs_S_budget=(0 if c["S_ns"] < 100 else
                                                  ns_to_cycles(v("switched_budget_ns")) - ns_to_cycles(max(c["D_ns"]))))
    # ---- power
    it_w = sum(t["it_w"] for t in tray_rows)
    dc_w = sum(t["dc_input_w"] for t in tray_rows)
    d_cable_w = aec_d * v("aec_w") + opt_d * 2 * v("optic_w")
    s_extra_w = S_["switch_w"] + S_["aec_w"]
    wall = lambda w: w / v("psu_efficiency")
    # ---- per-token latency effect (derived): critical-path crossings a token
    stage_cross = sum(1 for r in rows if r["cls"] in ("stage_hop", "head_hop", "token_return") and r["a_rank"] == 0)
    if crossings is None:
        crossings = (phases or 0) + stage_cross
    off = [k for k in hop if hop[k]["S_budget_ns"]]
    d_mean = sum(hop[k]["D_cycles_max"] * hop[k]["circuits"] for k in off) / max(1, sum(hop[k]["circuits"] for k in off))
    saved = crossings * (ns_to_cycles(v("switched_budget_ns")) - d_mean) if token_cycles else None
    racks = []
    for rk in range(nracks):
        trs = [t for t, s in enumerate(slots) if s[0] == rk]
        racks.append(dict(rack="R%d" % (rk + 1), trays=len(trs), spare_trays=spare_per_rack,
                          it_kw=round(sum(tray_rows[t]["it_w"] for t in trs) / 1000, 1),
                          dc_kw=round(sum(tray_rows[t]["dc_input_w"] for t in trs) / 1000, 1),
                          wall_kw=round(wall(sum(tray_rows[t]["dc_input_w"] for t in trs)) / 1000, 1),
                          shelves="%d + %d (2N), %.1f kW usable a side" % (v("shelves_per_side"), v("shelves_per_side"),
                                                                           v("shelves_per_side") * v("shelf_usable_kw")),
                          cooling="direct liquid cold plates on every package (dies + HBM), rear manifold, in-row CDU; "
                                  "air only for PSUs / misc"))
    compare = dict(
        D=dict(cables=cables_d, aec=aec_d, optics=opt_d, board_trace_circuits=by_med.get("board trace", {}).get("circuits", 0),
               cable_circuits=sum(1 for r in rows if r["D"]["medium"] != "board trace" and not inpkg(r)), switch_chips=0,
               latency_ns_range=[min(r["D"]["latency_ns"] for r in rows if not inpkg(r)),
                                 max(r["D"]["latency_ns"] for r in rows if not inpkg(r))],
               link_power_w=round(d_cable_w), racks=nracks,
               sparing="tray is the FRU; a failed die/tray is swapped (~%d min, MODEL); circuits are fixed copper, so a "
                       "spare tray must take the failed tray's slot and cables" % v("tray_swap_min"),
               repointing="none: a new copy count or stage map means re-cabling the affected tray boundaries"),
        S=dict(cables=S_["cables"], aec=S_["aec_cables"], optics=0, board_trace_circuits=0, cable_circuits=len(rows),
               cable_circuits_offpkg=sum(1 for r in rows if not inpkg(r)),
               switch_chips=S_["chips"], switch_racks=S_["switch_racks"], latency_ns=S_["crossing"]["latency_ns"],
               latency_ns_best=S_["crossing_best"]["latency_ns"], budget_ns=v("switched_budget_ns"),
               link_power_w=round(s_extra_w), racks=nracks + S_["switch_racks"],
               sparing="hot re-point of static circuits (~%d s, MODEL) to any die on the same chip domain that already "
                       "holds the same ROM content (copy-B groups, or a hot-standby duplicate group)" % v("repoint_s"),
               repointing="any circuit inside a chip domain, by table rewrite; copy count / user calendar changes need no "
                          "cabling"),
        grade="derived from the connection list; switch-domain overhead and leg lengths MODEL")
    rec = dict(
        name=name, title=title, counts=counts, die_links=die_links, die_power=die_power_src,
        circuits=dict(total=len(rows), by_class={k: hop[k]["circuits"] for k in hop}, by_medium_D=by_med,
                      lanes_per_dir=lanes, gbps_per_dir_raw=round(2 * v("lane_bits") * F_CLK / 1e9, 1),
                      gbps_per_dir_usable=round(2 * v("lane_bits") * v("lane_usable") * F_CLK / 1e9, 1)),
        trays=dict(count=len(tray_rows), rows=tray_rows, worst_dc_w=max(t["dc_input_w"] for t in tray_rows),
                   liquid_limit_w=v("liquid_tray_kw_max") * 1000,
                   board=board or ("1 OU ORv3 tray, 4 quads of 2 x 2 single-die packages (16 dies); each TP group is one "
                                   "quad, its 6 mesh circuits are board traces; stage hops inside a tray are traces, "
                                   "between trays flyover twinax to rear OSFP cages and 8-lane cables")),
        racks=dict(count=nracks, trays_per_rack=per_rack, rows=racks, slots=slots),
        power=dict(it_kw=round(it_w / 1000, 1), dc_kw=round(dc_w / 1000, 1), wall_kw_D=round(wall(dc_w + d_cable_w) / 1000, 1),
                   wall_kw_S=round(wall(dc_w + s_extra_w) / 1000, 1), D_link_w=round(d_cable_w), S_switch_w=S_["switch_w"],
                   S_aec_w=S_["aec_w"], grade="derived on die power (spec where a die report exists, else MODEL)"),
        option_s=S_, compare=compare, hop_latency=hop,
        token_effect=dict(crossings_per_token=crossings, collective_phases=phases, stage_crossings=stage_cross,
                          token_cycles=token_cycles, D_saved_cycles=round(saved) if saved else None,
                          D_rate_gain_pct=round(100 * (token_cycles / (token_cycles - saved) - 1), 1) if saved else None,
                          grade="derived (token cycles and phase count from the 81-stage calendar / links report; the "
                                "241-stage calendar is not priced)" if token_cycles else "not priced"),
        sparing=sparing_plan(name, len(tray_rows), nracks, spare_per_rack, rows, counts),
    )
    if extra:
        rec.update(extra)
    rec["_rows"] = rows
    return rec


def sparing_plan(name, ntrays, nracks, spare_per_rack, rows, counts):
    spare_lanes = math.ceil(circuit_lanes() / v("cable_lanes")) * v("cable_lanes") - circuit_lanes()
    return dict(
        principle="every ROM die is unique (its weights are in its masks), so a spare must be the same die type: spares are "
                  "held per tray type, shared across all deployed replicas of the system (fleet stock), not per rack",
        D=[f"1 spare slot per rack ({nracks} slots, power and liquid pre-plumbed, blind-mate quick disconnects) to swap a "
           f"failed tray in place; MTTR ~{v('tray_swap_min')} min (MODEL)",
           f"fleet stock: 1 tray of each of the {ntrays} tray types per K deployed replicas (K chosen from die FIT; "
           "MODEL)",
           f"lane sparing: a {circuit_lanes()}-lane circuit rides 8-lane cables, leaving {spare_lanes} spare lanes a circuit for "
           "PHY lane remap (requirement on the SerDes macro: lane remap, MODEL)",
           "board-trace TP mesh has no spare: a die or trace fault is a tray swap"],
        S=["same fleet stock (ROM content is fixed per die)",
           "hot re-point in ~1 s (MODEL) where an identical die is already cabled to the same chip domain: copy-B groups "
           "back up their copy-A groups (MU users drop from the duplicated group instead of the array stopping)",
           "switch / cable faults: re-point onto spare switch ports (+10% port domain overhead already counted)"],
        grade="MODEL")


# ---------------------------------------------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------------------------------------------
CSV_COLS = ["id", "system", "cls", "a_die", "a_unit", "a_rank", "a_macros", "b_die", "b_unit", "b_rank", "b_macros",
            "lanes_per_dir", "a_tray", "b_tray", "D_medium", "D_length_m", "D_loss_db", "D_reach_ok", "D_reach_limit",
            "D_latency_ns", "D_cycles", "S_medium", "S_length_m", "S_latency_ns", "S_cycles",
            "traffic_beats_per_user_token", "traffic_grade"]


def write_csv(path, rows):
    with path.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(CSV_COLS)
        for r in rows:
            w.writerow([r["id"], r["system"], r["cls"], r["a_die"], r["a_unit"], r["a_rank"], r["a_macros"], r["b_die"],
                        r["b_unit"], r["b_rank"], r["b_macros"], r["lanes_per_dir"], r["a_tray"], r["b_tray"],
                        r["D"]["medium"], r["D"]["length_m"], r["D"]["loss_db"], r["D"]["reach_ok"],
                        r["D"]["reach_limit"], r["D"]["latency_ns"], r["D"]["cycles"], r["S"]["medium"],
                        r["S"]["length_m"], r["S"]["latency_ns"], r["S"]["cycles"],
                        round(r["traffic"]["beats_per_user_token"], 1) if r.get("traffic") else "",
                        r["traffic"]["grade"] if r.get("traffic") else ""])


def build(systems=None):
    builders = dict(S81=build_s81)
    builders.update({"Qwen-ROM": build_qwen_rom, "HBM-DS": build_hbm_ds, "HBM-Qwen": build_hbm_qwen})
    recs = [builders[k]() for k in (systems or builders)]
    return dict(
        schema="opentallas.release_rack.v1", lane="RACK-1021", tool="tools/release_rack_design.py",
        grades="published = vendor / standard figure; spec = this repo's committed record; MODEL = allocator / analytical "
               "model or engineering estimate, unqualified; derived = arithmetic on the others",
        constants={**{k: dict(value=e["value"], grade=e["grade"], source=e["source"]) for k, e in C.items()},
                   **{k: P(k) for k in ("cable_hop_s", "hop_flight_included_m", "twinax_ns_per_m", "pcb_ns_per_m",
                                        "dac_112g_reach_m", "aec_112g_reach_m", "switch_latency_s", "switch_capacity_tbps",
                                        "serdes_pj_per_bit", "lane_gbps", "switch_tray_w", "vr_efficiency",
                                        "psu_efficiency", "hbm3e_stack_static_w", "orv3_usable_ou", "orv3_ou_mm")}},
        systems=recs,
        compare_published=[V41.NVL72, V41.CM384])


EXTRA_BUILDERS = {"Qwen-ROM": None, "HBM-DS": None, "HBM-Qwen": None}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    rec = build()
    hop = dict(schema="opentallas.release_rack.hop_latency.v1", clock_hz=F_CLK,
               note="per-hop off-die latency per circuit class for the token-pass static schedule: D = direct "
                    "(board trace / cable, full RS(544,514) KP4 hop 209 ns + flight beyond 0.3 m + AEC retimer); S = "
                    "static circuit through one Tomahawk-Ultra-class switch (PHY/FEC 100 + switch 250 + flight); "
                    "S_budget = the 377.6 ns contract the xdie co-sims model today. Cycles at 1.2 GHz, rounded up.",
               systems={s["name"]: s["hop_latency"] for s in rec["systems"]})
    (OUT / "hop_latency.json").write_text(json.dumps(hop, indent=1) + "\n")
    for s in rec["systems"]:
        write_csv(OUT / f"connections_{s['name'].lower()}.csv", s.pop("_rows"))
    (OUT / "rack.json").write_text(json.dumps(rec, indent=1, default=list) + "\n")
    for s in rec["systems"]:
        c = s["compare"]
        print(f"{s['name']}: dies {s['counts']['total_dies']} circuits {s['circuits']['total']} trays {s['trays']['count']} "
              f"racks {s['racks']['count']} | D cables {c['D']['cables']} (AEC {c['D']['aec']}) lat "
              f"{c['D']['latency_ns_range']} ns wall {s['power']['wall_kw_D']} kW | S chips {c['S']['switch_chips']} "
              f"cables {c['S']['cables']} lat {c['S']['latency_ns']} ns wall {s['power']['wall_kw_S']} kW")


if __name__ == "__main__":
    main()
