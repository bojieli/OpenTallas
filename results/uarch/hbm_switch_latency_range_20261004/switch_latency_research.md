# Small-message collective latency through a one-tier scale-up switch domain: published numbers and a hardware-path estimate

Compiled 2026-10-04 from web sources. Every number has a source and a label saying what it measures. **[V]** means I read the number in the primary source (paper text, figure, or vendor spec PDF). **[S]** means it comes from a secondary or reseller source and was not confirmed in a primary document. **[U]** means it is unverified or contradicted, and should not be used as a calibration point. **[FIG]** means I read the value off a log-scale plot, so it is approximate (about ±20%).

## 1. Published numbers

### 1a. NVLink / NVSwitch point-to-point (GPU to GPU through the switch)

| # | Number | What it measures | System | Size | HW-only? | Source | Status |
|---|---|---|---|---|---|---|---|
| 1 | **L_remote_store = 0.792 µs** (one-way) | Derived from a GPU-to-GPU ping-pong as (L_pingpong − 2·L_L2RTT)/2, so the implied ping-pong RTT is about 2.20 µs. It covers SM→L2→NVLink→NVSwitch→NVLink→remote L2 visibility. | 2× GB200 inside an NVL72 (the path crosses an NVLink Switch chip) | one 128 B cache line / one value | Close to hardware-only: no host, but it does include the SM store-issue and L2 visibility path | Shen et al., "Every µs Matters", arXiv:2607.16100, §VI, https://arxiv.org/abs/2607.16100 | [V] |
| 2 | **L_L2_RTT = 0.306 µs** | Latency of one `__threadfence()`, used as a proxy for the L2 round trip | GB200 | — | on-chip | same, §VI | [V] |
| 3 | **SoL AllReduce = 1.404 µs** = 2·L_L2RTT + L_remote_store | Paper's "absolute hardware lower bound" for a one-shot push AllReduce. It assumes all peers' stores are issued at the same moment and ignores sync, issue and bandwidth. It does not depend on rank count. | GB200 | 128 B (one cache line) | Yes, by construction | same, §VI | [V] |
| 4 | NVLink latency **822 ns** best-achievable, **829 ns** with MSCCL++ MemoryChannel | P2P NVLink latency (the paper does not define the operation precisely; the baseline comes from nvbandwidth) | H100 (8-GPU NVSwitch node) | small | Device-side, no host launch (as far as stated) | MSCCL++, arXiv:2504.09014, Table 1, https://arxiv.org/abs/2504.09014 | [V] (operation definition vague) |
| 5 | NVSHMEM intra-node put/get **1.8–2.5 µs**; scalar p/g **1.3–2.2 µs** | Device-initiated one-sided RMA latency, measured with perftest | H100-class (NVLink-4, 8 GPUs per node, NVSwitch) | small | Device-side; includes NVSHMEM software path | Ma, Shen et al., "Demystifying NVSHMEM", arXiv:2606.05951, §IV, https://arxiv.org/abs/2606.05951 | [V] |
| 6 | Block-scope probe **~1 µs**; 1.2 µs NVLink4 direct, 1.6 µs NVLink3 via NVSwitch | Put+signal probe latency | H100 / A100 | small | Device-side, includes the probe kernel | "Move the Query, Not the Cache", arXiv:2606.01502, https://arxiv.org/abs/2606.01502 | [S] (summarised by the fetch tool, not checked line by line) |
| 7 | ~9 µs directly connected, about 2–3× more when routed through another GPU | P2P latency measured with cudaMemcpy | P100/V100 DGX-1, plus DGX-2 NVSwitch in Fig. 11 | shortest message | **No.** Dominated by the CUDA memcpy software path. | Li et al., "Evaluating Modern GPU Interconnect", arXiv:1903.04611, https://arxiv.org/abs/1903.04611 | [V], useless for hardware calibration |
| 8 | "any GPU to any memory location within **300 ns**" | Marketing-style claim | GB200 NVL72 | — | ? | introl.com blog, https://introl.com/blog/gb200-nvl72-deployment-72-gpu-liquid-cooled (no citation; the same page says "four switch chips per tray", which conflicts with NVL72's 18 chips across 9 trays) | **[U]**. It disagrees with #1 by 2.6×, so do not use it. |
| 9 | "NVLink remote access averages 15 ns vs 50 ns for PCIe" | — | — | — | — | varidata.com blog | **[U]**. Physically implausible (a single SerDes+FEC hop alone exceeds it). Discard. |

### 1b. GB200 / H100 small-message AllReduce (device-side, includes kernel-side sync)

| # | Number | What it measures | System | Size | HW-only? | Source | Status |
|---|---|---|---|---|---|---|---|
| 10 | **11.0 µs** NCCL ring vs **2.37 µs** new LL one-shot | AllReduce mean over 10 trials | 4× GB200 | small (128 B) | No. Includes kernel, flags and polling. | arXiv:2607.16100 §I | [V] |
| 11 | Best kernel at 128 B is **+7% over SoL at 2 GPUs** (≈1.50 µs), **+29–34% at 8** (≈1.81 µs), **+34–35% at 16** (≈1.9 µs), **+48–50% at 32** (≈2.09 µs), **+68–72% at 64** (≈2.36–2.41 µs). The multicast (NVLS) one-shot variants are the best at 64. | AllReduce latency for 128 B; overhead percentages are relative to 1.404 µs | GB200 NVL72, 2–64 GPUs | 128 B | No (kernel sync included) but no host launch in the overhead accounting | arXiv:2607.16100 Fig. 11 bottom panel (percent labels read from the figure; µs = 1.404×(1+%)) | [V] percentages / [FIG] for the µs conversion |
| 12 | At **32 KB (2^15)**: best ≈ **5–7 µs at 32 ranks** and ≈ **5–6 µs at 64 ranks** (LL128-atomic MC / one-shot MC). NCCL ring ≈ 80 µs (32 ranks) and ≈ 170 µs (64 ranks). | AllReduce latency against message size | GB200 NVL72 | 32 KB | No | arXiv:2607.16100 Fig. 11 top panels | [FIG] |
| 13 | Device barrier **0.85 µs (2 GPUs) to 1.68 µs (32 GPUs)**, unicast and NVLS-multicast variants. "Each barrier … more than 1 µs". Two barriers ≈ 40% of a ~5 µs AllReduce on 4 GPUs. | Global GPU barrier | GB200 | — | Kernel-level sync | arXiv:2607.16100 Fig. 3, §III | [V] (series-to-value mapping read from the figure) |
| 14 | One-shot AllReduce at 8 KB: TP2 3.36 → 2.36 µs; TP4 ~4.66 → 2.33 µs; TP8 5.11 → 2.44 µs (baseline → barrier-free). Barriers are up to 62% of the time. | AllReduce | 8× H200 (NVSwitch) | 8 KB | No | SiFAR, arXiv:2607.08973, https://arxiv.org/abs/2607.08973 | [V] via fetch summary |
| 15 | NCCL NVLS (RSxLDMC_AGxSTMC symmetric kernel) **5.6–5.9 µs**; NCCL ring 4.7–8.9 µs; NVSHMEM device 3.8–7.1 µs | AllReduce, up to 64 KiB | 8-GPU NVLink-4 node | ≤64 KiB | No | arXiv:2606.05951 §IV-C | [V] |
| 16 | nccl-tests all_reduce minimum latency at 8 B: **~2.3 µs on 8× H800/H200**, **~3 µs on 8× B200** | nccl-tests `time` column (kernel time, after host launch) | HGX 8-GPU | 8 B | No | NVIDIA dev forum thread (user-reported, no NVIDIA reply), https://forums.developer.nvidia.com/t/inter-gpu-latency-on-b200-higher-than-on-hopper/352473 | [S] |
| 17 | NCCL 2.27 symmetric kernels give "up to 9× lower latency for small messages" (no absolute µs) | — | NVL72 / NVL8 | small | — | NVIDIA blog, https://developer.nvidia.com/blog/enabling-fast-inference-and-resilient-training-with-nccl-2-27 | [V], relative only |
| 18 | NVSwitch3 SHARP ALUs: **400 GFLOPS FP32** per chip; NVL72 Hot Chips 2024 slide: "SHARP In-Network Compute — 3.6 TFLOPS". The slide does not give a per-unit basis; it is probably per switch tray. | Reduction throughput, not latency | H100 NVSwitch3 / NVL72 | — | — | NVIDIA NVSwitch3 dev blog (ko-kr copy); HC2024 Tirumala/Wong deck, https://www.hc2024.hotchips.org/assets/program/conference/day1/64_HC2024.NVIDIA.TirumalaWong.pdf | [S] / [V] |

**No public source gives an NVSwitch port-to-port latency or an NVLink5 SerDes+FEC latency in nanoseconds.** I checked the HC2024 NVIDIA deck text, the NVSwitch blogs, and the microbenchmark papers. Nor have I found a published latency for `multimem.ld_reduce` or `multimem.st` on their own. The best substitute is the end-to-end one-way figure in #1 (0.79 µs, GB200).

### 1c. Other scale-up and scale-out switches

| # | Number | What it measures | Source | Status |
|---|---|---|---|---|
| 19 | **Tomahawk Ultra: 250 ns switch latency "at full load"**, 51.2 Tb/s, 64 B line rate, in-network AllReduce/AllGather "in switch silicon", LLR+FEC, CBFC | Switch port-to-port (vendor claim) | Broadcom PR via ConvergeDigest, https://convergedigest.com/broadcom-ships-tomahawk-ultra-to-power-ai-scale-up/ ; HPCwire mirror | [V] (vendor claim). No collective latency is given. |
| 20 | **SUE: "sub-400 ns end-to-end"** (Tomahawk Ultra PR) | XPU-to-XPU (vendor claim) | same | [V] claim. Note it is lower than #21's own budget. |
| 21 | **SUE one-way budget (Appendix A, Fig. 22): 100 ns endpoint bridge (NoC↔Ethernet, Tx+Rx) + 100 ns endpoint Ethernet link+PHY (Tx+Rx) + 2× cable + 250 ns switch (Tx+Rx) = 477.6 ns (3 m twinax), 496 ns (5 m hollow-core fibre), 549.2 ns (10 m SMF).** Cable delay 4.6 ns/m twinax, 4.96 ns/m SMF. Requirements table: "E2E latency < 2 µs RTT", "Up to 10 m". FEC: RS-272 as a lower-latency option than RS-544, and reduced or no FEC interleave. | One-way endpoint-to-endpoint hardware budget | Broadcom Scale-Up Ethernet Framework Spec RM104 (2025-09-26), https://docs.broadcom.com/doc/scale-up-ethernet-framework, p. 31 | [V]. This is the cleanest hardware-only breakdown available. |
| 22 | **UALink 1.0: "Req-To-Resp RTT < 1 µs"**, cable < 4 m, 1–4 racks, ≤1K endpoints. The PHY uses 802.3dj 212.5G/106.25G with reduced FEC interleave "to achieve better FEC latency". 640 B DL flit = one RS(544,514) codeword. | Protocol target (request to response) | UALink 1.0 white paper, https://ualinkconsortium.org/wp-content/uploads/2025/04/UALink-1.0-White_Paper_FINAL.pdf | [V] |
| 23 | UALink "port-to-port hop latency 100–150 ns" | Switch hop | nand-research note, https://nand-research.com/research-note-ualink-consortium-releases-ualink-1-0/ | [S]. Not in the white paper text I read. |
| 24 | Quantum-2 (NDR) **130 ns** port-to-port | Switch | NADDOD reseller product pages (e.g. https://www.naddod.com/products/nvidia-networking/102404) | [S]. Not found in the NVIDIA QM9700 datasheet copies I could read. |
| 25 | Quantum-X800 "< 100 ns" port-to-port | Switch | introl blog, gpusmith / enterasource reseller pages | **[U]**. The NVIDIA X800 datasheet (NADDOD-hosted and Dell copies) says only "ultra-low latency". |
| 26 | SHARP (Switch-IB 2): 8 B MPI_Allreduce on 128 hosts **6.01 → 2.83 µs** | Host-to-host MPI, including the HCA and software | Graham et al., "SHARP" (COMHPC'16), https://network.nvidia.com/pdf/solutions/hpc/paperieee_copyright.pdf ; also superfri article | [S] (quoted in search snippets of the paper; I did not open the PDF) |
| 27 | SHARP streaming aggregation (Quantum HDR): LLT/SAT crossover at 4–8 KB on 64 nodes (about 16 KB including the lock); no µs given in text | — | Graham et al., ISC 2020, https://pmc.ncbi.nlm.nih.gov/articles/PMC7295336/ | [V] (qualitative only) |

### 1d. SerDes / FEC per-hop

| # | Number | Source | Status |
|---|---|---|---|
| 28 | Concatenated RS(544,514) + Hamming(128,120) inner-code interleaver latency: **~140 ns** (800G, 2-way), **~56 ns** (800G, 4-way), ~140 ns (400G) | IEEE P802.3dj, Patra, Mar 2023, https://www.ieee802.org/3/dj/public/23_03/patra_3dj_01b_2303.pdf p. 24 | [V] (inner-code / interleaver part only) |
| 29 | 100G/lane 400GbE module: ~100 ns module DSP + ~100 ns host KP4 FEC ≈ 200 ns end-to-end. 200G/lane target < 400 ns. End-to-end RS(544,514) at 200G/lane ≈ 230 ns. RS(544,514) block time 25.6 ns at 400GbE. | IEEE 802.3dj/df contributions (Li 2023-02/05, He 2024-01, etc.) as summarised in search results | [S]. Search snippet only; I could not extract the PDF text to confirm which deck states which number. |
| 30 | SUE: endpoint "Ethernet link and PHY Tx+Rx < 100 ns"; switch Tx+Rx < 250 ns (includes the switch's own PHY/FEC) | #21 | [V] |
| — | **NVLink5 (224G PAM4) SerDes/FEC latency**: no public number found. | — | gap |

## 2. Calibrated estimate: one 32 KB AllReduce across 48 packages in one NVL72-class tier, hardware path only

### Assumptions
- One tier of S = 18 switch chips. Every package has one link (or link group) to every chip, so any-to-any traffic crosses exactly one switch.
- Per-package bandwidth is about 900 GB/s per direction (NVLink5 class: 18 links × 50 GB/s/dir).
- "Hardware path" means everything from the last contributor's data being ready in its L2/SRAM to the reduced result being visible in every package's memory. It excludes kernel launch, host, and software polling loops. It includes one mandatory readiness/completion mechanism, because a collective cannot finish without one.
- 32 KB per package (BF16 is 16K elements). The data is striped across the 18 links, about 1.8 KB per link, which takes about 36 ns to serialize at 50 GB/s.

### Building blocks (sources in brackets)
- One-way endpoint→switch→endpoint: **0.48–0.55 µs** on a SUE-class budget [21]. **0.79 µs measured** on GB200 including the SM/L2 path [1]. The vendor floor claim is < 0.4 µs [20].
- Request→response RTT: < 1 µs UALink target [22]; about 2.2 µs implied GB200 ping-pong [1,2].
- On-chip L2 access at each end: about 0.3 µs on GB200 [2].
- In-switch reduction compute: 16K elements × 47 adds ≈ 0.77 MFLOP per all-reduce, or about 43 kFLOP per chip. At 0.4–1.8 TFLOPS per chip [18] that is about 25–110 ns, and it pipelines with arrival. Small.
- Bandwidth term without in-switch reduction: a push one-shot (unicast or `multimem.st`) delivers 47 × 32 KB ≈ 1.5 MB into each package. At 900 GB/s that is **≈1.7 µs of ingress serialization**, which cannot be avoided. This is why 32 KB at 48 ranks already leaves the "latency-only" regime unless the switch performs the reduction.

### Cross-chip striping tail
The operation finishes when the slowest of 18 stripes, from the slowest of 48 sources, has landed. That is a max over about 864 paths. Three things contribute to the tail:
1. **Per-path jitter**: SerDes CDR and FEC codeword alignment, switch arbitration, credit return. With σ ≈ 20–50 ns per path, the expected maximum of about 864 samples is roughly +3σ, or **+60–150 ns**.
2. **FEC codeword granularity**: a 1.8 KB stripe is 3–4 RS(544,514) codewords per 2-lane link. The receiver cannot release the last bytes until the last codeword is decoded. That adds one block time plus decode, **~30–60 ns**. Low-interleave or RS-272 modes reduce this [21,22,28].
3. **Link-level retry (LLR)**: a CRC/FEC failure on any one of the 864 paths adds about one link RTT, **~0.2–0.5 µs**. It is rare per path, but the probability multiplies by about 864 per collective. Treat it as a p99–p99.9 term, not a median term.

In-switch reduction also synchronizes the 18 chips implicitly. Each chip waits for its own last contributor, so a skew of one source shows up on every stripe. That skew is compute or launch skew, which this estimate excludes.

### Estimate (median, hardware path, 48 packages, 32 KB)

| Case | Mechanism | Composition | Estimate |
|---|---|---|---|
| **Low** | Push-mode in-switch reduce (SHARP / Tomahawk-Ultra-style streaming aggregation: every package pushes its stripe, each switch chip reduces and multicasts the result). SUE/UALink-class endpoint latency. | ~0.5 µs one-way [21] + 36 ns serialization + ~50 ns reduce pipeline + ~0.1 µs stripe tail | **≈ 0.65 µs** (floor ~0.55 µs) |
| **Central** | Same push-mode in-switch reduce, but with **measured GB200-class endpoint constants** | 0.79 µs one-way [1] + ~0.3 µs L2 read/visibility at source/destination [2] + 0.04 µs serialization + ~0.05 µs reduce + ~0.1–0.15 µs tail | **≈ 1.3–1.5 µs** |
| **High** | What NVIDIA NVLS exposes today: pull-mode `multimem.ld_reduce` + `multimem.st`, which needs a readiness barrier first. Alternatively, the one-shot multicast-store path, which is ingress-bandwidth bound. | NVLS: barrier/flag one-way ~0.8 + ld_reduce RTT ~1.6 + multicast store ~0.8 + tail ~0.15 ≈ 3.3 µs. One-shot MC: 1.4 µs SoL + 1.7 µs ingress ≈ 3.1 µs. | **≈ 3.0–3.5 µs**, plus 0.2–0.5 µs at p99.9 for LLR |

Sanity check against measurement: the best GB200 kernels at 32–64 ranks run about **2.1–2.4 µs at 128 B** [11] and about **5–7 µs at 32 KB** [12]. Those include kernel-side sync and polling. The hardware "high" case (about 3.3 µs) sits below the 32 KB measurement and above the 128 B one, which is consistent with software and sync accounting for the remaining ~2–3 µs, as #13 and #14 report (barriers up to 40–62% of small AllReduce time).

**AllGather note:** if "32 KB" is the per-package input, each package receives 1.5 MB. Serialization alone is then about 1.7 µs, giving ≈ 2.3–2.6 µs hardware (one-way plus ingress), and switch support cannot remove that term. If 32 KB is the total gathered output (about 680 B per package), the operation is latency-bound at roughly one one-way traversal plus tail: ≈ 0.6 µs (SUE-class) to ≈ 1.2 µs (GB200-class).

### Caveats
- There is no published NVSwitch port-to-port or NVLink5 PHY/FEC latency. The NVIDIA-specific split between switch and link is unknown, and only the GB200 end-to-end one-way 0.79 µs [1] is measured. That figure includes GPU NoC and L2 time, which a custom endpoint could shrink.
- The Tomahawk Ultra 250 ns and SUE < 400 ns figures are vendor claims. Broadcom's own spec budget is 478–549 ns one-way [21]. I found no published in-network collective latency for Tomahawk Ultra.
- The numbers marked [FIG] are read from log plots and carry about ±20% uncertainty.
