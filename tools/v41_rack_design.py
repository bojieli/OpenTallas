#!/usr/bin/env python3
"""DeepSeek-V4.1-Flash ROM array: logical map, link topology and physical rack (one model replica per rack).

Analytical design, no simulation.  Inputs are the committed spec records; every physical constant carries a
published source (PHYS below) or is marked ESTIMATE with its basis.

  logical   188 dies -> role, stage, tensor group, package, stage module, tray, rack unit
  traffic   per-token bytes and messages per link class, at batch 1 and at the 28-user pipeline fill
  links     five tiers (UCIe, on-module trace, in-rack cable, switch, out-of-rack optics): reach, latency,
            bandwidth, lanes per package; every link's length is derived from the elevation and checked
            against its reach class and the modelled 130 ns hop
  physical  package, stage module, tray, rack elevation, power (static + dynamic + HBM + SerDes) at batch 1,
            fill and saturation, power shelves, cooling, weight estimate
  compare   GB200 NVL72 and Huawei CloudMatrix384 (published figures)
  conflicts every place where a spec assumption meets a physical limit

Output: results/arch/v41_rack.json and the figure snippets under results/arch/figures/ (tools/v41_rack_figures.py).
Tested by tests/test_v41_rack_design.py.
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

BUDGET = ROOT / "results/arch/arch_budget_v41.json"
UTIL = ROOT / "results/arch/v41_utilization.json"
HBM_BEST = ROOT / "results/arch/v41_hbm_best.json"
LADDER = ROOT / "results/arch/v41_latency_ladder.json"
V41_CONFIG = ROOT / "configs/models/candidates/deepseek-v4.1-flash.json"
TECH = ROOT / "configs/hardware/technology.json"
OUT = ROOT / "results/arch/v41_rack.json"
PLACEMENT = ROOT / "results/arch/v41_die_placement.json"

CTX = 1048576                 # primary context (user decision 2026-09-27)
FILL = 28                     # pipeline-fill batch: one user per stage keeps the batch-1 rate
DIES, PKG_DIES, G = 188, 2, 4
STAGES = 28
POSITIONS, TAU = 6, 5.0          # DSpark verify pass: 6 positions, 5.0 accepted tokens (spec headline)
INGEST_NICS, NIC_BPS = 2, 50e9   # two 400G NICs on the host tray (prefill KV ingest), 50 GB/s each
HBM_STACKS_PER_LAYER_DIE = 4
SHELVES_PER_SIDE = 3              # 2N: side A carries the provisioned load on its shelves (N+1 inside each), B mirrors
PROVISION_MARGIN = 1.2            # spec agent: provision at 1.2 x worst case / (VR x PSU)  # user rule 2026-09-27: 8 per two-die package (B200/B300 class)

# ---------------------------------------------------------------------------------------------------------
# Physical constants.  grade: published (a vendor/standard figure), derived (arithmetic on published figures),
# spec (from this repo's committed spec records), estimate (engineering estimate with the basis stated).
# ---------------------------------------------------------------------------------------------------------
PHYS = {
    # ---- links -----------------------------------------------------------------------------------------
    "ucie_advanced_reach_mm": dict(value=2.0, grade="published",
        source="UCIe electrical summary: advanced package channel reach <= 2 mm (25-55 um bump pitch, 165-1,317 GB/s/mm)",
        url="https://www.hc2023.hotchips.org/assets/program/tutorials/ucie/Electrical%20Form%20Factor%20and%20Compliance.pdf"),
    "ucie_standard_reach_mm": dict(value=25.0, grade="published",
        source="UCIe electrical summary: standard package reach <= 25 mm (28-224 GB/s/mm)", url="https://www.hc2023.hotchips.org/assets/program/tutorials/ucie/Electrical%20Form%20Factor%20and%20Compliance.pdf"),
    "ucie_latency_ns": dict(value=2.0, grade="published",
        source="UCIe PHY latency target (TX+RX) 12-16 UI (~0.75 ns at 16 GT/s); adapter included the spec charges 10 ns per hop",
        url="https://www.hc2023.hotchips.org/assets/program/tutorials/ucie/Electrical%20Form%20Factor%20and%20Compliance.pdf"),
    "ucie_link_Bps": dict(value=4.2e12, grade="spec", source="configs/hardware/technology.json links.rom_package_ucie.bytes_s"),
    "ucie_hop_s": dict(value=10e-9, grade="spec", source="technology.json links.rom_package_ucie.hop_latency_s (PHY+adapter+on-die routing)"),
    "lane_gbps": dict(value=112.0, grade="published", source="112G PAM4 SerDes class (OIF CEI-112G; IEEE 802.3ck 100 Gb/s per lane)",
        url="https://www.oiforum.com/wp-content/uploads/00311c-OIF-112G-OFC-slides_ofc20_presentation.pdf"),
    "lane_net_fraction": dict(value=(514 / 544) * (256 / 257), grade="derived",
        source="RS(544,514) and 256b/257b transcoding (IEEE 802.3 100 Gb/s per lane PHYs); technology.json rom_board_serdes"),
    "lanes_per_package": dict(value=90, grade="spec",
        source="technology.json links.rom_board_serdes.bytes_s note: 128 lanes for a four-die package scaled by sqrt(2/4) -> 90 for two dies"),
    "hop_s": dict(value=130e-9, grade="spec", band=(100e-9, 170e-9),
        source="committed baseline, light (reduced-interleave) FEC package link: 121 ns channel + 4 CDC + 5 endpoint cycles "
               "(worktree-agent-a6155059c72eb0abd configs/hardware/technology.json links.rom_board_serdes.hop_latency_s)"),
    "hop_full_kp4_s": dict(value=209e-9, grade="spec", source="same entry, full_kp4_fec_s (plain option (b))"),
    "hop_flight_included_m": dict(value=0.3, grade="spec",
        source="technology.json latency_components_s: the 200/121 ns channel includes ~0.3 m of board flight"),
    "pcb_ns_per_m": dict(value=6.7, grade="published",
        source="stripline ~170 ps/in = 6.7 ns/m (FR-4 class; low-loss laminates Dk 3.3-3.7 are slightly faster)",
        url="https://www.protoexpress.com/blog/signal-propagation-delay-pcb/"),
    "twinax_ns_per_m": dict(value=4.6, grade="published",
        source="Broadcom SUE spec RM104 (2025-09-26) App. A Fig. 22: twinax 4.6 ns per m (Samtec 30 AWG 4.79; Belden "
               "4.3-5.1) -- sync/power validation (research agent adae6788, branch worktree-agent-adae6788cbf2f3f86, technology.json quotes)",
        url="https://suddendocs.samtec.com/notesandwhitepapers/tx-30100-fep-01_datasheet.pdf"),
    "dac_112g_reach_m": dict(value=2.0, grade="published",
        source="IEEE P802.3ck objectives: twinax (CR) lengths up to at least 2 m; backplane (KR) insertion loss <= 28 dB at "
               "26.56 GHz; RS(544,514) FEC mandatory for CR1/KR1",
        url="https://www.ieee802.org/3/ck/P802_3ck_Objectives_2018mar.pdf"),
    "dac_800g_cr8": dict(value=8, grade="published",
        source="IEEE 802.3df 800GBASE-CR8: 8 lanes of 100G PAM4 over passive twinax (OSFP/QSFP-DD 800G DAC), <= 2 m "
               "class; a stage link of 14 lanes rides two such cables per package per ring neighbour",
        url="https://www.ieee802.org/3/df/"),
    "aec_112g_reach_m": dict(value=7.0, grade="published",
        source="Credo 800G AEC (8 x 100G PAM4): 4.0-7.0 m, typ. 10 W per cable",
        url="https://credosemi.com/wp-content/uploads/Credo_AEC_800G_SPAN_O_O_RHS_Product_Brief_2025Sept26.pdf"),
    "aec_added_latency_ns": dict(value=(3, 90), grade="published/estimate",
        source="Point2 P1B121 AEC retimer 3 ns (analog) vs DSP PAM4 retimers ~20x more (~60 ns); an FEC-terminating retimer "
               "adds one more KP4 decode (~100 ns). Not needed in this design.",
        url="https://www.businesswire.com/news/home/20241118930122/en/"),
    "board_trace_budget_mm": dict(value=(50, 120, 1000), grade="published",
        source="OIF CEI-112G: XSR up to 50 mm (6-10 dB, 'Lite FEC'); VSR >= 10 cm host trace + 1 connector (16 dB at 29 GHz, "
               "pre-FEC BER <= 1e-6); MR 20 dB at 28 GHz; LR 100 cm over 1-2 connectors (28 dB, FEC to BER 1e-4)",
        url="https://www.oiforum.com/wp-content/uploads/00311c-OIF-112G-OFC-slides_ofc20_presentation.pdf"),
    "serdes_pj_per_bit": dict(value=6.5, grade="published", band=(5.6, 7.5),
        source="5.6 pJ/b per lane incl. analog and DSP at 112 Gb/s (5 nm, VLSI 2022); 7 nm LR 602 mW per channel "
               "excluding DSP (JSSC 2021); conservative production value 6.5 -- sync/power validation (research agent adae6788, branch worktree-agent-adae6788cbf2f3f86, technology.json quotes). Was 5 (assumed)."),
    "switch_latency_s": dict(value=250e-9, grade="published",
        source="Broadcom Tomahawk Ultra (shipping July 2025): 250 ns switch latency at full 51.2 Tb/s; sub-400 ns XPU-to-XPU "
               "with SUE including switch transit; headers down to 10 B",
        url="https://www.globenewswire.com/news-release/2025/07/15/3115637/19933/en/Broadcom-Ships-Tomahawk-Ultra-Reimagining-the-Ethernet-Switch-for-HPC-and-AI-Scale-up.html"),
    "switch_capacity_tbps": dict(value=51.2, grade="published", source="Tomahawk Ultra",
        url="https://www.globenewswire.com/news-release/2025/07/15/3115637/19933/en/Broadcom-Ships-Tomahawk-Ultra-Reimagining-the-Ethernet-Switch-for-HPC-and-AI-Scale-up.html"),
    "switch_tray_w": dict(value=1500.0, grade="assumed",
        source="no primary source (validation, adae6788): a 51.2 Tb/s switch ASIC ~500-550 W, a 1-2 RU DAC-port system "
               "~1-1.5 kW assumed"),
    "ualink_fec": dict(value="RS(544,514), 1-way/2-way interleave", grade="published",
        source="UALink 1.0: 'lower latency via 1-way and 2-way code word interleave'; 640-B flit = one RS(544,514) codeword; "
               "cable length < 4 m; request-to-response RTT < 1 us",
        url="https://ualinkconsortium.org/wp-content/uploads/2025/04/UALink-1.0-White_Paper_FINAL.pdf"),
    "kp4_fec_latency_ns": dict(value=198, grade="published",
        source="Credo IEEE 802.3cd contribution: RS(544,514) KP4 ~198 ns, RS(272,257) ~99 ns (50GE); Clause 91 RS-FEC budget "
               "409.6 ns tx+rx at 100G",
        url="https://www.ieee802.org/3/cd/public/adhoc/archive/sun_030216_50GE_NGOATH_adhoc.pdf"),
    "cable_hop_s": dict(value=209e-9, grade="published", band=(160e-9, 300e-9),
        source=("ring/stage cable hop: full-strength RS(544,514) KP4, un-interleaved -- UALink 1.0's in-rack mode "
                "(640-B flit = one RS(544,514) codeword, cables < 4 m); IEEE 802.3ck mandates RS(544,514) for CR1; an "
                "RS(272)-class light FEC is not qualified on CR copper (ETC LL-FEC spec 1.0 Annex A Table 1: pre-FEC "
                "BER <= 9.9e-5 random, 8.9e-9 under DFE bursts). Cable flight added on top. -- sync/power validation (research agent adae6788, branch worktree-agent-adae6788cbf2f3f86, technology.json quotes). Was 130 ns."),
        url="https://ualinkconsortium.org/wp-content/uploads/2025/04/UALink-1.0-White_Paper_FINAL.pdf"),
    "logic_leak_w_per_die": dict(value=56.0, grade="published",
        source="0.10 W/mm2 of logic: H100 71.8 W idle over 814 mm2, TPUv4i 55 W on < 400 mm2 (7 nm) -- sync/power validation (research agent adae6788, branch worktree-agent-adae6788cbf2f3f86, technology.json quotes). Was 33.5 "
               "(N5 analytical); non-layer dies scaled by the same ratio"),
    "mac_pj_per_op": dict(value=dict(fp4=0.052, fp8=0.13, bf16=0.41, fp32=1.18), grade="published",
        was=dict(fp4=0.023, fp8=0.054, bf16=0.33, fp32=1.09),
        source="Keller (FP4 at nominal 0.67 V, 38.7 TOPS/W); Jouppi ISCA 2021 Table 2 x0.7 to N5 -- sync/power validation (research agent adae6788, branch worktree-agent-adae6788cbf2f3f86, technology.json quotes)"),
    "cdu_fraction": dict(value=0.006, grade="published",
        source="CoolIT CHx2000: 12.24 kW per 2,000 kW of IT -- sync/power validation (research agent adae6788, branch worktree-agent-adae6788cbf2f3f86, technology.json quotes) (facility-side, reported beside the rack input)"),
    "fan_fraction": dict(value=0.03, grade="assumed", source="fans 'a few percent' of IT; 3% assumed -- sync/power validation (research agent adae6788, branch worktree-agent-adae6788cbf2f3f86, technology.json quotes)"),
    "ethernet_hop_s": dict(value=209e-9, grade="spec",
        source="an Ethernet port runs the full RS(544,514) FEC (IEEE 802.3ck/df): the full-KP4 hop, technology.json full_kp4_fec_s"),
    # ---- package / board / rack -----------------------------------------------------------------------
    "die_mm": dict(value=(25.6, 31.8), grade="spec", source="technology.json reticle.area_mm2 815 (Taalas HC1), 25.6 x 31.8 mm"),
    "hbm3e_footprint_mm": dict(value=(11.0, 11.0), grade="published",
        source="Micron HBM3E cube 11 x 11 mm (product brief, via search summary); 1,024 I/O, > 1.2 TB/s per placement",
        url="https://www.micron.com/products/memory/hbm/hbm3e"),
    "hbm3e_stack_GB": dict(value=36, grade="published", source="Micron HBM3E 12-high 36 GB; >1.2 TB/s per stack",
        url="https://www.micron.com/products/memory/hbm/hbm3e"),
    "hbm3e_stack_static_w": dict(value=2.8, grade="spec", band=(1.2, 6.4), source="results/arch/v41_utilization.json energy_with_static.stack_w"),
    "package_mm": dict(value=(85.0, 85.0), grade="estimate",
        source="two ~815 mm2 dies + 8 HBM3E on a ~3.3-reticle CoWoS-L interposer (TSMC today: '3.3x reticle ... eight HBM "
               "stacks'); TSMC's 5.5x-reticle interposer 'requires a substrate measuring 100x100mm', so a 3.3x package is "
               "below 100 x 100 mm; 85 x 85 mm drawn. B200 substrate dimensions are not published",
        url="https://www.3dincites.com/2024/12/iftle-615-tsmc-evolves-cowos-technology-promising-9x-reticle-size-by-2027/"),
    "orv3_ou_mm": dict(value=48.0, grade="published", source="Open Rack: OpenU = 48 mm; 21-inch (533 mm) equipment bay; 48 V DC busbar",
        url="https://en.wikipedia.org/wiki/Open_Rack"),
    "orv3_usable_ou": dict(value=44, grade="published", source="ORv3 racks are built at 44 OU (e.g. ATEN RC8000); NVL72's MGX rack is 2,236 mm tall",
        url="https://www.opencompute.org/wiki/Open_Rack/SpecsAndDesigns"),
    "orv3_it_width_mm": dict(value=533.0, grade="published", source="Open Rack equipment bay 21 in = 533 mm (24 in = 610 mm outside)",
        url="https://en.wikipedia.org/wiki/Open_Rack"),
    "orv3_tray_depth_mm": dict(value=800.0, grade="estimate", source="ORv3 IT depth ~ 800-1,000 mm; 800 mm used for cable lengths"),
    "busbar_v": dict(value=50.0, grade="published", source="ORv3 48 V class busbar; NVL72 power shelves output nominal 50-51 V DC to the busbar",
        url="https://docs.nvidia.com/dgx/dgxgb200-user-guide/hardware.html"),
    "power_shelf_kw": dict(value=33.0, grade="published",
        source="ORv3 HPR power shelf: six 5.5 kW PSUs, 50 V 660 A (33 kW; 27.5 kW N+1). Standard ORv3 shelf: 18 kW (15 kW N+1)",
        url="https://www.advancedenergy.com/en-us/products/ac-dc-power-supply-units/power-shelves/orv3-high-power-rack-(hpr)/"),
    "power_shelf_ou": dict(value=1, grade="published", source="ORv3 power shelf 1 OU"),
    "vr_efficiency": dict(value=0.87, grade="published",
        source="48 V -> core: Vicor NBM 95.6% at full load x ~0.91 core stage; arXiv:2309.10141 reports >30% "
               "delivery loss in AI accelerators -- sync/power validation (research agent adae6788, branch worktree-agent-adae6788cbf2f3f86, technology.json quotes). Was 0.90."),
    "psu_efficiency": dict(value=0.96, grade="published",
        source="80 PLUS Titanium: 96% at 50% load, 91% at 100% -- sync/power validation (research agent adae6788, branch worktree-agent-adae6788cbf2f3f86, technology.json quotes). Was 0.975."),
    "air_limit_w_per_ou": dict(value=700.0, grade="assumed",
        source="no primary source (validation, adae6788): an engineering assumption; ASHRAE TC9.9 (2021) says 1U/2U "
               "servers become difficult to air-cool as socket power moves through 300-400 W",
        url="https://www.ashrae.org/file%20library/technical%20resources/bookstore/emergence-and-expansion-of-liquid-cooling-in-mainstream-data-centers_wp.pdf"),
    "air_rack_limit_kw": dict(value=(20, 25), grade="published",
        source="Uptime Institute: above 20-25 kW per rack, direct liquid cooling and precision air become more economical; "
               "mean rack 8.4 kW (2020)", url="https://journal.uptimeinstitute.com/rack-density-is-rising/"),
    "tray_mass_kg": dict(value=(18, 25), grade="estimate", source="1OU liquid-cooled compute tray with 4 packages, cold plates, manifolds"),
}

# published comparison systems (filled from cited sources; see compare())
NVL72 = dict(
    name="NVIDIA GB200 NVL72", accelerators=72, accel_unit="B200 GPUs (1,000 W class) + 36 Grace CPUs", racks=1,
    compute_trays="18 x 1RU (4 GPU + 2 CPU each)", switch_trays="9 x 1RU NVLink switch", rack_kw=132.0,
    rack_kw_basis="provisioned 132 kW (Supermicro 'Operating Power 125kW to 135kW'); NVIDIA DGX guide ~120 kW; B200 "
                  "1,200 W TDP in NVL72; MLPerf v5.1 8xB200 10,401 W at the wall (1.30 kW per GPU)",
    power_shelves="8 x 33 kW (6 x 5.5 kW PSU), N+N, 50-51 V busbar", cooling="liquid cold plates on CPUs/GPUs; rest air",
    weight_kg=1360, cables="over 5,000 active copper cables in 4 rear NVLink cartridges (>3.2 km)",
    fabric="NVLink 5 all-to-all through 9 switch trays; 1.8 TB/s bidirectional per GPU; 130 TB/s aggregate",
    built_for="all-to-all tensor/expert parallelism for any model; training and batched serving",
    per_accel_scaleup_TBps_per_dir=0.9,
    sources=["https://www.nvidia.com/en-us/data-center/gb200-nvl72/",
             "https://docs.nvidia.com/dgx/dgxgb200-user-guide/hardware.html",
             "https://developer.nvidia.com/blog/nvidia-contributes-nvidia-gb200-nvl72-designs-to-open-compute-project/",
             "https://www.theregister.com/2024/03/21/nvidia_dgx_gb200_nvk72/"])
CM384 = dict(
    name="Huawei CloudMatrix384", accelerators=384, accel_unit="Ascend 910C NPUs + 192 Kunpeng CPUs", racks=16,
    compute_trays="12 compute racks (48 nodes x 8 NPU)", switch_trays="4 communication racks (L2 UB switches)", rack_kw=559.0,
    rack_kw_grade="SemiAnalysis, via search summary (the same source states 4.1x the power of a GB200 NVL72)",
    power_shelves="not published", cooling="not published in the paper", weight_kg=None,
    cables="optical scale-up links; transceiver count and rate are not stated in the cited research paper",
    fabric="Unified Bus, all-to-all over a 2-tier switch (7 sub-planes x 16 L2 switch chips); 392 GB/s per NPU per direction",
    built_for="large-scale MoE expert parallelism and distributed KV-cache access; disaggregated serving",
    per_accel_scaleup_TBps_per_dir=0.392,
    sources=["https://arxiv.org/abs/2506.12708", "https://arxiv.org/html/2506.12708v1",
             "https://newsletter.semianalysis.com/p/huawei-ai-cloudmatrix-384-chinas-answer-to-nvidia-gb200-nvl72"])


def _v(k):
    v = PHYS[k]["value"]
    return v


# ---------------------------------------------------------------------------------------------------------
# 1. logical map
# ---------------------------------------------------------------------------------------------------------
def placement():
    """The spec's integer die map (results/arch/v41_die_placement.json, tools/v41_die_placement.py, spec agent):
    dies 0-111 = 28 stages x tensor group 4 (stage s = packages 2s, 2s+1 = one stage module); dies 112-115 =
    head + DSpark + embedding group (stage 28, packages 56-57; HBM per the placement record -- 4 stacks per die
    after the spec's C10 ruling); dies 116-187 = Engram tables
    (packages 58-93, no HBM).  Adds the stage of each layer's start (where its attention, Engram and KV live)."""
    P = json.loads(PLACEMENT.read_text())
    cfg = json.loads(V41_CONFIG.read_text())
    oc = cfg["metadata"]["operator_config"]
    start = {}
    for st in P["stages"]:
        for l in st["layers"]:
            start.setdefault(l["layer"], st["stage"])
    dies = P["die_table"]
    roles = {}
    for d in dies:
        roles[d["role"]] = roles.get(d["role"], 0) + 1
    eng_pk = {}
    for d in dies:
        for e in d.get("engram") or []:
            eng_pk.setdefault(e["table"], set()).add(d["package"])
    emb_dies = [d["die"] for d in dies if d.get("embedding_bytes", 0) > 0]
    groups = [dict(stage=st["stage"], label="S%d" % st["stage"], layers=st["layers"],
                   packages=[2 * st["stage"], 2 * st["stage"] + 1],
                   kv_owner_layers=[L for L in oc["kv_source_layer_ids"] if start[L] == st["stage"]],
                   index_layers=[L for L in oc["index_source_layer_ids"] if start[L] == st["stage"]],
                   engram_layers=[L for L in oc["engram_layer_ids"] if start[L] == st["stage"]])
              for st in P["stages"]]
    return dict(
        source=str(PLACEMENT.relative_to(ROOT)), per_die_capacity_bytes=P["rom_bytes_per_die"], bytes=P["bytes"],
        engram_spill=P["engram_spill"], roles=roles, groups=groups, dies=dies,
        head=dict(stage=STAGES, dies=[d["die"] for d in dies if d["role"].startswith("head")], packages=[56, 57]),
        embedding_dies=emb_dies, embedding_packages=sorted({dies[d]["package"] for d in emb_dies}),
        engram_packages={k: sorted(v) for k, v in eng_pk.items()},
        engram_consumers={L: start[L] for L in oc["engram_layer_ids"]},
        kv_owner_stages=sorted({start[L] for L in oc["kv_source_layer_ids"]}),
        index_stages=sorted({start[L] for L in oc["index_source_layer_ids"]}),
        counts=dict(layer=roles.get("layer", 0), head=G, table=DIES - roles.get("layer", 0) - G, total=len(dies),
                    packages=P["packages"], layer_packages=56, head_packages=2, table_packages=36,
                    hbm_stacks=sum(d.get("hbm_stacks", 0) for d in dies),
                    head_hbm_stacks_per_die=max(d.get("hbm_stacks", 0) for d in dies
                                                if d["role"].startswith("head"))))


# ---------------------------------------------------------------------------------------------------------
# 2. physical layout: stage modules, trays, folded ring, elevation
# ---------------------------------------------------------------------------------------------------------
def ring_order():
    """Token ring: H (argmax + next embedding) -> S0 -> ... -> S27 -> H.  29 stage modules."""
    return ["H"] + [f"S{s}" for s in range(STAGES)]


def folded_trays(ring):
    """Fold the ring so every ring neighbour is on the same tray or the adjacent one: tray t holds ring
    positions t and n-1-t (the classic folded-torus embedding); with n = 29 the middle tray holds one module."""
    n = len(ring)
    trays = []
    for t in range((n + 1) // 2):
        a, b = t, n - 1 - t
        mods = [ring[a]] + ([ring[b]] if b != a else [])
        trays.append(dict(tray=t, modules=mods))
    pos = {m: tr["tray"] for tr in trays for m in tr["modules"]}
    span = [abs(pos[ring[i]] - pos[ring[(i + 1) % n]]) for i in range(n)]
    return trays, pos, max(span)


def elevation(cooling="liquid", pl=None):
    """Rack units bottom-up.  Liquid (headline): 1 OU stage trays.  Air (alternative): 2 OU stage trays."""
    ring = ring_order()
    trays, pos, maxspan = folded_trays(ring)
    st_ou = 1 if cooling == "liquid" else 2
    rows = []
    ou = 1

    def put(kind, label, h, **kw):
        nonlocal ou
        rows.append(dict(ou=ou, height=h, kind=kind, label=label, **kw))
        ou += h
    for side in "AB":
        for j in range(SHELVES_PER_SIDE):
            put("power", "power shelf %s%d (33 kW, 6 x 5.5 kW PSU)%s" % (side, j + 1, "" if side == "A" else ", 2N"), 1)
    for t in range(9):
        pk = list(range(58 + 4 * t, 62 + 4 * t))
        tabs = []
        if pl:
            for name, pks in pl["engram_packages"].items():
                if set(pks) & set(pk):
                    tabs.append(name.replace("Engram layer ", "E-"))
        what = "/".join(tabs or ["Engram"])
        put("table", f"table tray T{t}: packages {pk[0]}-{pk[-1]} ({what})", 1, tray=f"T{t}", packages=pk)
    put("switch", "Engram / host switch (51.2T class, 1 OU)", 1)
    put("host", "host: 2-socket CPU + 2 x 400G NIC (prefill KV ingest) + BMC", 2)
    for tr in trays:
        put("stage", "stage tray %d: %s" % (tr["tray"], " + ".join(tr["modules"])), st_ou, tray=tr["tray"],
            modules=tr["modules"])
    put("mgmt", "management switch (1 GbE OOB) + leak detection", 1)
    used = ou - 1
    return dict(cooling=cooling, rows=rows, used_ou=used, fits=used <= _v("orv3_usable_ou"),
                usable_ou=_v("orv3_usable_ou"), stage_tray_ou=st_ou, trays=trays, module_tray=pos,
                ring_max_tray_span=maxspan)


def cable_length_m(ou_a, ou_b):
    """Package flyover to the rear bulkhead in one tray, vertical run in the rear cable channel, into the other
    tray: 2 x in-tray run + vertical distance + service slack (ESTIMATE geometry, stated in PHYS)."""
    in_tray = 0.30
    slack = 0.15
    return 2 * in_tray + abs(ou_a - ou_b) * _v("orv3_ou_mm") / 1000 + slack


# ---------------------------------------------------------------------------------------------------------
# 3. lanes, link tiers, per-link timing
# ---------------------------------------------------------------------------------------------------------
LANES_REC = ROOT / "results/arch/v41_lanes.json"
HBM_SWITCHED = ROOT / "results/arch/v41_hbm_switched.json"
LANES_RACK_V1 = dict(tp=32, stage_out=24, stage_in=24, switch=4, spare=6)   # this study's first split (C8)


def _lanes():
    """R-L9 (utilisation agent, results/arch/v41_lanes.json best_split): TP 52 / stage 14 + 14 / switch 4 / spare 6,
    large all-reduces as a fixed-order two-step.  Falls back to the first rack split if the record is absent."""
    try:
        b = json.loads(LANES_REC.read_text())["best_split"]
        return dict(tp=b["tp"], stage_out=b["stage"], stage_in=b["stage"], switch=b["switch"], spare=b["spare"]), b
    except (OSError, KeyError):
        return dict(LANES_RACK_V1), None


LANES, LANES_R_L9 = _lanes()


def lane_budget():
    lane_Bps = _v("lane_gbps") * 1e9 * _v("lane_net_fraction") / 8
    tot = sum(LANES.values())
    per_pair = LANES["tp"] // 4                      # 2 dies x 2 partner dies per package
    return dict(per_package=LANES, total=tot, available=_v("lanes_per_package"), fits=tot <= _v("lanes_per_package"),
                lane_net_Bps=lane_Bps, tp_lanes_per_die_pair=per_pair,
                tp_per_die_pair_Bps=per_pair * lane_Bps, tp_package_Bps=LANES["tp"] * lane_Bps,
                stage_package_Bps=LANES["stage_out"] * lane_Bps, stage_module_Bps=2 * LANES["stage_out"] * lane_Bps,
                spec_per_neighbour_Bps=0.30e12, source="R-L9, results/arch/v41_lanes.json" if LANES_R_L9 else
                "rack study v1 split",
                two_step_allreduce=bool(LANES_R_L9 and LANES_R_L9.get("two_step")),
                cables_per_package_per_hop=math.ceil(LANES["stage_out"] / 8),
                ring_cables=29 * 2 * math.ceil(LANES["stage_out"] / 8),
                cable=("stage link per package: %d lanes forward on %d x 8-lane 800G-class passive DACs (802.3df CR8 "
                       "class) to the same-position package of the next module, populated %d of %d lanes (7 of 8 per cable) so "
                       "the stage stays inside the 90-lane budget; each populated lane is a duplex SerDes lane whose "
                       "reverse half carries credit returns, so credits need no extra lanes; the TP link is %d board "
                       "lanes per die pair"
                       % (LANES["stage_out"], math.ceil(LANES["stage_out"] / 8), LANES["stage_out"],
                          8 * math.ceil(LANES["stage_out"] / 8), per_pair)),
                note=("per package: TP = each die 2 x %d lanes to both dies of the partner package (R-U8 flat one-shot); "
                      "stage = %d lanes to the next module's same-position package, %d from the previous; switch = 4 "
                      "lanes (one 400G-class port); 6 spare (lane sparing / debug)"
                      % (per_pair, LANES["stage_out"], LANES["stage_in"])))


def hop_latency(length_m, medium, fec=None):
    """T1 board trace: the 130 ns light-FEC link (which already includes ~0.3 m of flight) re-based to the actual
    trace.  T2 cable: the full-KP4 cable hop (209 ns, validated) plus the cable's own flight on top."""
    if medium == "pcb" and fec != "full":
        included = _v("hop_flight_included_m") * _v("pcb_ns_per_m") * 1e-9
        return _v("hop_s") - included + length_m * _v("pcb_ns_per_m") * 1e-9
    return _v("cable_hop_s") + length_m * _v("twinax_ns_per_m") * 1e-9


def link_inventory(el):
    """Every physical link class with its count, length, reach class and latency."""
    ou_of = {}
    for r in el["rows"]:
        if r["kind"] == "stage":
            for m in r["modules"]:
                ou_of[m] = r["ou"]
    sw_ou = next(r["ou"] for r in el["rows"] if r["kind"] == "switch")
    table_ous = [r["ou"] for r in el["rows"] if r["kind"] == "table"]
    ring = ring_order()
    n = len(ring)
    stage_links = []
    for i in range(n):
        a, b = ring[i], ring[(i + 1) % n]
        same = ou_of[a] == ou_of[b]
        L = 0.25 if same else cable_length_m(ou_of[a], ou_of[b])
        stage_links.append(dict(src=a, dst=b, same_tray=same, length_m=round(L, 3),
                                medium="in-tray flyover cable" if same else "rear-channel twinax",
                                latency_s=hop_latency(L, "cable"), reach_m=_v("dac_112g_reach_m"),
                                within_reach=L <= _v("dac_112g_reach_m"), retimer=False))
    tp_trace_m = 0.12
    sw_lengths = [cable_length_m(ou_of[m], sw_ou) for m in ring] + [cable_length_m(o, sw_ou) for o in table_ous]
    tiers = [
        dict(tier="T0 in-package UCIe (advanced)", reach="<= 2 mm", length="~1 mm die edge to die edge",
             latency_s=_v("ucie_hop_s"), Bps=_v("ucie_link_Bps"), per_package="1 die-to-die link",
             count=DIES // PKG_DIES, within_reach=True, note="the two dies of a package; carries 1 of 3 one-shot peers"),
        dict(tier="T1 on-module PCB trace (TP)", reach="VSR/MR class 100-500 mm", length=f"~{int(tp_trace_m * 1000)} mm",
             latency_s=hop_latency(tp_trace_m, "pcb"), Bps=lane_budget()["tp_per_die_pair_Bps"],
             per_package="4 die-pair links x %d lanes = %d" % (lane_budget()["tp_lanes_per_die_pair"], LANES["tp"]), count=(STAGES + 1) * 4, within_reach=tp_trace_m * 1000 <= 500,
             note="package pair on one stage-module board; the two cross-package peers of every one-shot collective"),
        dict(tier="T2 in-rack copper (stage hop, token return)", reach="passive DAC <= 2 m (802.3ck CR)",
             length="%.2f-%.2f m" % (min(l["length_m"] for l in stage_links), max(l["length_m"] for l in stage_links)),
             latency_s=max(l["latency_s"] for l in stage_links), Bps=2 * LANES["stage_out"] * lane_budget()["lane_net_Bps"],
             per_package="%d out + %d in" % (LANES["stage_out"], LANES["stage_in"]), count=n * 2, within_reach=all(l["within_reach"] for l in stage_links),
             note="folded ring: every ring neighbour on the same or the adjacent tray"),
        dict(tier="T3 switched copper (Engram, token id, host)", reach="passive DAC <= 2 m to a mid-rack switch",
             length="%.2f-%.2f m" % (min(sw_lengths), max(sw_lengths)),
             latency_s=2 * _v("ethernet_hop_s") + _v("switch_latency_s") + max(sw_lengths) * 2 * _v("twinax_ns_per_m") * 1e-9,
             Bps=LANES["switch"] * lane_budget()["lane_net_Bps"], per_package="4 lanes (layer/head), 2 (table)",
             count=58 + 36, within_reach=max(sw_lengths) <= _v("dac_112g_reach_m"),
             note="Ethernet framing with full KP4 FEC on these ports; one 51.2T-class switch"),
        dict(tier="T4 out-of-rack optics (KV ingest)", reach="400G/800G optics, 100 m - 2 km",
             length="to the GPU prefill pod", latency_s=None, Bps=2 * 50e9, per_package="via the switch",
             count=2, within_reach=True, note="host NICs; ingest lands in the KV-owning stages' HBM through the switch"),
    ]
    return dict(stage_links=stage_links, tiers=tiers, tp_trace_m=tp_trace_m, switch_cable_m=sw_lengths)


# ---------------------------------------------------------------------------------------------------------
# 4. per-token traffic per link class
# ---------------------------------------------------------------------------------------------------------
def traffic(pl):
    B = json.loads(BUDGET.read_text())
    cfg = json.loads(V41_CONFIG.read_text())
    oc = cfg["metadata"]["operator_config"]
    cpl = B["collectives_per_layer"]
    modes = [m["mode"] for m in cfg["metadata"]["csa2_layer_modes"]]

    def klass(L):
        if L in (0, 1):
            return "0"
        if L == 20:
            return "20"
        if modes[L] == "full":
            return "2"
        if modes[L] == "reindex":
            return "24"
        return "3"
    ar = ag = 0
    ar_b = ag_b = 0
    for L in range(cfg["num_layers"]):
        for name, kind, by in cpl[klass(L)]:
            if kind == "all_reduce":
                ar += 1
                ar_b += by
            else:
                ag += 1
                ag_b += by
    # flat one-shot on 4 dies: all-reduce -> each die sends its full partial to 3 peers (1 UCIe + 2 board);
    # all-gather -> each die sends its quarter to 3 peers
    ucie_b = ar_b * 4 * 1 + ag_b / 4 * 4 * 1
    board_tp_b = ar_b * 4 * 2 + ag_b / 4 * 4 * 2
    msgs_tp = (ar + ag) * 4 * 3
    hc, Dm = oc["hc_mult"], oc["hidden_size"]
    resid = hc * Dm * 2                                      # 4 x 5,120 BF16 residual stream
    stage_hops = STAGES - 1 + 1                              # 27 boundaries + S27 -> H
    ret_b = Dm * 2                                           # H -> S0: the next token's embedding row (BF16)
    engram_rows = 2 * oc["engram_hash_columns"]
    engram_b = engram_rows * 264
    tokid_msgs = 72 + 4                                      # token-id multicast to table + head dies
    kv = B["workload"][str(CTX)]["totals"]["bytes"]
    rate_b1 = B["batch"][str(CTX)]["rows"]["rom"][0]["ar_tokens_s_per_user"]
    rate_mtp = B["batch"][str(CTX)]["rows"]["rom"][0]["mtp_tokens_s_per_user"]
    per_token = {
        "T0_ucie": dict(bytes=ucie_b, messages=(ar + ag) * 4),
        "T1_tp_trace": dict(bytes=board_tp_b, messages=(ar + ag) * 8),
        "T2_stage_hop": dict(bytes=stage_hops * resid, messages=stage_hops * 2),
        "T2_token_return": dict(bytes=ret_b, messages=1),
        "T3_engram": dict(bytes=engram_b + tokid_msgs * 16, messages=engram_rows + tokid_msgs),
        "hbm_kv_index": dict(bytes=kv["kv_hbm"] + kv["idx"], messages=None),
    }
    out = dict(collectives=dict(all_reduce=ar, all_gather=ag, all_reduce_bytes=ar_b, all_gather_bytes=ag_b,
                                spec_total=B["workload"][str(CTX)]["totals"]["collectives"],
                                spec_payload_bytes=B["workload"][str(CTX)]["totals"]["collective_bytes"]),
               per_token=per_token, residual_bytes=resid, stage_hops_per_token=stage_hops,
               rates=dict(b1=rate_b1, fill=rate_b1 * FILL, b1_mtp=rate_mtp, fill_mtp=rate_mtp * FILL))
    lb = lane_budget()
    link_caps = {"T0_ucie": _v("ucie_link_Bps") * 2 * (DIES // PKG_DIES),
                 "T1_tp_trace": lb["tp_package_Bps"] * 58,
                 "T2_stage_hop": lb["stage_module_Bps"] * 29,
                 "T2_token_return": lb["stage_module_Bps"],
                 "T3_engram": 4 * lb["lane_net_Bps"] * 2}
    rows = {}
    for k, v in per_token.items():
        r = dict(bytes_per_token=v["bytes"], messages_per_token=v["messages"])
        for tag, rate, f in (("b1", rate_b1, 1.0), ("fill", rate_b1 * FILL, 1.0),
                             ("fill_mtp", rate_mtp * FILL, POSITIONS / TAU)):
            r[f"Bps_{tag}"] = v["bytes"] * rate * f
        if k in link_caps:
            r["capacity_Bps"] = link_caps[k]
            r["utilisation_fill_mtp"] = r["Bps_fill_mtp"] / link_caps[k]
        rows[k] = r
    kvpt = cfg["metadata"]["global_kv_bytes_per_token"]
    ingest_user = kvpt * CTX
    rows["T4_kv_ingest"] = dict(bytes_per_user_1m=ingest_user, bytes_per_token_context=kvpt,
                                nic_Bps=INGEST_NICS * NIC_BPS, seconds_per_1m_user=ingest_user / (INGEST_NICS * NIC_BPS),
                                lands_on_stages=pl["kv_owner_stages"],
                                note=("GPU-prefilled compressed KV + index keys (890 B per context token, FP4 latent + FP4 "
                                      "index key) into the KV-owning stages' HBM through the switch; window rows are "
                                      "re-derived by SWA bounded replay"))
    out["rows"] = rows
    # serialisation of one stage hop on the physical lanes vs the spec's 0.3 TB/s per neighbour
    out["stage_hop_serialisation_s"] = dict(physical_module=resid / lb["stage_module_Bps"],
                                            spec_per_neighbour=resid / 0.30e12)
    return out


# ---------------------------------------------------------------------------------------------------------
# 5. power, cooling, weight
# ---------------------------------------------------------------------------------------------------------
TECH_ENERGY = ROOT / "configs/hardware/technology.json"


def mac_energy_delta_j():
    """Per-token MAC energy the spec budget does NOT yet carry: the validated per-op energies minus the ones in
    technology.json (which the budget prices).  Zero once the technology file carries the validated values."""
    B = json.loads(BUDGET.read_text())
    macs = B["workload"][str(CTX)]["totals"]["macs"]
    tech = json.loads(TECH_ENERGY.read_text())["energy"]["mac_energy_j_per_op"]
    cur = {k: v["value"] * 1e12 for k, v in tech.items() if isinstance(v, dict) and "value" in v}
    new = PHYS["mac_pj_per_op"]["value"]
    fmt = {"fp8": "fp8", "fp4": "fp4", "bf16": "bf16", "bf16xfp8": "bf16", "bf16xfp8w": "bf16", "fp32": "fp32"}
    return sum(v * 2 * (new[fmt[k.split(":")[1]]] - cur[fmt[k.split(":")[1]]]) * 1e-12 for k, v in macs.items())


def power(el, pl):
    """Rack power on the spec's per-die terms (arch_budget_v41.json power, re-derived on the validated values):
    layer and head dies carry the spec's static (leakage + HBM idle + always-on SerDes + UCIe idle) and, at
    provisioning, its worst-case die (saturated dynamic at m = 2 + HBM interface at full bandwidth); table dies
    carry leakage of their right-sized logic and ROM array, UCIe idle and their two switch lanes.  Wall =
    chips / VR + infrastructure, times (1 + CDU + fans) / PSU; provisioning = 1.2 x the worst case at the wall
    (technology.json power.rack_overheads, the spec's rule)."""
    B = json.loads(BUDGET.read_text())
    U = json.loads(UTIL.read_text())
    pw = B["power"]
    tech = json.loads(TECH_ENERGY.read_text())["power"]
    ro = {k: (v["value"] if isinstance(v, dict) else v) for k, v in tech["rack_overheads"].items() if k != "purpose"}
    lk = {k: (v["value"] if isinstance(v, dict) else v) for k, v in tech["static_leakage_w_per_mm2"].items()}
    vr, psu = ro["vr_efficiency_48v_to_core"], ro["psu_efficiency"]
    over = 1 + ro["cdu_fraction_of_it"] + ro["fan_fraction_of_it"]
    st = pw["static_w_per_die"]
    die_static = st["total"]                                         # layer and head dies
    die_worst = pw["worst_case_die_w"]
    serdes_lane_w = _v("serdes_pj_per_bit") * 1e-12 * _v("lane_gbps") * 1e9
    active_lanes = sum(LANES.values()) - LANES["spare"]
    # table dies: the layer die's logic less its engines (right-sized, R-U1) + ROM array, UCIe idle, 2 lanes/package
    import decode_critical_path as D
    import arch_budget_v41 as AB
    detail = AB._env()["designs"][D.ARRAY_DESIGN]["static_power"]["detail"]
    engines = U["nonlayer_right_size"]["engine_area_per_die_spec_mm2"]
    table_leak = (detail["logic_mm2_per_device"] - engines) * lk["logic"] + detail["rom_array_mm2_per_device"] * lk["rom_array"]
    table_static = table_leak + st["ucie_idle"] + 2 * serdes_lane_w / 2
    rows = B["batch"][str(CTX)]["rows"]["rom"]
    b1, fill = rows[0], next(r for r in rows if r["batch"] == FILL)
    sat = max(rows, key=lambda r: r["mtp_aggregate_tokens_s"])
    dmac = mac_energy_delta_j()
    dmtp = dmac * POSITIONS / TAU
    n_ld = 116                                                       # 112 layer + 4 head dies
    DP = json.loads(HBM_SWITCHED.read_text()) if HBM_SWITCHED.exists() else None
    if DP:
        # THE DESIGN POINT (R-L8 pooled engines doubled, R-L9 lanes, validated links and power): the utilisation
        # agent's record -- dynamic = energy per token x aggregate rate; static per die class; worst die saturated
        # with MTP; the off-path switch at 13 W per Tb/s (NVL72 tray basis, assumed)
        e = DP["energy"][str(CTX)]
        wd = DP["rom_worst_die_w"]
        sw = json.loads(LANES_REC.read_text())["static_w"]
        dyn = {k: e[src]["rom"]["dynamic_j"] * e[src]["rom"]["aggregate_tokens_s"]
               for k, src in (("b1", "b1"), ("fill", "fill28"), ("fill_mtp", "fill28_mtp"),
                              ("saturated_mtp", "sat1024_mtp"))}
        static = dict(layer_dies=112 * sw["layer_die"], head_dies=4 * sw["head_die"], table_dies=72 * sw["table_die"])
        # the worst die adds the HBM interface IDLE only (in static): the 13 pJ/b dynamic energy already carries the
        # I/O, so any separate 'hbm_interface_active_w' in the record is a double count (spec ef93dda0) -- excluded
        die_worst = wd["static_w"] + wd["dynamic_w"]
        worst_chips = static["layer_dies"] + static["head_dies"] + static["table_dies"] + 112 * wd["dynamic_w"]
        switch_w = _v("switch_tray_w")       # the physical switch; the per-port 1.1 kW is the ratio basis
        basis = ("design point: results/arch/v41_hbm_switched.json (energy, rom_worst_die_w) and results/arch/"
                 "v41_lanes.json static_w, utilisation agent b07a5745 on the spec's validated per-die terms")
        table_static = sw["table_die"]
    else:
        dyn = dict(
            b1=b1["ar_aggregate_tokens_s"] * (b1["ar_energy_j_per_token_gated"] + dmac),
            fill=fill["ar_aggregate_tokens_s"] * (fill["ar_energy_j_per_token_gated"] + dmac),
            fill_mtp=fill["mtp_aggregate_tokens_s"] * (fill["mtp_energy_j_per_token"] + dmtp),
            saturated_mtp=sat["mtp_aggregate_tokens_s"] * (sat["mtp_energy_j_per_token"] + dmtp))
        static = dict(layer_and_head_dies=n_ld * die_static, table_dies=72 * table_static)
        worst_chips = n_ld * die_worst + 72 * table_static
        switch_w = _v("switch_tray_w")
        basis = "spec widths: arch_budget_v41.json power and batch rows"
    static_total = sum(static.values())
    serdes_total = n_ld * st["serdes_always_on"] + 36 * 2 * serdes_lane_w
    infra = dict(switch=switch_w, host=900.0, mgmt=100.0)
    infra_total = sum(infra.values())

    def wall(chips):
        return (chips / vr + infra_total) * over / psu
    scen = {k: dict(dynamic_w=d, chips_w=static_total + d, rack_input_w=wall(static_total + d)) for k, d in dyn.items()}
    worst_wall = max(wall(worst_chips), max(v["rack_input_w"] for v in scen.values()))
    prov_wall = PROVISION_MARGIN * worst_wall
    layer_pkg_w = 2 * die_worst
    stage_tray_w = 4 * layer_pkg_w / vr + 60.0
    table_pkg_w = 2 * table_static
    table_tray_w = 4 * table_pkg_w / vr + 40.0
    shelf = _v("power_shelf_kw") * 1000
    shelf_n1 = shelf * 5 / 6
    cool = dict(
        stage_tray_w=stage_tray_w, stage_tray_w_per_ou_liquid=stage_tray_w, stage_tray_w_per_ou_air=stage_tray_w / 2,
        table_tray_w=table_tray_w,
        choice="liquid cold plates on the stage packages (1 OU trays); table trays, switch and host air-cooled",
        basis=("a 1 OU stage tray dissipates %.2f kW: above what 1U/2U air handles (ASHRAE TC9.9; the 700 W/OU "
               "figure is an assumption), so the packages take cold plates. The ALTERNATIVE all-air rack with 2 OU "
               "stage trays (%.0f W/OU) fills %d OU." % (stage_tray_w / 1e3, stage_tray_w / 2,
                                                         elevation("air")["used_ou"])),
        liquid_fraction=(worst_chips - 72 * table_static) / worst_chips)
    return dict(
        basis=basis,
        energy_j_per_token_b1=dict(chip=(DP["energy"][str(CTX)]["b1"]["rom"]["total_j"] if DP else None),
                                   wall_with_switch=(DP["energy"][str(CTX)]["b1"]["rom"]["wall_j"] if DP else None),
                                   rack_input=scen["b1"]["rack_input_w"] / (DP["energy"][str(CTX)]["b1"]["rom"][
                                       "aggregate_tokens_s"] if DP else 1.0),
                                   note="chip = static + dynamic of the ROM dies; wall = x 1.24 + the off-path switch "
                                        "(utilisation agent); rack_input adds the host and management trays"),
        mac_energy_delta_j_per_token=dmac,
        per_die=dict(static_w=st, layer_static_w=die_static, worst_case_w=die_worst,
                     hbm_interface_worst_w=pw["hbm_interface_worst_w_per_die"], table_static_w=table_static,
                     table_leakage_w=table_leak, cooling_limit_w=_cooling_2die(),
                     cooling_basis="configs/hardware/power_scenarios.json cooling classes, 2-die packages (B200 HGX "
                                   "air / GB200 liquid, less the stacks), as the budget's power check "
                                   "(arch_budget_v41.json power.cooling_limit_w_per_die_by_class)",
                     spec_provisioned_wall_w=pw["provisioned_wall_w_per_die"]),
        serdes=dict(lane_w=serdes_lane_w, active_lanes_per_layer_pkg=active_lanes,
                    per_layer_pkg_w=2 * st["serdes_always_on"], per_table_pkg_w=2 * serdes_lane_w,
                    total_w=serdes_total, note="always-on PAM4 lanes; part of the spec's static_w_per_die"),
        static=static, static_total_w=static_total, infra_w=infra, dynamic_w=dyn, scenarios=scen,
        wall_factor=over / (vr * psu),
        per_package=dict(layer_worst_w=layer_pkg_w, table_w=table_pkg_w),
        per_tray=dict(stage_w=stage_tray_w, table_w=table_tray_w),
        worst_case_rack_input_w=worst_wall, provision_margin=PROVISION_MARGIN,
        provisioned_rack_input_w=prov_wall, provisioned_chips_w=worst_chips,
        reconciliation=dict(
            spec_rule_w=(n_ld * pw["provisioned_wall_w_per_die"] +
                         72 * PROVISION_MARGIN * table_static * over / (vr * psu) +
                         PROVISION_MARGIN * infra_total * over / psu),
            note="116 x the spec's 303 W provisioned per die + 72 table dies + infrastructure, each at 1.2 x wall"),
        shelves=dict(shelf_w=shelf, n_plus_1_w=shelf_n1, per_side=SHELVES_PER_SIDE, count=2 * SHELVES_PER_SIDE,
                     side_capacity_w=SHELVES_PER_SIDE * shelf_n1,
                     redundancy="2N (sides A and B, %d shelves each), each shelf N+1 inside" % SHELVES_PER_SIDE,
                     fits=prov_wall <= SHELVES_PER_SIDE * shelf_n1),
        busbar_a=prov_wall / _v("busbar_v"),
        cooling=cool)


def weight_estimate(el):
    lo, hi = PHYS["tray_mass_kg"]["value"]
    n_st = sum(1 for r in el["rows"] if r["kind"] == "stage")
    n_tb = sum(1 for r in el["rows"] if r["kind"] == "table")
    trays = (n_st * (lo + hi) / 2) + n_tb * 14
    rest = 2 * 22 + 15 + 25 + 5 + 170 + 60  # shelves, switch, host, mgmt, ORv3 frame+busbar, cables+manifolds
    return dict(kg=round(trays + rest), grade="estimate",
                basis="stage trays %d-%d kg, table trays ~14 kg, ORv3 frame+busbar ~170 kg, cables/manifolds ~60 kg" % (lo, hi))


# ---------------------------------------------------------------------------------------------------------
# 6. conflicts and comparison
# ---------------------------------------------------------------------------------------------------------
def critical_paths(pl, links):
    """Latency of the switched and ring paths that touch the token (analytical, from PHYS)."""
    sw = 2 * _v("ethernet_hop_s") + _v("switch_latency_s") + 2 * 1.2 * _v("twinax_ns_per_m") * 1e-9
    ring_hop = max(l["latency_s"] for l in links["stage_links"])
    gather_read = 396e-9                     # budget engram.port_cycles at 1 GHz: 13 KB in 256-bit beats
    ser = 24 * 264 / (LANES["switch"] * lane_budget()["lane_net_Bps"])   # 24 rows into one 4-lane port
    engram_l1 = sw + gather_read + sw + ser
    B = json.loads(BUDGET.read_text())
    T = 1.0 / B["batch"][str(CTX)]["rows"]["rom"][0]["ar_tokens_s_per_user"]
    l14_slack = T * pl["engram_consumers"][14] / STAGES
    return dict(switched_one_way_s=sw, ring_hop_s=ring_hop, engram_l1_s=engram_l1, engram_l14_slack_s=l14_slack,
                token_return_ring_s=ring_hop, token_return_via_table_die_s=sw + 100e-9 + sw,
                note="switched = port hop (full KP4) + 250 ns switch + port hop + ~2.4 m of cable; the table die's row "
                     "read is charged 100 ns")


def head_draft_sram():
    model = json.loads(V41_CONFIG.read_text())
    window = next(g for g in model["attention_groups"] if g["kind"] == "window")
    tech = json.loads(TECH.read_text())
    bitcell_um2 = tech["nodes"]["N5"]["sram_hd_bitcell_um2"]["value"]
    efficiency = tech["sram"]["array_efficiency"]["value"]
    per_die_bytes = 3 * window["window_tokens"] * window["entry_bytes"] * FILL / 4
    density_B_per_mm2 = 1e6 / bitcell_um2 * efficiency / 8
    return dict(draft_blocks=3, window_tokens=window["window_tokens"], entry_bytes=window["entry_bytes"],
                users=FILL, head_dies=4, single_buffer_bytes_per_die=per_die_bytes,
                double_buffer_bytes_per_die=2 * per_die_bytes,
                min_double_buffer_mm2_per_die=2 * per_die_bytes / density_B_per_mm2,
                bitcell_um2=bitcell_um2, array_efficiency=efficiency,
                note="capacity-only lower bound; banks, ports, margin, leakage and timing still require floorplanning")


def conflicts(pl, links, tr, pwr, el, draft_sram):
    B = json.loads(BUDGET.read_text())
    c = []
    L = links["stage_links"]
    worst = max(l["latency_s"] for l in L)
    c.append(dict(
        id="C1", severity="info",
        item="ring cable hop on the validated full-KP4 link",
        finding=("every ring hop is a <= %.2f m passive DAC carrying full RS(544,514) KP4 (validated 209 ns, band "
                 "160-300) plus %.1f ns of flight: worst hop %.1f ns. No retimer or AEC: 802.3ck CR reaches >= 2 m at "
                 "100G/lane (802.3dj at 200G/lane only >= 1.0 m, so a 200G-lane refresh sits near the limit)."
                 % (max(l["length_m"] for l in L), max(l["length_m"] for l in L) * _v("twinax_ns_per_m"), worst * 1e9))))
    c.append(dict(
        id="C2", severity="adopted-baseline",
        item="FEC on the ring cables",
        finding=("the light-FEC (130 ns) ring hop is NOT qualified on CR copper (ETC LL-FEC 1.0 Annex A; 802.3ck "
                 "mandates RS(544,514) for CR1), so the ring runs full KP4, UALink 1.0's un-interleaved in-rack mode "
                 "(209 ns). This was risk C2; it is now the baseline and costs %d hops x %.0f ns = %.2f us per token "
                 "against the 130 ns assumption (Table R-1 geometry row). The on-module T1 board link keeps the light "
                 "FEC (OIF CEI-112G-MR channel, raw BER 1e-6)."
                 % (tr["stage_hops_per_token"] + 1, (worst - _v("hop_s")) * 1e9,
                    (tr["stage_hops_per_token"] + 1) * (worst - _v("hop_s")) * 1e6))))
    c.append(dict(
        id="C3", severity="resolved-in-adopted-model",
        item="the baseline mesh is replaced by the adopted folded ring",
        finding=("technology.json keeps a 2-D mesh as the generic baseline and HBM-comparator fabric. The adopted "
                 "ROM ladder already applies ring_placement_return, so the token return is one cable hop, and its "
                 "stage hops are cut through. The physical folded ring validates adjacency: a module-to-module "
                 "hop has %.2f TB/s (%d lanes), so a 41 KB residual serialises in %.0f ns, less than the %.0f ns "
                 "priced at 0.30 TB/s per mesh neighbour. The rack sensitivity charges the actual worst cable flight "
                 "once per hop; no second ring-return credit is taken."
                 % (lane_budget()["stage_module_Bps"] / 1e12, 2 * LANES["stage_out"],
                    tr["stage_hop_serialisation_s"]["physical_module"] * 1e9,
                    tr["stage_hop_serialisation_s"]["spec_per_neighbour"] * 1e9))))
    lanes_rec = json.loads(LANES_REC.read_text()) if LANES_REC.exists() else {}
    sw = lanes_rec.get("static_w", {})
    c.append(dict(
        id="C4", severity="resolved-in-model" if sw.get("rom_serdes") else "conflict",
        item="SerDes power in static power",
        finding=("%d always-on 112G lanes per layer/head package at ~%.2f W each = %.0f W per package (%.0f W per "
                 "die); table packages %.2f W; %.2f kW per rack. The rack power scenarios carry it as static. %s"
                 % (pwr["serdes"]["active_lanes_per_layer_pkg"], pwr["serdes"]["lane_w"], pwr["serdes"]["per_layer_pkg_w"],
                    pwr["serdes"]["per_layer_pkg_w"] / 2, pwr["serdes"]["per_table_pkg_w"], pwr["serdes"]["total_w"] / 1e3,
                    ("The utilisation record (results/arch/v41_lanes.json static_w) charges %.0f W of ROM SerDes in a "
                     "ROM chip static total of %.0f W; batch-1 energy %.3f J per token at 1M at the chips (the "
                     "comparator's SerDes is charged on the same basis in results/arch/v41_hbm_switched.json)."
                     % (sw["rom_serdes"], sw["rom_total"], lanes_rec["energy"][str(CTX)]["b1"]["rom"]["total_j"]))
                    if sw.get("rom_serdes") else "Add it to static power on both machines."))))
    c.append(dict(
        id="C5", severity="resolved-in-budget",
        item="HBM interface power scaled to four stacks",
        finding=("arch_budget_v41.json kv_state.stacks_per_die = %d and capacity %d users at 1M; HBM interface "
                 "%.1f W idle per die (4 x 2.8 W) and %.1f W at full bandwidth (idle + 0.8 pJ/b active I/O), the "
                 "latter in the spec's worst-case die. The worst case adds full-bandwidth I/O on top of dynamic energy "
                 "that already charges the actual HBM bytes at 13.1 pJ/b (which includes the I/O): conservative, "
                 "overlap <= ~2 W per die."
                 % (B["kv_state"]["stacks_per_die"], B["capacity"][str(CTX)]["rom_users"],
                    B["power"]["static_w_per_die"]["hbm_interface_idle"], B["power"]["hbm_interface_worst_w_per_die"]))))
    ep = critical_paths(pl, links)
    c.append(dict(
        id="C6", severity="resolved-in-placement",
        item="embedding rows on the head dies avoid the switched token return",
        finding=("embedding quarters occupy head dies %s beside the matching lm_head quarters. The winner reads "
                 "the next embedding locally and returns it to S0 over one %.0f ns ring hop. The former table-die "
                 "path would have taken %.0f ns; the new placement moves 1.32 GB of Engram spill onto the "
                 "table dies and leaves every ROM die within capacity. The modeled path saves %.2f us per token."
                 % (pl["embedding_dies"], ep["token_return_ring_s"] * 1e9,
                    ep["token_return_via_table_die_s"] * 1e9,
                    (ep["token_return_via_table_die_s"] - ep["token_return_ring_s"]) * 1e6))))
    lb = lane_budget()
    c.append(dict(
        id="C8", severity="resolved-in-model" if LANES_R_L9 else "conflict",
        item="two-die package link bandwidth (T1 on-module TP link)",
        finding=("a two-die package has 90 lanes = %.2f TB/s per direction (1.687 TB/s is the four-die package's 128). "
                 "%s TP %d lanes = %d per die pair (%.0f GB/s per peer), stage %d + %d, switch %d, spare %d. A 20 KB "
                 "one-shot partial crosses a peer link in %.0f ns%s. %s"
                 % (90 * lb["lane_net_Bps"] / 1e12, "R-L9 split:" if LANES_R_L9 else "Split:", LANES["tp"],
                    lb["tp_lanes_per_die_pair"], lb["tp_per_die_pair_Bps"] / 1e9, LANES["stage_out"], LANES["stage_in"],
                    LANES["switch"], LANES["spare"], 20480 / lb["tp_per_die_pair_Bps"] * 1e9,
                    "; all-reduces whose payload would outlast a board flight run as a fixed-order reduce-scatter + "
                    "all-gather (each peer receives n/2), bit-identical on every die" if lb["two_step_allreduce"] else "",
                    ("Priced on the lanes (collective bytes on their peer links, hops on the stage lanes): %.0f / %.0f "
                     "tok/s/user at 1M without / with MTP, against %.0f / %.0f at the first rack split and 8,832 with "
                     "overlap assumed." % (LANES_R_L9[str(CTX)]["ar"], LANES_R_L9[str(CTX)]["mtp"],
                                            lanes_rec["rack_split_result"][str(CTX)]["ar"],
                                            lanes_rec["rack_split_result"][str(CTX)]["mtp"]))
                    if LANES_R_L9 else "Re-price the collectives at the lane allocation."))))
    c.append(dict(
        id="C9", severity="info",
        item="'point-to-point only, no switch' vs the Engram gather and host/ingest",
        finding=("72 table dies must receive the token id and return 48 rows to S%d (layer 1) and S%d (layer 14); "
                 "direct cables would need ~36 ports on the consumers. One 51.2T switch carries it OFF the stage path: "
                 "layer 1's gather completes %.2f us after the argmax against the spec's 3.57 us slack (margin %.2f us); "
                 "layer 14's slack is ~%.0f us. No token-path collective or stage hop crosses the switch."
                 % (pl["engram_consumers"][1], pl["engram_consumers"][14], ep["engram_l1_s"] * 1e6,
                    3.57 - ep["engram_l1_s"] * 1e6, ep["engram_l14_slack_s"] * 1e6))))
    hh = pl["counts"]["head_hbm_stacks_per_die"]
    alloc = draft_sram_allocation(pl, draft_sram)
    fp = head_draft_floorplan(pl, draft_sram, alloc)
    c.append(dict(
        id="C10", severity="gate" if hh else "conflict",
        item="head + DSpark draft KV: SRAM reserve at the fill%s" % (", HBM beyond it" if hh else ", no HBM"),
        finding=("three %d-token draft windows at %.0f B per entry and the %d-user fill require %.2f MB per head "
                 "die with four-way striping, or %.2f MB with double buffering. At the assumed N5 SRAM density "
                 "(%.3f um2 bitcell, %.0f%% array efficiency), double buffering needs at least %.2f mm2 per head "
                 "die before banks and ports. %s"
                 % (draft_sram["window_tokens"], draft_sram["entry_bytes"], draft_sram["users"],
                    draft_sram["single_buffer_bytes_per_die"] / 1e6,
                    draft_sram["double_buffer_bytes_per_die"] / 1e6, draft_sram["bitcell_um2"],
                    100 * draft_sram["array_efficiency"], draft_sram["min_double_buffer_mm2_per_die"],
                    ("Spec ruling (C10): the head dies carry %d HBM3E stacks each like the layer dies, so users beyond "
                     "the fill page their draft windows to HBM and all 29 stage modules stay identical. Floorplan "
                     "(head_draft_floorplan): %d compiler macros (ot_sram_1r1w_1024x256, 32 KB, 1R1W, repairable), one "
                     "4-macro row per user slot = a 1,024-bit read port and an independent write port; a %.2f x %.2f "
                     "mm block (%.2f mm2) that displaces %.1f MB of the head die's %.0f MB spare ROM; macro fmax "
                     "%.0f MHz at ss, read registered at the macro (%d-cycle latency); %.1f mW leakage. The "
                     "floorplan is analytical; a routed head-die floorplan remains."
                     % (hh, fp["organisation"]["macros"], fp["area"]["block_w_mm"], fp["area"]["block_h_mm"],
                        fp["area"]["block_mm2"], fp["area"]["displaced_rom_bytes"] / 1e6,
                        fp["area"]["head_die_spare_rom_bytes"] / 1e6, fp["timing"]["fmax_ss_mhz"],
                        fp["timing"]["read_latency_cycles"], fp["power"]["leakage_mw"]))
                    if hh else "The floorplan reserves zero SRAM; allocate and route this state, or give packages "
                               "56-57 HBM."))))
    c.append(dict(
        id="C7", severity="gate",
        item="collective overlap and whole-system clock must be demonstrated",
        status=_c7_status(),
        finding=("the overlap-assumed lane-priced rate assumes collective bytes chase their producers (%.2f us of "
                 "exposed bytes per token) and a %.3f GHz clock on every die. %s Serialising only the collective bytes "
                 "from the conditional point gives %.0f tok/s/user -- not a bound, since the bench's fold, hop and "
                 "row-gather tails add more. The demonstration plan (record key demonstration_plan) states the benches, "
                 "parameters and acceptance for both."
                 % (LANES_R_L9[str(CTX)]["collective_bytes_us"] if LANES_R_L9 else float("nan"),
                    json.loads(LADDER.read_text())["ladder"][-1]["clock_hz"] / 1e9, _c7_measured_text(),
                    reprice_sensitivity(pl, links, tr, pwr)["no_collective_overlap_stress"]["rate_tokens_s"]))))
    return c


def _cooling_2die():
    """Per-die cooling limit of a two-die package by class (air / liquid), from the sourced power scenarios."""
    import power_scenarios as PS
    lim = PS.cooling_limits(PS.load_cfg())
    return {cls: v["2"]["die_w"] for cls, v in lim.items()}


def _c7_lanes():
    ln = json.loads(LANES_REC.read_text())
    return ln if ln.get("collective_exposure") else None


def _c7_status():
    return "NOT MET (measured)" if _c7_lanes() else "open"


def _c7_measured_text():
    ln = _c7_lanes()
    if not ln:
        return "Neither is shown in RTL or routed silicon."
    dp, cond = ln["design_point"], ln["design_point_overlap_assumed"]
    nl = ln.get("design_point_no_levers", dp)
    rs = ln["collective_exposure"].get("recovered_share", {}).get("1048576", {}).get("ar", 0.0)
    return ("Overlap is MEASURED NOT MET (RTL stage bench, results/rtl/v41_stage_collective_campaign.json): the "
            "one-shot engine's exposed tails exceed the overlap model (without recovery the design point would be "
            "%.0f against %.0f tok/s/user overlapped at 1M). The adopted levers (results/rtl/"
            "v41_collective_levers_campaign.json, bit-exact) give %.0f tok/s/user at 1M (%.0f at 200K), %.0f%% of the "
            "overlap loss at 1M. The whole-system clock is not shown."
            % (nl["1048576"]["ar"], cond["1048576"]["ar"], dp["1048576"]["ar"], dp["200000"]["ar"], 100 * rs))


def compare(pwr, el, pl):
    ours = dict(name="OpenTallas V4.1 ROM rack (this design)", accelerators=DIES // PKG_DIES,
                accel_unit="two-die ROM packages (188 reticle dies, %d HBM3E stacks)" % pl["counts"]["hbm_stacks"], racks=1,
                rack_kw=round(pwr["provisioned_rack_input_w"] / 1e3, 1), cooling=pwr["cooling"]["choice"],
                weight_kg=weight_estimate(el)["kg"],
                fabric="point-to-point folded ring of 29 stage modules + on-board TP + one 51.2T switch for Engram/host",
                built_for="one model replica, pipeline-parallel decode at batch 1-28, latency-bound collectives",
                per_accel_scaleup_TBps_per_dir=round(90 * lane_budget()["lane_net_Bps"] / 1e12, 2),
                used_ou=el["used_ou"])
    return [ours, NVL72, CM384]


def kv_replication(pl):
    """Spec section 15.1 replicate-on-write: each compressed-KV owner (layers 2/8/14/20) multicasts every new row
    (288 B main + 68 B index key) to the HBM of every stage that runs one of its reader layers, so every sparse
    gather is a local read.  Decode: the rows ride the ring behind the residual.  Prefill ingest: the host sends
    each owner stream once and the switch replicates it to the reader stages' switch ports (the ring stays free)."""
    cfg = json.loads(V41_CONFIG.read_text())
    modes = cfg["metadata"]["csa2_layer_modes"]
    oc = cfg["metadata"]["operator_config"]
    row_b = 288 + 68
    start = {}
    for g in pl["groups"]:
        for l in g["layers"]:
            start.setdefault(l["layer"], g["stage"])
    owners = oc["kv_source_layer_ids"]
    readers = {o: [] for o in owners}
    for m in modes:
        L = m["layer"]
        if m["ratio"] == 0:
            continue
        own = max(o for o in owners if o <= L and oc["compress_ratios"][o] == m["ratio"])
        readers[own].append(L)
    lb = lane_budget()
    rows, per_stage = {}, {}
    for o in owners:
        r = oc["compress_ratios"][o]
        st = sorted({start[L] for L in readers[o]})
        ingest_b = CTX // r * row_b
        rows[o] = dict(owner_stage=start[o], ratio=r, reader_layers=readers[o], reader_stages=st,
                       ring_hops=max(st) - start[o], decode_bytes_per_token=row_b / r,
                       decode_ring_bytes_per_token=row_b / r * (max(st) - start[o]),
                       ingest_bytes_per_user_1m=ingest_b, replicas=len(st))
        for s_ in st:
            per_stage[s_] = per_stage.get(s_, 0) + ingest_b
    window_b = 528 * 128                                            # every layer keeps its own 128-row window ring
    for g in pl["groups"]:
        per_stage[g["stage"]] = per_stage.get(g["stage"], 0) + window_b * len({l["layer"] for l in g["layers"]})
    busiest = max(per_stage.values())
    stack_B = 22.5e9                                               # technology.json hbm3e shipping-derived capacity
    users = int(G * HBM_STACKS_PER_LAYER_DIE * stack_B // busiest)
    ingest_once = sum(v["ingest_bytes_per_user_1m"] for v in rows.values())
    nic = INGEST_NICS * NIC_BPS
    stage_port = 2 * LANES["switch"] * lb["lane_net_Bps"]          # two packages' switch ports per stage
    worst_stage_ingest = max(per_stage.values())
    replicated = sum(per_stage.values())
    pcie_x8_Bps = 24.6e9                                           # ingest agent: Gen5 x8 effective (ab5912ef 0378199a)
    ingest_paths = dict(
        ethernet_switch=dict(
            path="host NICs (2 x 400G) -> the rack's 51.2T switch -> each reader stage's 4-lane 112G switch ports",
            per_package_Bps=LANES["switch"] * lb["lane_net_Bps"],
            replication="switch multicast: the NICs send each owner stream once (%.2f GB per 1M user)" % (ingest_once / 1e9),
            nic_seconds_per_user=ingest_once / nic, extra_hardware="none (ports already in the lane budget)",
            needs="an RDMA-write (RoCEv2-class) target in front of each die's ingest engine"),
        pcie_fabric=dict(
            path="NICs -> PCIe Gen5 switch tree (PEX89144 class) -> x8 endpoint per package (peer-to-peer RDMA)",
            per_package_Bps=pcie_x8_Bps,
            replication="none in PCIe peer-to-peer writes, so the NICs send every replica: %.2f GB per 1M user"
                        % (replicated / 1e9),
            nic_seconds_per_user=replicated / nic,
            extra_hardware=("~%d PCIe switches for 94 x8 endpoints + 2 x16 NICs + host; rack-scale Gen5 cabling "
                            "(MCIO/CDFP) over the rack's 0.3-1.6 m, where retimers are usually needed; an x8 PCIe "
                            "PHY per package outside the 90-lane SerDes budget" % -(-(94 * 8 + 2 * 16 + 16) // 128)),
            needs="PCIe endpoint + peer-to-peer BAR per package"),
        recommendation=("Ethernet-switch path: it reuses budgeted ports and the existing switch, gives %.0f GB/s per "
                        "package against %.1f for PCIe x8, and replicates in the switch. Both paths are hidden under a "
                        "~2.9 s cold 1M GPU prefill when streamed layer by layer (ingest agent)."
                        % (LANES["switch"] * lb["lane_net_Bps"] / 1e9, pcie_x8_Bps / 1e9)))
    return dict(
        row_bytes=row_b, owners=rows, per_stage_bytes_per_user_1m=per_stage,
        replicated_bytes_per_user_1m=replicated, ingest_paths=ingest_paths,
        busiest_stage=max(per_stage, key=per_stage.get), busiest_stage_bytes_per_user=busiest,
        busiest_die_bytes_per_user=busiest / G, users_at_1m_by_capacity=users,
        decode_ring_bytes_per_token=sum(v["decode_ring_bytes_per_token"] for v in rows.values()),
        ingest=dict(bytes_sent_once_per_user=ingest_once, nic_Bps=nic, seconds_per_user_nic=ingest_once / nic,
                    stage_port_Bps=stage_port, worst_stage_bytes=worst_stage_ingest,
                    seconds_per_user_worst_stage_port=worst_stage_ingest / stage_port,
                    path="host NICs -> switch (replicates each owner stream to its reader stages) -> the two "
                         "packages' 4-lane switch ports of each reader stage -> HBM; the ring is not used"),
        note=("replicate-on-write per spec section 15.1; decode multicast rides the ring behind the residual (%d B per "
              "token across all owners and hops); capacity counts the replicas and the 40 window rings (%d B per layer)"
              % (sum(v["decode_ring_bytes_per_token"] for v in rows.values()), window_b)))


def draft_sram_allocation(pl, draft_sram):
    """Allocate the head-die draft-KV SRAM (C10): size with banking overhead, the ROM it displaces, the head die's
    spare ROM, and the read port the draft attention needs.  Beyond the fill the windows live in the head HBM."""
    P = json.loads(PLACEMENT.read_text())
    die_mm2 = 815.0
    envelope = 328.9                                                # N5 compute envelope per die (spec section 9)
    rom_mm2_per_B = (die_mm2 - envelope) / P["rom_bytes_per_die"]   # ROM + its periphery, derived
    bank_overhead = 1.5                                             # ESTIMATE: banking, ports, redundancy, routing
    alloc_mm2 = draft_sram["min_double_buffer_mm2_per_die"] * bank_overhead
    displaced = alloc_mm2 / rom_mm2_per_B
    spare = P["head_die_spare_bytes"]
    block_window_die = draft_sram["window_tokens"] * draft_sram["entry_bytes"] / 4   # one block, one die's quarter
    port_B_cycle = 128
    return dict(
        capacity_bytes_per_die=draft_sram["double_buffer_bytes_per_die"], banks=16,
        bank_bytes=draft_sram["double_buffer_bytes_per_die"] / 16,
        min_mm2=draft_sram["min_double_buffer_mm2_per_die"], bank_overhead=bank_overhead, allocated_mm2=alloc_mm2,
        rom_mm2_per_byte=rom_mm2_per_B, displaced_rom_bytes=displaced, head_die_spare_rom_bytes=spare,
        fits=displaced <= spare,
        read_port_bytes_per_cycle=port_B_cycle, block_window_bytes_per_die=block_window_die,
        block_read_cycles=block_window_die / port_B_cycle,
        placement=("16 banks of %.0f KB beside the drafter's BF16 attention engine; the window of one draft block "
                   "(%.1f KB per die) streams in %.0f cycles on a %d B/cycle port; users beyond the 28-user fill page "
                   "their windows to the head die's HBM (4 stacks, spec C10)"
                   % (draft_sram["double_buffer_bytes_per_die"] / 16 / 1e3, block_window_die / 1e3,
                      block_window_die / port_B_cycle, port_B_cycle)),
        grade="estimate: capacity from the N5 bitcell (spec), overhead 1.5x assumed; floorplan and timing not run")


DRAFT_MACRO = ROOT / "physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.json"


def head_draft_floorplan(pl, draft_sram, alloc):
    """Gate C10: the head die's draft-KV memory built from this repository's ASAP7 SRAM compiler
    (tools/mem_compiler/sram_gen.py; macro ot_sram_1r1w_1024x256_m2_r2c2, 32 KB, 1R1W, row + column repair).

    Organisation: one ROW per user slot of the 28-user fill; a row is 4 macros side by side, so a read is
    4 x 256 = 1,024 bits = 128 B per cycle (the allocation's port) and the write port (new window rows) is
    independent (1R1W).  A row holds 128 KB >= one slot's double-buffered windows (3 blocks x 128 rows x 528 B / 4
    dies x 2).  Rows are stacked in two columns of 14 beside the drafter's BF16 attention engine."""
    m = json.loads(DRAFT_MACRO.read_text())
    ar, t = m["area"], m["timing"]
    f = json.loads(LADDER.read_text())["ladder"][-1]["clock_hz"]
    period_ps = 1e12 / f
    per_slot_B = draft_sram["double_buffer_bytes_per_die"] / FILL
    macro_B = m["capacity_bits"] / 8 if "capacity_bits" in m else 1024 * 256 / 8
    wide = 4                                                       # 4 x 256 b = the 128 B/cycle read port
    row_B = wide * macro_B
    slots = FILL
    macros = slots * wide
    w_um, h_um = ar["macro_width_um"], ar["macro_height_um"]
    halo = 5.0                                                     # um keep-out between macros (ESTIMATE)
    cols, rows_per_col = 2, math.ceil(slots / 2)
    blk_w = cols * (wide * (w_um + halo)) + 60.0                   # + a 60 um channel for the read/write buses
    blk_h = rows_per_col * (h_um + halo)
    mux_ps = 60.0                                                  # 28:1 slot select on the 1,024-bit bus (ESTIMATE)
    wire_ps_per_mm = 120.0                                         # repeated upper-metal wire (ESTIMATE)
    route_mm = 1.0
    ss = t["ss"]
    path_ps = ss["clk_to_q_ps"] + mux_ps + wire_ps_per_mm * route_mm + ss["setup_ps"]
    reads_per_block = alloc["block_window_bytes_per_die"] / (wide * 32)
    return dict(
        macro=dict(name="ot_sram_1r1w_1024x256_m2_r2c2", source=str(DRAFT_MACRO.relative_to(ROOT)),
                   bytes=macro_B, width_um=w_um, height_um=h_um, area_um2=ar["macro_area_um2"],
                   density_mb_per_mm2=ar["density_mb_per_mm2"], fmax_mhz=m["fmax_mhz"],
                   clk_to_q_ps=dict(tt=t["tt"]["clk_to_q_ps"], ss=ss["clk_to_q_ps"]),
                   leakage_uw=t["tt"]["leakage_nw"] / 1e3, read_energy_pj=t["tt"]["read_energy_fj"] / 1e3,
                   write_energy_pj=t["tt"]["write_energy_fj"] / 1e3, repair="2 spare rows + 2 spare IO columns",
                   claim_boundary=m["claim_boundary"]),
        organisation=dict(slots=slots, macros_per_slot=wide, macros=macros, bytes=macros * macro_B,
                          slot_bytes=row_B, needed_per_slot_bytes=per_slot_B, fits=row_B >= per_slot_B,
                          read_port_bits=wide * 256, write_port_bits=wide * 256, ports="1R1W per macro: one "
                          "1,024-bit read port (the draft attention's window stream) and one 1,024-bit write port "
                          "(new window rows from the draft pass and from the KV paging engine)"),
        area=dict(macros_mm2=macros * ar["macro_area_um2"] / 1e6, block_w_mm=blk_w / 1e3, block_h_mm=blk_h / 1e3,
                  block_mm2=blk_w * blk_h / 1e6, vs_allocation_mm2=alloc["allocated_mm2"],
                  displaced_rom_bytes=blk_w * blk_h / 1e6 / alloc["rom_mm2_per_byte"],
                  head_die_spare_rom_bytes=alloc["head_die_spare_rom_bytes"],
                  fits_spare_rom=blk_w * blk_h / 1e6 / alloc["rom_mm2_per_byte"] <= alloc["head_die_spare_rom_bytes"]),
        placement=("two columns of 14 slot-rows (4 macros each) with a 60 um bus channel between them, abutting the "
                   "drafter's BF16 attention engine on the die's core side; the paging engine to the head die's 4 "
                   "HBM3E stacks enters on the write bus"),
        timing=dict(clock_hz=f, period_ps=period_ps, fmax_ss_mhz=m["fmax_mhz"]["ss"],
                    macro_meets_clock=m["fmax_mhz"]["ss"] * 1e6 >= f,
                    read_path_ss_ps=path_ps, margin_required=0.15,
                    read_path_meets_one_cycle=path_ps <= 0.85 * period_ps,
                    pipeline="macro read registered at the macro, then one bus stage to the engine" if path_ps >
                             0.85 * period_ps else "single-cycle read into the engine's input register",
                    read_latency_cycles=2 if path_ps > 0.85 * period_ps else 1,
                    basis="ss clk-to-q + 28:1 select (est.) + 1 mm repeated wire (est.) + setup"),
        power=dict(leakage_mw=macros * t["tt"]["leakage_nw"] / 1e6,
                   block_read_nj=reads_per_block * wide * t["tt"]["read_energy_fj"] / 1e6,
                   block_read_cycles=reads_per_block),
        grade="compiler datasheet (analytical ASAP7 model) for the macros; halo, bus channel, select and wire delay "
              "are ESTIMATES; no floorplan run")


def demonstration_plan(lb):
    """How the whole-system clock and the collective overlap will be demonstrated (gate C7)."""
    ladder = json.loads(LADDER.read_text())["ladder"][-1]
    f = ladder["clock_hz"]

    def lane_B_cycle(lanes):
        return lanes * lb["lane_net_Bps"] / f
    coll_us = LANES_R_L9[str(CTX)]["collective_bytes_us"] if LANES_R_L9 else float("nan")
    hop_c = round(_v("hop_s") * f)
    plan = dict(
        clock=dict(
            architecture=("no rack-wide synchronous clock: every package runs its own PLL from a local reference on its "
                          "tray; die-to-die inside a package is source-synchronous UCIe; every board/cable link is "
                          "plesiochronous (IEEE 802.3 PHYs tolerate +-100 ppm) with an elastic buffer in the endpoint's "
                          "4-cycle clock-domain crossing"),
            target_hz=f,
            steps=[
                dict(id="K1", what="per-block closure at the target",
                     status="exists for the qualified blocks (ASAP7 routes); design-point pools pending",
                     accept="every block's post-route WNS >= 0 at %.3f GHz, read from pnr.json "
                            "place_and_route.metrics, never the pre-layout setup_path.rpt" % (f / 1e9)),
                dict(id="K2", what="layer-die and head-die P&R",
                     status="blocked on the spec's P&R gate (R-U2, R-U9 in RTL)",
                     accept="routed die closes at %.3f GHz at the signoff corner with the clock tree across the die; "
                            "hierarchical, two routes at a time, <= 14 files per umbrella" % (f / 1e9)),
                dict(id="K3", what="plesiochronous link endpoint",
                     status="to build: ot_rom_pkg_link.sv has one clock and a delay-line CDC stand-in",
                     accept="two-clock bench (TX and RX clocks offset by +-100 and +-200 ppm), 1e9 flits, zero "
                            "overflow/underflow, idle-insertion rate sized, first-flit latency within the budgeted "
                            "4 CDC + 5 endpoint cycles"),
                dict(id="K4", what="two-module system run", status="to build",
                     accept="two stage modules (8 dies) on independent clocks run a reduced vehicle bit-exact against "
                            "the golden, cycle count within 2% of the model's"),
            ]),
        overlap=dict(
            claim=("collective bytes chase their producers: a partial streams onto its peer links as the matvec "
                   "produces it, so only the last beats plus one hop are exposed"),
            link_parameters=dict(tp_lanes_per_die_pair=lb["tp_lanes_per_die_pair"],
                                 tp_bytes_per_cycle=lane_B_cycle(lb["tp_lanes_per_die_pair"]),
                                 stage_bytes_per_cycle_per_package=lane_B_cycle(LANES["stage_out"]),
                                 hop_cycles=hop_c, two_step_allreduce=lb["two_step_allreduce"]),
            steps=[
                dict(id="O1", what="one-shot unit at the rack link rate",
                     status="exists at optimistic all-to-all UCIe links (results/rtl/hdc_package_tp_campaign.json)",
                     accept=("re-run tb_rom_oneshot_allreduce with two remote peers on the T1 model (%d lanes, %.0f "
                             "B/cycle, %d-cycle hop) and one UCIe peer: a 20 KB all-reduce completes <= 40 cycles "
                             "after the last partial beat (R-U3) plus one hop; the two-step variant bit-identical on "
                             "all 4 dies" % (lb["tp_lanes_per_die_pair"], lane_B_cycle(lb["tp_lanes_per_die_pair"]),
                                             hop_c))),
                dict(id="O2", what="producer-chased collectives in a stage module",
                     status="to build: package TP bench with the design-point matvec engines streaming into the one-shot",
                     accept=("measured exposed collective time per token, summed over the layer program, <= the lane "
                             "model's %.2f us (results/arch/v41_lanes.json best_split); any excess re-prices the "
                             "headline between it and the no-overlap bound" % coll_us)),
                dict(id="O3", what="link bench parameters at R-L9",
                     status="stale: rom_pkg_link_campaign uses 1,800 B flits (1.8 TB/s)",
                     accept="FLIT_BYTES set to the stage (%.0f B/cycle per package) and TP (%.0f B/cycle per pair) rates"
                            % (lane_B_cycle(LANES["stage_out"]), lane_B_cycle(lb["tp_lanes_per_die_pair"]))),
            ]),
        note="headline rates stay conditional on K2 and O2 (and K3/O1 until their records land)")
    plan = _attach_results(plan)
    return plan


K3_REC = ROOT / "results/rtl/v41_link_cdc_campaign.json"
O1_REC = ROOT / "results/rtl/v41_oneshot_link_campaign.json"
O2_REC = ROOT / "results/rtl/v41_stage_collective_campaign.json"


def _attach_results(plan):
    """Fold landed campaign records into the plan's steps (status + evidence)."""
    if K3_REC.exists():
        k = json.loads(K3_REC.read_text())
        sm = k["summary"]
        s2 = {c["case"]: c for c in k["cases"]}
        for st in plan["clock"]["steps"]:
            if st["id"] == "K3":
                st["status"] = "PASS" if sm["all_pass"] else "FAIL"
                st["evidence"] = str(K3_REC.relative_to(ROOT))
                st["result"] = (
                    "%s flits across two clocks at 0, +-100 and +-200 ppm (1e9 at +200 ppm): zero mismatches, zero "
                    "overflow/underflow; the idle-starved negative case (1 idle per 65,536 at 200 ppm) latches overflow "
                    "as required. Crossing latency 3.0-%.1f RX cycles with 2-flop synchronisers, inside the budgeted "
                    "4 + 1 (output register); 3-flop synchronisers reach %.1f cycles, i.e. +1 cycle (~0.9 ns) per hop "
                    "if the MTBF analysis demands them."
                    % (f"{sm['flits_checked']:,}", s2["rx_slow_200ppm_1e9"]["latency_rx_cycles"]["max"],
                       s2["rx_slow_200ppm_sync3"]["latency_rx_cycles"]["max"]))
    if O1_REC.exists():
        o = json.loads(O1_REC.read_text())
        sm = o["summary"]
        for st in plan["overlap"]["steps"]:
            if st["id"] == "O1":
                st["status"] = "PASS" if sm["all_pass"] and sm["bit_exact"] else "FAIL"
                st["evidence"] = str(O1_REC.relative_to(ROOT))
                st["result"] = sm
    if O2_REC.exists():
        o = json.loads(O2_REC.read_text())
        ln = json.loads(LANES_REC.read_text())
        cx = ln.get("collective_exposure")
        for st in plan["overlap"]["steps"]:
            if st["id"] == "O2" and cx:
                dp, cond = ln["design_point"], ln["design_point_overlap_assumed"]
                st["status"] = "NOT MET (measured)" if any(v["ar"] > 1e-4 for v in cx["loss"].values()) else "PASS"
                st["evidence"] = [str(O2_REC.relative_to(ROOT)), str(LANES_REC.relative_to(ROOT))]
                st["result"] = dict(
                    bench_all_pass=o["summary"]["all_pass"], bit_exact=o["summary"]["bit_exact"],
                    source_binding=cx["campaign_binding"]["current"],
                    exposed_tail_cycles={k: v["measured_exposed_tail_cycles"] for k, v in o["summary"]["patterns"].items()},
                    headline_tokens_s_per_user={c: dict(
                        overlap_assumed=cond[c],
                        measured_exposure_no_levers=dict(ar=ln["design_point_no_levers"][c]["ar"],
                                                         mtp=ln["design_point_no_levers"][c]["mtp"]),
                        with_adopted_levers=dict(ar=dp[c]["ar"], mtp=dp[c]["mtp"])) for c in dp},
                    recovery=dict(levers=cx["levers"]["why"], campaign=cx["levers"]["campaign"],
                                  tails=cx["levers"]["tails"], consumers=cx["levers"]["consumers"],
                                  recovered_share=cx["recovered_share"]))
        if cx:
            plan["note"] = ("O2 measured: the headline is the design point with the bench-measured tails of the adopted "
                            "collective levers (v41_lanes.json design_point; design_point_no_levers is the ablation); "
                            "the overlap-assumed rate is conditional on recovering all of C7; K2 pending")
    return plan


def reprice_sensitivity(pl, links, tr, pwr):
    """Bind the adopted 1M rate to this rack's geometry and expose the two missing physical costs.

    The adopted ladder already credits a one-hop ring return, so relocating the embedding is a
    physical validation of that lever, not a second speed credit.  The baseline is the HEADLINE: the design
    point with the RTL stage bench's measured collective tails and the adopted levers (gate C7, v41_lanes.json
    design_point); the overlap-assumed (conditional) point is kept beside it.  The bytes-only serialisation row
    serialises every on-path collective's payload on one peer link after its producer, from the conditional
    point; it charges bytes only, not the measured fold / hop / row-gather tails, so it is NOT a lower bound (the
    headline sits below it).
    """
    best = json.loads(HBM_BEST.read_text())["rungs"]["top"]["energy"][str(CTX)]["b1"]["rom"]
    top_rung = json.loads(LADDER.read_text())["ladder"][-1]
    overlap_assumed_rate = best["tokens_s_per_user"]
    # baseline: the design point priced on this rack's lanes (R-L9) when available -- its collective bytes already
    # sit on their peer links and its hops on the stage lanes; else the overlap-assumed ladder top
    conditional_rate = LANES_R_L9[str(CTX)]["ar"] if LANES_R_L9 else overlap_assumed_rate
    ln = _c7_lanes()
    baseline_rate = ln["design_point"][str(CTX)]["ar"] if ln else conditional_rate
    baseline_t = 1 / baseline_rate
    conditional_t = 1 / conditional_rate
    hops = len(links["stage_links"])
    base_hop = _v("cable_hop_s") if LANES_R_L9 and LANES_R_L9[str(CTX)].get("hops_us", 0) > 8.0 else _v("hop_s")
    extra_hop = max(0.0, max(x["latency_s"] for x in links["stage_links"]) - base_hop) * hops
    c = tr["collectives"]
    lb = lane_budget()
    ar_peer = c["all_reduce_bytes"] * (0.5 if lb["two_step_allreduce"] else 1.0)
    peer_bytes = ar_peer + c["all_gather_bytes"] / G
    charged = (LANES_R_L9[str(CTX)]["collective_bytes_us"] * 1e-6) if LANES_R_L9 else 0.0
    no_overlap = max(0.0, peer_bytes / lb["tp_per_die_pair_Bps"] - charged)
    geom_rate = 1 / (baseline_t + extra_hop)
    stress_rate = 1 / (conditional_t + extra_hop + no_overlap)
    serdes_w = pwr["serdes"]["total_w"]
    baseline_static_w = pwr["static_total_w"] - serdes_w          # validated leakage + HBM idle (no SerDes)
    dyn_j = best["dynamic_j"] + pwr["mac_energy_delta_j_per_token"]
    return dict(
        evidence_class="analytical sensitivity; not a routed whole-system result",
        baseline=dict(rate_tokens_s=baseline_rate, period_s=baseline_t, clock_hz=top_rung["clock_hz"],
                      dynamic_j_per_token=dyn_j, static_w=baseline_static_w,
                      basis=("design point priced on the R-L9 lanes with the bench-measured C7 collective tails of "
                             "the adopted levers (results/arch/v41_lanes.json design_point)" if ln else
                             "design point priced on the R-L9 lanes (results/arch/v41_lanes.json best_split)"
                             if LANES_R_L9 else "adopted ladder top, collective overlap assumed"),
                      conditional_rate_tokens_s=conditional_rate,
                      overlap_assumed_rate_tokens_s=overlap_assumed_rate),
        geometry=dict(extra_s_per_token=extra_hop, rate_tokens_s=geom_rate,
                      note="29 ring cables at the worst layout-estimated length; adopted ladder already has a one-hop return"),
        no_collective_overlap_stress=dict(extra_s_per_token=no_overlap, rate_tokens_s=stress_rate,
                                          note="from the CONDITIONAL (overlap-assumed) point: all 209 token-collective "
                                               "peer payloads serialised after their producers on one %d-lane peer link "
                                               "(two-step all-reduce: n/2 per peer), minus the bytes it already exposes. "
                                               "Bytes only: the RTL stage bench also measures fold, hop and row-gather "
                                               "tails, so the headline (baseline) is BELOW this row -- it is not "
                                               "a lower bound" % lb["tp_lanes_per_die_pair"]),
        serdes_static=dict(additional_w=serdes_w,
                           geometry_j_per_token=dyn_j + (baseline_static_w + serdes_w) / geom_rate,
                           no_overlap_j_per_token=dyn_j + (baseline_static_w + serdes_w) / stress_rate,
                           note="ROM chip-side correction only; no HBM rack SerDes/infrastructure model, so no energy ratio"),
        embedding_return=dict(previous_switched_s=critical_paths(pl, links)["token_return_via_table_die_s"],
                              adopted_ring_s=critical_paths(pl, links)["token_return_ring_s"],
                              note="the adopted ladder already priced the ring return; relocation validates that premise"))


def build():
    pl = placement()
    el = elevation("liquid", pl)
    el_air = elevation("air", pl)
    links = link_inventory(el)
    tr = traffic(pl)
    pwr = power(el, pl)
    draft_sram = head_draft_sram()
    rec = dict(
        schema="v41_rack/1", tool="tools/v41_rack_design.py", context=CTX, fill=FILL,
        inputs=dict(budget=str(BUDGET.relative_to(ROOT)), utilisation=str(UTIL.relative_to(ROOT)),
                    model=str(V41_CONFIG.relative_to(ROOT))),
        physical_constants=PHYS,
        logical=pl, ring=ring_order(), elevation=el, elevation_air=el_air, lanes=lane_budget(), links=links,
        traffic=tr, power=pwr, head_draft_sram=draft_sram,
        weight=weight_estimate(el), comparison=compare(pwr, el, pl))
    rec["paths"] = critical_paths(pl, links)
    rec["conflicts"] = conflicts(pl, links, tr, pwr, el, draft_sram)
    rec["reprice_sensitivity"] = reprice_sensitivity(pl, links, tr, pwr)
    rec["kv_replication"] = kv_replication(pl)
    rec["head_draft_sram_allocation"] = draft_sram_allocation(pl, draft_sram)
    rec["head_draft_floorplan"] = head_draft_floorplan(pl, draft_sram, rec["head_draft_sram_allocation"])
    rec["demonstration_plan"] = demonstration_plan(lane_budget())
    return rec


def main():
    rec = build()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(rec, indent=1, default=float) + "\n")
    p = rec["power"]
    print("elevation: %d OU used of %d (liquid), %d OU (air)" % (rec["elevation"]["used_ou"], rec["elevation"]["usable_ou"],
                                                                rec["elevation_air"]["used_ou"]))
    print("rack input: provisioned %.1f kW; b1 %.1f kW; fill %.1f kW; fill+MTP %.1f kW; sat+MTP %.1f kW" % (
        p["provisioned_rack_input_w"] / 1e3, *(p["scenarios"][k]["rack_input_w"] / 1e3 for k in ("b1", "fill", "fill_mtp", "saturated_mtp"))))
    for c in rec["conflicts"]:
        print(c["id"], c["severity"], "-", c["finding"][:160])
    print("wrote", OUT.relative_to(ROOT))


if __name__ == "__main__":
    main()
