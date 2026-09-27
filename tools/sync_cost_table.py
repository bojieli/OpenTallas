#!/usr/bin/env python3
"""Synchronisation-cost and power-assumption tables for the paper, every cell with an evidence class and a source.

User directive (2026-09-27): no link latency or power figure from memory; each value the V4.1 rack and the
comparison rely on is backed by a normative spec, a production datasheet/spec, a peer-reviewed paper or a
measurement, quoted verbatim, and optimistic values are corrected in configs/hardware/technology.json.

Inputs (read, never re-derived here):
  results/gpu/blackwell_dependency_latency.json, results/gpu/blackwell_gather_designs.json  (measured GPU boundaries)
  results/rtl/hdc_package_tp_campaign.json   (RTL one-shot all-reduce, 331 cycles per token step per die)
  configs/hardware/technology.json           (link tiers, corrected power inputs)
  tools/decode_critical_path.ArrayFabric     (the cross-package collective as the model prices it)
The per-token OpenTallas totals are the adopted V4.1 DESIGN POINT's headline token (results/arch/v41_lanes.json
design_point, 1M context, batch 1, on the 209 ns rack-cable tier, with the RTL stage bench's MEASURED collective
exposure -- rack gate C7): collective latency + exposed collective bytes + pipeline hops; the specification-width
budget (results/arch/arch_budget_v41.json, whose stage hops ride the same cable tier via
decode_critical_path.ArrayFabric.alpha_stage) is reported beside it.  The power table reads the
tagged power scenarios (configs/hardware/power_scenarios.json, results/arch/power_scenarios.json).

Outputs: results/arch/sync_cost_table.json, results/arch/power_assumptions.json,
         results/arch/figures/sync_cost_table.html (paper snippet: both tables, findings, references).
"""
from __future__ import annotations

import hashlib
import html
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import decode_critical_path as D  # noqa: E402

TECH = ROOT / "configs/hardware/technology.json"
GPU_DEP = ROOT / "results/gpu/blackwell_dependency_latency.json"
GPU_GATHER = ROOT / "results/gpu/blackwell_gather_designs.json"
RTL_TP = ROOT / "results/rtl/hdc_package_tp_campaign.json"
V41_BUDGET = ROOT / "results/arch/arch_budget_v41.json"
V41_LANES = ROOT / "results/arch/v41_lanes.json"
PSCEN_CFG = ROOT / "configs/hardware/power_scenarios.json"
PSCEN = ROOT / "results/arch/power_scenarios.json"
OUT = ROOT / "results/arch/sync_cost_table.json"
OUT_P = ROOT / "results/arch/power_assumptions.json"
OUT_H = ROOT / "results/arch/figures/sync_cost_table.html"

# The V4.1 budget on this branch (tools/arch_budget_v41.py): the baseline's light-FEC package link and the
# stage-hop count of its 28 layer-group stages.
LIGHT_FEC_HOP_S = 130e-9        # tools/arch_budget_v41.BASELINE["board_hop_s"] (asserted in tests)
STAGE_HOPS, V41_COLLECTIVES = 27, 209
# tools/arch_budget_v41.py re-run with and without links.rom_rack_cable_serdes (2026-09-27, this branch): the
# pipeline hops go 9.10 -> 11.95 us per token (36 board traversals x 79 ns)
CABLE_EFFECT = ("+79 ns per stage hop; adopted design (overlap assumed) 8,819 -> 8,622 tok/s/user at 1M (b07a5745); specification budget "
                "at batch 1: 4,978 -> 4,909 at 1M (-1.4%), 5,448 -> 5,365 at 200K (-1.5%), with MTP 10,383 -> 10,309 at 1M; "
                "pipeline hops 9.10 -> 11.95 us per token")


# The ADOPTED V4.1 design point's headline token at 1M, batch 1 (results/arch/v41_lanes.json design_point: the
# design-point model with the RTL stage bench's measured collective exposure, rack gate C7 measured NOT MET).  The
# synchronisation cost is its collective latency + the collective bytes the bench measured as exposed + the stage
# hops; the specification-width budget (results/arch/arch_budget_v41.json) is reported beside it (v41_spec_budget)
# so the two are never confused.
def v41_design_point():
    ln = json.loads(V41_LANES.read_text())
    d = ln["design_point"]["1048576"]
    b = d["breakdown_us"]
    c = ln["design_point_overlap_assumed"]["1048576"]
    return dict(T_us=round(d["T_us"], 3), tokens_s_per_user=d["ar"], collective_latency_us=round(b["collective_latency"], 3),
                collective_exposed_bytes_us=round(b["collective_bytes"], 3), pipeline_hops_us=round(b["pipeline_hops"], 3),
                stage_hops=STAGE_HOPS, collectives=V41_COLLECTIVES, overlap_assumed_tokens_s_per_user=c["ar"],
                source="results/arch/v41_lanes.json design_point['1048576'] (design-point model, collective exposure "
                       "measured in the RTL stage bench, 209 ns rack-cable tier)")


LADDER = v41_design_point()


def v41_spec_budget():
    """Collective latency and pipeline hops of the SPECIFICATION-width V4.1 token at 1M, batch 1 (this branch)."""
    r = json.loads(V41_BUDGET.read_text())["required_priced"]["1048576"]
    b = r["breakdown_us"]
    return dict(T_us=r["T_us"], tokens_s_per_user=r["tokens_s_per_user"], collective_latency_us=b["collective_latency"],
                pipeline_hops_us=b["pipeline_hops"],
                source="results/arch/arch_budget_v41.json required_priced['1048576'] (tools/arch_budget_v41.py)")


HDC_ISSUE_CYCLES, HDC_CLOCK_HZ = 5, 1.034e9       # dependent issue interval, routed-unit clock used in the paper (Fig. 4-2)
ONESHOT_CLOCK_HZ = 1.006e9                        # ot_rom_oneshot_die routed on ASAP7 (1,006-1,068 MHz, not closed)
QWEN_BOUNDARIES = 220                             # all-SM boundaries per Qwen3-8B token (paper Fig. 4-2 caption)

# ------------------------------------------------------------------------------------------------ references
REFS = {
 "r-sue": dict(text="Broadcom, Scale-Up Ethernet Framework Specification, Scale-Ethernet-RM104, 26 Sep 2025, Appendix A, Figure 22",
   url="https://docs.broadcom.com/doc/scale-up-ethernet-framework", cls="production spec",
   quote="Ethernet Link and PHY Tx+Rx Latency <100ns; Switch Tx+Rx Latency <250ns; Twinax Copper Cable latency/m 4.6ns; 3m Twinax Copper - 100 + 100 + 13.8 + 13.8 + 250 =477.6 ns"),
 "r-ucie-tcpmt": dict(text="D. Das Sharma, G. Pasdast, Z. Qian, K. Aygun, Universal Chiplet Interconnect Express (UCIe): An Open Industry Standard for Innovations With Chiplets at Package Level, IEEE Trans. CPMT 12(9):1423, Sept 2022, Table I",
   url="http://emlab.uiuc.edu/ece546/appnotes/UCie_Paper.pdf", cls="normative (spec key metrics), peer-reviewed",
   quote="Latency (Tx + Rx) < 2ns Includes D2D Adapter and PHY (FDI to bump and back); Channel Reach (mm) <= 25 <=2"),
 "r-ucie-jssc26": dict(text="UCIe advanced-package transceiver, 3 nm CoWoS, IEEE JSSC 2026, doi:10.1109/JSSC.2026.3651425",
   url="https://doi.org/10.1109/JSSC.2026.3651425", cls="measured silicon, peer-reviewed",
   quote="exhibit 0.29 pJ/bit power efficiency with 5.27Tb/s/mm bandwidth density and 3.5 ns measured FDI-to-FDI latency ... for 16 Gb/s/pin operation"),
 "r-ucie-hc23": dict(text="UCIe Consortium, Hot Chips 2023 tutorial, Electrical Summary",
   url="https://www.hc2023.hotchips.org/assets/program/tutorials/ucie/Electrical%20Form%20Factor%20and%20Compliance.pdf", cls="consortium spec targets",
   quote="Power Efficiency Target (pJ/b) ... 0.3-0.6 [Adv 16] 0.3-0.6 [Adv 24/32]; Idle Power (% of peak) 15%"),
 "r-gustlin3ck": dict(text="M. Gustlin et al., Interleaved 100GbE FEC Sublayer, IEEE P802.3ck, Nov 2018, p.8",
   url="https://www.ieee802.org/3/ck/public/18_11/gustlin_3ck_01_1118.pdf", cls="standards-body contribution",
   quote="Current Clause 91 RS544 Latency: 51ns Block time / 50-100ns Processing* / 101-151ns Total; Potential RS544 Interleaved: 102ns Block time / 50-150ns Processing* / 152-252ns Total"),
 "r-nicholl3ck": dict(text="G. Nicholl, P. Jones, Sublayer Delay for Interleaved 100G FEC, IEEE P802.3ck, Jan 2020 (quoting IEEE 802.3-2018 Table 80-5 and Clause 91.4)",
   url="https://www.ieee802.org/3/ck/public/20_01/nicholl_3ck_01a_0120.pdf", cls="normative text (quoted) / standards-body contribution",
   quote="The current 100GBASE-R RS-FEC Sublayer delay is 40960 bit times = 80 pause_quanta = 409.60 ns; CL161 Interleaved 100G FEC consumes an additional 51-102 ns of latency beyond CL91 latency"),
 "r-brown3cd": dict(text="T. Brown, A. Ran, Addressing Delay, Skew, and Skew Variation, IEEE P802.3cd, Nov 2016, slides 7-9",
   url="https://www.ieee802.org/3/cd/public/Nov16/brown_3cd_03_1116.pdf", cls="standards-body contribution (adopted)",
   quote="The minimum decoding delay is ~55 ns for storing a codeword; another ~55 for error marking; PMA 92.16 ns; CR/KR PMD 81.92 ns"),
 "r-sun3cd": dict(text="P. Sun (Credo), Feasibility of 50GE Low-latency Schemes, IEEE 802.3 50GE/NGOATH ad hoc, 2 Mar 2016, slide 7",
   url="https://www.ieee802.org/3/cd/public/adhoc/archive/sun_030216_50GE_NGOATH_adhoc.pdf", cls="standards-body contribution",
   quote="RS(272,257) ... ~99ns; RS(544,514), KP4 ... ~198ns; RS(272,257), RS(181,172), or RS(136,129) can be added to KP4 implementation with negligible cost, and achieves 1/2, 1/3, or 1/4 of KP4 latency"),
 "r-llfec": dict(text="25G/50G Ethernet Consortium (Ethernet Technology Consortium), Low Latency Reed Solomon FEC Specification 1.0, 9 Nov 2018, s3 and Annex A Table 1",
   url="https://ethernettechnologyconsortium.org/wp-content/uploads/2020/03/LL-FEC-Specification-1.0-25G-Consortium.pdf", cls="consortium spec",
   quote="As the codeword length is half the codeword length of RS(544), it expected that the overall latency associated with error correction will scale accordingly; required BER (FLR 6.2e-10): RS(544,514) 3.7677e-04 random / 5.7878e-05 burst a=0.75; RS(272,258) 9.9248e-05 / 8.8834e-09"),
 "r-ualink": dict(text="UALink Consortium, UALink 200G 1.0 Specification white paper, Apr 2025",
   url="https://ualinkconsortium.org/wp-content/uploads/2025/04/UALink-1.0-White_Paper_FINAL.pdf", cls="consortium white paper",
   quote="operates in additional codeword interleave modes, with reduced interleave, to achieve better FEC latency at the cost of decreased burst error correction; 640-byte Flits from the DL fit exactly into one RS (544, 514) codeword; cable length < 4 meters"),
 "r-oif-cei5": dict(text="OIF, Common Electrical I/O (CEI) 5.0 Implementation Agreement, OIF-CEI-05.0, 5 May 2022, clauses 26-27",
   url="https://www.oiforum.com/wp-content/uploads/OIF-CEI-5.0.pdf", cls="industry implementation agreement",
   quote="CEI-112G-MR: up to 500 mm of PCB and up to 1 connector, raw BER 10-6 or better; CEI-112G-LR: up to 1000 mm of backplane and up to 2 connectors, raw BER 10-4 or better; The definition of FEC is outside the scope of this IA"),
 "r-ieee3ck-obj": dict(text="IEEE P802.3ck objectives (Mar 2018); IEEE Std 802.3ck-2022 approved 21 Sep 2022; IEEE P802.3dj objectives (14 Mar 2024)",
   url="https://www.ieee802.org/3/ck/P802_3ck_Objectives_2018mar.pdf", cls="standards body",
   quote="twin-axial copper cables with lengths up to at least 2 m (100 Gb/s per lane); P802.3dj: a reach of up to at least 1.0 meter (200 Gb/s per lane)"),
 "r-dassharma-ofa": dict(text="D. Das Sharma, OpenFabrics Workshop 2023 keynote; D. Das Sharma, UCIe 2.0, IEEE BUSS 2025",
   url="https://www.openfabrics.org/wp-content/uploads/2023-workshop/2023-workshop-presentations/day-2/201_DDasSharma.pdf", cls="spec-chair presentation",
   quote="PHY latency (Tx + Rx) = 20+ ns (+ >100 FEC) [networking]; PCIe/CXL: PHY latency (Tx+ Rx: PHY-PIPE) = <10ns (0-1ns FEC overhead); UCIe: <2ns"),
 "r-cxl-survey": dict(text="D. Das Sharma, R. Blankenship, D. Berger, An Introduction to the Compute Express Link (CXL) Interconnect, arXiv:2306.11227 (ACM CSUR), s5.1, s6",
   url="https://arxiv.org/abs/2306.11227", cls="peer-reviewed survey by the spec authors",
   quote="The total latency from the SERDES pin to the internal application layer ... and back is 21 ns in common reference clock mode and 25 ns in independent reference clock mode; applying CRC first helps reduce the latency by 2 nanoseconds on a x16 link"),
 "r-uec": dict(text="Ultra Ethernet Consortium, UE Specification 1.0.3, 16 Jul 2026, s6.3, Tables 6-7, 6-10, 6-11",
   url="https://ultraethernet.org/wp-content/uploads/sites/20/2026/08/UE-Specification-1.0.3.pdf", cls="normative spec",
   quote="FLR = UCR x (CIR + 1/FPC); MTBPE = T_CW / UCR; the link is always protected by ... RS(544,514)"),
 "r-ti-scaa082": dict(text="Texas Instruments, High-Speed Layout Guidelines, SCAA082A, s1.3.1 Table 2", url="https://www.ti.com/lit/an/scaa082a/scaa082a.pdf",
   cls="vendor application note", quote="Stripline ... 4.6 [er] ... 139.8 [mm/ns] ... 715.3 [ps per 100 mm]"),
 "r-megtron6": dict(text="Panasonic, MEGTRON 6 (R-5775) datasheet", url="https://industrial.panasonic.com/ww/products/pt/megtron/megtron6",
   cls="manufacturer datasheet", quote="Dk 3.34 (R-5775(N), 13 GHz); 3.62 (normal glass)"),
 "r-belden": dict(text="Belden 9207 and 9182 twinax datasheets (rev. 0.535, 2026-02-20)", url="https://catalog.belden.com/techdata/EN/9207_techdata.pdf",
   cls="manufacturer datasheet", quote="Nom. Velocity of Prop. 66% (9207); 78% (9182)"),
 "r-sol": dict(text="Shen, Korzh, Bachan et al., Every Microsecond Matters: Achieving Near Speed-of-Light Latency in GPU Collectives, arXiv:2607.16100 (2026), s1 Fig. 1, s6, s7-C",
   url="https://arxiv.org/abs/2607.16100", cls="measured (GB200 NVL72), preprint",
   quote="On two GB200, we measured the L_L2_RTT and L_remote_store as 0.306 us and 0.792 us, respectively. Therefore, the SoL latency of an AllReduce is computed to be 1.404 us; ... an absolute lower bound that is independent of the number of ranks involved; [Fig. 1, 4 GB200] 2.37 us low-latency kernel vs 11.0 us NCCL ring"),
 "r-nccl227": dict(text="NVIDIA, Enabling Fast Inference and Resilient Training with NCCL 2.27, technical blog, 14 Jul 2025 (Fig. 1 corrected 1 Oct 2025)",
   url="https://developer.nvidia.com/blog/enabling-fast-inference-and-resilient-training-with-nccl-2-27/", cls="vendor measurement",
   quote="up to 9x reduction in latency for small message sizes ... Results from NVIDIA GB200, 32-Ranks [chart: ~5 us all-reduce, 8 B-4 KB]"),
 "r-nccl-cost": dict(text="NVIDIA NCCL v2.32.3, src/tuning/cost_model.cc (baseLatencies, hwLatencies) and src/tuning/sym_model/lsa_base.cc",
   url="https://github.com/NVIDIA/nccl", cls="vendor source code (cost model)",
   quote="{6.6, 14.0, 8.4}, // Ring [baseLat, us]; {0.6, 1.9, 3.4}, // Ring (LL/LL128/Simple) [NVLINK hwLat, us]; Blackwell symmetric LL all-reduce baseLat 11.0"),
 "r-anton3": dict(text="K. Shim et al., The Specialized High-Performance Network on Anton 3, HPCA 2022, arXiv:2201.08357, s3-C, Fig. 5-6",
   url="https://arxiv.org/abs/2201.08357", cls="measured, peer-reviewed",
   quote="a linear fit of 55.9 ns of fixed overhead plus 34.2 ns of per-hop latency; The minimum inter-node latency measured for a single hop was approximately 55 ns, almost half that of the Anton 2 network (99 ns); Tofu interconnect D ... has a minimum one-way latency of 490 ns"),
 "r-bgq": dict(text="IBM, IBM System Blue Gene Solution: Blue Gene/Q Application Development, Redbook SG24-7872-01, s2.1, May 2013",
   url="https://www.redbooks.ibm.com/redbooks/pdfs/sg247872.pdf", cls="vendor technical document",
   quote="The latency of each hop is approximately 35 ns ... The direct neighbor one-way latency is 0.3 us; powerful Reed-Solomon error detection codes with retry on the links"),
 "r-slingshot": dict(text="D. De Sensi et al., An In-Depth Analysis of the Slingshot Interconnect, SC20, arXiv:2008.08886, s2-A, Fig. 2",
   url="https://arxiv.org/abs/2008.08886", cls="measured, peer-reviewed",
   quote="ROSETTA has a mean and median latency of 350 nanoseconds, with all the distribution lying between 300 and 400 nanoseconds; low-latency Forward Error Correction (FEC)"),
 "r-pcie6-fec": dict(text="Synopsys, PCIe 6.0 Verification of FEC and CRC, 22 Aug 2022", url="https://www.synopsys.com/blogs/chip-design/pcie-6-verifaction-fec-crc.html",
   cls="vendor", quote="To keep the latency (<2ns) and complexity low, a lightweight FEC is used which can correct a single byte error; The retry probability per FLIT is around 5x10^-6"),
 "r-gpu-meas": dict(text="OpenTallas, Blackwell dependent-boundary microbenchmarks (RTX PRO 6000 Blackwell, GB202, 188 SMs): results/gpu/blackwell_dependency_latency.json, blackwell_gather_designs.json, blackwell_sync_breakdown.json",
   url="", cls="measured (this work)", quote=""),
 "r-rtl-tp": dict(text="OpenTallas, package tensor-group RTL campaign, results/rtl/hdc_package_tp_campaign.json (Verilator, one-shot all-reduce engine rtl/rom/ot_rom_oneshot_allreduce.sv)",
   url="", cls="RTL simulation (this work)", quote=""),
 # power
 "r-keller": dict(text="B. Keller et al., A 17-95.6 TOPS/W Deep Learning Inference Accelerator with Per-Vector Scaled 4-bit Quantization for Transformers in 5nm, 2022 Symposium on VLSI Technology and Circuits, pp. 16-17, Table 2 (journal version IEEE JSSC 2023, doi:10.1109/JSSC.2023.3234893)",
   url="https://d1qx31qr3h6wln.cloudfront.net/publications/C02-1.PDF", cls="measured silicon, peer-reviewed; INTEGER arithmetic",
   quote="Table 2: 'INT4 / INT4 VSQ / INT8'; '91.1\u2020 (0.46V)' '95.6\u2020 (0.46V)' '39.1\u2020 (0.46V)' TOPS/W; '\u2020 Measured with 50% non-zero input densities. Includes estimated leakage power.'; p.16: '24b partial sums are temporally accumulated in a 16-entry latch array'"),
 "r-sc25": dict(text="O. Antepara, Z. Zhao, B. Austin, N. Ding, L. Oliker, N. J. Wright, S. Williams, Benchmark-driven Models for Energy Analysis and Attribution of GPU-Accelerated Supercomputing, SC'25, doi:10.1145/3712285.3759815, Fig. 1 and Table 3",
   url="https://escholarship.org/content/qt6189368s/qt6189368s.pdf", cls="measured (regressed from board power), peer-reviewed",
   quote="Fig. 1: 'n.b., memory controller energy is tabulated with HBM energy.'; Table 3 HBM [pJ/bit] control / datapath / total: A100 8.47 / 4.64 / 13.11, GH200 8.69 / 2.99 / 11.68, MI250X GCD 11.82 / 1.82 / 13.64, MI300A 13.47 / 1.25 / 14.72; s4.1 'by performing computations on zeros, we exercise only the control plane'; Matrix-FP16 control 0.37 / datapath 0.33 pJ/FLOP"),
 "r-signoff": dict(text="OpenTallas, ASAP7 energy-per-token sign-off, results/physical_abi3/asap7/signoff/energy_per_token.json (routed matrix engine, TT, RTL activity)",
   url="", cls="measured-ours (predictive PDK)", quote=""),
 "r-tpuv4i": dict(text="N. Jouppi et al., Ten Lessons From Three Generations Shaped Google's TPUv4i, ISCA 2021, doi:10.1109/ISCA52012.2021.00010, Tables 1-2",
   url="https://doi.org/10.1109/ISCA52012.2021.00010", cls="peer-reviewed",
   quote="[7 nm, pJ] Int 8 mult 0.070; Int 32 add 0.030; BFloat 16 mult 0.210; IEEE FP 32 add 0.380, mult 1.310; Idle Power (Watts) Chip 55; Die Size < 400 mm2"),
 "r-tsmc-n5": dict(text="G. Yeap et al. (TSMC), 5nm CMOS Production Technology Platform, IEDM 2019/2020, doi:10.1109/IEDM13553.2020.9372009",
   url="https://doi.org/10.1109/IEDM13553.2020.9372009", cls="peer-reviewed (foundry)",
   quote="~1.8x improvement in logic density, 15% speed gain and 30% power reduction as compared to its previous 7nm generation"),
 "r-h100-idle": dict(text="H100 power characterisation, arXiv:2605.23918, Table 2", url="https://arxiv.org/abs/2605.23918", cls="measured, preprint",
   quote="Bare idle: 71.8 W; Bare idle (345 MHz): mean 74.7 W +/- 7.9 W"),
 "r-tpuv4": dict(text="N. Jouppi et al., TPU v4: An Optically Reconfigurable Supercomputer, ISCA 2023, arXiv:2304.01433, Table 4",
   url="https://arxiv.org/abs/2304.01433", cls="measured, peer-reviewed",
   quote="Idle, min/mean/max power 90, 121/170/192 W; 7 nm, <600 mm2; Measured power is for the ASIC and HBM"),
 "r-oconnor": dict(text="M. O'Connor et al., Fine-Grained DRAM: Energy-Efficient DRAM for Extreme Bandwidth Systems, MICRO 2017, s1-2, Table 3",
   url="https://d1qx31qr3h6wln.cloudfront.net/publications/MICRO_2017_Fine_Grained_DRAM.pdf", cls="peer-reviewed",
   quote="The energy to access a bit in HBM2 is approximately 3.97 pJ/bit; ... requires 2.24 pJ/bit ... an additional 0.3 pJ/bit ... with the average of 1.21 pJ/bit of activation energy, each HBM2 access incurs 3.92 pJ/bit of energy (including ECC overhead); Table 3 I/O (pJ/b)* 0.80 (*at 50% activity)"),
 "r-serdes-vlsi22": dict(text="112 Gb/s PAM4 transceiver with DSP in 5 nm, VLSI 2022, doi:10.1109/VLSITechnologyandCir46769.2022.9830304",
   url="https://doi.org/10.1109/VLSITechnologyandCir46769.2022.9830304", cls="measured silicon, peer-reviewed",
   quote="achieves a total power efficiency of 5.6pJ/b per lane including analog and DSP at 112Gb/s"),
 "r-serdes-jssc21": dict(text="7 nm 112 Gb/s PAM4 long-reach transceiver, IEEE JSSC Jan 2021, doi:10.1109/JSSC.2020.3024261",
   url="https://doi.org/10.1109/JSSC.2020.3024261", cls="measured silicon, peer-reviewed", quote="dissipating 602 mW per channel, excluding DSP"),
 "r-80plus": dict(text="80 PLUS Titanium efficiency table (230 V internal redundant)", url="https://en.wikipedia.org/wiki/80_Plus",
   cls="normative table (secondary copy)", quote="N.D. | 90% | 94% | 96% | 91% [10/20/50/100% load]"),
 "r-vicor": dict(text="Vicor NBM2317S60D1580T0R bus converter datasheet", url="https://www.vicorpower.com/documents/datasheets/ds-NBM2317S60D1580T0R-VICOR.pdf",
   cls="production datasheet", quote="97.9% peak efficiency; Efficiency (Ambient) ... I_LO_OUT_DC = 80A ... 95.6 %"),
 "r-vr48": dict(text="Vertical power delivery for AI accelerators, arXiv:2309.10141, s2-3", url="https://arxiv.org/abs/2309.10141", cls="peer-reviewed modelling",
   quote="The reference architecture (A0) is modeled with a 90% efficient 48V-to-1V converter; over 30% power loss has recently been reported in state-of-the-art AI accelerators"),
 "r-coolit": dict(text="CoolIT Systems CHx2000 CDU datasheet", url="https://www.coolitsystems.com/chx2000/", cls="production datasheet",
   quote="Cooling Capacity: 2000 kW; Power Consumption: 12.24 kW"),
 "r-gb200-guide": dict(text="NVIDIA DGX GB200 User Guide, s1.4 Hardware (updated 2026-09-17); NVIDIA Blackwell datasheet (2025-10-28)",
   url="https://docs.nvidia.com/dgx/dgxgb200-user-guide/hardware.html", cls="vendor normative",
   quote="The rack power consumption is approximately 120kW; ... 33kW per power shelf; Max Thermal Design Power (TDP) Configurable up to 1,200 W"),
 "r-h200": dict(text="NVIDIA H200 product page (H200 SXM / NVL specifications); NVIDIA Hopper Architecture In-Depth (GH100 die size); NVIDIA DGX H100/H200 User Guide, Introduction (environmental and power specifications)",
   url="https://www.nvidia.com/en-us/data-center/h200/", cls="vendor specification",
   quote="H200 SXM 'Max Thermal Design Power (TDP) Up to 700W (configurable)', 'GPU Memory 141GB', 'GPU Memory Bandwidth 4.8TB/s'; Hopper blog 'a die size of 814 mm 2'; DGX H100/H200 'Airflow 1105 CFM Front-to-Back', '10.2 kW max.'"),
 "r-dgxb200": dict(text="NVIDIA DGX B200 product page and DGX B200 User Guide, Introduction; NVIDIA Blackwell architecture page",
   url="https://docs.nvidia.com/dgx/dgxb200-user-guide/introduction-to-dgxb200.html", cls="vendor specification",
   quote="'8x NVIDIA Blackwell GPUs', '1,440 GB total, 64 TB/s HBM3e bandwidth', '~14.3 kW max'; 'Airflow 1,550 CFM'; 'All NVIDIA Blackwell products feature two reticle-limited dies'; Blackwell datasheet '1,000 W HGX B200'"),
 "r-gaudi3": dict(text="Intel Gaudi 3 AI Accelerator White Paper",
   url="https://cdrdv2-public.intel.com/817486/gaudi-3-ai-accelerator-white-paper.pdf", cls="vendor specification",
   quote="'supports up to 900W Total Device Power (TDP) with passive cooling and up to 900W TDP with liquid cooling'; 'two compute dies'; '8 HBM2e devices ... 3.7 TB/s'"),
 "r-amd-instinct": dict(text="AMD Instinct MI300X, MI350X and MI355X product specifications",
   url="https://www.amd.com/en/products/accelerators/instinct/mi350/mi355x.html", cls="vendor specification",
   quote="MI300X 'Total Board Power (TBP) 750W Peak', 'Cooling Passive OAM'; MI350X 'Total Board Power (TBP) 1000W', 'Cooling Passive OAM'; MI355X 'Total Board Power (TBP) 1400W', 'Cooling Passive & Active'"),
 "r-smc-nvl72": dict(text="Supermicro SuperCluster GB200 NVL72 datasheet (2025-09-12)", url="https://www.supermicro.com/datasheet/datasheet_SuperCluster_GB200_NVL72.pdf",
   cls="OEM datasheet", quote="total power 132kW; Operating Power 125kW to 135kW"),
 "r-mlperf51": dict(text="MLCommons, MLPerf Inference v5.1 results, ID 5.1-0061 (Lenovo SR680a V3, 8 x B200), Llama-2-70B Offline",
   url="https://github.com/mlcommons/inference_results_v5.1", cls="measured, audited", quote="Power_Result: 10400.9988793425, Power_Units: Watts"),
 "r-b200-decode": dict(text="B200 disaggregated serving power measurement, arXiv:2609.11133", url="https://arxiv.org/abs/2609.11133", cls="measured, preprint",
   quote="Decode natural draw held at 688-689 W"),
 "r-fan-barroso": dict(text="X. Fan, W.-D. Weber, L. A. Barroso, Power Provisioning for a Warehouse-sized Computer, ISCA 2007",
   url="https://static.googleusercontent.com/media/research.google.com/en//archive/power_provisioning.pdf", cls="measured, peer-reviewed",
   quote="only reach a maximum of 145W, which is less than 60% of the nameplate value; noticeable gap (7 - 16%) between achieved and theoretical aggregate peak"),
 "r-polca": dict(text="P. Patel et al., POLCA: Power Oversubscription in LLM Cloud Providers, arXiv:2308.12908", url="https://arxiv.org/abs/2308.12908",
   cls="measured, production data", quote="LLM inference clusters utilize only up to 80% of the provisioned power ... often going beyond GPU's TDP values"),
}


def sha_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def build():
    tech = json.loads(TECH.read_text())
    dep = json.loads(GPU_DEP.read_text())
    gat = json.loads(GPU_GATHER.read_text())
    rtl = json.loads(RTL_TP.read_text())
    Ln = tech["links"]
    spec = v41_spec_budget()
    cable = Ln["rom_rack_cable_serdes"]["hop_latency_s"]
    ucie = Ln["rom_package_ucie"]["hop_latency_s"]

    # ---- measured GPU primitives
    handoff = dep["best_min_ns"]["flag_pingpong_handoff_ns"]
    pdl = dep["best_min_ns"]["pdl_boundary_ns"]
    allsm = gat["conclusions"]["lowest_all_sm_gather_with_data_ns"]["bf16_8KiB"]
    # ---- RTL one-shot
    pk = rtl["packages"][0]
    cyc_step = pk["collective_cycles_per_step_per_die"]
    ncoll = sum(rtl["tensor_split"]["collectives_per_token"].values())
    oneshot_cycles = cyc_step / ncoll
    oneshot_ns = oneshot_cycles / ONESHOT_CLOCK_HZ * 1e9
    hdc_ns = HDC_ISSUE_CYCLES / HDC_CLOCK_HZ * 1e9
    # ---- model: cross-package TP4 all-reduce of 20 KB (FP32 hidden 5,120), package pair, on-module link
    links = D.link_consts(tech)
    light = dict(links, rom_board_serdes=dict(links["rom_board_serdes"], hop=LIGHT_FEC_HOP_S))
    fab = D.ArrayFabric(light, 2, "ring", 4, "best")
    ar = fab.collective("all_reduce", 20480, 4)
    ar_ns = (ar["latency_s"] + ar["bytes_s"]) * 1e9
    fab_f = D.ArrayFabric(links, 2, "ring", 4, "best")     # the package link at technology.json's full-KP4 hop
    ar_f = fab_f.collective("all_reduce", 20480, 4)
    ar_f_ns = (ar_f["latency_s"] + ar_f["bytes_s"]) * 1e9
    # one stage hop in the rack = one cable hop (the folded ring puts consecutive stages on adjacent modules) + UCIe fan-out
    stage_ns = (cable["value"] + ucie["value"]) * 1e9
    # ---- GPU cross-package points (arXiv:2607.16100, NCCL)
    sol_us, best_us, nccl_ring_us, nccl227_us, remote_store_us = 1.404, 2.37, 11.0, 5.0, 0.792
    # ---- per token, V4.1 at 1M, batch 1
    rom_tok_us = LADDER["collective_latency_us"] + LADDER["collective_exposed_bytes_us"] + LADDER["pipeline_hops_us"]
    gpu_tok = {k: LADDER["collectives"] * v + LADDER["stage_hops"] * remote_store_us
               for k, v in (("best_kernel", best_us), ("nccl_2_27", nccl227_us), ("nccl_ring", nccl_ring_us), ("sol", sol_us))}

    def cell(value, unit, cls, refs, note=""):
        return dict(value=value, unit=unit, evidence=cls, refs=refs, note=note)

    rows = [
     dict(event="On-chip dependent handoff (one producer -> consumer)",
          gpu=cell(round(handoff), "ns", "measured", ["r-gpu-meas"], f"persistent-kernel flag handoff through L2 (PDL boundary {pdl:.0f} ns); GB202, not B200"),
          ot=cell(round(hdc_ns, 1), "ns", "RTL simulation", ["r-rtl-tp"], f"{HDC_ISSUE_CYCLES}-cycle dependent issue at {HDC_CLOCK_HZ/1e9:.3f} GHz (routed units)"),
          ratio=round(handoff / hdc_ns)),
     dict(event="On-chip all-unit gather (every SM / lane -> next op)",
          gpu=cell(round(allsm), "ns", "measured", ["r-gpu-meas"], "best of 12 designs, bf16 vector delivered to all 188 SMs"),
          ot=cell(round(hdc_ns, 1), "ns", "RTL simulation", ["r-rtl-tp"], "the schedule is compiled: a lane-array reduction retires into the next issue"),
          ratio=round(allsm / hdc_ns)),
     dict(event="In-package die-to-die collective (all-reduce over the dies of one package)",
          gpu=cell(None, "ns", "not published", [], "B200 NV-HBI cross-die latency is not published; the nearest measured analogue is the all-SM gather above"),
          ot=cell(round(oneshot_ns), "ns", "RTL simulation", ["r-rtl-tp", "r-ucie-tcpmt", "r-ucie-jssc26"],
                  f"one-shot fixed-order all-reduce of 128 fp32 over 4 dies: {cyc_step:.0f} cycles per token step / {ncoll} collectives = "
                  f"{oneshot_cycles:.1f} cycles, with a {rtl['ucie_link']['lat_cycles']}-cycle UCIe model (spec <2 ns PHY+adapter; measured 3.5 ns FDI-to-FDI; model charges 10 ns)"),
          ratio=round(allsm / oneshot_ns)),
     dict(event="Cross-package point-to-point handoff (pipeline stage hop)",
          gpu=cell(round(remote_store_us * 1e3), "ns", "measured", ["r-sol"], "GB200 remote store over NVLink, one way"),
          ot=cell(round(stage_ns), "ns", "model, normative basis", ["r-ualink", "r-gustlin3ck", "r-llfec", "r-sue"],
                  f"rack-cable tier {cable['value']*1e9:.0f} ns (full RS(544,514), un-interleaved) + UCIe fan-out"),
          ratio=round(remote_store_us * 1e3 / stage_ns, 1)),
     dict(event="Cross-package collective (TP4 all-reduce, 20 KB)",
          gpu=cell(best_us * 1e3, "ns", "measured", ["r-sol", "r-nccl227"],
                   f"best low-latency kernel, 4 GB200; speed-of-light floor {sol_us} us; NCCL 2.27 ~{nccl227_us:.0f} us (32 ranks); NCCL ring {nccl_ring_us} us"),
          ot=cell(round(ar_ns), "ns", "model, normative basis", ["r-sue", "r-sun3cd", "r-gustlin3ck", "r-ucie-tcpmt", "r-rtl-tp"],
                  f"one-shot: reduce over UCIe, ONE exchange across the pair on the on-module link ({LIGHT_FEC_HOP_S*1e9:.0f} ns light FEC), broadcast over UCIe: "
                  f"{ar['latency_s']*1e9:.0f} ns latency + {ar['bytes_s']*1e9:.0f} ns serialisation; {ar_f_ns:.0f} ns with full KP4"),
          ratio=round(best_us * 1e3 / ar_ns, 1),
          ratio_vs=dict(sol_floor=round(sol_us * 1e3 / ar_ns, 1), nccl_2_27=round(nccl227_us * 1e3 / ar_ns), nccl_ring=round(nccl_ring_us * 1e3 / ar_ns))),
     dict(event="Rack-wide all-reduce (72 GPUs)",
          gpu=cell(sol_us * 1e3, "ns", "measured floor + vendor cost model", ["r-sol", "r-nccl-cost"],
                   "floor 'independent of the number of ranks'; no measured NCCL figure at 72 found; NCCL cost model: ring LL 6.6 + 142 x 0.6 = 92 us, symmetric LL ~11 us"),
          ot=cell(None, "ns", "not on the decode path", [],
                  "tensor groups span 4 dies; no rack-wide collective per token. The token return is one cable hop; Engram requests take the switch (2 x 209 + 250 ns + cable, ~680 ns)"),
          ratio=None),
     dict(event="Per token, V4.1 at 1M context, batch 1 (209 collectives + 27 stage hops)",
          gpu=cell(round(gpu_tok["best_kernel"]), "us", "model on measured primitives", ["r-sol", "r-nccl227"],
                   f"same graph priced at 2.37 us per collective + 0.79 us per stage handoff; NCCL 2.27: {gpu_tok['nccl_2_27']:.0f} us; NCCL ring: {gpu_tok['nccl_ring']:.0f} us; SoL floor: {gpu_tok['sol']:.0f} us"),
          ot=cell(round(rom_tok_us, 1), "us", "model, normative basis", ["r-rtl-tp", "r-sue", "r-ualink"],
                  f"adopted design point, collective exposure measured in the RTL stage bench: collectives {LADDER['collective_latency_us']:.1f} us "
                  f"+ exposed collective bytes {LADDER['collective_exposed_bytes_us']:.1f} us + hops {LADDER['pipeline_hops_us']:.1f} us "
                  f"(27 stage hops on the {cable['value']*1e9:.0f} ns cable tier); {rom_tok_us/LADDER['T_us']:.0%} of the {LADDER['T_us']:.1f} us token. "
                  f"Specification widths (this branch's budget): {spec['collective_latency_us'] + spec['pipeline_hops_us']:.1f} us of "
                  f"{spec['T_us']:.1f} us"),
          ratio=round(gpu_tok["best_kernel"] / rom_tok_us),
          ratio_vs=dict(sol_floor=round(gpu_tok["sol"] / rom_tok_us), nccl_2_27=round(gpu_tok["nccl_2_27"] / rom_tok_us), nccl_ring=round(gpu_tok["nccl_ring"] / rom_tok_us))),
     dict(event="Per token, Qwen3-8B on one die (~220 all-SM boundaries)",
          gpu=cell(round(QWEN_BOUNDARIES * allsm / 1e3), "us", "model on measured primitive", ["r-gpu-meas"], "220 x 1,004 ns"),
          ot=cell(round(QWEN_BOUNDARIES * hdc_ns / 1e3, 2), "us", "RTL-derived", ["r-rtl-tp"], "220 x 4.8 ns"),
          ratio=round(allsm / hdc_ns)),
    ]

    hpc = [
     dict(system="D. E. Shaw Anton 3 (HPCA 2022)", per_hop="34.2 ns/hop", end_to_end="~55 ns one-way to a neighbour node", fec="not stated", refs=["r-anton3"], evidence="measured"),
     dict(system="D. E. Shaw Anton 2", per_hop="not found", end_to_end="99 ns minimum inter-node", fec="not stated", refs=["r-anton3"], evidence="measured (quoted in Anton 3 paper)"),
     dict(system="IBM Blue Gene/Q 5-D torus", per_hop="~35 ns/hop", end_to_end="0.3 us one-way to a neighbour; 2.5 us for 31 hops", fec="RS error detection + link retry", refs=["r-bgq"], evidence="vendor technical document"),
     dict(system="HPE Slingshot (Rosetta switch)", per_hop="350 ns per switch (300-400)", end_to_end="~2-3.5 us MPI", fec="low-latency FEC + LLR", refs=["r-slingshot"], evidence="measured"),
     dict(system="Fujitsu Tofu-D (Fugaku)", per_hop="not found", end_to_end="490 ns minimum one-way", fec="-", refs=["r-anton3"], evidence="secondary"),
     dict(system="Broadcom SUE budget (Tomahawk-Ultra class)", per_hop="endpoint link+PHY <100 ns; switch <250 ns", end_to_end="477.6 ns one-way, 3 m copper, switched", fec="RS-544 or RS-272 + LLR", refs=["r-sue"], evidence="production spec"),
     dict(system="PCIe 6.0 FLIT / CXL", per_hop="FEC <2 ns; PHY Tx+Rx <10 ns", end_to_end="PHY pin-to-app and back 21-25 ns", fec="3-way single-symbol FEC + CRC + replay", refs=["r-pcie6-fec", "r-cxl-survey", "r-dassharma-ofa"], evidence="spec authors / vendor"),
     dict(system="UCIe (advanced package)", per_hop="<2 ns PHY+adapter (spec); 3.5 ns FDI-to-FDI (measured)", end_to_end="-", fec="CRC + retry", refs=["r-ucie-tcpmt", "r-ucie-jssc26"], evidence="normative + measured"),
    ]

    hop_decomp = dict(
      on_module_light_fec_130ns=dict(phy_tx_rx_ns=[20, 60], fec_accumulate_ns=25.6, fec_decode_ns=[25, 50], pcs_alignment_ns=[3, 5],
        flight_ns=0.9, cdc_ns=4, endpoint_ns=5, total_ns=[89, 185], point_ns=130,
        derivation="RS(272,257) codeword 2,720 b / 106.25 Gb/s = 25.6 ns to accumulate on one lane (6.4 ns striped over 4); decode ~half of KP4's 50-100 ns processing; PHY '20+ ns' (Das Sharma) to 56-106 ns (DSP-heavy, inferred); flight 120 mm x 7.15 ns/m (TI); CDC and endpoint from rtl/rom/ot_rom_pkg_link.sv",
        cross_check="Broadcom SUE: endpoint Ethernet link + PHY Tx+Rx <100 ns -> <100 + 0.9 + 9 = <110 ns",
        includes="PHY, FEC, PCS, flight, CDC, fixed-function framing and credit check (credits pre-provisioned)",
        excludes="general bridge/transport layer (Broadcom budgets a separate <100 ns 'Bridge NOC to Ethernet'); link-level retry (only on an uncorrectable codeword)"),
      rack_cable_full_kp4_209ns=dict(phy_tx_rx_ns=[20, 60], fec_accumulate_ns=51.2, fec_decode_ns=[50, 100], flight_ns=3.7, cdc_ns=4, endpoint_ns=5,
        total_ns=[139, 225], point_ns=209,
        derivation="RS(544,514) 5,440 b / 106.25 Gb/s = 51.2 ns block + 50-100 ns processing = Clause 91 '101-151ns Total' (Gustlin); flight 0.8 m x 4.6 ns/m (Broadcom SUE); Clause 161 2-way interleave would add 51-102 ns",
        normative_ceiling_ns=583.7, ceiling_basis="IEEE 802.3 RS-FEC 409.6 + PMA 92.16 + CR/KR PMD 81.92 ns per direction (Nicholl & Jones; Brown & Ran)"),
      ber_tail=dict(
        method="random-symbol-error arithmetic on 10-bit symbols, P(codeword uncorrectable) = P(> t symbol errors); DFE bursts make it worse (LL-FEC Table 1)",
        codewords_per_token=dict(rs272=47000, rs544=23500, basis="T1 13.9 MB + T2 1.15 MB per token (results/arch/v41_rack.json traffic.per_token)"),
        rs272_t7=dict(ber_1e_6=6.7e-26, ber_1e_5=6.5e-18, ber_1e_4=5.3e-10, ber_2_4e_4=4.2e-7),
        rs544_t15=dict(ber_1e_6=2.2e-50, ber_1e_5=2.1e-34, ber_1e_4=1.4e-18, ber_2_4e_4=8.2e-13),
        reading=("On the OIF MR-class on-module channel (raw BER <= 1e-6) the light code's retry probability per token is ~3e-21: nothing. "
                 "On a CR-class cable at a compliant-limit raw BER near 2.4e-4 it would be ~2% of tokens retrying (47,000 x 4.2e-7), and under "
                 "DFE bursts the LL-FEC spec needs raw BER <= 8.9e-9; hence the cable tier runs full RS(544,514), whose tail at 2.4e-4 is 2e-8 per token.")),
      all_reduce_crossings=("A one-shot TP4 all-reduce across a package pair crosses the package link ONCE (each package sends its partial and both "
                            "reduce in fixed order) plus two UCIe hops and the 20 KB serialisation (27 ns at the per-neighbour link rate). A two-step "
                            "reduce-scatter/all-gather would cross it twice; the model picks one-shot, the RTL engine implements it."),
    )

    values_checked = [
     dict(value="On-module package link, light FEC", model="130 ns (100-170)", verdict="HELD; band 100-185",
          basis="Broadcom SUE <100 ns link+PHY -> <110 ns; component sum 89-124 ns (IEEE 802.3 contributions); DSP-heavy PHY inference 108-184 ns", refs=["r-sue", "r-sun3cd", "r-gustlin3ck", "r-dassharma-ofa", "r-oif-cei5"]),
     dict(value="Rack-cable stage hop (T2, <= 0.8 m twinax)", model="130 ns (light FEC)", verdict="CHANGED to 209 ns (160-300)",
          basis="light RS(272) not qualified on CR-class copper (LL-FEC Table 1; 802.3ck mandates RS(544,514)); UALink 1.0 in-rack mode is un-interleaved RS(544,514)", refs=["r-llfec", "r-ualink", "r-ieee3ck-obj", "r-gustlin3ck"],
          effect=CABLE_EFFECT),
     dict(value="Full-KP4 hop", model="209 ns (129-409)", verdict="HELD (conservative end of 139-199 typical; 190-300 with Clause 161 interleave)", refs=["r-gustlin3ck", "r-nicholl3ck", "r-brown3cd"]),
     dict(value="UCIe hop", model="10 ns (3-30)", verdict="HELD, pessimistic (~3x measured)", basis="spec <2 ns PHY+adapter; measured 3.5 ns FDI-to-FDI", refs=["r-ucie-tcpmt", "r-ucie-jssc26"]),
     dict(value="On-module trace", model="~120 mm at 6.7 ns/m", verdict="HELD (0.8 ns; 6.1-7.15 ns/m sourced)", refs=["r-ti-scaa082", "r-megtron6"]),
     dict(value="Stage cable", model="<= 0.80 m twinax, 4.79 ns/m, no retimer", verdict="HELD (4.3-5.1 ns/m; 2 m DAC reach at 100G/lane, but only 1.0 m at 200G/lane)", refs=["r-belden", "r-sue", "r-ieee3ck-obj"]),
     dict(value="Switch", model="250 ns port-to-port", verdict="HELD (production spec budget, switch ports included; our switched path double-counts the switch-side PHY, conservative)", refs=["r-sue"]),
     dict(value="One-shot all-reduce engine", model="331 cycles per token step per die (9 collectives)", verdict="HELD (RTL simulation, bit-exact); 36.8 cycles per collective with a 12-cycle UCIe model", refs=["r-rtl-tp"]),
     dict(value="NVL72 collective (GPU side)", model="1.2 us per traversal (0.7-5.5)", verdict="HELD: 2 x 1.2 = 2.4 us ~ measured best kernel 2.37 us", refs=["r-sol", "r-nccl227", "r-nccl-cost"]),
    ]

    claim = dict(
      on_chip=f"{round(handoff/hdc_ns)}-{round(allsm/hdc_ns)}x (dependent handoff and all-unit gather: RTL cycles vs measured Blackwell)",
      cross_package=(f"{rows[4]['ratio_vs']['sol_floor']}-{rows[4]['ratio']}x against the GPU speed-of-light floor and best measured kernel; "
                     f"{rows[4]['ratio_vs']['nccl_2_27']}-{rows[4]['ratio_vs']['nccl_ring']}x against NCCL"),
      stage_hop=f"{rows[3]['ratio']}x (point-to-point hop vs NVLink remote store)",
      per_token_v41=(f"{rows[6]['ratio_vs']['sol_floor']}x vs the GPU floor, {rows[6]['ratio']}x vs the best kernel, "
                     f"{rows[6]['ratio_vs']['nccl_2_27']}-{rows[6]['ratio_vs']['nccl_ring']}x vs NCCL"),
      statement=("The order-of-magnitude synchronisation advantage is an ON-CHIP property (a compiled schedule replaces L2 fences: "
                 "~80-200x). Across packages both machines pay SerDes and FEC physics; there the advantage narrows to ~8-13x against the "
                 "best GPU kernel and its speed-of-light floor (fixed-function one-shot endpoints, no software, one link crossing), and "
                 "~28-62x against shipped NCCL."),
    )

    rec = dict(schema="opentallas.sync-cost-table.v1", tool="tools/sync_cost_table.py",
               inputs={str(p.relative_to(ROOT)): sha_file(p) for p in (TECH, GPU_DEP, GPU_GATHER, RTL_TP, V41_BUDGET, V41_LANES)},
               ladder=LADDER, v41_spec_budget=spec, rows=rows, hpc_precedents=hpc, hop_decomposition=hop_decomp, values_checked=values_checked,
               narrowed_claim=claim, references={k: v for k, v in REFS.items()},
               caveats=["GPU on-chip primitives are measured on an RTX PRO 6000 Blackwell (GB202), not a B200.",
                        "The GPU per-token rows price the SAME collective graph as the ROM array; a GPU deployment would choose its own parallelism.",
                        "No production measurement of a 112G PAM4 port's end-to-end latency was found; the 130/209 ns points are component sums cross-checked against Broadcom's budget.",
                        "The V4.1 ROM per-token figure is the adopted design point with the measured collective exposure (results/arch/v41_lanes.json design_point, 209 ns cable tier); the specification-width budget is reported beside it."])
    return rec, tech


def power_record(tech):
    """The power-assumption table on the tagged two-scenario model (configs/hardware/power_scenarios.json,
    results/arch/power_scenarios.json): every energy input with its evidence class and boundary."""
    P, E = tech["power"], tech["energy"]
    ro = P["rack_overheads"]
    lj = E["link_j_per_bit"]
    g = P["gpu_reference_power"]
    cfg = json.loads(PSCEN_CFG.read_text())
    ps = json.loads(PSCEN.read_text())
    L, M, Dd = cfg["mac_lane"], cfg["memory"], cfg["die"]
    B = L["scenario_B"]["per_mac"]
    hb = ps["hbm_split_pj_per_bit"]
    rows = [
     dict(quantity="MAC lane, scenario A (measured implementation)",
          value=f"Qwen3 {L['scenario_A']['qwen3']['value']:.2f} / V4.1 {L['scenario_A']['v41']['value']:.2f} pJ per MAC, every format",
          was="-", cls="measured-ours (ASAP7 routed matrix engine, BF16 x BF16 -> FP32)", verdict="new scenario: the lane that exists",
          refs=["r-signoff"]),
     dict(quantity="MAC lane, scenario B: W4A8 / FP4 (FP32 accumulate)", value=f"{B['w4a8']['value']:.2f} pJ per MAC",
          was="0.09 (a per-op value charged per MAC)", cls="published-spec (7 nm per-op estimates)",
          verdict="re-derived: INT8 mult 0.07 (upper bound) + FP32 add 0.38; 5x the old input", refs=["r-tpuv4i"]),
     dict(quantity="MAC lane, scenario B: FP8 / BF16 (FP32 accumulate)", value=f"{B['fp8']['value']:.2f} / {B['bf16']['value']:.2f} pJ per MAC",
          was="0.26 / 0.82 (2 x per-op)", cls="published-spec (7 nm per-op estimates)",
          verdict="re-derived: BF16 mult 0.21 + FP32 add 0.38, no node credit", refs=["r-tpuv4i"]),
     dict(quantity="MAC lane, scenario B: FP32 FMA", value=f"{B['fp32']['value']:.2f} pJ per MAC", was="2.36 (2 x per-op)",
          cls="published-spec", verdict="re-derived: FP32 mult 1.31 + add 0.38", refs=["r-tpuv4i"]),
     dict(quantity="4-bit MAC lower bound (Keller)", value=f"{L['bounds']['integer_lower_bound']['value']:.3f} pJ per MAC (INT4 VSQ, 0.46 V)",
          was="labelled an FP4 MAC", cls="published-measured, INTEGER",
          verdict="relabelled: integer 4-bit with per-vector scales and 24-bit partial sums; lower bound only", refs=["r-keller"]),
     dict(quantity="Tensor-core sensitivity", value=f"{L['bounds']['gpu_tensor_measured']['value']:.2f} pJ per MAC", was="-",
          cls="published-measured (A100, control included)", verdict="scenario-B sensitivity row", refs=["r-sc25"]),
     dict(quantity="HBM path energy", value=f"{hb['total']:.2f} pJ/b (MI250X path, controller included; measured range 11.68-14.72)",
          was="13.11 (A100)", cls="published-measured",
          verdict="least favourable SC'25 path without a last-level cache (MI300A's 14.72 carries a 256 MB cache)", refs=["r-sc25"]),
     dict(quantity="HBM path, stack share", value=f"{hb['stack']:.2f} pJ/b (high {hb['stack_high']:.2f})", was="12.31 (13.11 - 0.8)",
          cls="published-spec (DRAM model)", verdict="corrected: in-DRAM activation + data movement only", refs=["r-oconnor"]),
     dict(quantity="HBM path, die share (controller, PHY, I/O, control plane)", value=f"{hb['die']:.2f} pJ/b, charged to die cooling",
          was="9.66 (A100, assumed); 0.80 (I/O only) before that", cls="published-spec (measured path minus DRAM model)",
          verdict="no fixed-function credit: no source measures an HBM controller or PHY alone; GH200 (HBM3) would leave 8.23",
          refs=["r-sc25", "r-oconnor"]),
     *[dict(quantity=f"Cooling, {cls}, {n}-die package", value=f"{lim['die_w']:.1f} W per die; package {lim['package_w']:,.0f} W",
            was="407.5 W (0.5 W/mm2 x 815, A100 module over die area)",
            cls="vendor package rating less its stacks at peak bandwidth x 3.92 pJ/b",
            verdict=(f"least favourable matched reference: {lim['reference']}" + (f" ({lim['note']})" if lim.get("note") else "")),
            refs={"h200_sxm": ["r-h200"], "b200_hgx": ["r-dgxb200"], "gb200_nvl72": ["r-gb200-guide"]}[lim["reference"]])
       for cls, lims in ps["cooling_limits_w"].items() for n, lim in lims.items()],
     dict(quantity="Cooling cross-checks (chiplet / unmatched)", value="Gaudi 3 900 W air = liquid; MI300X 750 W air; MI350X 1,000 W air; MI355X 1,400 W liquid",
          was="-", cls="vendor specification", verdict="class envelopes only, not per-die limits", refs=["r-gaudi3", "r-amd-instinct"]),
     dict(quantity="HBM stack idle", value=f"{M['idle_w_per_stack']['value']} W/stack, charged to the die", was="2.8", cls="assumed",
          verdict="unverified; die side for cooling", refs=[]),
     dict(quantity="Logic leakage", value=f"{Dd['leakage_w_per_mm2']['logic']['value']:.2f} W/mm2", was="0.06", cls="assumed (idle anchors)",
          verdict="conservative", refs=["r-h100-idle", "r-tpuv4i", "r-tpuv4"]),
     dict(quantity="Stream-unit FP32 op", value=f"{Dd['stream_fp32_op_j']['value']*1e12:.2f} pJ", was="1.18", cls="published-spec",
          verdict="FP32 mult + add at 7 nm, no node credit", refs=["r-tpuv4i"]),
     dict(quantity="112G PAM4 SerDes", value=f"{lj['board_serdes_112g']['value']*1e12:.1f} pJ/b (5.6-7.5)", was="5 pJ/b",
          cls="measured silicon", verdict="corrected", refs=["r-serdes-vlsi22", "r-serdes-jssc21"]),
     dict(quantity="UCIe, advanced package", value="0.5 pJ/b; idle 15% of peak", was="0.29 pJ/b", cls="spec target + measured",
          verdict="corrected (0.29 is a 3 nm best case)", refs=["r-ucie-hc23", "r-ucie-jssc26"]),
     dict(quantity="PSU efficiency", value=f"{ro['psu_efficiency']['value']}", was="0.975", cls="normative table", verdict="corrected",
          refs=["r-80plus", "r-gb200-guide"]),
     dict(quantity="48 V -> core VR", value=f"{ro['vr_efficiency_48v_to_core']['value']}", was="0.90", cls="datasheet + peer-reviewed model",
          verdict="corrected", refs=["r-vicor", "r-vr48"]),
     dict(quantity="CDU", value="0.6% of IT", was="-", cls="datasheet (rated)", verdict="added", refs=["r-coolit"]),
     dict(quantity="Fans", value="3% of IT (1-6%)", was="-", cls="assumed", verdict="added, no primary number", refs=[]),
     dict(quantity="Switch tray", value="1.5 kW", was="1.5 kW", cls="assumed", verdict="unverified", refs=[]),
     dict(quantity="B200 in NVL72", value=f"TDP {g['b200_tdp_nvl72_w']['value']:.0f} W; measured 1.30 kW/GPU at the wall saturated (8xB200); decode 689 W",
          was="1,000 W", cls="vendor + measured", verdict="GPU rows", refs=["r-gb200-guide", "r-mlperf51", "r-b200-decode"]),
     dict(quantity="GB200 NVL72 rack", value="132 kW provisioned (125-135 operating)", was="120 kW", cls="vendor / OEM", verdict="GPU rows",
          refs=["r-gb200-guide", "r-smc-nvl72"]),
    ]
    scen = [dict(scenario=r["scenario"], design=r["design"], point=r["point"],
                 cooling=r["cooling"], energy_per_token_mj=r["energy_per_token_mj"], die_w=r["die_w"], cooling_w=r["cooling_w"],
                 package_w=r["package_w"], design_rate=r["design_rate"], capped_rate=r["capped_rate"], cooling_binds=r["binds"],
                 bound_by=r["bound_by"])
            for r in ps["summary"]]
    worst = dict(
      statement=("A statically scheduled machine has a knowable ceiling: the saturated schedule (every die issuing every cycle) IS its worst "
                 "case, so it can be provisioned at 1.2x that ceiling rather than at nameplate. GPUs cannot: measured draw depends on the "
                 "workload and spikes past TDP, so operators provision at nameplate and oversubscribe (Fan/Weber/Barroso; POLCA)."),
      refs=["r-fan-barroso", "r-polca"])
    return dict(schema="opentallas.power-assumptions.v2", tool="tools/sync_cost_table.py",
                inputs={str(p.relative_to(ROOT)): sha_file(p) for p in (TECH, PSCEN_CFG, PSCEN)},
                rows=rows, scenarios=scen, worst_case=worst,
                withdrawn=dict(
                  note=("Figures the 2026-09-27 validation record (worktree-agent-adae6788 @872da542) carried that depend on code "
                        "absent from this branch or on the withdrawn HBM allocation; NOT re-stated here"),
                  items=["V4.1 rack power 21.4 / 36.9 / 44.3 kW and per-die 98.8 W static / 203.7 W worst (v41-rack-gates @6424ca03, "
                         "results/arch/v41_rack.json: not on this branch)",
                         "V4.1 headline 8,622 tok/s/user at 1M and 2.34 J/token wall (worktree-agent-ad495baa @ef5b95e2: not on this branch)",
                         "Qwen3 82.4 mJ/token, 187.2 W die, 1,459 W provisioned (codex/qwen-* @f04f3c17: the 0.8 pJ/b die / 12.31 pJ/b stack "
                         "allocation and the 0.09 pJ W4A8 MAC, both corrected in results/arch/power_scenarios.json)"]),
                unverified=["HBM3E stack idle/self-refresh W", "HBM3E pJ/b (vendor)", "HBM controller vs PHY pJ/b split",
                            "SerDes always-on idle per lane (measured)", "mask-ROM leakage", "SRAM leakage at N5/N3", "SFU energy per op",
                            "switch tray W", "air limit 700 W/OU", "batch-1 GPU decode W",
                            "a single-reticle package rated above 700 W (liquid)", "sustainable hot-spot W/mm2 of a logic region",
                            "any measured FP8 or FP4 x FP8 MAC with FP32 accumulation"])


# ------------------------------------------------------------------------------------------------ HTML
TAG = {"measured": ("meas", "measured"), "RTL simulation": ("meas", "RTL sim"), "RTL-derived": ("meas", "RTL"),
       "model, normative basis": ("mod", "model · normative"), "model on measured primitives": ("mod", "model · measured"),
       "model on measured primitive": ("mod", "model · measured"), "measured floor + vendor cost model": ("mod", "measured floor"),
       "not published": ("pend", "not published"), "not on the decode path": ("sup", "n/a")}


def fmt(c):
    if c["value"] is None:
        v = "—"
    elif c["unit"] == "ns" and c["value"] >= 1000:
        v = f"{c['value']/1e3:,.2f} µs"
    else:
        v = f"{c['value']:,}".rstrip("0").rstrip(".") if isinstance(c["value"], float) else f"{c['value']:,}"
        v += " " + ("µs" if c["unit"] == "us" else c["unit"])
    cls, lab = TAG.get(c["evidence"], ("sup", c["evidence"]))
    refs = " ".join(f'[<a href="#{r}">{r[2:]}</a>]' for r in c["refs"])
    return f'<span class="m">{html.escape(v)}</span> <span class="tag {cls}">{html.escape(lab)}</span> {refs}'


def render(rec, prec):
    e = html.escape
    out = ['<!-- generated by tools/sync_cost_table.py from results/arch/sync_cost_table.json and power_assumptions.json -->',
           '<div class="tablebox"><table class="data">',
           '  <caption>Table 8-S. Synchronisation cost per event: GB200 NVL72 / Blackwell against OpenTallas. Every cell carries its evidence '
           'class and source; GPU on-chip rows are measured on GB202 (RTX PRO 6000 Blackwell), not a B200.</caption>',
           '  <thead><tr><th>Sync event</th><th>NVL72 / Blackwell</th><th>OpenTallas</th><th class="r">GPU ÷ OT</th><th>Basis</th></tr></thead>',
           '  <tbody>']
    for r in rec["rows"]:
        ratio = "—" if r["ratio"] is None else f"{r['ratio']}×"
        if r.get("ratio_vs") and r["event"].startswith("Cross-package collective"):
            rv = r["ratio_vs"]; ratio = f"{rv['sol_floor']}–{r['ratio']}× (NCCL {rv['nccl_2_27']}–{rv['nccl_ring']}×)"
        if r.get("ratio_vs") and r["event"].startswith("Per token, V4.1"):
            rv = r["ratio_vs"]; ratio = f"{rv['sol_floor']}–{r['ratio']}× (NCCL {rv['nccl_2_27']}–{rv['nccl_ring']}×)"
        out.append(f'    <tr><td>{e(r["event"])}</td><td>{fmt(r["gpu"])}</td><td>{fmt(r["ot"])}</td><td class="r m">{e(ratio)}</td>'
                   f'<td>{e(r["ot"]["note"])}</td></tr>')
    out.append('    <tr><th colspan="5">HPC precedent (published per-hop / end-to-end latency)</th></tr>')
    for h in rec["hpc_precedents"]:
        refs = " ".join(f'[<a href="#{x}">{x[2:]}</a>]' for x in h["refs"])
        out.append(f'    <tr><td>{e(h["system"])}</td><td class="m">{e(h["per_hop"])}</td><td class="m">{e(h["end_to_end"])}</td>'
                   f'<td class="r">{e(h["fec"])}</td><td><span class="tag sup">{e(h["evidence"])}</span> {refs}</td></tr>')
    out += ['  </tbody>', '</table></div>', '']
    out += ['<div class="tablebox"><table class="data">',
            '  <caption>Table 8-L. Link values the model relies on, checked against normative and production sources (full quotes in results/arch/sync_cost_table.json).</caption>',
            '  <thead><tr><th>Value</th><th>Model</th><th>Verdict</th><th>Sources</th></tr></thead>', '  <tbody>']
    for v in rec["values_checked"]:
        refs = " ".join(f'[<a href="#{x}">{x[2:]}</a>]' for x in v["refs"])
        cls = ' class="rej"' if v["verdict"].startswith("CHANGED") else ""
        out.append(f'    <tr{cls}><td>{e(v["value"])}</td><td class="m">{e(v["model"])}</td><td>{e(v["verdict"])}'
                   f'{(" — " + e(v["effect"])) if v.get("effect") else ""}</td><td>{refs}</td></tr>')
    out += ['  </tbody>', '</table></div>', '']
    out += ['<div class="tablebox"><table class="data">',
            '  <caption>Table 8-P. Power inputs with evidence class and boundary (configs/hardware/power_scenarios.json; '
            'results/arch/power_assumptions.json).</caption>',
            '  <thead><tr><th>Quantity</th><th>Value</th><th>Was</th><th>Evidence</th><th>Verdict</th><th>Sources</th></tr></thead>', '  <tbody>']
    for p in prec["rows"]:
        refs = " ".join(f'[<a href="#{x}">{x[2:]}</a>]' for x in p["refs"]) or "—"
        out.append(f'    <tr><td>{e(p["quantity"])}</td><td class="m">{e(p["value"])}</td><td class="m">{e(p["was"])}</td>'
                   f'<td><span class="tag sup">{e(p["cls"])}</span></td><td>{e(p["verdict"])}</td><td>{refs}</td></tr>')
    out += ['  </tbody>', '</table></div>', '']
    out += ['<div class="tablebox"><table class="data">',
            '  <caption>Table 8-Q. Scenario A (the routed lane) against scenario B (the proposed lane): energy per token, the hottest '
            'die against its cooling class\'s per-die limit (air: H200 SXM for one die, B200 HGX for two; liquid: GB200 for two, '
            'air for one, no single-reticle part being rated higher), and the rate each class allows (results/arch/power_scenarios.json).</caption>',
            '  <thead><tr><th>Scenario</th><th>Design</th><th>Point</th><th>Cooling</th><th class="r">mJ/token</th><th class="r">Die W</th>'
            '<th class="r">Limit W</th><th class="r">Design tok/s</th><th class="r">Cooling-capped tok/s</th></tr></thead>', '  <tbody>']
    for r in prec["scenarios"]:
        if not r["scenario"].startswith(("A_", "B_proposed")):
            continue
        out.append(f'    <tr><td>{e(r["scenario"][0])}</td><td>{e(r["design"])}</td><td>{e(r["point"])}</td><td>{e(r["cooling"])}</td>'
                   f'<td class="r m">{r["energy_per_token_mj"]:,.1f}</td><td class="r m">{r["die_w"]:,.0f}</td>'
                   f'<td class="r m">{r["cooling_w"]:,.0f}</td>'
                   f'<td class="r m">{r["design_rate"]:,.0f}</td><td class="r m">{r["capped_rate"]:,.0f}'
                   f'{" (binds, " + r["bound_by"] + ")" if r["cooling_binds"] else ""}</td></tr>')
    w = prec["worst_case"]
    out += ['  </tbody>', '</table></div>', '',
            '<p><b>Finding.</b> ' + e(rec["narrowed_claim"]["statement"]) +
            f' Per V4.1 token (1 M context, batch 1) synchronisation costs {rec["rows"][6]["ot"]["value"]} µs on the ROM array against '
            f'{rec["rows"][6]["gpu"]["value"]:,} µs for the same collective graph at the best measured GB200 kernel '
            f'({rec["rows"][6]["ratio"]}×; {rec["rows"][6]["ratio_vs"]["nccl_2_27"]}–{rec["rows"][6]["ratio_vs"]["nccl_ring"]}× against NCCL). '
            'The one link value that did not survive the check was the rack-cable stage hop: a light FEC is qualified only on the on-module '
            'channel, so the cable tier now runs full RS(544,514) at 209 ns (' + e(CABLE_EFFECT) + '). '
            'Power is stated in two scenarios that are never mixed: A charges every MAC at the routed matrix engine\'s reported energy, B at '
            'a derived floating-point lane; the HBM path is split between the DRAM stack and the logic die, whose share (controller, PHY, '
            'I/O) is charged to die cooling, and die cooling is stated per class from shipping packages less their own stacks. ' + e(w["statement"]) + '</p>',
            '', '<ol class="refs">']
    used = sorted({r for row in rec["rows"] for r in row["gpu"]["refs"] + row["ot"]["refs"]} |
                  {r for h in rec["hpc_precedents"] for r in h["refs"]} | {r for v in rec["values_checked"] for r in v["refs"]} |
                  {r for p in prec["rows"] for r in p["refs"]} | set(w["refs"]))
    for k in used:
        r = rec["references"][k]
        link = f', <a href="{e(r["url"])}">{e(r["url"])}</a>' if r["url"] else ""
        out.append(f'  <li id="{k}">{e(r["text"])}{link}.</li>')
    out.append('</ol>')
    return "\n".join(out) + "\n"


def main():
    rec, tech = build()
    prec = power_record(tech)
    OUT.write_text(json.dumps(rec, indent=1) + "\n")
    OUT_P.write_text(json.dumps(prec, indent=1) + "\n")
    OUT_H.parent.mkdir(parents=True, exist_ok=True)
    OUT_H.write_text(render(rec, prec))
    for r in rec["rows"]:
        print(f"{r['event'][:60]:60s} GPU {r['gpu']['value']} {r['gpu']['unit']}  OT {r['ot']['value']} {r['ot']['unit']}  ratio {r['ratio']} {r.get('ratio_vs', '')}")
    print(rec["narrowed_claim"])


if __name__ == "__main__":
    main()
