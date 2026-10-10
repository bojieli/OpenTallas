#!/usr/bin/env python3
"""DeepSeek-V4.1 ROM S81 array composition v2 on the 1,792-pair mapping (stream s81-dies, 2026-10-08).

Owner question: "does everything still fit, or do we need a new array design?"  One record of every die type with its
real content, its area against the 858 mm2 reticle, the die count, packages, link topology, power / cooling and the
rack, plus a delta table against the current published array (rack.json at 85 stages, reprice_20261008 headline).

Sources (each row carries its status: built / plan / PLACEHOLDER):
  layer1  results/rtl/dsrom_s81_fulldie_20261004/m221pq (built, r3 full-die GRT + STA); WFC slab placeholder from the
          mtp-die stream (--wfc-hard, 231.12 um x hub column) until it lands
  scan    results/rtl/dsrom_s81_fulldie_20261004/s81dies/scan (tools/s81/s81_dies_recipe.py, this stream)
  head    results/rtl/dsrom_s81_fulldie_20261004/s81dies/{head12,head14,headp2}; MTP sequencer + 5 draft SerDes
          PLACEHOLDER (mtp-die --mtp-seq 0.15 mm2 / --mtp-links 5) until mtp-die lands
  draft   mtp-die P2 package-pair fan-out (40 dies, layer1 recipe 1,680 of 1,792 pairs): PLACEHOLDER (mtp-die plan,
          not on main); the published rack has 52
  table   Engram tables: PLACEHOLDER 36 (published rack; engram stream sizes them: 202.76 GB, 32-56 dies by density)
  ingest  host / KV-ingest: the rack's host tray; the on-die ingest master (ingest stream ot_rom_host_ingest) has no
          area yet: PLACEHOLDER 0 mm2
Mapping: results/uarch/dsrom_s81_mixed1792_mapping_20261007/{half_dedicated (HALF_PHL, adopted), full_shared}.
Rack: tools/dsrom_s81_rack.py re-packed at the mapping's stage count (set_mapping), per-die power as the published rack.
Headline: results/arch/reprice_20261008/reprice.json (tools/reprice_20261008.py) + the us deltas this composition
changes (stage-hop cable classes at the real 120-stage packing vs the composition's charge, mtp-die's P2 UCIe
crossings), added to AR_us and the MTP step exactly as tools/s81/field_phases_1792.py adds extra stage hops.

    python3 tools/dsrom_array_v2.py      # writes results/arch/array_v2_20261008/{array_v2.json,README.md}
"""
from __future__ import annotations

import hashlib
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import dsrom_s81_rack as R  # noqa: E402

OUT = ROOT / "results/arch/array_v2_20261008"
FD = "results/rtl/dsrom_s81_fulldie_20261004"
L1 = f"{FD}/m221pq/plan/floorplan.json"
S81D = f"{FD}/s81dies"
MAP = "results/uarch/dsrom_s81_mixed1792_mapping_20261007"
RACK85 = "results/arch/dsrom_s81_rack_20261006/rack.json"
REPRICE = "results/arch/reprice_20261008/reprice.json"
CMP = "results/arch/three_machine_compose/compose.json"
LFF = "results/rtl/dsrom_1m_allmeasured_20261004/links_full_fec.json"
EVID = "results/arch/die_evidence_20261008/report.json"
DIE_MM2 = 858.0
COOL_W = 474.56                    # liquid-cooling baseline a die (memory liquid-cooling-baseline; floorplan cooling_limit_w)
UTIL_MAX = 0.60                    # OWNER floorplan margin: placed std + macro over core <= 55-60 %
CLK = 1.2e9

# ---- placeholders from other streams (update as they land)
MTPDIE = dict(src="claude/mtp-die-20261008 results/arch/mtp_die_20261008/plan.json (uncommitted plan, 2026-10-08 21:33)",
              wfc_slab_h_um=231.12, mtp_seq_mm2=0.15, head_links=5, primary_head_dies=4, draft_dies=40,
              draft_pairs_used=1680, p2_step_us=0.2, board_links=20, ucie_pairs=20, rack_draft_dies=52)
ENGRAM = dict(src="engram stream (claude/engram-20261008, started 21:28 PT): no die count yet; COMPLETENESS_AUDIT "
                  "finding 1 (202.76 GB; 32 dies at the Qwen-embedding density, 51-56 at the S81 field density)",
              dies=36, range=(32, 56), payload_gb=202.76, rows_per_token=48, row_B=264)
INGEST = dict(src="ingest stream (claude/ingest-20261008: ot_rom_host_ingest RTL + bench d14c1955c): no area / placement yet",
              mm2=0.0)


def J(p):
    return json.loads((ROOT / p).read_text())


def sha(p):
    return hashlib.sha256((ROOT / p).read_bytes()).hexdigest()


def die_rec(name):
    p = ROOT / S81D / name / "floorplan.json"
    if not p.exists():
        return dict(status="pending (recipe not built)")
    d = json.loads(p.read_text())
    if d.get("fits") is False:
        return dict(status="does not fit", error=d["error"], options=d["options"])
    v = d["variant"]
    ml = d.get("margin_lint", {})
    return dict(status="plan built", placed_mm2=d["placed_footprint_mm2"], util=d["utilisation"]["placed_over_die"],
                pairs=v["pairs"], bf=v["bf"], head_bundles=v["head_bundles"], stacks=v["stacks"],
                instances=d["legality_python"]["instances"], overlaps=d["legality_python"]["overlaps"],
                outside=d["legality_python"]["outside"], pin_clashes=d["generated_pin_clashes"],
                margin_lint=ml.get("verdict"), wfc=bool(d.get("child_reservations")),
                options=d["recipe"]["options"], record=f"{S81D}/{name}/floorplan.json",
                area_mm2_by_kind=d["area_mm2_by_kind"])


def dies():
    l1 = J(L1)
    cw = l1["variant"]["hub_column_width_um"]
    wfc_mm2 = round(MTPDIE["wfc_slab_h_um"] * cw / 1e6, 3)
    ev = J(EVID)["dies"].get("s81", {}) if (ROOT / EVID).exists() else {}
    l1row = dict(kind="layer1", what="1-stack stage die (448 of 480 at HALF_PHL)", status="built (m221pq)",
                 placed_mm2=l1["placed_footprint_mm2"], util=l1["utilisation"]["placed_over_die"], stacks=1,
                 pairs=l1["variant"]["pairs"], record=L1,
                 adds=[dict(item="WFC slab (dsfd_wfc, bound)", mm2=wfc_mm2, status="PLACEHOLDER (mtp-die --wfc-hard; "
                            "m221pq has no WFC: child_reservations {})")],
                 evidence=dict(grt_overflow=(ev.get("grt") or {}).get("overflow"), sta="r3 balanced kit; see "
                               f"{EVID}"))
    scan = die_rec("scan")
    scan.update(kind="scan", what="4-stack index-scanning stage die (8 scan stages x TP4 = 32), q-only flavour (the "
                "mapping homes every scan service on a q stage)", stacks=4, adds=[],
                note="the generator's 4-stack kind carries the WFC soft reservation (0.456 mm2) in its spine")
    scanbf = die_rec("scanbf")
    scanbf.update(kind="scanbf", what="scan die, BF flavour (sensitivity)", stacks=4, adds=[])
    heads = {n: die_rec(n) for n in ("head12", "head14", "headp2")}
    for n, h in heads.items():
        h.update(kind=n, stacks=4, adds=[dict(item="MTP sequencer + accept (dsfd_mtp_seq)", mm2=MTPDIE["mtp_seq_mm2"],
                                              status="PLACEHOLDER (mtp-die --mtp-seq)"),
                                         dict(item=f"{MTPDIE['head_links']} draft fan-out SerDes (h0..h3)",
                                              mm2=round(MTPDIE["head_links"] * 0.53, 2),
                                              status="PLACEHOLDER (mtp-die --mtp-links; ot_pdie_serdes LEF ~0.53 mm2 each)")])
    draft = dict(kind="draft", what="DSpark expert replicas, mtp-die P2 (5 row packages x TP4 x 2 dies)",
                 status="PLACEHOLDER (mtp-die plan; layer1 recipe, ROM image only)", placed_mm2=l1["placed_footprint_mm2"],
                 util=l1["utilisation"]["placed_over_die"], stacks=0, pairs=MTPDIE["draft_pairs_used"], adds=[])
    table = dict(kind="table", what="Engram tables L1 + L14 (202.76 GB)", status="PLACEHOLDER (no recipe; engram stream)",
                 placed_mm2=None, util=None, stacks=0, adds=[],
                 sizing=dict(dies_at_qwen_embedding_density=32, dies_at_s81_field_density="51-56",
                             note="36 dies x 858 mm2 = 30,888 mm2 holds the tables only at the Qwen embedding's RTL'd "
                                  "frame overhead (~27,800 mm2); at the S81 field density (~43,400 mm2) it needs 51-56"))
    for r in [l1row, scan, scanbf, draft] + list(heads.values()):
        if r.get("placed_mm2") is not None:
            tot = r["placed_mm2"] + sum(a["mm2"] for a in r["adds"])
            r["placed_with_placeholders_mm2"] = round(tot, 2)
            r["util_with_placeholders"] = round(tot / DIE_MM2, 4)
            r["fits"] = tot / DIE_MM2 <= UTIL_MAX
    return dict(layer1=l1row, scan=scan, scanbf=scanbf, draft=draft, table=table, **heads)


def head_choice(D):
    """the head-die flavour the array composes: P2 when it fits (mtp-die proposal), else the current content at the
    smallest head-die count that fits"""
    for n, cnt in (("headp2", 12), ("head12", 12), ("head14", 14)):
        if D[n].get("fits"):
            return n, cnt
    return None, None


def mapping(name):
    inv = J(f"{MAP}/{name}/inventory.json")
    return dict(stages=inv["stages"], layer_dies=inv["layer_dies"], bf_stages=inv["bf_stages"], q_stages=inv["q_stages"])


def rack_at(stages, head, table, draft):
    c = dict(stages=stages, layer=stages * R.RANKS, head=head, table=table, draft=draft,
             dies=stages * R.RANKS + head + table + draft,
             src=dict(stages=f"{MAP} inventory stages", head="array v2 head choice", table=ENGRAM["src"],
                      draft=MTPDIE["src"]))
    R.set_mapping(stages, c, dict(stages=stages, layer_dies=stages * R.RANKS, src=f"{MAP} (1,792 pairs a die)"))
    name = "half_dedicated" if stages == mapping("half_dedicated")["stages"] else "full_shared"
    R.SCAN_STAGES_OVERRIDE = sorted(set(J(f"{MAP}/{name}/stage_map.json")["scan_service_homes"].values()))
    return R.build()


def links(rk, stages, head, D_head_links, table, draft):
    lf = J(LFF)
    hs = rk["hop_summary"]
    serdes_stage_die = 6          # recipe: one UCIe + three board SerDes on each of the W / E edges
    return dict(
        stage_hops=dict(count=stages - 1, physical_links=(stages - 1) * R.RANKS, by_class=hs["stage_hops"],
                        extra_cycles=hs["stage_hop_extra_cycles"]),
        head_hop=dict(cls=rk["head_hop"]["cls"], length_m=rk["head_hop"]["length_m"], extra_cycles=hs["head_hop_extra_cycles"]),
        token_return=dict(cls=rk["token_return"]["cls"], traversals=lf["token_return"]["traversals"],
                          extra_cycles_each=hs["token_return_extra_cycles_each"]),
        in_package_ucie=dict(pairs=(stages * R.RANKS + head + table + draft) // 2,
                             note="every die sits in a two-die package (TP4 half / draft row A-B); UCIe 10 ns"),
        draft_fanout=dict(board_links=MTPDIE["board_links"], ucie_pairs=MTPDIE["ucie_pairs"], cls=rk["draft_links"]["cls"],
                          status="PLACEHOLDER (mtp-die P2: primary on head dies h0..h3, 5 SerDes each, row package A "
                                 "forwards to B over UCIe)"),
        engram_transport=dict(status="PLACEHOLDER: unpriced (engram stream)", rows_per_token=ENGRAM["rows_per_token"],
                              bytes_per_token=ENGRAM["rows_per_token"] * ENGRAM["row_B"],
                              path="table dies -> Engram / host switch (rack R1 infra) -> L1 / L14 stage dies; not "
                                   "in the token path (COMPLETENESS_AUDIT finding 1)"),
        ingest=dict(status="PLACEHOLDER: host tray 2 x 400G NIC -> switch -> stage dies; on-die master unplaced", src=INGEST["src"]),
        serdes_ports=dict(per_stage_die=serdes_stage_die, head_extra=D_head_links,
                          total=stages * R.RANKS * serdes_stage_die + head * serdes_stage_die
                                + MTPDIE["primary_head_dies"] * D_head_links + draft // 2 * 1,
                          note="recipe edge columns (W: UCIe + 3 SerDes, E: UCIe + 3 SerDes); draft row package A die "
                               "1 SerDes up; table dies' links unpriced"))


def headline(racks):
    """reprice_20261008 HALF_PHL / full-rate rows + this composition's us deltas"""
    rp = J(REPRICE)["ds_rom"]["after"]
    c = J(CMP)["ds_rom"]
    tau = c["tau"]
    r85 = J(RACK85)["hop_summary"]
    ii = c["link_fec"]["full_fec"]["ii_hop_cable_us"]
    # what field_phases_1792 charges: the 85-stage rack's cable flight + (stages - 85) x the worst stage-hop flight
    charged_cyc = r85["stage_hop_extra_cycles"] + r85["head_hop_extra_cycles"]
    cab, rows = {}, {}
    for k in ("half_phl", "full_rate_shared98"):
        rk = racks[k]
        charged_us = charged_cyc / CLK * 1e6 + (rk["counts"]["stages"] - 85) * ii
        real = rk["hop_summary"]
        real_us = (real["stage_hop_extra_cycles"] + real["head_hop_extra_cycles"]) / CLK * 1e6
        tr_us = (real["token_return_extra_cycles_each"] - r85["token_return_extra_cycles_each"]) * J(LFF)["token_return"]["traversals"] / CLK * 1e6
        d_cable = round(real_us - charged_us + tr_us, 4)
        cab[k] = dict(stages=rk["counts"]["stages"], charged_us=round(charged_us, 4), real_packing_us=round(real_us, 4),
                      token_return_delta_us=round(tr_us, 4), delta_us=d_cable)
        ar_us, mtp_us = 1e6 / rp[k]["AR_tok_s"], tau * 1e6 / rp[k]["MTP_tok_s"]
        a2, m2 = ar_us + d_cable, mtp_us + d_cable + MTPDIE["p2_step_us"]
        rows[k] = dict(published=rp[k], v2=dict(AR_tok_s=round(1e6 / a2, 1), MTP_tok_s=round(tau * 1e6 / m2, 1)),
                       dAR_pct=round(100 * (ar_us / a2 - 1), 3), dMTP_pct=round(100 * (mtp_us / m2 - 1), 3))
    return dict(rule="AR_us += cable delta; MTP step += cable delta + mtp-die P2 UCIe crossings (field_phases_1792 adds "
                     "extra stage hops the same way)",
                cable=dict(cab, note="composition charge = 85-stage rack flight + (stages-85) x worst stage-hop flight; "
                                     "real = the mapping's own packing (120 / 98 stages) per-hop classes"),
                mtp_p2_us=MTPDIE["p2_step_us"], rows=rows,
                unpriced=["Engram table read + transport to L1 / L14 (not in the DS token path; engram stream)",
                          "host / KV ingest (not on the decode path; bandwidth unpriced)",
                          "head-die count change (14 instead of 12) on the head sweep if P2 does not land"])


def build():
    D = dies()
    hname, hcnt = head_choice(D)
    hm = mapping("half_dedicated")
    fm = mapping("full_shared")
    table, draft = ENGRAM["dies"], MTPDIE["draft_dies"]
    hcnt_ = hcnt or 12
    rk = rack_at(hm["stages"], hcnt_, table, draft)
    rk98 = rack_at(fm["stages"], hcnt_, table, draft)
    pub = J(RACK85)
    scan_dies = rk["stacks"]["scan_dies"]
    counts = dict(layer1=hm["layer_dies"] - scan_dies, scan=scan_dies, head=hcnt_, table=table, draft=draft)
    counts["total"] = sum(counts.values())
    pkgs = counts["total"] // 2
    D_head_links = MTPDIE["head_links"]
    lk = links(rk, hm["stages"], hcnt_, D_head_links, table, draft)
    hl = headline(dict(half_phl=rk, full_rate_shared98=rk98))
    W = R.J(R.RACK)["physical_constants"]["hbm3e_stack_static_w"]["value"]
    die_w = rk["die_w"]
    power = dict(chips_kw=round(sum(r["chips_kw"] for r in rk["racks"]), 2), wall_kw=round(sum(r["wall_kw"] for r in rk["racks"]), 2),
                 provisioned_kw=round(sum(r["prov_kw"] for r in rk["racks"]), 2), stacks=rk["stacks"]["total"],
                 per_die_w=dict(layer_scan_draft=die_w["layer"], head_table=die_w["head_table"], hbm_stack=W),
                 cooling=dict(limit_w_per_die=COOL_W, worst_die_w=max(die_w["layer"], die_w["head_table"]) + 4 * W,
                              fits=max(die_w["layer"], die_w["head_table"]) + 4 * W <= COOL_W,
                              note="liquid baseline 474.6 W a die; the worst die (4-stack, saturated) is far under it. "
                                   "Per-die W is the published rack's (81-stage busiest layer die / C1 head-table "
                                   "ledger): PLACEHOLDER until a 1,792 power pass"))
    pr = pub["counts"]
    delta = [
        dict(item="stages", published=pr["stages"], v2=hm["stages"]),
        dict(item="layer-class stage dies (layer1 + scan)", published=pr["layer"], v2=hm["layer_dies"]),
        dict(item="scan dies (in the stage dies)", published=pub["stacks"]["scan_dies"], v2=scan_dies),
        dict(item="head dies", published=pr["head"], v2=hcnt_),
        dict(item="Engram table dies", published=pr["table"], v2=table, status="PLACEHOLDER"),
        dict(item="draft dies", published=pr["draft"], v2=draft, status="PLACEHOLDER (mtp-die P2)"),
        dict(item="dies total", published=pr["dies"], v2=counts["total"]),
        dict(item="two-die packages", published=pr["dies"] // 2, v2=pkgs),
        dict(item="HBM3E stacks", published=pub["stacks"]["total"], v2=rk["stacks"]["total"]),
        dict(item="racks / OU used", published=[(r["name"], r["used_ou"]) for r in pub["racks"]],
             v2=[(r["name"], r["used_ou"]) for r in rk["racks"]]),
        dict(item="chips kW / provisioned kW", published=[round(sum(r["chips_kw"] for r in pub["racks"]), 2),
                                                          round(sum(r["prov_kw"] for r in pub["racks"]), 2)],
             v2=[power["chips_kw"], power["provisioned_kw"]]),
        dict(item="stage hops (in-tray / in-rack / rack-to-rack)", published=pub["hop_summary"]["stage_hops"],
             v2=rk["hop_summary"]["stage_hops"]),
        dict(item="draft fan-out links", published="15-link star a primary die (unpriced)",
             v2=f"{MTPDIE['board_links']} board + {MTPDIE['ucie_pairs']} UCIe (P2)", status="PLACEHOLDER"),
        dict(item="HALF_PHL AR / MTP tok/s", published=[hl["rows"]["half_phl"]["published"]["AR_tok_s"],
                                                       hl["rows"]["half_phl"]["published"]["MTP_tok_s"]],
             v2=[hl["rows"]["half_phl"]["v2"]["AR_tok_s"], hl["rows"]["half_phl"]["v2"]["MTP_tok_s"]]),
        dict(item="full-rate (98 st) AR / MTP tok/s", published=[hl["rows"]["full_rate_shared98"]["published"]["AR_tok_s"],
                                                                 hl["rows"]["full_rate_shared98"]["published"]["MTP_tok_s"]],
             v2=[hl["rows"]["full_rate_shared98"]["v2"]["AR_tok_s"], hl["rows"]["full_rate_shared98"]["v2"]["MTP_tok_s"]]),
    ]
    fit = []
    for k, r in D.items():
        if r.get("fits") is False or r.get("status") == "does not fit":
            fit.append(k)
    options = {
        "head12": ["move the drafter's experts to dedicated draft dies (mtp-die P2: head content 1,471 -> 511 pairs a "
                   "die, 40 draft dies)", "add head dies (head14: the same content over 14 dies, +2 dies / +8 stacks)",
                   "shorter q frame on the head die only (needs a closed shorter q element; none today)"],
        "table": ["engram stream: dense 4096x266 / 16384x266 table banks with a tap tree (Qwen embedding element as "
                  "template), 32-56 dies by density", "move the tables to HBM (202.76 GB ~ 9 HBM3E 24 GB stacks on the "
                  "table dies; row reads are token-indexed and prefetchable)"],
    }
    return dict(
        schema="opentallas.dsrom-array-v2.v1", date="2026-10-08", tool="tools/dsrom_array_v2.py",
        question="does everything still fit, or do we need a new array design?",
        mapping=dict(adopted="half_dedicated (HALF_PHL)", half=hm, full_rate=fm, src=MAP),
        dies=D, head_choice=dict(name=hname, dies=hcnt_), counts=counts, packages=pkgs,
        dies_not_fitting=fit, structural_options=options,
        links=lk, power=power, rack=dict(half_120=dict(racks=[{k: v for k, v in r.items() if k != "rows"} for r in rk["racks"]],
                                                       packing=rk["packing"]),
                                         full_98=dict(racks=[{k: v for k, v in r.items() if k != "rows"} for r in rk98["racks"]])),
        rack_record_120=str((OUT / "rack_120.json").relative_to(ROOT)),
        headline=hl, delta_vs_published=delta,
        placeholders=dict(mtp_die=MTPDIE, engram=ENGRAM, ingest=INGEST),
        inputs={p: sha(p) for p in (L1, MAP + "/half_dedicated/inventory.json", RACK85, REPRICE, CMP, LFF)
                if (ROOT / p).exists()}), rk


def readme(a):
    L = ["# DeepSeek ROM S81 array v2 (1,792 mapping, HALF_PHL 120 stages)", "",
         f"Tool `tools/dsrom_array_v2.py`, {a['date']}. Answers the owner question: *{a['question']}*", "",
         "## Dies", "", "| Die | Count | Status | Placed mm² (+placeholders) | Util | Fits 60 % | Note |", "|---|---:|---|---:|---:|---|---|"]
    cnt = dict(layer1=a["counts"]["layer1"], scan=a["counts"]["scan"], draft=a["counts"]["draft"], table=a["counts"]["table"])
    cnt[a["head_choice"]["name"] or "head12"] = a["counts"]["head"]
    for k, r in a["dies"].items():
        pm = r.get("placed_mm2")
        pw = r.get("placed_with_placeholders_mm2")
        L.append(f"| {k} | {cnt.get(k, '(option)')} | {r.get('status')} | {pm if pm is not None else '-'}"
                 f"{f' ({pw})' if pw is not None else ''} | {r.get('util_with_placeholders', r.get('util', '-'))} | "
                 f"{r.get('fits', '-')} | {r.get('what', r.get('error', r.get('note', '')))[:140]} |")
    L += ["", f"Head die composed: **{a['head_choice']['name']}** x {a['head_choice']['dies']}. Dies not fitting: "
          f"{', '.join(a['dies_not_fitting']) or 'none'}.", "", "## Delta vs the published array", "",
          "| Item | Published | v2 | Status |", "|---|---|---|---|"]
    for d in a["delta_vs_published"]:
        L.append(f"| {d['item']} | {d['published']} | {d['v2']} | {d.get('status', '')} |")
    h = a["headline"]
    L += ["", "## Headline", ""]
    for k, c in h["cable"].items():
        if isinstance(c, dict):
            L.append(f"- cable reconcile {k} ({c['stages']} stages): composition charges {c['charged_us']} us, the "
                     f"packing needs {c['real_packing_us']} us (token return {c['token_return_delta_us']} us): delta {c['delta_us']} us")
    L += [f"- mtp-die P2 UCIe crossings: +{h['mtp_p2_us']} us a MTP step", ""]
    for k, r in h["rows"].items():
        L.append(f"- {k}: AR {r['published']['AR_tok_s']} -> {r['v2']['AR_tok_s']} ({r['dAR_pct']} %), "
                 f"MTP {r['published']['MTP_tok_s']} -> {r['v2']['MTP_tok_s']} ({r['dMTP_pct']} %)")
    L += ["", "Unpriced: " + "; ".join(h["unpriced"]), "", "## Structural options where a die does not fit", ""]
    for k, v in a["structural_options"].items():
        L.append(f"- **{k}**: " + " / ".join(v))
    p = a["power"]
    L += ["", "## Power and cooling", "", f"Chips {p['chips_kw']} kW, wall {p['wall_kw']} kW, provisioned "
          f"{p['provisioned_kw']} kW, {p['stacks']} HBM3E stacks. Worst die {p['cooling']['worst_die_w']} W vs "
          f"{p['cooling']['limit_w_per_die']} W liquid limit: fits = {p['cooling']['fits']}. {p['cooling']['note']}", "",
          "## Placeholders (update as the streams land)", ""]
    for k, v in a["placeholders"].items():
        L.append(f"- {k}: {v['src']}")
    return "\n".join(L) + "\n"


def main():
    a, rk = build()
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "rack_120.json").write_text(json.dumps(rk, indent=1) + "\n")
    (OUT / "array_v2.json").write_text(json.dumps(a, indent=1, default=str) + "\n")
    (OUT / "README.md").write_text(readme(a))
    for d in a["delta_vs_published"]:
        print(f"{d['item']}: {d['published']} -> {d['v2']}")
    print("not fitting:", a["dies_not_fitting"], "head:", a["head_choice"])
    print("->", OUT.relative_to(ROOT))


if __name__ == "__main__":
    main()
