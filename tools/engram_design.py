#!/usr/bin/env python3
"""DS-ROM (DeepSeek-V4.1-Flash, S81 1,792 array) Engram table design record (stream engram, 2026-10-08).

Top-down sizing of the Engram tables of layers 1 and 14 and the choice between ROM table dies (the 36 carried
in the rack) and HBM-resident tables on the consuming stage's own rank dies; the lookup / transport chain of the
chosen design with cycles; the cost record for the next reprice.  Writes results/arch/engram_20261008/design.json.

Every input is a committed record or the released config; every derived number says how it was derived.
Grades: 'released' (checkpoint/config), 'measured' (committed RTL/route record), 'vendor' / 'assumed'
(technology.json), 'modelled' (this design, until the blocks close).

    python3 tools/engram_design.py            # writes the record
    python3 tools/engram_design.py --check    # exits 1 if the committed record is stale
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import hdc_v41_engram_shipped as ES  # noqa: E402

OUT = ROOT / "results/arch/engram_20261008/design.json"
TECH = ROOT / "configs/hardware/technology.json"
TOKEN_PATH = ROOT / "results/arch/token_path_20261008/ds_rom.json"
STAGE_MAP = ROOT / "results/uarch/dsrom_s81_field_phases_1792_20261007/binding/half_dedicated_ksplit/stage_map.json"
RACK = ROOT / "results/arch/dsrom_s81_rack_20261006/rack.json"
FLOORPLAN = ROOT / "results/rtl/dsrom_s81_fulldie_20261004/m221pq/plan/floorplan.json"
CAMPAIGN = ROOT / "results/rtl/dsrom_engram_lookup_campaign.json"
ROM_LEF = ROOT / "physical/asap7_memory_macros/ot_rom_4096x266_m8_skew330/ot_rom_4096x266_m8.lef"
CLK = 1.2e9
NR, CPR = 4, 6
HASH_CYC = 17                    # TP4 ranks, hash columns per rank (24 / 4)
ATOM = 32                         # HBM read atom (B): HBM3E pseudo-channel BL8 x 32 bit
ATOMS_PER_ROW = 9                 # 264-B row at a 0/8/16/24-B start in a 32-B atom (column bases 32-B aligned)
DIE_MM2 = 858.0
UTIL = (0.55, 0.60)               # owner floorplan margin rule (REDESIGN_RULES: 55-60 % placed)

# ---- committed constants, cited -------------------------------------------------------------------------------
S81_PAIR_B, S81_PAIR_MM2 = 512 * 1024, 0.1122     # one 512 KB ROM pair per 0.1122 mm2 of S81 field (COMPLETENESS_AUDIT f1)
QWEN_EMB_B, QWEN_EMB_MM2 = 622.9e6, 88.1           # Qwen embedding as RTL'd (EMB_HBM_FEASIBILITY: 151,936 x 4,096 + scales)
C1_TABLE_W = 3324.4                                 # tools/dsrom_return_storage_hbm.py C1 table_w (36 table dies)
C1_TABLE_DIES = 36
ALLGATHER_BASIS = dict(cycles=442, words_per_rank=160, bytes_per_word=4, fec_leg_cycles=100,
                       src="results/arch/token_path_20261008/ds_rom.json node 'embed' note: TP4 owner->4 ranks "
                           "all_gather 160 words/rank on tb_w15b_v41_tp4 S81 442 cyc + 100 cyc full-FEC board leg")
# the composition's Engram side branch (tools/dsrom_1m_allmeasured graph via token_path_export.ds_capture, us)
E_SIDE = {1: dict(wkv=1.5633, knorm=0.2024 + 0.1825 + 0.1169, gather=0.2542, deliver=0.6699),
          14: dict(wkv=0.4416, knorm=0.2024 + 0.1825 + 0.1169, gather=0.2542, deliver=0.6699)}
E_SIDE_SRC = ("tools/dsrom_1m_allmeasured.py composition graph (replayed by tools/token_path_export.ds_capture): "
              "E{L}.wkv / E{L}.knorm.{sumsq,rsqrt,scale} contributions; E{L}.gather (0.25 us 'row gather port' "
              "placeholder of the ROM tables) and E{L}.deliver (2 board legs) are the terms this design replaces")


def J(p):
    return json.loads(Path(p).read_text())


def lef_size(p):
    for ln in Path(p).read_text().splitlines():
        if ln.strip().startswith("SIZE"):
            a = ln.split()
            return float(a[1]), float(a[3])
    raise ValueError(p)


def r(x, n=3):
    return round(float(x), n)


def tables():
    t = ES.shipped_tables()
    primes = t.primes.reshape(2, -1)
    rows = [int(x) for x in primes.sum(1)]
    pb = ES.PACKED_ROW_BYTES
    per_col = [[int(q) * pb for q in primes[li]] for li in range(2)]
    per_rank = [[sum(((b + ATOM - 1) // ATOM) * ATOM for b in per_col[li][rk * CPR:(rk + 1) * CPR])
                 for rk in range(NR)] for li in range(2)]
    return dict(layers=ES.SHIPPED["engram_layer_ids"], rows_per_layer=rows, row_bytes_packed=pb,
                row_layout="256 E4M3 codes, 1 UE8M0 scale, 7 bytes free in the release -> CRC-32 of bytes 0..256 "
                           "at 257..260 (this design), 0 at 261..263",
                columns_per_layer=ES.SHIPPED["engram_n_heads"] * (ES.SHIPPED["engram_max_ngram_size"] - 1),
                rows_per_column=dict(min=int(primes.min()), max=int(primes.max())),
                bytes_total=sum(rows) * pb, bytes_per_layer=[x * pb for x in rows],
                bytes_per_rank_region=per_rank, src="tools/hdc_v41_engram_shipped.shipped_tables (released "
                "engram_vocab_size 16,000,000, 8 heads, n-grams 2..4; rows [384,006,168, 384,016,682])")


def access(tb):
    sm = J(STAGE_MAP)
    home = {L: sm["dense_stage"][str(L)] for L in tb["layers"]}
    return dict(lookups_per_token=48, rows_per_layer_per_token=24, rows_per_rank_per_layer_per_token=CPR,
                bytes_per_token_packed=48 * tb["row_bytes_packed"],
                hbm_bytes_per_rank_per_layer_per_token=CPR * ATOMS_PER_ROW * ATOM,
                index_depends_on="the last 4 compressed token ids only (NgramHashState): known when the token is "
                                 "known, before the embedding -- every lookup can be issued at token start",
                consumers={f"L{L}": dict(op=f"L{L}.eng.* (wkv on the rows, then the gate on h)",
                                         home_stage_1792=home[L]) for L in tb["layers"]},
                home_stage_src=f"{STAGE_MAP.relative_to(ROOT)} dense_stage (layer L's first stage, 3L)",
                pattern="random rows (hash), exactly one row per hash column per token: column-banked storage "
                        "never conflicts and splits evenly over 4 ranks by column")


def rom_option(tb):
    w, h = lef_size(ROM_LEF)
    macro_b = 4096 * 266 // 8
    words = tb["rows_per_layer"][0] * 8 + tb["rows_per_layer"][1] * 8       # 8 x 264-bit beats a row
    n_macro = math.ceil(words / 4096)
    bare = n_macro * w * h / 1e6
    dens = {"bare_macro": tb["bytes_total"] / bare / 1e6,
            "qwen_embedding_as_rtld": QWEN_EMB_B / QWEN_EMB_MM2 / 1e6,
            "s81_field": S81_PAIR_B / S81_PAIR_MM2 / 1e6}
    rows = {}
    for k, d in dens.items():
        mm2 = tb["bytes_total"] / (d * 1e6)
        rows[k] = dict(MB_per_mm2=r(d, 2), table_mm2=r(mm2, 0),
                       dies_at_100pct=math.ceil(mm2 / DIE_MM2),
                       dies_at_60pct=math.ceil(mm2 / (DIE_MM2 * UTIL[1])),
                       dies_at_55pct=math.ceil(mm2 / (DIE_MM2 * UTIL[0])))
    lo, hi = rows["qwen_embedding_as_rtld"]["dies_at_60pct"], rows["s81_field"]["dies_at_55pct"]
    return dict(
        macro=dict(name="ot_rom_4096x266_m8", um=[w, h], bytes=macro_b, count=n_macro, bare_mm2=r(bare, 0),
                   src=str(ROM_LEF.relative_to(ROOT))),
        density_cases=rows,
        realistic_dies=[lo, hi],
        carried_36_dies="inherited: HEAD_TABLE_DIES = 44 (8 head + 36 table) of the S = 58 C1 ledger "
                        "(tools/dsrom_c_recheck.py:24), not derived from the tables. 36 x 858 = 30,888 mm2 holds "
                        "them only at the Qwen-embedding density with ~93 % of every die placed, or as bare macros; "
                        "at the 55-60 % rule the tables need the realistic_dies range",
        always_on_w=dict(c1_36_dies=C1_TABLE_W, per_die=r(C1_TABLE_W / C1_TABLE_DIES, 1),
                         at_realistic_dies=[r(C1_TABLE_W / C1_TABLE_DIES * lo, 0), r(C1_TABLE_W / C1_TABLE_DIES * hi, 0)]),
        transport="table trays at the bottom of rack R2 (rack.json packing) feed stage 3 (R1 top) and stage 42 over "
                  "in-rack / rack-to-rack cable with full KP4 FEC (209 ns a leg); the 24 rows of a layer come from "
                  "24 column banks spread over many dies, so every home rank die needs a fan-in of table links",
        design="a ROM table die = the S81 field generator's pair frames carrying table banks (column-banked, one "
               "row per column per token) + a per-die row reader + link endpoints; not built: rejected below")


def hbm_option(tb, tech):
    hb = tech["hbm"]["hbm3e"]
    cap = hb["stack_capacity_bytes"]["value"]
    bw = hb["stack_bandwidth_bytes_s"]["value"]
    lat = tech["serial_latency"]["rom_datapath"]["hbm_random_row_latency_s"]
    usable = cap * 0.9
    region = max(max(x) for x in tb["bytes_per_rank_region"])
    stacks_needed = math.ceil(region / usable)
    kv_per_user_busiest = 20.25e9 / 216
    head = 2 * usable - region
    return dict(
        placement="layer L's table in the 4 rank dies of its home stage (3L: stage 3 for L1, stage 42 for L14); "
                  "rank r holds hash columns 6r..6r+5 in a load-once read-only region of its own stacks",
        region_bytes_per_rank=region, stack_capacity_bytes=cap, usable_fraction=0.9,
        stacks_per_home_die=2, stacks_added=2 * NR,          # 1 more on each of 2 layers x 4 ranks
        stacks_added_note="+1 HBM3E stack on each of the 8 home dies (1 -> 2): region 25.35 GB > 20.25 GB usable "
                          "of one 22.5 GB shipping stack (technology.json); with Micron 12-high 36 GB stacks "
                          "(32.4 GB usable) no stack is added (sensitivity)",
        kv_headroom_bytes_per_home_die=r(head, 0),
        kv_headroom_users_1M_at_busiest_rate=int(head // kv_per_user_busiest),
        bandwidth=dict(stack_Bps=bw, per_token_bytes=CPR * ATOMS_PER_ROW * ATOM,
                       share_at_64_users_mtp_4352=r(64 * 4352 * CPR * ATOMS_PER_ROW * ATOM / bw, 6)),
        read_latency_s=dict(value=lat["value"], range=[lat["range_low"], lat["range_high"]], grade=lat["grade"],
                            used=lat["range_high"], used_cycles=round(lat["range_high"] * CLK)),
        load="written once at power-on (25.35 GB a die) through the die's host / KV-ingest port -- the port the "
             "completeness audit (finding 6) finds missing on every ROM die; at 32 GB/s ~0.8 s, all dies in "
             "parallel.  Read-only afterwards.",
        integrity="HBM3E on-die ECC + per-row CRC-32 in the release's 7 free bytes, checked by the engine; a bad "
                  "row poisons its prefetch slot (no silent wrong value)",
        src=dict(capacity="configs/hardware/technology.json hbm.hbm3e.stack_capacity_bytes",
                 latency="configs/hardware/technology.json serial_latency.rom_datapath.hbm_random_row_latency_s",
                 kv_per_user="tools/dsrom_return_storage_hbm.py kv_sizing: one stack holds 216 users at 1M on the "
                             "busiest die"))


def die_change():
    fp = J(FLOORPLAN)
    placed = fp["placed_footprint_mm2"]
    phy_w, phy_h, ctrl_d, svc_d, edge = 8500.056, 1177.2, 248.4, 1576.8, 20.0
    g = fp["geometry"]
    x_fe, x_le = g["x_fe"], g["x_le"]
    x_phy = math.ceil((x_fe + (x_le - x_fe) / 2 - phy_w / 2) / 0.054) * 0.054
    eng_w, eng_h = 1188.0, 432.0
    add = 10.006 + 2.111 + eng_w * eng_h / 1e6
    return dict(
        base_die="m221pq (S81 layer1 die, 33 x 26 mm, 1 HBM3E stack SW, placed 414.27 mm2 = 48.3 %)",
        new_kind="layer1e: m221pq + the SE stack band, used on the 8 Engram home dies only",
        instances=[
            dict(name="phy_SE", master="ot_hbm3e_phy_v41x_aw30_e8p5", x=r(x_phy, 3), y=21.6, w=phy_w, h=phy_h,
                 note="same PHY abstract as phy_SW (x 2,884.896, y 21.6 in the m221pq DEF), at the generator's SE slot (empty on layer1 dies)"),
            dict(name="ctrl_SE", master="dsfd_ctrl", x=r(x_phy, 3), y=1207.44, w=phy_w,
                 h=ctrl_d, note="the closed streaming controller (ctrl_pc / ctr), unchanged"),
            dict(name="eng_SE", master="dsfd_engram (dsfd_engram_lkp + dsfd_engram_sink + 12 x ot_sram_1r1w_256x256 prefetch buffer)", x=r(x_phy + phy_w / 2 - eng_w / 2, 3),
                 y=1464.48, w=eng_w, h=eng_h,
                 note="lookup engine (ot_dsrom_engram_lookup) + row sink + prefetch buffer SRAM, in the svc_SE "
                      "slot (8,500 x 1,577 um free), centred on ctrl_SE's request face; outline sized for ~55 % util "
                      "pending synthesis (route variant A)"),
        ],
        svc_SE_slot_free_um=[phy_w, svc_d],
        placed_mm2_after=r(placed + add, 2), util_after=r((placed + add) / DIE_MM2, 4),
        links="unchanged: the rows' all-gather uses the TP4 collective (slab v4: lk_W0/E0 UCIe in-package, "
              "SerDes across the package pair); the lead flit uses the existing stage-hop SerDes",
        relays="eng_SE <-> ctrl_SE request/response faces abut (< 100 um); eng_SE -> sp_collective rows cross the "
               "S band to the hub: relay stations at <= 504 um (SS reach) on the generator's chain rules",
        package="2-die package with 4 stacks (2 a die) on the 4 home packages -- within the 8-stack B200-class "
                "interposer the rack already assumes (kv-lives-in-hbm: 4 per die is the limit)",
        generator="tools/dsrom_s81_fulldie.py: STACKS['layer1e'] = ('SW', 'SE') with the SE svc slot replaced by "
                  "dsfd_engram -- a generator change AFTER review (not made in this pass)")


def timeline(camp):
    tp = J(TOKEN_PATH)
    nodes = {n["id"]: n for n in tp["nodes"]}
    hop = round(tp["headline"]["hop_us"] * 1e-6 * CLK)
    sm = J(STAGE_MAP)
    ag_bytes = CPR * ES.PACKED_ROW_BYTES
    b = ALLGATHER_BASIS
    ag = math.ceil(ag_bytes / (b["words_per_rank"] * b["bytes_per_word"])) * b["cycles"] + b["fec_leg_cycles"]
    loc = None
    if camp:
        m = camp["modes"].get("isolated_token_hbm_200ns_local_allgather", {})
        loc = m.get("latency_cycles_window_to_slot_ready", {}).get("layer_1", {}).get("max")
    loc_src = "measured: RTL bench isolated token, 200-ns HBM, 4-cycle all-gather (window out of idwin -> slot ready)"
    if loc is None:
        loc, loc_src = 500, "modelled (campaign record absent)"
    out = {}
    for L in (1, 14):
        stage = sm["dense_stage"][str(L)]
        fwd = stage * (hop + 4)
        rows_ready = fwd + loc + (ag - 4)
        e = E_SIDE[L]
        kv_ready = rows_ready + round((e["wkv"] + e["knorm"]) * 1e-6 * CLK)
        cons = nodes[f"L{L}.eng.dot"]["start"]
        old = round((e["gather"] + e["deliver"]) * 1e-6 * CLK)
        out[f"L{L}"] = dict(
            home_stage=stage,
            lead_flit_cycles=fwd, lead_flit_note=f"{stage} stage hops x ({hop} hop + 4 relay) from S0, cut-through",
            lookup_local_cycles=loc, lookup_local_src=loc_src,
            hash_cycles=HASH_CYC, hash_note="ot_hdc_engram_hash_shipped inside dsfd_engram_lkp: pin flop 1 + window fed "
                                            "oldest first 4 + fixed latency 12 (part of lookup_local_cycles)",
            hbm_read_cycles=loc - HASH_CYC, hbm_read_note="address 2 + request + HBM read (200 ns, 240 cycles) + 9 atoms x 6 "
                                                          "rows + alignment / CRC + local sink (rest of lookup_local_cycles)",
            allgather_cycles=ag, allgather_note=f"{ag_bytes} B a rank (6 packed FP8 rows), upper bound "
                                                f"ceil({ag_bytes}/640) x 442 + 100 FEC leg ({b['src']})",
            rows_ready_cycles=rows_ready,
            wkv_knorm_cycles=round((e["wkv"] + e["knorm"]) * 1e-6 * CLK), wkv_knorm_src=E_SIDE_SRC,
            wkv_cycles=round(e["wkv"] * 1e-6 * CLK), knorm_cycles=round((e["wkv"] + e["knorm"]) * 1e-6 * CLK) - round(e["wkv"] * 1e-6 * CLK),
            wkv_note="engram.wkv [25,600 x 6,144] FP8 matvec on the home die's ROM field (the composition's E{L}.wkv; "
                     "weights in that stage's field)",
            key_value_ready_cycles=kv_ready,
            consumer_start_cycles=cons, consumer_src=f"{TOKEN_PATH.relative_to(ROOT)} node L{L}.eng.dot start",
            slack_cycles=round(cons - kv_ready),
            on_critical_path=cons - kv_ready < 0,
            replaces=dict(gather_plus_deliver_cycles=old, src=E_SIDE_SRC),
            mtp_note="verify of gamma+1 = 6 positions: 6 windows serial in one engine (~405 cycles each, bench "
                     "throughput) = +2,025 cycles, still inside the slack",
            grade="modelled (lead flit on the measured+vendor hop; HBM read at the technology.json upper bound; "
                  "all-gather upper bound; local chain measured in RTL bench)")
    return out


def run():
    tech = J(TECH)
    tb = tables()
    camp = J(CAMPAIGN) if CAMPAIGN.exists() else None
    acc = access(tb)
    rom = rom_option(tb)
    hbm = hbm_option(tb, tech)
    tl = timeline(camp)
    rack = J(RACK)
    stack_w = rack["die_w"]["stack"]
    d_pw = -C1_TABLE_W + 2 * NR * stack_w
    rec = dict(
        schema="opentallas.dsrom-engram-design.v1", date="2026-10-08", tool="tools/engram_design.py",
        status="design (modelled); RTL bench in results/rtl/dsrom_engram_lookup_campaign.json; routes await review",
        tables=tb, access=acc, rom_option=rom, hbm_option=hbm,
        recommendation=dict(
            choice="HBM-resident Engram tables on the home stages' rank dies (+8 HBM3E stacks), the 36 ROM table "
                   "dies deleted",
            why=["the index is a function of token ids only, so a 200-ns random HBM read is hidden: L1 slack "
                 f"{tl['L1']['slack_cycles']:,} cycles, L14 {tl['L14']['slack_cycles']:,} (0 on the critical path)",
                 f"bandwidth is negligible ({CPR * ATOMS_PER_ROW * ATOM:,} B a token a die)",
                 f"ROM needs {rom['realistic_dies'][0]}-{rom['realistic_dies'][1]} dies at 55-60 % util "
                 f"(not 36) and {rom['always_on_w']['at_realistic_dies'][0]:,.0f}-"
                 f"{rom['always_on_w']['at_realistic_dies'][1]:,.0f} W always-on; HBM needs 8 stacks and "
                 f"{2 * NR * stack_w:.1f} W idle",
                 "no new links, no table trays, no rack-to-rack table cable; the rows stay inside the home stage",
                 "the same placement the HBM accelerator and the engram_hbm candidate config already use"],
            costs=["8 extra HBM3E stacks and PHY/ctrl bands on 8 dies (a new die kind layer1e)",
                   "a table load path at power-on (needs the host/ingest port the audit finds missing)",
                   "DRAM is not ROM: integrity by ECC + per-row CRC with slot poisoning"]),
        die_change=die_change(),
        transport=dict(
            lead_flit="72-bit window (4 x 17-bit compressed ids + dead) formed on S0 by ot_dsrom_engram_idwin, sent "
                      "at token start as one control flit on each stage hop and forwarded cut-through to the home "
                      "stages (stage 3, stage 42); +1 flit on a ~40,976-B hop (0.2 % occupancy)",
            hbm="local: eng_SE <-> ctrl_SE (abutting faces), 6 requests of 9 x 32-B atoms",
            allgather="TP4 collective: 1,584 B a rank of packed FP8 rows + 1 status a row; the sink merges 4 sources",
            links_added=0, fec="the existing full-KP4 stage hops and collective links (owner 10-06)"),
        timeline_cycles=tl,
        mtp_history_restore=dict(
            where="ot_dsrom_engram_idwin on the S0 rank dies (the only Engram state; home dies are stateless)",
            how="rewind port rb_valid / rb_user / rb_n: the user's history ring (8 entries) moves back by the number of "
                "rejected drafts (<= 5) and the position count with it = the official cache truncated to the accepted prefix",
            cycles=1, on_path=False,
            node="accept.engram_rewind in the DS MTP token path, parallel to the commit tail",
            coordination="mtp-rollback stream (mtp-rollback.log): the commit sequencer issues one rewind per user per step",
            verified="tb_dsrom_engram_lookup rewind events vs the official cache truncation; 2 rewind mutants caught"),
        rtl=dict(files=["rtl/dsrom_sys/engram/ot_dsrom_engram_idwin.sv", "rtl/dsrom_sys/engram/dsfd_engram_lkp.sv", "rtl/dsrom_sys/engram/ot_dsrom_engram_lookup.sv",
                        "rtl/dsrom_sys/engram/ot_dsrom_engram_rowsink.sv"],
                 bench="rtl/test/tb_dsrom_engram_lookup.sv via tools/rtl_dsrom_engram_lookup_campaign.py",
                 campaign_status=camp["status"] if camp else "absent"),
        reprice_item=dict(
            item="engram_hbm_lookup", status="modelled (blocks not routed)",
            per_field_phase=0, per_node=[], on_path_cycles_ar=0,
            off_path_slack_cycles={k: v["slack_cycles"] for k, v in tl.items()},
            replace_in_composition={f"E{L}.gather+E{L}.deliver": dict(was_cycles=v["replaces"]["gather_plus_deliver_cycles"],
                                                                     now_rows_ready_cycles=v["rows_ready_cycles"])
                                    for L, v in ((1, tl["L1"]), (14, tl["L14"]))},
            dies=dict(table_dies_removed=C1_TABLE_DIES, stacks_added=2 * NR, home_dies_changed=2 * NR),
            power_w=dict(table_dies_removed=-C1_TABLE_W, stacks_idle_added=r(2 * NR * stack_w, 1), net=r(d_pw, 1)),
            silicon_mm2=dict(logic_removed=-C1_TABLE_DIES * DIE_MM2, phy_ctrl_engine_added=r(2 * NR * 12.63, 1)),
            note="tok/s unchanged at AR and MTP (the Engram branch stays off the critical path); the reprice must "
                 "replace the ROM-gather placeholder by these terms and drop the 36 table dies from the rack, the "
                 "C1 power and the equal-silicon comparison"),
        inputs={str(p.relative_to(ROOT)): "read" for p in (TECH, TOKEN_PATH, STAGE_MAP, RACK, FLOORPLAN, ROM_LEF)},
    )
    return rec


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    rec = run()
    txt = json.dumps(rec, indent=1, sort_keys=False) + "\n"
    if a.check:
        ok = OUT.exists() and OUT.read_text() == txt
        print("current" if ok else "STALE")
        return 0 if ok else 1
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(txt)
    print(json.dumps(dict(rom=rec["rom_option"]["density_cases"], tl={k: (v["rows_ready_cycles"], v["slack_cycles"])
                                                                      for k, v in rec["timeline_cycles"].items()},
                          reprice=rec["reprice_item"]["power_w"]), indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
