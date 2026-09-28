#!/usr/bin/env python3
"""The best HBM comparator on its REAL fabric -- an NVL72-class switched NVLink domain -- and the ROM:HBM rate and
energy ratios against it.  Model work only; imports tools/arch_hbm_best_v41.py (graph at tensor group G) and the
ROM design point of tools/arch_lanes_v41.py (results/arch/v41_lanes.json).

    python3 tools/arch_hbm_switched_v41.py [--out results/arch/v41_hbm_switched.json]

Fabric (spec agent's request, 2026-09-27; closes the asymmetry that the comparator's collectives were on the board
mesh with overlapped bytes while the ROM array's are on its real 112G lanes):

* every comparator die is an endpoint of one switch tier; a traversal is SerDes -> switch -> SerDes:
  alpha = 2 x 209 ns (technology.json links.rom_rack_cable_serdes: full KP4 over rack cable, validated 2026-09-27;
  the same hop the ROM array's stage links use) + 250 ns (one cut-through tier) = 668 ns;
* each die's link to the switch carries 1.8 TB/s per direction (the spec agent's figure, "B200 NVLink"; note B200's
  published 1.8 TB/s is the bidirectional total, 0.9 TB/s per direction -- priced as a sensitivity);
* a collective's bytes cross the die's ONE switch link: one-shot all-reduce (p - 1) n, two-step (reduce-scatter +
  all-gather, fixed order) 2 (p - 1) / p n at two traversals, all-gather (p - 1) / p n; the faster per collective;
  in-switch reduction (NVLS/SHARP: one traversal, n bytes) is a sensitivity, not the baseline;
* stage hops and the token return are one traversal plus the payload on the die link;
* bytes overlap their producer only where the DAG allows (the same rule as the ROM side);
* static power on the validated inputs (U.static_terms): logic leakage 0.10 W/mm2 x 628 mm2, 4 stacks x 2.8 W,
  UCIe idle, and the SerDes lanes that carry the package's link (0.9 TB/s per direction = 68 lanes x 0.728 W, 6.5
  pJ/b), shared by its 2 dies;
* switches on BOTH machines (spec ruling): NVL72's NVSwitch trays at 1.5 kW each (ASSUMED) scaled to the
  comparator's 50 packages by port capacity, and the ROM rack's one off-path switch on the same W per Tb/s; then
  both machines' chip + switch power through the same wall chain (technology.json power.rack_overheads).
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import arch_hbm_best_v41 as HB  # noqa: E402
import arch_lanes_v41 as LN  # noqa: E402

LX, U, A, D = HB.LX, HB.U, HB.A, HB.D
SCHEMA = "opentallas.v41-hbm-switched.v1"
OUT = ROOT / "results/arch/v41_hbm_switched.json"
CONTEXTS = LX.CONTEXTS
GROUPS = (4, 8, 16, 24, 32, 48, 64, 96)
SW_S = D.SWITCH_LATENCY_S["value"]
LANE_NET = LN.LANE_NET_BPS


class SwitchFabric:
    """One NVLink switch tier; the endpoints are 2-die PACKAGES (a B200-class GPU is 2 dies behind one NVLink port
    set).  A collective over p dies = an in-package step on UCIe (10 ns) + a switched step among q = p / 2 packages
    on the package's link + the in-package broadcast."""
    board = "switch"
    refused = None
    DIES_PER_PKG = 2
    DOMAIN_PKGS = 72                                   # NVL72: 72 GPUs (packages) on one switch tier

    def __init__(self, G, dies, B_pkg=0.9e12, nvls=True):
        self.G, self.dies, self.B, self.nvls = G, dies, B_pkg, nvls
        lk = A.links_for(A.BASELINE)
        # a switched traversal is over rack cable: 2 x the rack-cable SerDes hop (209 ns, full KP4) + the switch
        self.hop_s = (lk["rom_rack_cable_serdes"] if "rom_rack_cable_serdes" in lk else lk["rom_board_serdes"])["hop"]
        self.ucie = lk["rom_package_ucie"]["hop"]
        self.ucie_bw = lk["rom_package_ucie"]["bw"]
        self.alpha = 2 * self.hop_s + SW_S
        if math.ceil(dies / self.DIES_PER_PKG) > self.DOMAIN_PKGS:
            self.refused = "more packages than one NVL72 domain"

    def label(self):
        return (f"switched NVLink domain ({self.B / 1e12:.1f} TB/s per package per direction"
                f"{', NVLS' if self.nvls else ''}; alpha {self.alpha * 1e9:.0f} ns)")

    def collective(self, op, n, span, algorithm=None):
        p = span
        if p <= 1:
            return dict(latency_s=0.0, bytes_s=0.0, algo="none", where="")
        q = math.ceil(p / self.DIES_PER_PKG)
        a, B, l1 = self.alpha, self.B, self.ucie
        pk = n / self.ucie_bw
        if q <= 1:
            return dict(latency_s=(2 if op == "all_reduce" else 1) * l1, bytes_s=pk, algo="in_package", where="")
        if op == "all_reduce":
            cands = [("one_shot", 2 * l1 + a, (q - 1) * n / B + pk),
                     ("two_step", 2 * l1 + 2 * a, 2 * (q - 1) / q * n / B + pk)]
            if self.nvls:
                cands.append(("nvls_in_switch", 2 * l1 + a, n / B + pk))
        else:
            cands = [("one_shot", l1 + a, (q - 1) / q * n / B + pk)]
        algo, lat, byt = min(cands, key=lambda x: x[1] + x[2])
        return dict(latency_s=lat, bytes_s=byt, algo=algo, where=f"{q} packages on one switch tier: {algo}")

    def hop(self, kind, payload, stage=None):
        return dict(latency_s=self.alpha, bytes_s=payload / self.B, link="switch traversal")

    def combine_a2a(self, v, m, kmax, span):
        raise NotImplementedError


def serdes_w_per_die(B_pkg):
    """Always-on lanes that carry B_pkg per direction on a 2-die package, at the ROM array's 0.56 W per lane."""
    return B_pkg / LANE_NET * LN.LANE_W / SwitchFabric.DIES_PER_PKG


def run(cfg, sp, muts, hz, hb, hbm, static_die_w):
    HB.FABRIC = lambda G, dies: SwitchFabric(G, dies, **cfg)
    out = {}
    for ctx in CONTEXTS:
        grid = []
        for G in GROUPS:
            mu = HB.rung_muts(G, muts)
            ar = HB.evaluate_g(sp, ctx, G, hbm, 1, False, 1, U.CHAIN_L3, mu, hz)
            row = dict(G=G, stages=ar["stages"], ar=ar["tokens_s_per_user"],
                       breakdown_us={k: round(v, 2) for k, v in ar["breakdown_us"].items()})
            for m in HB.LANE_MULTS:
                row[f"mtp_m{m}"] = HB.evaluate_g(sp, ctx, G, hbm, 1, True, m, U.CHAIN_L3, mu, hz)["tokens_s_per_user"]
            grid.append(row)
        ba = max(grid, key=lambda r: r["ar"])
        bm, mm = max(((r, m) for r in grid for m in HB.LANE_MULTS), key=lambda x: x[0][f"mtp_m{x[1]}"])
        out[str(ctx)] = dict(grid=grid, best_ar=dict(G=ba["G"], rate=ba["ar"]),
                             best_mtp=dict(G=bm["G"], m=mm, rate=bm[f"mtp_m{mm}"]))
    HB.FABRIC = None
    return out


def _cooling_2die():
    """Per-die cooling limit of a two-die package by class (air / liquid), from the sourced power scenarios."""
    import power_scenarios as PS
    lim = PS.cooling_limits(PS.load_cfg())
    return {cls: v["2"]["die_w"] for cls, v in lim.items()}


def build():
    E = A._env()
    c = E["c"]
    hb = U.hbm_comparator(c)
    hbm = dict(bw_Bps=hb["bw_Bps"], lat_s=hb["lat_s"], dies=hb["dies"])
    base = U.unified(U.req_spec())
    adopted = {r["key"] for r in json.loads((ROOT / "results/arch/v41_latency_ladder.json").read_text())["ladder"]
               if r["adopted"]}
    LX.LADDER[:] = [(k, lab, kind if k in adopted else "none", pay, f) for k, lab, kind, pay, f in LX.LADDER]
    sp, muts, hz = LX.rung_spec(base, len(LX.LADDER))
    lanes = json.loads((ROOT / "results/arch/v41_lanes.json").read_text())
    hbrec = json.loads((ROOT / "results/arch/v41_hbm_best.json").read_text())
    ST = U.static_terms(hb)
    die_static_noserdes = ST["hbm_die_no_serdes"]      # leakage 0.10 W/mm2 x logic + stacks + UCIe idle
    rec = dict(schema=SCHEMA, tool="tools/arch_hbm_switched_v41.py", basis=__doc__.split("Fabric (")[1].strip(),
               alpha_s=SwitchFabric(4, hb["dies"]).alpha, dies=hb["dies"])
    cfgs = dict(nvl_0p9_nvls=dict(B_pkg=0.9e12, nvls=True), nvl_0p9=dict(B_pkg=0.9e12, nvls=False),
                nvl_1p8_nvls=dict(B_pkg=1.8e12, nvls=True), nvl_1p8=dict(B_pkg=1.8e12, nvls=False))
    rec["configs"] = {k: run(v, sp, muts, hz, hb, hbm, None) for k, v in cfgs.items()}
    rec["headline_config"] = "nvl_0p9_nvls"
    # the board-mesh comparator of v41_hbm_best, for comparison
    rec["board_mesh_was"] = {str(ctx): hbrec["rungs"]["top"]["hbm"][str(ctx)] for ctx in CONTEXTS}
    # energy at the baseline switched config: every operating point, the best G per (AR, MTP)
    main = rec["configs"]["nvl_0p9_nvls"]
    HB.FABRIC = lambda G, dies: SwitchFabric(G, dies, B_pkg=0.9e12, nvls=True)
    s_die = die_static_noserdes + serdes_w_per_die(0.9e12)
    rec["hbm_static_w_per_die"] = dict(total=s_die, serdes=serdes_w_per_die(0.9e12),
                                       leakage_hbm_ucie=die_static_noserdes, serdes_at_1p8=serdes_w_per_die(1.8e12))
    npkg = math.ceil(hb["dies"] / 2)
    hbm_switch_w = npkg * 0.9e12 * 8 * 2 / 1e12 * ST["switch_w_per_tbps"]
    rom_switch_w = lanes["static_w"]["rom_switch_w"]
    wall = ST["wall"]
    rec["switches_and_wall"] = dict(hbm_switch_w=hbm_switch_w, rom_switch_w=rom_switch_w, wall_factor=wall,
                                    hbm_chip_static_w=s_die * hb["dies"], rom_chip_static_w=lanes["static_w"]["rom_total"],
                                    basis=lanes["static_w"]["switch_basis"] + "; NVL72 trays scaled to the "
                                          f"comparator's {npkg} packages (ASSUMED 1.5 kW a tray); both machines' chip "
                                          "and switch power go through the same wall chain (1/(VR x PSU) x (1 + CDU "
                                          "+ fans))")
    rec["domain"] = dict(packages=math.ceil(hb["dies"] / 2), nvl72_packages=SwitchFabric.DOMAIN_PKGS,
                         fits_one_tier=math.ceil(hb["dies"] / 2) <= SwitchFabric.DOMAIN_PKGS,
                         note="99 dies are 50 two-die packages (GPUs), inside one NVL72 domain of 72; G = 96 dies is "
                              "48 packages: no second switch tier is needed")
    energy = {}
    for ctx in CONTEXTS:
        rows = {}
        for ptag, bt in HB.POINTS:
            for mtp in (False, True):
                k = ptag + ("_mtp" if mtp else "")
                best = main[str(ctx)]["best_mtp" if mtp else "best_ar"]
                G, m = best["G"], (best.get("m") if mtp else 1)
                h = HB.evaluate_g(sp, ctx, G, hbm, bt, mtp, m, U.CHAIN_L3, HB.rung_muts(G, muts), hz)
                h.update(batch=bt, mtp=mtp)
                e = HB.energy_point(sp, ctx, h, hb["dies"], h["stages"], LX.area(sp, m if mtp else 1),
                                    s_die * hb["dies"], hbm=hbm, m=m)
                r = lanes["energy"][str(ctx)][k]["rom"]
                h_sw = hbm_switch_w / h["aggregate_tokens_s"]
                r_sw = rom_switch_w / r["aggregate_tokens_s"]
                h_wall = (e["total_j"] + h_sw) * wall
                r_wall = (r["total_j"] + r_sw) * wall
                rows[k] = dict(hbm=dict(G=G, m=m if mtp else None, tokens_s_per_user=h["tokens_s_per_user"],
                                        aggregate_tokens_s=h["aggregate_tokens_s"], switch_j=h_sw, wall_j=h_wall, **e),
                               rom=dict(tokens_s_per_user=r["tokens_s_per_user"],
                                        aggregate_tokens_s=r["aggregate_tokens_s"], total_j=r["total_j"],
                                        dynamic_j=r["dynamic_j"], static_j=r["static_j"], switch_j=r_sw,
                                        wall_j=r_wall),
                               ratio_rate_per_user=r["tokens_s_per_user"] / h["tokens_s_per_user"],
                               ratio_aggregate=r["aggregate_tokens_s"] / h["aggregate_tokens_s"],
                               ratio_energy_with_static=h_wall / r_wall,
                               ratio_energy_chip_only=e["total_j"] / r["total_j"])
        energy[str(ctx)] = rows
    HB.FABRIC = None
    rec["energy"] = energy
    # cross-check: the comparator's modelled chip power per 2-die package against B200's published figures
    gpu = E["tech"]["power"].get("gpu_reference_power", {})
    chk = {}
    for k, v in energy["1048576"].items():
        h = v["hbm"]
        chip_w = h["total_j"] * h["aggregate_tokens_s"]
        chk[k] = dict(chip_w_per_package=chip_w / npkg, wall_w_per_package=(chip_w + hbm_switch_w) * wall / npkg)
    rec["gpu_crosscheck"] = dict(modelled_1M=chk, reference={kk: (vv.get("value") if isinstance(vv, dict) else vv)
                                                             for kk, vv in gpu.items() if kk not in ("purpose",)},
                                 note="a check only: the comparator stays modelled (its engines, HBM and SerDes), not "
                                      "scaled to a GPU's measured draw")
    # the ROM design point's worst-case die (saturated, MTP m = 2, the R-L8 pools doubled)
    dyns = {}
    for ctx in CONTEXTS:
        for k in ("sat1024", "sat1024_mtp"):
            r = lanes["energy"][str(ctx)][k]["rom"]
            dyns[f"{ctx}/{k}"] = r["dynamic_j"] * r["aggregate_tokens_s"] / U.LAYER_DIES
    worst_key = max(dyns, key=dyns.get)
    dyn_die = dyns[worst_key]
    worst = lanes["static_w"]["layer_die"] + dyn_die
    rec["rom_worst_die_w"] = dict(static_w=lanes["static_w"]["layer_die"], dynamic_w=dyn_die, worst_point=worst_key,
                                  dynamic_w_by_point=dyns, total_w=worst,
                                  cooling_limit_w=_cooling_2die(),
                                  cooling_basis="configs/hardware/power_scenarios.json cooling classes, 2-die packages "
                                                "(tools/power_scenarios.cooling_limits: per-die W, air / liquid)",
                                  provisioned_wall_w=1.2 * worst * wall,
                                  basis="max over saturation without and with MTP at the design point (R-L8 pools "
                                        "doubled, m = 2): the array's dynamic energy per token x its rate over the "
                                        "112 layer dies, plus the static die. No separate HBM-interface active term: "
                                        "the dynamic energy charges every HBM byte at the system-level 13 pJ/b, which "
                                        "contains the I/O (adae6788's ruling); the interface idle is in the static "
                                        "98.8 W")
    rec["rom_design_point"] = lanes["design_point"]
    rec["ratios_batch1"] = {
        str(ctx): {k: dict(rom=lanes["design_point"][str(ctx)]["ar" if k == "ar" else "mtp"],
                           hbm=v[str(ctx)]["best_ar" if k == "ar" else "best_mtp"]["rate"],
                           ratio=lanes["design_point"][str(ctx)]["ar" if k == "ar" else "mtp"]
                           / v[str(ctx)]["best_ar" if k == "ar" else "best_mtp"]["rate"])
                   for k in ("ar", "mtp") for v in [rec["configs"]["nvl_0p9_nvls"]]}
        for ctx in CONTEXTS}
    for r in rec["ratios_batch1"].values():   # what MTP buys each machine at batch 1 (with / without, same machine)
        r["mtp_speedup"] = {m: r["mtp"][m] / r["ar"][m] for m in ("rom", "hbm")}
    # replicate-on-write KV to reader stages (spec requirement) on R-L9's stage lanes
    cS = c
    src = cS["kv_source_layer_ids"]
    readers = {}
    for L in range(cS["num_layers"]):
        r = cS["compress_ratios"][L]
        if r and L not in src:
            s_ = max(s for s in src if s <= L) if any(s <= L for s in src) else None
            if s_ is not None:
                readers.setdefault(s_, set()).add(L)
    plan = A.dag_machine(1).hop_plan
    per_token = 0.0
    rows = {}
    for s_, Ls in readers.items():
        groups = {plan[L][0] for L in Ls} - {plan[s_][0]}
        b_row = A.CKV_ROW_B + A.IDX_KEY_B
        per_token += len(groups) * b_row
        rows[f"L{s_}"] = dict(reader_groups=len(groups), bytes_per_token=len(groups) * b_row)
    stage_Bps = 2 * lanes["best_split"]["stage"] * LANE_NET
    sat = max(v["rom"]["aggregate_tokens_s"] for v in lanes["energy"]["1048576"].values())
    rec["kv_replicate_on_write"] = dict(
        by_source=rows, bytes_per_token_upper=per_token, residual_hop_bytes_per_token=41000,
        stage_link_Bps_per_group=stage_Bps, worst_aggregate_tokens_s=sat,
        link_load_fraction=(per_token + 41000) * sat / stage_Bps,
        batch1_write_time_s=per_token / stage_Bps,
        note="upper bound: every source layer's new compressed row + index key (288 + 68 B) written to each distinct "
             "reader group, all on one stage link (store-and-forward along the ring); off the critical path (the "
             "readers need it from the next token on)")
    return rec


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", type=Path, default=OUT)
    a = ap.parse_args()
    rec = build()
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(rec, indent=1, default=lambda o: None) + "\n")
    for k, v in rec["configs"].items():
        for ctx, r in v.items():
            print(k, ctx, "best", r["best_ar"], r["best_mtp"],
                  [(g["G"], round(g["ar"]), round(g["mtp_m6"])) for g in r["grid"]])
    print("board mesh was", rec["board_mesh_was"])
    print("ratios b1", rec["ratios_batch1"])
    for ctx, rows in rec["energy"].items():
        for k, v in rows.items():
            print(ctx, k, f"rom {v['rom']['wall_j'] * 1e3:.1f} hbm {v['hbm']['wall_j'] * 1e3:.1f} (wall) "
                          f"x{v['ratio_energy_with_static']:.2f} rate x{v['ratio_rate_per_user']:.2f} "
                          f"agg x{v['ratio_aggregate']:.2f}")
    print("kv", {k: v for k, v in rec["kv_replicate_on_write"].items() if k != "by_source"})


if __name__ == "__main__":
    main()
