#!/usr/bin/env python3
"""Token-path export of 2026-10-09 (stream reprice): the per-token critical paths plus the system numbers of the three
targets -- per-user tok/s, aggregate tok/s, tok/s/W, $, die / stack counts and rack power -- with every input labelled
measured / derived / modelled / assumed / third-party and its source.

No new performance model.  The graphs are tools/token_path_export.py (unchanged), driven for the 10-09 design points:
  qwen_rom   the Qwen3-8B ROM is now the TP4 ROM die + KV die pair (owner 10-09): export target qwen_kvdie, written as
             qwen_rom.json (the Qwen ROM design) so consumers keyed on qwen_rom read the current design point;
  ds_rom     S81, 1,792 pairs, HALF_PHL BF (accepted path; BF decision 21:30 PT pending), Engram rows from HBM
             (owner 10-09, off the critical path: tools/token_path_export.ds_engram_nodes);
  hbm_ds     HBM accelerator, DS-V4.1 1M (unified composition + 10-08 re-price; the generic die keeps the DS mode as
             its default, so the DS token is unchanged until a fork cost is measured).
The system layer (systems.json) composes those rates with the existing records:
  rack / dies / stacks   tools/dsrom_array_v2.py rack_at (1,792 mapping, mtp-die P2) with the Engram table dies removed
                         and +1 stack on the 8 home dies (results/arch/engram_20261008/design.json);
  Qwen ROM + KV die      results/arch/qwen_kv_die_20261009 (reprice, r22k and KV-die records);
                         aggregate results/arch/qwen_tp8_vs_sysdie_20261009/result.json (SYS-1b);
  Qwen on r25 (HBM)      results/arch/hgi_sim_20261009/qwen_timing_P8191.json + qwen_int8_packing.json (pathfinding
                         simulator; no token-path graph yet);
  power                  results/arch/energy_silicon_measured/energy_silicon.json terms + the rack record;
  $                      results/uarch/economics.json cost_inputs + configs/hardware/architectures.json economics;
  GPU / served           results/external/registry.json (third-party; owner rule).

    python3 tools/token_path_systems.py                 # graphs + systems.json + README.md
    python3 tools/token_path_systems.py --systems-only  # re-compose systems.json from the graphs already written
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
OUT = ROOT / "results/arch/token_path_20261009"
CLK = 1.2e9
DATE = "2026-10-09"

KVD = "results/arch/qwen_kv_die_20261009/reprice.json"
KVROM = "results/arch/qwen_kv_die_20261009/rom_r22k.json"
KVPLAN = "results/arch/qwen_kv_die_20261009/kv_die/plan.json"
TP8 = "results/arch/qwen_tp8_vs_sysdie_20261009/result.json"
ENGRAM = "results/arch/engram_20261008/design.json"
REPRICE = "results/arch/reprice_20261008/reprice.json"
ES = "results/arch/energy_silicon_measured/energy_silicon.json"
ECON = "results/uarch/economics.json"
ARCH = "configs/hardware/architectures.json"
RACK = "results/arch/v41_rack.json"
REG = "results/external/registry.json"
HQT = "results/arch/hgi_sim_20261009/qwen_timing_P8191_v10.json"
HQP = "results/arch/hgi_sim_20261009/qwen_int8_packing.json"
HQD = "results/arch/hgi_sim_20261009/dflash/dflash_timing.json"
HDT = "results/arch/hgi_sim_20261009/ds_native_timing_1M.json"   # the spec-conformant native record stream
HCA = "results/arch/hgi_sim_20261009/e2e_calibration.json"
HAPP = "results/arch/hgi_sim_20261009/ds_sw_seq_pricing.json"
MAP = "results/uarch/dsrom_s81_mixed1792_mapping_20261007"
HBM_GENERIC = ("claude/hbm-generic-20261009 01f643326 results/arch/hbm_generic_20261009/plan.json (die_fit R25G "
               "798.49 mm2 measured with tools/hbm_accel_die_fp.py; branch, planning record)")
HBM_FORKS = "/home/ubuntu/claude-takeover-20261007/hbm-forks.log 05:24 RQ-HF-7 (one-beat INT8: zero added cycles, DS cycle-identical)"
STACK_MM2 = 1089.0     # energy_silicon convention (dram_mm2 / stacks); memory qwen3-comparisons-are-iso-area: 1,000-1,300


def J(p):
    return json.loads((ROOT / p).read_text())


def sha(p):
    return hashlib.sha256((ROOT / p).read_bytes()).hexdigest()[:16]


def f(value, unit, grade, source, note=None, **kw):
    """one labelled number"""
    d = dict(value=value, unit=unit, grade=grade, source=source)
    if note:
        d["note"] = note
    d.update(kw)
    return d


def r1(x):
    return round(x, 1)


# ============================================================================== graphs
def export_graphs(out):
    subprocess.run([sys.executable, str(ROOT / "tools/token_path_export.py"), "--out", str(out),
                    "--only", "qwen_kvdie,ds_rom,hbm_ds"], check=True, cwd=ROOT)
    # the Qwen ROM design point IS the ROM + KV die pair now: publish it under the design's own key
    src = out / "qwen_kvdie.json"
    rec = json.loads(src.read_text())
    rec["design"] = "qwen_rom"
    rec["variant"] = "kvdie"
    rec["variant_note"] = ("owner 2026-10-09: TP4 ROM die + KV die per package (tools/token_path_export.py target "
                           "qwen_kvdie); the single-die TP4 record is results/arch/token_path_20261008/qwen_rom.json")
    (out / "qwen_rom.json").write_text(json.dumps(rec, separators=(",", ":")) + "\n")
    src.unlink()
    idx = json.loads((out / "index.json").read_text())
    for d in idx["designs"]:
        if d["design"] == "qwen_kvdie":
            d.update(design="qwen_rom", file="qwen_rom.json", variant="kvdie")
    (out / "index.json").write_text(json.dumps(idx, indent=1) + "\n")


# ============================================================================== shared inputs
def find(o, k):
    """first value of key k anywhere in a JSON tree"""
    if isinstance(o, dict):
        if k in o:
            return o[k]
        o = list(o.values())
    if isinstance(o, list):
        for v in o:
            r = find(v, k)
            if r is not None:
                return r
    return None


def econ_inputs():
    e = J(ECON)["cost_inputs"]
    dd = J(ARCH)   # architectures.json carries the economics block once (lifetime / utilisation / electricity / PUE)

    life, util, kwh, pue = (find(dd, k) for k in ("lifetime_years", "utilization", "electricity_cost_per_kwh", "facility_pue"))
    return dict(package_usd=e["package_usd"], mask_set_usd=e["mask_set_usd"], rom_coding_fraction=e["rom_coding_fraction"],
                production_units=e["production_units"], hbm_stack_usd=e["hbm_stack_usd"], life=life, util=util, kwh=kwh, pue=pue)


def capex(packages, rom_sets, E):
    base = packages * E["package_usd"]
    lo = base + rom_sets * E["mask_set_usd"] * E["rom_coding_fraction"] / E["production_units"]
    hi = base + rom_sets * E["mask_set_usd"] / E["production_units"]
    return round(lo), round(hi)


def usd_per_mtok(capex_usd, wall_w, agg, E):
    """(capex over the lifetime + energy at the facility PUE) per token served at the aggregate rate x utilisation"""
    if not agg or not wall_w:
        return None
    yr = 365 * 24 * 3600
    tokens = agg * E["util"] * yr
    cost = capex_usd / E["life"] + wall_w * E["pue"] / 1e3 * E["util"] * 365 * 24 * E["kwh"]
    return round(cost / tokens * 1e6, 4)


def tp(name):
    return json.loads((OUT / name).read_text())


# ============================================================================== Qwen ROM + KV die
def qwen_rom(E, wall):
    g = tp("qwen_rom.json")
    kv = J(KVD)
    rom, kvp = J(KVROM), J(KVPLAN)
    sb = {r["id"]: r for r in J(TP8)["side_by_side"]}["SYS-1b"]
    es = J(ES)["qwen_8k"]["rom"]
    t = g["totals"]
    per_user = t["tok_s_published"]
    rom_mm2, kv_mm2 = rom["die_mm2"], kvp["die_mm2"]
    dies, packages, stacks = 8, 2, 16
    logic = 4 * (rom_mm2 + kv_mm2)
    # power: the uarch model's static (4 ROM dies, ungated clock) + dynamic J/token, plus the KV die's NEW logic
    # (aggregators, host SerDes, relays, centre blocks, UCIe) at the same static W/mm2; PHY/ctrl/row engines/landings/CDC
    # moved from the ROM die and are already in the 4-die static.
    static = es["terms"]["static"]["value"]
    dyn = es["terms"]["dyn"]["value"]
    m = kvp["masters"]
    new_mm2 = 4 * (m["qkd_astk"]["mm2"] + m["ot_qfd_serdes_112g_x12_phy"]["mm2"] + m["ot_qkvd_ucie_x64_phy"]["mm2"]
                   + m["qkd_seq"]["mm2"] + m["qkd_host"]["mm2"] + m["qkd_pll"]["mm2"] + m["qkd_ahub"]["mm2"])
    w_per_mm2 = static / es["silicon"]["logic_mm2"]
    kv_static = new_mm2 * w_per_mm2
    agg = sb["aggregate"]["aggregate_tok_s"]
    p_b1 = static + kv_static + dyn * per_user
    p_sat = static + kv_static + dyn * agg
    lo, hi = capex(packages, 4, E)
    pk_note = ("each package is 2 ROM + 2 KV dies + 8 stacks on a ~3.5-4-reticle interposer (CoWoS-L class, larger than "
               f"B200's): the iso-package price understates it ({TP8} system_die.packaging); KV-die mask NRE not charged")
    return dict(
        id="qwen_rom", name="Qwen3-8B ROM (TP4 ROM die + KV die)", model="Qwen3-8B", context="8K (position 8,191)",
        modes=["AR"], graph="qwen_rom.json",
        per_user=dict(
            AR=f(per_user, "tok/s", "derived", f"results/arch/token_path_20261009/qwen_rom.json totals.tok_s_published <- {KVD} headline",
                 note=f"{t['cycles']:,.0f} cycles at 1.2 GHz; the attention layer step through the link is MEASURED in RTL "
                      f"(bench bit-exact, {kv['cases']['typical']['layer_step_measured']} cycles typical), the rest is the measured "
                      f"STREAM4 token + priced adders (by grade: {t['by_grade']}); range {kv['headline']['range_tok_s']} (PHY latency best/worst)",
                 vs_tp4_single_die=kv["headline"]["vs_tp4"]),
            MTP=f(None, "tok/s", "derived", "results/rtl/qwen_rom_kv_fullbw_20261004/dspark_verdict.json",
                  note="AR only (owner 2026-10-05 AR_MODE: DSpark measured below AR on the compute-balanced ROM)")),
        aggregate=f(agg, "tok/s", "modelled", f"{TP8} side_by_side[id=SYS-1b].aggregate.aggregate_tok_s",
                    note=f"ceiling per instance, bound by {sb['aggregate']['binding']} (KV-stream bound {sb['aggregate']['kv_bound_tok_s']:,}); "
                         f"about {sb['aggregate']['users_to_saturate']} users at full per-user rate; KV room for {sb['aggregate']['kv_capacity_users']} users; "
                         "no batched run exists"),
        dies=dict(
            total=f(dies, "dies", "derived", f"{KVROM} + {KVPLAN}", note="4 ROM dies (r22k) + 4 KV dies; 2 packages of 2 ROM + 2 KV dies + 8 stacks"),
            rom_die_mm2=f(round(rom_mm2, 1), "mm2", "derived", f"{KVROM} die_mm2", note="generator floorplan (placement legal); reticle margin "
                          f"{rom['margin_mm2']:.1f} mm2"),
            kv_die_mm2=f(round(kv_mm2, 1), "mm2", "derived", f"{KVPLAN} die_mm2", note="generator floorplan; OpenROAD placement legal"),
            pair_mm2=f(round(rom_mm2 + kv_mm2, 1), "mm2", "derived", f"{KVROM} + {KVPLAN}"),
            packages=f(packages, "packages", "derived", f"{TP8} system_die.packaging"),
            stacks=f(stacks, "HBM3E stacks", "derived", f"{TP8} side_by_side[id=SYS-1b].aggregate.stacks", note="4 a KV die (KV, embedding)"),
            logic_mm2=f(r1(logic), "mm2", "derived", "4 x pair"),
            total_silicon_mm2=f(r1(logic + stacks * STACK_MM2), "mm2", "derived", f"logic + stacks x {STACK_MM2:.0f} mm2 ({ES} convention)")),
        power=dict(
            static_w=f(r1(static + kv_static), "W", "modelled", f"{ES} qwen_8k.rom.terms.static + KV-die new logic",
                       note=f"{static} W uarch static (4 dies, ungated clock) + {kv_static:.1f} W for {new_mm2:.1f} mm2 of new KV-die logic "
                            f"at the same {w_per_mm2 * 1e3:.1f} mW/mm2 (aggregators, host SerDes, UCIe, sequencer, host, PLL); the moved "
                            "PHY / controller / row-engine / landing / CDC blocks are already in the 4-die static"),
            dynamic_j_per_token=f(dyn, "J/token", "modelled", f"{ES} qwen_8k.rom.terms.dyn",
                                  note="uarch model; UCIe crossing energy (~0.3 MB a token at sub-pJ/bit) is below its resolution"),
            batch1_w=f(r1(p_b1), "W", "modelled", "static + dyn x per-user rate"),
            saturated_w=f(r1(p_sat), "W", "modelled", "static + dyn x aggregate"),
            wall_w=f(r1(p_sat * wall), "W", "derived", f"saturated x wall factor {wall:.4f} ({RACK} power.wall_factor)",
                     note="per instance (no Qwen rack layout exists)"),
        ),
        efficiency=dict(
            per_user_tok_s_per_kw=f(r1(per_user / p_b1 * 1e3), "tok/s per kW (batch 1)", "modelled", "per-user / batch1_w"),
            aggregate_tok_s_per_w=f(round(agg / p_sat, 2), "tok/s per W (saturated)", "modelled", "aggregate / saturated_w"),
            j_per_token_batch1=f(round(p_b1 / per_user, 4), "J/token", "modelled", "batch1_w / per-user")),
        cost=cost_block(lo, hi, 4, packages, p_sat * wall, agg, per_user, E, note=pk_note),
    )


def cost_block(lo, hi, rom_sets, packages, wall_w, agg, per_user, E, note=None):
    src = (f"{ECON} cost_inputs (package ${E['package_usd']:,.0f} iso-package, mask set ${E['mask_set_usd']:,.0f}, ROM coding "
           f"{E['rom_coding_fraction']:.0%}, {E['production_units']} units) + {ARCH} (lifetime {E['life']} y, utilisation "
           f"{E['util']}, ${E['kwh']}/kWh, PUE {E['pue']})")
    d = dict(
        capex_usd=f([lo, hi], "USD per instance [low, high]", "assumed", src,
                    note=f"{packages} packages x ${E['package_usd']:,.0f} + {rom_sets} ROM mask sets / {E['production_units']} units "
                         "(low: coding layers only; high: full mask sets)" + (f"; {note}" if note else "")),
        usd_per_user_tok_s=f([round(lo / per_user, 2), round(hi / per_user, 2)], "USD per (tok/s) at batch 1", "assumed", "capex / per-user"),
    )
    if agg:
        d["usd_per_agg_tok_s"] = f([round(lo / agg, 2), round(hi / agg, 2)], "USD per (tok/s) aggregate", "assumed", "capex / aggregate")
        d["usd_per_mtok"] = f([usd_per_mtok(lo, wall_w, agg, E), usd_per_mtok(hi, wall_w, agg, E)], "USD per million tokens",
                              "assumed", "(capex / lifetime + wall W x PUE x $/kWh) / (aggregate x utilisation)")
    return d


# ============================================================================== DS ROM S81 + Engram HBM
def ds_rom(E, wall):
    import dsrom_array_v2 as A
    g, gm = tp("ds_rom.json"), tp("ds_rom_mtp.json")
    eg = J(ENGRAM)
    rp = J(REPRICE)
    ri = eg["reprice_item"]
    half = A.mapping("half_dedicated")
    full = A.mapping("full_shared")
    mv = gm["mtp_variants"]

    def rack(stages, table):
        rk = A.rack_at(stages, 12, table, A.MTPDIE["draft_dies"])
        racks = rk["racks"]
        chips = sum(r["chips_kw"] for r in racks) * 1e3
        wall_r = sum(r["wall_kw"] for r in racks) * 1e3
        prov = sum(r["prov_kw"] for r in racks) * 1e3
        return dict(rk=rk, dies=rk["counts"]["dies"], stacks=rk["stacks"]["total"], chips=chips, wall=wall_r, prov=prov,
                    racks=[dict(name=r["name"], used_ou=r["used_ou"], dies=r["dies"], stacks=r["stacks"], chips_kw=r["chips_kw"],
                                wall_kw=r["wall_kw"], prov_kw=r["prov_kw"]) for r in racks])
    stack_w = J(RACK)["physical_constants"]["hbm3e_stack_static_w"]["value"]
    add_st = ri["dies"]["stacks_added"]
    rk_t = rack(half["stages"], 36)          # published array v2 (table dies)
    rk = rack(half["stages"], 0)             # Engram in HBM: no table dies
    stacks = rk["stacks"] + add_st
    chips = rk["chips"] + add_st * stack_w
    wall_w = rk["wall"] + add_st * stack_w * wall
    rk_f = rack(full["stages"], 0)
    ii = mv["half_phl"]["II_us"]
    tau = mv["half_phl"]["tau"]
    ar, mtp = g["totals"]["tok_s_published"], gm["totals"]["tok_s_published"]
    agg_ar, agg_mtp = 1e6 / ii, tau * 1e6 / (6 * ii)
    dies = rk["dies"]
    packages = dies // 2
    rom_sets = dies                          # every ROM die carries its own image (economics convention)
    lo, hi = capex(packages, rom_sets, E)
    lr = J(ES)["deepseek_1m"]["rom"]["silicon"]
    die_mm2 = 858.0
    logic = dies * die_mm2
    v2 = J("results/arch/array_v2_20261008/array_v2.json") if (ROOT / "results/arch/array_v2_20261008/array_v2.json").exists() else None
    return dict(
        id="ds_rom", name="DeepSeek-V4.1 ROM array (S81, 1,792 pairs, HALF_PHL BF, Engram tables in HBM)", model="DeepSeek-V4.1-Flash",
        context="1M (position 1,048,575)", modes=["AR", "MTP"], graph="ds_rom.json", graph_mtp="ds_rom_mtp.json",
        per_user=dict(
            AR=f(ar, "tok/s", "derived", "results/arch/token_path_20261009/ds_rom.json totals.tok_s_published <- "
                 f"{REPRICE} ds_rom after.half_phl", note=f"measured field phases (19,312 regions exact) + measured/vendor hops, "
                 f"composed; by grade {g['totals']['by_grade']}; Engram branch 0 cycles on the path (slack L1 "
                 f"{ri['off_path_slack_cycles']['L1']:,} / L14 {ri['off_path_slack_cycles']['L14']:,} cycles, modelled)"),
            MTP=f(mtp, "tok/s", "derived", "results/arch/token_path_20261009/ds_rom_mtp.json totals.tok_s_published",
                  note=f"DSpark gamma 5, tau {tau} (owner 6-class blend; results/speculative/v41_mtp_acceptance_qualified_20261003/"
                       f"blend_owner6.json); draft dies / seed not built (hatched in the graph), Markov head modelled")),
        bf_variants=dict(
            decision="owner BF decision 2026-10-09 21:30 PT pending; HALF_PHL is the accepted closure path (headline)",
            half_phl=dict(AR=mv["half_phl"]["AR_tok_s"], MTP=mv["half_phl"].get("MTP_tok_s_charged", mv["half_phl"]["MTP_tok_s"]),
                          MTP_composed=mv["half_phl"]["MTP_tok_s"], stages=half["stages"],
                          dies=rk["dies"], grade="derived", source=f"{REPRICE} ds_rom after.half_phl"),
            full_rate_shared98=dict(AR=mv["full_rate_shared98"]["AR_tok_s"], MTP=mv["full_rate_shared98"]["MTP_tok_s"],
                                    stages=full["stages"], dies=rk_f["dies"], stacks=rk_f["stacks"] + add_st,
                                    chips_w=r1(rk_f["chips"] + add_st * stack_w), grade="derived",
                                    source=f"{REPRICE} ds_rom after.full_rate (no BF cost: the no-cost bound until recut / deep4 closes)"),
            full_rate_dedicated120=dict(AR=rp["ds_rom"]["after"]["full_rate_dedicated120"]["AR_tok_s"],
                                        MTP=rp["ds_rom"]["after"]["full_rate_dedicated120"]["MTP_tok_s"], stages=half["stages"],
                                        dies=rk["dies"], grade="derived",
                                        source=f"{REPRICE} ds_rom.after.full_rate_dedicated120 (full-rate BF on the dedicated mapping)")),
        aggregate=dict(
            AR=f(r1(agg_ar), "tok/s", "derived", "1 / II (results/arch/token_path_20261009/ds_rom_mtp.json mtp_variants.half_phl.II_us)",
                 note=f"pipeline bound: the slowest stage admits one position every II = {ii} us; ~{round(mv['half_phl']['AR_us'] / ii, 1)} "
                      "users to fill; ignores draft-die and collective contention (upper bound)"),
            MTP=f(r1(agg_mtp), "tok/s", "derived", "tau / (6 II)", note="each step sends 6 positions through the pipeline (upper bound)")),
        dies=dict(
            total=f(dies, "dies", "derived", f"tools/dsrom_array_v2.py rack_at({half['stages']}, head 12, table 0, draft {A.MTPDIE['draft_dies']})",
                    note=f"layer {half['layer_dies']} (incl. 32 scan) + head 12 + draft {A.MTPDIE['draft_dies']}; Engram table dies "
                         f"{rk_t['dies'] - dies} removed ({ENGRAM})"),
            layer1e_dies=f(ri["dies"]["home_dies_changed"], "dies", "derived", f"{ENGRAM} reprice_item.dies.home_dies_changed",
                           note="Engram home dies (layers 1 and 14, 4 ranks each) with a second stack"),
            packages=f(packages, "packages", "derived", "two-die packages"),
            stacks=f(stacks, "HBM3E stacks", "derived", f"rack_at stacks {rk['stacks']} + {add_st} Engram ({ENGRAM})"),
            die_mm2=f(die_mm2, "mm2", "assumed", "reticle (858 mm2) charged per die; S81 m221pq floorplan 33 x 26 mm",
                      note=f"{ES} carries {lr['die_mm2']['value']} mm2 decision-priced for the 85-stage die"),
            logic_mm2=f(r1(logic), "mm2", "derived", "dies x die_mm2"),
            total_silicon_mm2=f(r1(logic + stacks * STACK_MM2), "mm2", "derived", f"logic + stacks x {STACK_MM2:.0f} mm2")),
        power=dict(
            chips_w=f(r1(chips), "W", "modelled", "tools/dsrom_array_v2.py rack_at (per-die W: the busiest saturated layer die "
                      f"{rk['rk']['die_w']['layer']} W for every layer / scan / draft die, head {rk['rk']['die_w']['head_table']} W, "
                      f"stack {rk['rk']['die_w']['stack']} W) + Engram stacks",
                      note="upper bound: every die at the busiest die's saturated power (array v2 placeholder until a 1,792 power pass)"),
            wall_w=f(r1(wall_w), "W", "derived", "rack_at wall_kw (chips x wall factor + infra) + Engram stacks"),
            provisioned_w=f(r1(rk["prov"]), "W", "derived", "rack_at prov_kw"),
            engram_delta_w=f(ri["power_w"]["net"], "W", "modelled", f"{ENGRAM} reprice_item.power_w.net",
                             note=f"-{ri['dies']['table_dies_removed']} table dies, +{add_st} stacks"),
            racks=rk["racks"],
        ),
        efficiency=dict(
            per_user_tok_s_per_kw=dict(AR=f(round(ar / chips * 1e3, 2), "tok/s per kW", "modelled", "per-user / chips_w"),
                                       MTP=f(round(mtp / chips * 1e3, 2), "tok/s per kW", "modelled", "per-user / chips_w")),
            aggregate_tok_s_per_w=dict(AR=f(round(agg_ar / chips, 3), "tok/s per W", "modelled", "aggregate bound / chips_w"),
                                       MTP=f(round(agg_mtp / chips, 3), "tok/s per W", "modelled", "aggregate bound / chips_w"))),
        cost=cost_block(lo, hi, rom_sets, packages, wall_w, agg_mtp, mtp, E, note="aggregate = MTP pipeline bound"),
        array_v2_cable_delta=(dict(AR=v2["headline"]["rows"]["half_phl"]["v2"]["AR_tok_s"], MTP=v2["headline"]["rows"]["half_phl"]["v2"]["MTP_tok_s"],
                                   grade="derived", source="results/arch/array_v2_20261008/array_v2.json headline.rows.half_phl.v2",
                                   note="real 120-stage cable classes + mtp-die P2 crossings: +0.02 % AR / -0.01 % MTP; not in the graph")
                              if v2 else None),
    )


# ============================================================================== HBM accelerator (generic die)
def hbm(E, wall):
    g, gm = tp("hbm_ds.json"), tp("hbm_ds_mtp.json")
    es = J(ES)["deepseek_1m"]["hbm_accel"]
    terms = es["terms"]
    dt = J(HDT)["result"]
    qt = J(HQT)["result"]
    qp = J(HQP)
    qd = J(HQD)
    tp8 = J(TP8)
    approved = J(HAPP)["result"]
    calibration = J(HCA)["result"]["sensitivity"]
    approved_fixed = approved["approved_path_c2_g22"]
    approved_current = approved["approved_path_c2_g22_current_rtl_ratios"]
    if approved_fixed["n_races"] or approved_current["n_races"]:
        raise ValueError("approved HBM path contains schedule races")
    ar = approved_fixed["tok_s"]
    # Charge the approved gather delta relative to native S2 once per verify pass.
    # Keep the native S2-S0 CP effect as the existing separate sensitivity.
    mtp_step = gm["totals"]["step_cycles"]
    mtp_tau = gm["totals"]["tau"]
    mtp = r1(mtp_tau * CLK / (mtp_step + approved_fixed["delta_cycles"]))
    mtp_current = r1(mtp_tau * CLK / (mtp_step + approved_current["delta_cycles"]))
    cyc = g["totals"]["cycles"]
    dies, stacks, switches = 96, 384, 8
    die_mm2 = 798.49
    static, sw_w = terms["static"]["value"], terms["switch_w"]["value"] * switches
    p_ar = static + sw_w + terms["dyn_ar"]["value"] * ar
    p_mtp = static + sw_w + terms["dyn_mtp"]["value"] * mtp
    s0, s2 = dt["S0"]["total_cycles"], dt["S2"]["total_cycles"]
    v = dt.get("variants", {})
    sl = v["S2_list_scheduled"] if v.get("S2_list_scheduled_races", 1) == 0 else s2   # a racy schedule is not usable
    mt = gm["totals"]
    sens = dict(
        native_stream=dict(cycles=r1(s2), tok_s=r1(CLK / s2),
                           note="the native HGI-1 program alone, as compiled (fused SU chains, CP-aware order)"),
        mtp_as_emitted=dict(delta_cycles=r1(s2 - s0), MTP=r1(mt["tau"] * CLK / (mt["step_cycles"] + s2 - s0)),
                            note="the same delta once per verify pass (records issue once a pass; the columns ride "
                                 "in each record); no native verify program is compiled yet"),
        as_emitted=dict(delta_cycles=r1(s2 - s0), AR=r1(CLK / (cyc + s2 - s0))),
        compiler_list_scheduled=dict(delta_cycles=r1(sl - s0), AR=r1(CLK / (cyc + sl - s0))))
    lo, hi = capex(dies // 2, 0, E)
    # Qwen3-8B on the generic die (r25, TP4, INT8 fmt3): pathfinding simulator
    q2 = qt["S2"]
    q_ar = q2["tok_s"]
    # DFlash (z-lab/Qwen3-8B-DFlash-b16) step on the generic die: hgi_sim compiled step, S2 timing; headline = block 16,
    # the spec's shared-weight-read SM ('spec'), two-beat INT8 (the adopted front), the largest published tau (8.01)
    dft = [r for r in qd["table"] if r["sm_mode"] == "spec"]
    pick = lambda B, ob, tk: next(r for r in qd["table"] if r["B"] == B and r["sm_mode"] == "spec" and r["one_beat_int8"] == ob
                                  and r["tau_kind"] == tk)
    q_mtp = pick(16, False, "published")["tok_s"]
    q_dies, q_stacks = 4, 16
    q_static = static / dies * q_dies
    q_dyn = J(ES)["qwen_8k"]["hbm_accel"]["tp4_iso_silicon"]["terms"]["dyn"]["value"]
    q_p = q_static + q_dyn * q_ar
    pl_agg = [16254, 25169]
    q_lo, q_hi = capex(2, 0, E)
    ds_block = dict(
        id="hbm_ds", model="DeepSeek-V4.1-Flash", context="1M (position 1,048,575)", modes=["AR", "MTP"],
        graph="hbm_ds.json", graph_mtp="hbm_ds_mtp.json",
        graph_note="Historical unified composition retained; current AR uses the approved G20/G21/G22 record-path price. "
                   "MTP adds that path's delta once to the charged historical verify-step composition.",
        per_user=dict(
            AR=f(ar, "tok/s", "modelled", f"{HAPP} result.approved_path_c2_g22.tok_s",
                 note="approved G20/G21 gather path (2 slots per gather) and G22 row-sharded HC; modelled on the fixed RTL. "
                      f"Today's RTL service-time ratios give {approved_current['tok_s']} tok/s at full DMA bandwidth; "
                      "the hardware bandwidth implementation remains required. The separate token graph retains the "
                      "historical unified composition."),
            MTP=f(mtp, "tok/s", "modelled", f"{HAPP} result.approved_path_c2_g22.delta_cycles + "
                  "results/arch/token_path_20261009/hbm_ds_mtp.json totals.step_cycles",
                  note=f"DSpark gamma 5, tau {mtp_tau}; approved gather delta {approved_fixed['delta_cycles']} cycles "
                       f"charged once per verify pass on the charged composition {mtp_step} cycles; modelled on the fixed RTL. "
                       f"Today's RTL ratios give {mtp_current} tok/s. No native verify program is compiled.")),
        rtl_calibration=dict(
            grade="modelled", source=f"{HAPP}; {HCA}",
            note="Partial component sensitivity; DS SU/SFU remain uncalibrated, and calibrated peers are bench vehicles. No full-token RTL measurement. DMA is "
                 "priced at full bandwidth, with >=90% bandwidth an implementation acceptance gate.",
            AR=f(approved_current["tok_s"], "tok/s", "modelled",
                 f"{HAPP} result.approved_path_c2_g22_current_rtl_ratios.tok_s"),
            MTP=f(mtp_current, "tok/s", "modelled", f"{HAPP} result.approved_path_c2_g22_current_rtl_ratios.delta_cycles + "
                  "results/arch/token_path_20261009/hbm_ds_mtp.json totals.step_cycles"),
            charged_mtp_basis_cycles=mtp_step,
            approved_delta_per_verify=approved_fixed["delta_cycles"],
            calibrated_delta_per_verify=approved_current["delta_cycles"],
            native_AR=f(calibration["ds_1M"]["current_rtl_dma_full_bw_tok_s"], "tok/s", "modelled",
                        f"{HCA} result.sensitivity.ds_1M.current_rtl_dma_full_bw_tok_s",
                        note="original native program; does not implement the approved gather path"),
            ratios=approved["rtl_ratios_applied"]),
        sequencer_retiming=dict(
            grade="modelled", source=f"{HDT} result (the bit-exact native HGI-1 program, rank 0, CP modelled; unit costs walk-priced, "
                                     "CP entries ESTIMATES)",
            rule="delta = simulated program time - its own in-order dataflow (S0), added to the token path; not in the headline "
                 "until the sequencer (C2) costs are measured (simulator spec section 4: published numbers use measured entries only)",
            **sens),
        aggregate=f(None, "tok/s", "modelled", f"{ES} / results/uarch/hbm_accelerator_integration_20261004/model.json fairness.saturation_gap",
                    note="not composed: no batch / union / credit calendar exists for the HBM accelerator (owner rule: never infer from batch 1)"),
        dies=dict(
            total=f(dies, "dies", "derived", "TP-96 (hbm_ds token path)"),
            die_mm2=f(die_mm2, "mm2", "derived", HBM_GENERIC, note="R25G generic die (R25S + fmt3), geometry-only fit"),
            packages=f(dies // 2, "packages", "derived", "two-die packages"),
            stacks=f(stacks, "HBM3E stacks", "derived", f"{ES} deepseek_1m.hbm_accel.silicon.stacks", note="4 a die"),
            switch_chips=f(switches, "Tomahawk Ultra", "assumed", f"{ES} deepseek_1m.hbm_accel.silicon.switch_chips"),
            logic_mm2=f(r1(dies * die_mm2), "mm2", "derived", "dies x die_mm2"),
            total_silicon_mm2=f(r1(dies * die_mm2 + stacks * STACK_MM2 + switches * 800.0), "mm2", "derived",
                                f"logic + stacks x {STACK_MM2:.0f} + switches x 800 mm2 ({ES} switch_mm2 / switch_chips)")),
        power=dict(
            static_w=f(static, "W", "modelled", f"{ES} deepseek_1m.hbm_accel.terms.static", note="gated static, transferred constant"),
            switch_w=f(sw_w, "W", "assumed", f"{ES} deepseek_1m.hbm_accel.terms.switch_w x {switches}"),
            dynamic_j_per_token=dict(AR=f(terms["dyn_ar"]["value"], "J/token", "modelled", terms["dyn_ar"]["src"]),
                                     MTP=f(terms["dyn_mtp"]["value"], "J/token", "modelled", terms["dyn_mtp"]["src"])),
            batch1_w=dict(AR=f(r1(p_ar), "W", "modelled", "static + switches + dyn x per-user"),
                          MTP=f(r1(p_mtp), "W", "modelled", "static + switches + dyn x per-user")),
            wall_w=f(r1(p_mtp * wall), "W", "derived", f"MTP batch-1 W x wall factor {wall:.4f}")),
        efficiency=dict(per_user_tok_s_per_kw=dict(AR=f(round(ar / p_ar * 1e3, 2), "tok/s per kW", "modelled", "per-user / batch1_w"),
                                                   MTP=f(round(mtp / p_mtp * 1e3, 2), "tok/s per kW", "modelled", "per-user / batch1_w")),
                        aggregate_tok_s_per_w=f(None, "tok/s per W", "modelled", "aggregate not composed")),
        cost=cost_block(lo, hi, 0, dies // 2, p_mtp * wall, None, mtp, E, note="switch chips not priced"),
    )
    qwen_block = dict(
        id="hbm_qwen", model="Qwen3-8B", context="8K (position 8,191)", modes=["AR", "MTP"], graph=None,
        graph_note="no token-path graph yet (export target qwen_hbm not defined); the rate is the HGI-1 simulator's",
        per_user=dict(
            AR=f(q_ar, "tok/s", "modelled", f"{HQT} result.S2.tok_s",
                 note=f"pathfinding simulator on 4 r25 dies, TP4, INT8 fmt3 at the MEASURED SM issue (64 codes/cycle/SM, 2 beats a "
                      f"128-code line: SM-issue bound); {q2['total_cycles']:,.0f} cycles; CP entries estimates; dense 1,024-bit lines adopted "
                      "(0 % alone); one-beat INT8 (RQ-HF-7, REJECTED: NO_FIT, results/rtl/hbm_forks_20261009/int8_relayout_study.json) would give "
                      f"{qp['dense 1.0, fmt3 one-beat issue (128 codes/cyc/SM)']['tok_s']} ({HQP})",
                 one_beat_int8=qp["dense 1.0, fmt3 one-beat issue (128 codes/cyc/SM)"]["tok_s"]),
            MTP=f(q_mtp, "tok/s", "modelled", f"{HQD} table[B=16, sm_mode=spec, one_beat_int8=False, tau_kind=published]",
                  note=f"DFlash b16 step (draft + 2-pass verify + accept) compiled to HGI-1 and run bit-exact in hgi_sim "
                       f"(results/arch/hgi_sim_20261009/dflash/dflash_proof.json); step {pick(16, False, 'published')['step_cycles']:,.0f} "
                       f"cycles at 8K; tau 8.01 = DFlash arXiv:2602.06036v2 Table 3 (B200, MATH-500; largest published Qwen3-8B tau); "
                       f"sensitivity: our measured tau 3.656 -> {pick(16, False, 'measured')['tok_s']}; block 8 "
                       f"(1 weight pass) {pick(8, False, 'published')['tok_s']} at tau {pick(8, False, 'published')['tau']} "
                       f"(published-anchored) / {pick(8, False, 'measured')['tok_s']} at measured 3.2956; one-beat INT8 (NO_FIT) "
                       f"{pick(16, True, 'published')['tok_s']}; assumes the SM shares one issued line over <= 8 slots (SPEC_GAP G18: "
                       f"if every slot re-issues, block 16 falls to {next(r for r in qd['table'] if r['B'] == 16 and r['sm_mode'] == 'reissue' and not r['one_beat_int8'] and r['tau_kind'] == 'published')['tok_s']})",
                  table=[{k: r[k] for k in ("B", "sm_mode", "one_beat_int8", "tau_kind", "tau", "step_cycles", "tok_s", "vs_ar")}
                         for r in qd["table"]])),
        rtl_calibration=dict(
            grade="modelled", source=HCA,
            note="Reduced-reference service-time sensitivity (SU N64/M64/LV7 vs production N1024/M256); full D1 stage/drain remains unmeasured. DMA stays at full bandwidth. "
                 "Modelled on the fixed RTL; current RTL measures slower.",
            AR=f(calibration["qwen_P8191"]["current_rtl_dma_full_bw_tok_s"], "tok/s", "modelled",
                 f"{HCA} result.sensitivity.qwen_P8191.current_rtl_dma_full_bw_tok_s"),
            MTP=f(calibration["dflash_b16"]["current_rtl_dma_full_bw"]["tok_s_tau_8_01"], "tok/s", "modelled",
                  f"{HCA} result.sensitivity.dflash_b16.current_rtl_dma_full_bw.tok_s_tau_8_01")),
        aggregate=f(pl_agg, "tok/s [low, high]", "modelled", f"{HBM_GENERIC} qwen.aggregate_tp4.aggregate_estimate_tok_s",
                    note="KV-stream and SU-occupancy ceilings; SM compute at batch not checked"),
        dies=dict(total=f(q_dies, "dies", "derived", "TP4 (owner 10-09 qwen-on-r25-unified)"),
                  packages=f(2, "packages", "derived", "two-die packages"),
                  stacks=f(q_stacks, "HBM3E stacks", "derived", "4 a die"),
                  logic_mm2=f(r1(q_dies * die_mm2), "mm2", "derived", "dies x R25G die"),
                  total_silicon_mm2=f(r1(q_dies * die_mm2 + q_stacks * STACK_MM2), "mm2", "derived", f"logic + stacks x {STACK_MM2:.0f}")),
        power=dict(static_w=f(r1(q_static), "W", "modelled", f"DS gated static / {dies} x {q_dies} ({ES})"),
                   dynamic_j_per_token=f(q_dyn, "J/token", "modelled", f"{ES} qwen_8k.hbm_accel.tp4_iso_silicon.terms.dyn",
                                         note="transferred from the Qwen HBM tile die (same HBM-streamed weight path)"),
                   batch1_w=f(r1(q_p), "W", "modelled", "static + dyn x per-user"),
                   wall_w=f(r1(q_p * wall), "W", "derived", f"x wall factor {wall:.4f}")),
        efficiency=dict(per_user_tok_s_per_kw=f(round(q_ar / q_p * 1e3, 2), "tok/s per kW", "modelled", "per-user / batch1_w")),
        cost=cost_block(q_lo, q_hi, 0, 2, q_p * wall, None, q_ar, E),
    )
    return dict(id="hbm", name="HBM accelerator (one generic die, R25G, for DeepSeek-V4.1 and Qwen3-8B)", targets=[ds_block, qwen_block])


# ============================================================================== GPU / served (third-party)
def gpu():
    reg = J(REG)
    E = {e["id"]: e for e in reg["entries"]}

    def ext(eid, path, label):
        v = E[eid]["value"]
        for k in path:
            v = v[k]
        return f(v, "tok/s", "third-party", f"{REG} entries[id={eid}].value." + ".".join(str(k) for k in path), note=label,
                 title=E[eid]["title"], url=E[eid].get("url"))
    return dict(
        qwen=dict(best_batch1=ext("new:dflash_table3_table4", ["qwen3_8b_b200_c1_math500", "dflash_tok_s"],
                                  "1 x B200, SGLang + DFlash, concurrency 1, MATH-500 (tau 8.01, GPU-favourable)"),
                  ar_batch1=ext("new:dflash_table3_table4", ["qwen3_8b_b200_c1_math500", "ar_tok_s"],
                                "1 x B200, SGLang, AR baseline of the same table (like-for-like AR row)"),
                  served_median=ext("new:openrouter_qwen3_8b_20261009", ["median_tok_s"], "OpenRouter P50, one provider")),
        ds=dict(best_batch1=ext("new:sglang_v41flash_gb300_bs1", ["dspark_tok_s"],
                                "4 x GB300, SGLang + DSpark, batch 1, simulated accept length 5.5 (GPU-favourable vs our tau 4.159)"),
                ar_batch1=ext("new:sglang_v41flash_gb300_bs1", ["plain_tok_s"],
                              "4 x GB300, SGLang, no speculation, batch 1 (like-for-like AR row)"),
                b200_c1_p90=ext("new:infx_v41flash_b200_agentx", ["tp4_ep4", "1", 1], "B200 TP4, SGLang + DSpark, concurrency 1, p90 (AgentX)"),
                served_median=ext("new:openrouter_v41flash_20261009", ["median_tok_s"], "OpenRouter median of 30 providers, P50 1 week"),
                served_best=ext("new:openrouter_v41flash_20261009", ["best_standard_routed_tok_s"], "OpenRouter best standard-routed (Together)")))


def headline_rows(S, G):
    q, d, h = S["qwen_rom"], S["ds_rom"], S["hbm"]["targets"]
    hd, hq = h[0], h[1]
    g = lambda x: x["value"]
    rows = [
        dict(target="Qwen ROM (ROM + KV die)", model="Qwen3-8B 8K", mode="AR", per_user=g(q["per_user"]["AR"]),
             aggregate=g(q["aggregate"]), dies=g(q["dies"]["total"]), stacks=g(q["dies"]["stacks"]),
             power_w=g(q["power"]["saturated_w"]), tok_s_per_kw_b1=g(q["efficiency"]["per_user_tok_s_per_kw"]),
             capex=g(q["cost"]["capex_usd"]), gpu=g(G["qwen"]["best_batch1"]), served=g(G["qwen"]["served_median"])),
        dict(target="DS ROM (S81 + Engram HBM)", model="DeepSeek-V4.1-Flash 1M", mode="AR", per_user=g(d["per_user"]["AR"]),
             aggregate=g(d["aggregate"]["AR"]), dies=g(d["dies"]["total"]), stacks=g(d["dies"]["stacks"]),
             power_w=g(d["power"]["chips_w"]), tok_s_per_kw_b1=g(d["efficiency"]["per_user_tok_s_per_kw"]["AR"]),
             capex=g(d["cost"]["capex_usd"]), gpu=g(G["ds"]["best_batch1"]), served=g(G["ds"]["served_median"])),
        dict(target="DS ROM (S81 + Engram HBM)", model="DeepSeek-V4.1-Flash 1M", mode="MTP", per_user=g(d["per_user"]["MTP"]),
             aggregate=g(d["aggregate"]["MTP"]), dies=g(d["dies"]["total"]), stacks=g(d["dies"]["stacks"]),
             power_w=g(d["power"]["chips_w"]), tok_s_per_kw_b1=g(d["efficiency"]["per_user_tok_s_per_kw"]["MTP"]),
             capex=g(d["cost"]["capex_usd"]), gpu=g(G["ds"]["best_batch1"]), served=g(G["ds"]["served_median"])),
        dict(target="HBM accelerator (generic die)", model="DeepSeek-V4.1-Flash 1M", mode="AR", per_user=g(hd["per_user"]["AR"]),
             aggregate=None, dies=g(hd["dies"]["total"]), stacks=g(hd["dies"]["stacks"]), power_w=g(hd["power"]["batch1_w"]["AR"]),
             tok_s_per_kw_b1=g(hd["efficiency"]["per_user_tok_s_per_kw"]["AR"]), capex=g(hd["cost"]["capex_usd"]),
             gpu=g(G["ds"]["best_batch1"]), served=g(G["ds"]["served_median"])),
        dict(target="HBM accelerator (generic die)", model="DeepSeek-V4.1-Flash 1M", mode="MTP", per_user=g(hd["per_user"]["MTP"]),
             aggregate=None, dies=g(hd["dies"]["total"]), stacks=g(hd["dies"]["stacks"]), power_w=g(hd["power"]["batch1_w"]["MTP"]),
             tok_s_per_kw_b1=g(hd["efficiency"]["per_user_tok_s_per_kw"]["MTP"]), capex=g(hd["cost"]["capex_usd"]),
             gpu=g(G["ds"]["best_batch1"]), served=g(G["ds"]["served_median"])),
        dict(target="HBM accelerator (generic die)", model="Qwen3-8B 8K", mode="AR", per_user=g(hq["per_user"]["AR"]),
             aggregate=g(hq["aggregate"]), dies=g(hq["dies"]["total"]), stacks=g(hq["dies"]["stacks"]), power_w=g(hq["power"]["batch1_w"]),
             tok_s_per_kw_b1=g(hq["efficiency"]["per_user_tok_s_per_kw"]), capex=g(hq["cost"]["capex_usd"]),
             gpu=g(G["qwen"]["best_batch1"]), served=g(G["qwen"]["served_median"])),
    ]
    q_mtp = g(hq["per_user"]["MTP"])
    q_pm = g(hq["power"]["static_w"]) + g(hq["power"]["dynamic_j_per_token"]) * q_mtp
    rows.append(dict(target="HBM accelerator (generic die)", model="Qwen3-8B 8K", mode="MTP", per_user=q_mtp,
                     aggregate=None, dies=g(hq["dies"]["total"]), stacks=g(hq["dies"]["stacks"]), power_w=round(q_pm, 1),
                     tok_s_per_kw_b1=round(q_mtp / q_pm * 1e3, 2), capex=g(hq["cost"]["capex_usd"]),
                     gpu=g(G["qwen"]["best_batch1"]), served=g(G["qwen"]["served_median"])))
    for r in rows:
        r["vs_gpu_batch1"] = round(r["per_user"] / r["gpu"], 2)
        r["vs_served_median"] = round(r["per_user"] / r["served"], 1)
        fam = "qwen" if "Qwen" in r["model"] else "ds"
        r["gpu_same_mode"] = g(G[fam]["ar_batch1"] if r["mode"] == "AR" else G[fam]["best_batch1"])
        r["vs_gpu_same_mode"] = round(r["per_user"] / r["gpu_same_mode"], 2)
    return rows


def fmt(v, nd=1):
    if v is None:
        return "n/c"
    if isinstance(v, list):
        return "–".join(fmt(x, nd) for x in v)
    if isinstance(v, float) and nd == 0:
        return f"{v:,.0f}"
    return f"{v:,.{nd}f}" if isinstance(v, float) else f"{v:,}"


def calibration_table(S, annotation=None):
    """Expose fixed-price estimates beside the partial component-measured sensitivity."""
    lines = ["", "HBM estimates use fixed RTL prices. The partial measured-unit sensitivity applies measured service-time "
             "ratios analytically; DeepSeek SU/SFU remain uncalibrated. Qwen SU/SFU ratios use a reduced reference "
             "vehicle (N64/M64/LV7 rather than production N1024/M256); full D1 stage/drain is unmeasured. DMA stays at full bandwidth in both columns "
             "and must measure at least 90% bandwidth before adoption. No full-token RTL rate is established.", "",
             "| HBM workload | Mode | Fixed RTL (tok/s) | Partial measured-unit sensitivity (tok/s) |",
             "|---|---|---:|---:|"]
    for target in S["hbm"]["targets"]:
        for mode in ("AR", "MTP"):
            fixed = target["per_user"][mode]["value"]
            current = target["rtl_calibration"][mode]["value"]
            suffix = ""
            if annotation:
                path = f"hbm.targets[id={target['id']}]"
                suffix = " " + annotation(current, f"{path}.rtl_calibration.{mode}.value",
                                            f"{target['id']} {mode} partial RTL sensitivity")
                suffix += " " + annotation(fixed, f"{path}.per_user.{mode}.value", f"{target['id']} {mode} fixed RTL")
            lines.append(f"| {target['model']} | {mode} | {fixed:,.1f} | {current:,.1f} |{suffix}")
    return lines


def readme(S):
    L = ["# Token path and system numbers, 2026-10-09", "",
         "Generated by `tools/token_path_systems.py`; do not edit. The per-token critical-path graphs (`qwen_rom.json`, `ds_rom*.json`, "
         "`hbm_ds*.json`) come from `tools/token_path_export.py` unchanged. `systems.json` adds aggregate rate, power, cost, die and stack "
         "counts and rack power. Every number there carries a grade (measured / derived / modelled / assumed / third-party) and its source. "
         "None of these rows is a closed physical rate.", "",
         "## Headline", "",
         "| Target | Model | Mode | Per user (tok/s) | Aggregate (tok/s) | Dies | Stacks | Power (W) | tok/s per kW at batch 1 | Capex (USD, low–high) | × best GPU batch 1 | × GPU same mode | × served median |",
         "|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for r in S["headline"]:
        L.append(f"| {r['target']} | {r['model']} | {r['mode']} | {fmt(r['per_user'])} | {fmt(r['aggregate'], 0)} | {r['dies']:,} | "
                 f"{r['stacks']:,} | {fmt(r['power_w'], 0)} | {fmt(r['tok_s_per_kw_b1'])} | {fmt(r['capex'], 0)} | "
                 f"{r['vs_gpu_batch1']:.2f} | {r['vs_gpu_same_mode']:.2f} | {r['vs_served_median']:.1f} |")
    L += calibration_table(S)
    L += ["", "n/c: not composed. Power: Qwen rows are the modelled instance power (saturated for the ROM, batch 1 for the HBM die); "
          "the DS ROM row is the rack's chip power with every die at the busiest die's saturated power (an upper bound); the HBM DS rows "
          "are batch-1 power including 8 switches. GPU batch 1: Qwen 1 × B200 + DFlash (1,175); DeepSeek 4 × GB300 + DSpark (873.6, "
          "simulated acceptance 5.5). Same mode: AR rows against the GPU without speculation (Qwen 1 × B200 230, DFlash Table 3; "
          "DeepSeek 4 × GB300 203), MTP rows against the GPU with speculation. Served median: OpenRouter, 2026-10-09 (Qwen 55, DeepSeek 88.5).", "",
          "## What changed since 2026-10-08", ""]
    for c in S["changes"]:
        L.append(f"- **{c['item']}**: {c['effect']} ({c['grade']}; {c['source']})")
    L += ["", "## Pending", ""] + [f"- {p}" for p in S["pending"]] + [""]
    return "\n".join(L)


DOC = ROOT / "docs/ANALYTICAL_REPORT.md"
DOC_BEGIN, DOC_END = "<!-- BEGIN generated: tools/token_path_systems.py -->", "<!-- END generated: tools/token_path_systems.py -->"


def doc_section(S):
    """the report's current-design-point section, every figure bound to systems.json by a checked annotation"""
    src = "results/arch/token_path_20261009/systems.json"
    ann = lambda v, path, name: f'<!-- figure: {v} src="{src}#{path}" name="{name}" -->'
    q, d = S["qwen_rom"], S["ds_rom"]
    hd, hq = S["hbm"]["targets"]
    G = S["gpu"]

    def n(v, nd=1):
        return f"{v:,.{nd}f}"

    rows = [
        ("Qwen3-8B ROM: TP4 ROM die + KV die", "Qwen3-8B, 8K", "AR", q["per_user"]["AR"]["value"], "qwen_rom.per_user.AR.value",
         q["aggregate"]["value"], "qwen_rom.aggregate.value", q["dies"]["total"]["value"], "qwen_rom.dies.total.value",
         q["dies"]["stacks"]["value"], "qwen_rom.dies.stacks.value", q["power"]["saturated_w"]["value"], "qwen_rom.power.saturated_w.value",
         "modelled saturated, per instance"),
        ("DeepSeek-V4.1 ROM: S81, 1,792 pairs, HALF_PHL BF, Engram in HBM", "DeepSeek-V4.1-Flash, 1M", "AR",
         d["per_user"]["AR"]["value"], "ds_rom.per_user.AR.value", d["aggregate"]["AR"]["value"], "ds_rom.aggregate.AR.value",
         d["dies"]["total"]["value"], "ds_rom.dies.total.value", d["dies"]["stacks"]["value"], "ds_rom.dies.stacks.value",
         d["power"]["chips_w"]["value"], "ds_rom.power.chips_w.value", "rack chips, every die at the busiest die's saturated power"),
        ("", "", "MTP (τ 4.159)", d["per_user"]["MTP"]["value"], "ds_rom.per_user.MTP.value", d["aggregate"]["MTP"]["value"],
         "ds_rom.aggregate.MTP.value", None, None, None, None, None, None, ""),
        ("HBM accelerator, generic die (R25G)", "DeepSeek-V4.1-Flash, 1M", "AR", hd["per_user"]["AR"]["value"],
         "hbm.targets[id=hbm_ds].per_user.AR.value", None, None, hd["dies"]["total"]["value"], "hbm.targets[id=hbm_ds].dies.total.value",
         hd["dies"]["stacks"]["value"], "hbm.targets[id=hbm_ds].dies.stacks.value", hd["power"]["batch1_w"]["AR"]["value"],
         "hbm.targets[id=hbm_ds].power.batch1_w.AR.value", "modelled batch 1, with 8 switches"),
        ("", "", "MTP (τ 4.159)", hd["per_user"]["MTP"]["value"], "hbm.targets[id=hbm_ds].per_user.MTP.value", None, None,
         None, None, None, None, None, None, ""),
        ("", "Qwen3-8B, 8K", "AR", hq["per_user"]["AR"]["value"], "hbm.targets[id=hbm_qwen].per_user.AR.value",
         hq["aggregate"]["value"], "hbm.targets[id=hbm_qwen].aggregate.value",
         hq["dies"]["total"]["value"], "hbm.targets[id=hbm_qwen].dies.total.value", hq["dies"]["stacks"]["value"],
         "hbm.targets[id=hbm_qwen].dies.stacks.value", hq["power"]["batch1_w"]["value"], "hbm.targets[id=hbm_qwen].power.batch1_w.value",
         "modelled batch 1"),
        ("", "", "MTP (DFlash b16, τ 8.01)", hq["per_user"]["MTP"]["value"], "hbm.targets[id=hbm_qwen].per_user.MTP.value", None,
         None, None, None, None, None, None, None, ""),
    ]
    L = [DOC_BEGIN, "", "## Current design points (token path of 2026-10-09)", "",
         "This section is generated by `python3 tools/token_path_systems.py` from `results/arch/token_path_20261009/`. "
         "That export holds one decode token's critical path for each design (`tools/token_path_export.py`) and the system "
         "numbers in `systems.json`, where every input carries its grade (measured, derived, modelled, assumed or "
         "third-party) and its source. Unlike the roofline sections below, these rates are composed from RTL "
         "measurements and priced adders on the actual design points. None of them is a closed physical rate.", "",
         "| Design | Model, context | Mode | Per user (tok/s) | Aggregate (tok/s) | Dies | HBM stacks | Power (W) | Power basis |",
         "|---|---|---|---:|---:|---:|---:|---:|---|"]
    tags = ["Qwen ROM", "DS ROM", "DS ROM", "HBM DS", "HBM DS", "HBM Qwen", "HBM Qwen"]
    for tag, (name, model, mode, pu, pup, ag, agp, di, dip, st, stp, pw, pwp, basis) in zip(tags, rows):
        if isinstance(ag, list):
            agt = f"{n(ag[0], 0)}–{n(ag[1], 0)} (modelled range)"
        else:
            agt = n(ag, 0) if ag is not None else "not composed"
        cells = [name, model, mode, f"**{n(pu)}**", agt,
                 f"{di:,}" if di is not None else "", f"{st:,}" if st is not None else "", n(pw, 0) if pw is not None else "", basis]
        mtag = mode.split(" ")[0]
        a = [ann(pu, pup, f"{tag} {mtag} per user")]
        if isinstance(ag, list):
            a += [ann(ag[0], agp + "[0]", f"{tag} aggregate low"), ann(ag[1], agp + "[1]", f"{tag} aggregate high")]
        elif ag is not None:
            a.append(ann(round(ag), agp, f"{tag} {mtag} aggregate"))
        if di is not None:
            a.append(ann(di, dip, f"{tag} dies"))
            a.append(ann(st, stp, f"{tag} stacks"))
            a.append(ann(round(pw), pwp, f"{tag} power"))
        L.append("| " + " | ".join(cells) + " | " + " ".join(a))
    L += calibration_table(S, ann)
    gq, gd = G["qwen"], G["ds"]
    L += ["",
          f"The per-user rate is 1 / the critical-path latency of one token (or of one speculative step divided by τ). "
          f"The aggregate is a ceiling per instance. For the Qwen ROM it is the modelled tile-window bound. For the DeepSeek ROM it "
          f"is the pipeline bound: one position every stage interval, τ / 6 intervals with MTP. No batched calendar exists "
          f"for the HBM accelerator, so its aggregate is not composed. The Qwen3-8B rate on the generic HBM die comes from the "
          f"interface simulator at the measured SM issue rate. It is a pathfinding figure, and no token-path graph exists for it yet.",
          "",
          f"Best published GPU at batch 1: Qwen3-8B on one B200 with DFlash, **{n(gq['best_batch1']['value'], 0)}** tok/s "
          f"{ann(gq['best_batch1']['value'], 'gpu.qwen.best_batch1.value', 'GPU Qwen best batch 1')}; DeepSeek-V4.1-Flash on 4 × GB300 "
          f"with DSpark, **{n(gd['best_batch1']['value'])}** tok/s at a simulated acceptance of 5.5, which favours the GPU against "
          f"our τ of 4.159 {ann(gd['best_batch1']['value'], 'gpu.ds.best_batch1.value', 'GPU DS best batch 1')}. Compared like for "
          f"like (AR against AR), the same sources give Qwen3-8B on one B200 without speculation **{n(gq['ar_batch1']['value'], 0)}** "
          f"tok/s {ann(gq['ar_batch1']['value'], 'gpu.qwen.ar_batch1.value', 'GPU Qwen AR batch 1')} and DeepSeek-V4.1-Flash on "
          f"4 × GB300 without speculation **{n(gd['ar_batch1']['value'], 0)}** tok/s "
          f"{ann(gd['ar_batch1']['value'], 'gpu.ds.ar_batch1.value', 'GPU DS AR batch 1')}. Served today "
          f"(OpenRouter P50, 2026-10-09): Qwen3-8B **{n(gq['served_median']['value'], 0)}** tok/s "
          f"{ann(gq['served_median']['value'], 'gpu.qwen.served_median.value', 'served Qwen median')}, DeepSeek-V4.1-Flash median "
          f"**{n(gd['served_median']['value'])}** tok/s {ann(gd['served_median']['value'], 'gpu.ds.served_median.value', 'served DS median')}.",
          "",
          "Changes since the 2026-10-08 export:", ""]
    for c in S["changes"]:
        L.append(f"- **{c['item']}.** {c['effect'].replace(' -> ', ' → ')}.")
    L += ["", f"Capital cost per instance (assumed prices; `systems.json` `cost`): Qwen ROM "
          f"${q['cost']['capex_usd']['value'][0]:,}–{q['cost']['capex_usd']['value'][1]:,}; DeepSeek ROM "
          f"${d['cost']['capex_usd']['value'][0] / 1e6:,.2f}M–{d['cost']['capex_usd']['value'][1] / 1e6:,.2f}M; HBM accelerator "
          f"${hd['cost']['capex_usd']['value'][0] / 1e6:,.2f}M for DeepSeek (switches not priced) and "
          f"${hq['cost']['capex_usd']['value'][0]:,} for Qwen3-8B.", "", DOC_END]
    return "\n".join(L)


def write_doc(S):
    txt = DOC.read_text()
    sec = doc_section(S)
    if DOC_BEGIN in txt:
        a, b = txt.index(DOC_BEGIN), txt.index(DOC_END) + len(DOC_END)
        txt = txt[:a] + sec + txt[b:]
    else:
        anchor = "\n## 1. The two machines"
        i = txt.index(anchor)
        txt = txt[:i] + "\n" + sec + "\n" + txt[i:]
    DOC.write_text(txt)


def mtp_charge_changes():
    """the MTP block charges (tools/mtp_step_charges.py -> token_path_export.apply_mtp_charges), one change line"""
    out = []
    for key, name in (("ds_rom", "DS ROM"), ("hbm_ds", "HBM DS")):
        c = tp(f"{key}_mtp.json").get("mtp_charges")
        if c:
            out.append(f"{name} {c['MTP_tok_s_composed']:,} -> {tp(f'{key}_mtp.json')['totals']['tok_s_published']:,} tok/s "
                       f"(+{c['critical_cycles']:,.0f} cycles a step)")
    if not out:
        return []
    return [dict(item="MTP block cycles charged", effect="; ".join(out) + " (WFC kit, P2 selected path, sequencer, Markov floor, "
                 "hfd_mtp pins / FAST registers, spec state, fence, commit; per-charge critical / overlapped proof in the files)",
                 grade="measured", source="results/arch/mtp_step_20261009 (tools/mtp_step_charges.py)")]


def build_systems():
    E = econ_inputs()
    wall = J(RACK)["power"]["wall_factor"]
    q, d, h = qwen_rom(E, wall), ds_rom(E, wall), hbm(E, wall)
    G = gpu()
    S = dict(schema="opentallas.token_path.systems.v1", date=DATE, tool="tools/token_path_systems.py", clock_hz=CLK,
             grades=dict(measured="RTL bench / simulation / instrument record", derived="composed from measured records and priced "
                         "adders by an existing tool; or a count / sum of other fields", modelled="analytical model or pathfinding "
                         "simulator constants", assumed="a stated assumption (price, lifetime, switch power)", **{"third-party": "published "
                         "external figure (results/external/registry.json)"}),
             qwen_rom=q, ds_rom=d, hbm=h, gpu=G)
    S["headline"] = headline_rows(S, G)
    tp4 = json.loads((ROOT / "results/arch/token_path_20261008/qwen_rom.json").read_text())["totals"]["tok_s_published"]
    S["changes"] = [
        dict(item="Qwen KV die", effect=f"Qwen ROM per user {tp4:,} -> {q['per_user']['AR']['value']:,} tok/s "
             f"({q['per_user']['AR']['vs_tp4_single_die'] * 100:+.2f} %); pair {q['dies']['pair_mm2']['value']} mm2; 8 dies", grade="derived", source=KVD),
        dict(item="Engram tables in HBM", effect=f"DS ROM -{J(ENGRAM)['reprice_item']['dies']['table_dies_removed']} dies, "
             f"+{J(ENGRAM)['reprice_item']['dies']['stacks_added']} stacks, {d['power']['engram_delta_w']['value']:,} W; 0 cycles on the token path", grade="modelled", source=ENGRAM),
        dict(item="DS ROM array v2 (1,792 mapping, mtp-die P2 draft dies)", effect=f"{d['dies']['total']['value']} dies / "
             f"{d['dies']['stacks']['value']} stacks / {d['power']['chips_w']['value'] / 1e3:,.2f} kW chips (85-stage rack: 440 / 484 / 38.75)",
             grade="derived", source="tools/dsrom_array_v2.py"),
        dict(item="HBM generic die", effect=f"Qwen3-8B on r25 TP4 INT8: {h['targets'][1]['per_user']['AR']['value']} tok/s (pathfinding "
             f"simulator, SM-issue bound; one-beat INT8 {h['targets'][1]['per_user']['AR']['one_beat_int8']} rejected NO_FIT); DS uses the approved gather + G22 path; partial measured-unit sensitivity is recorded separately; DMA stays at full bandwidth", grade="modelled", source=f"{HQT}; {HAPP}; {HCA}"),
        dict(item="Qwen3-8B DFlash on the generic die", effect=f"block 16 {h['targets'][1]['per_user']['MTP']['value']} tok/s at the "
             "published tau 8.01 (one compiled step: draft + 2-pass verify + accept, bit-exact in hgi_sim; no hardware added; "
             "open: SM multi-slot issue G18, CTL.TOKX)", grade="modelled", source=HQD),
        dict(item="BF decision", effect="full-rate BF closure pending; HALF_PHL stays the headline, full-rate rows in ds_rom.bf_variants", grade="derived", source=REPRICE),
        *mtp_charge_changes(),
        dict(item="replica-fold / keep fixes", effect="0 cycles (synthesis attribute only: (* keep *) copies survive opt_merge)",
             grade="measured", source="main 0d3958d56, 816a3bec0, 54e3f8f9c"),
        dict(item="GPU baselines", effect="DS: SGLang V4.1-Flash 4 x GB300 + DSpark 873.6 (was V4-Pro 383.7); Qwen: B200 + DFlash 1,175; "
             "OpenRouter medians DS 88.5 / Qwen 55", grade="third-party", source=REG),
    ]
    S["pending"] = [
        "BF full-rate closure: switch the DS ROM headline to the chosen BF row and re-run this tool",
        "KV-die stream: GRT / STA of the ROM r22k and KV die (chain on EPYC1); the near-HBM attention elements are not closed",
        "HBM forks: fmt3 adapter bypass match, sequencer C2 measured costs; one-beat INT8 closed (NO_FIT)",
        "Qwen-HBM DFlash: SM multi-slot issue (G18, hbm-forks) and CTL.TOKX (cmdproc); a qwen_hbm token-path graph",
        "DS ROM 1,792 power pass (per-die W is the busiest saturated die for every die)",
        "HBM accelerator batch / union / credit calendar (no aggregate is composed)",
    ]
    ins = sorted({KVD, KVROM, KVPLAN, TP8, ENGRAM, REPRICE, ES, ECON, ARCH, RACK, REG, HQT, HQP, HQD, HDT, HCA, HAPP,
                  "results/arch/token_path_20261008/qwen_rom.json"})
    S["inputs"] = {p: sha(p) for p in ins}
    (OUT / "systems.json").write_text(json.dumps(S, indent=1) + "\n")
    idx = json.loads((OUT / "index.json").read_text())
    idx["systems"] = "systems.json"
    idx["date"] = DATE
    (OUT / "index.json").write_text(json.dumps(idx, indent=1) + "\n")
    (OUT / "README.md").write_text(readme(S))
    for r in S["headline"]:
        print(f"{r['target']:32s} {r['model']:24s} {r['mode']:4s} per-user {r['per_user']:>9,} agg {fmt(r['aggregate'], 0):>14s} "
              f"dies {r['dies']:>4} stacks {r['stacks']:>4} W {fmt(r['power_w'], 0):>9s} capex {fmt(r['capex'], 0)}")
    return S


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--systems-only", action="store_true")
    ap.add_argument("--no-doc", action="store_true", help="do not rewrite the generated section of docs/ANALYTICAL_REPORT.md")
    a = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    if not a.systems_only:
        export_graphs(OUT)
    S = build_systems()
    if not a.no_doc:
        write_doc(S)


if __name__ == "__main__":
    main()
