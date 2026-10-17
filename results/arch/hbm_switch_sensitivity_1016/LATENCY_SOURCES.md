# Die-to-die switch crossing: 377.6 ns, and why it is justified (HBM-NETSRC, 2026-10-16)

**Headline (owner decision 2026-10-16): one crossing = 377.6 ns.** This file is the paper's justification for that
number. Every figure is cited, or it is labelled **ours/measured** (a repository record) or **ours/derived**
(arithmetic on cited figures). Labels on sources: **[vendor]** is a vendor claim or budget; **[std]** is an IEEE
standard limit or task-force contribution; **[meas]** is a measurement; **[press]** is a secondary report.

## 1. What "one crossing" is

**One crossing goes through one switch chip.** The fabric has one tier and several planes. Each die has one port on
every plane chip, and any die reaches any other die through exactly one chip of a plane.

- 96 x d4c uses 8 planes of 400G ports.
- 192 x d4f uses 16 planes of 200G ports.
- `planes.json` and README §1 give the port arithmetic.

NVIDIA's scale-up domains have the same structure:

- **HGX H100 8-GPU:** "eight H100 Tensor Core GPUs and four third-generation NVSwitch. Each H100 GPU … connects to
  all four NVSwitches. Each NVSwitch is a fully non-blocking switch that fully connects all eight H100" [N1].
- **GB200 NVL72:** "the nine switches fully connect each of the 18 NVLink ports on every one of the 72 Blackwell
  GPUs". Each switch tray holds two NVLink Switch chips [N2], so there are 18 chips. Each GPU has 18 ports and each
  chip has 72 GPU ports (144 per tray), so every GPU has exactly one link to each chip (ours/derived).

**"Two crossings" means the two all-reduce phases, not two chips in series.** Phase 1 is a reduce-scatter to the
slice owner. Phase 2 is the owner's multicast. Each phase is one die→chip→die crossing. A gather pays one crossing.
The rule is in `tools/hgi_sim/ds_switch_sens.py` (k = 2 for ALL_REDUCE_SUM / GROUP_REDUCE_MCAST, otherwise 1).

**A crossing has two links:** die→switch and switch→die. The budget counts both. It is Broadcom's own one-way
decomposition [B2, Fig. 22]:

- the endpoint "Ethernet Link and PHY" Tx+Rx term covers the source die's Tx (link 1) and the destination die's Rx
  (link 2);
- the switch "Tx+Rx" term covers the switch's own PHY/FEC on both links;
- there are two cable legs.

Broadcom's fourth term, the 100 ns NoC↔Ethernet bridge, is **not** in our 377.6 ns. It is replaced by our measured
endpoint RTL, which the model charges separately: 108.6 cycles + 23.75 cycles per 64 B flit per rank at 1.2 GHz,
i.e. 90.5 ns + 19.8 ns per flit (`tools/dshbm_1m_coll.py`). The model also adds a 0.15 µs striping tail.

## 2. The budget, term by term

| term (one crossing) | value used | primary source | kind | corroborating / bracketing evidence |
|---|---:|---|---|---|
| Endpoint PHY + FEC, die Tx (link 1) + die Rx (link 2) | **100 ns** | SUE RM104 App. A Fig. 22: "Ethernet Link and PHY, Tx+Rx latency <100 ns" [B2] | [vendor] | RS(544,514) encode+decode, MAC-to-MAC: 62.6 ns for 400GE and 88.2 ns for 200GE, at a 1 GHz core, excluding SerDes and buffers [I1] [std]. Host KP4 FEC "~100 ns" [I2] [std]. Clause 91 decoder at 100G/lane: 51 ns block + 100 ns processing = 151 ns [I3] [std]. KP4 at 50G/lane: 198 ns [I4] [std]. The IEEE compliance ceiling of 409.6 ns (Clause 91 RS-FEC sublayer, Tx+Rx at one end) [I5] is a PAUSE-timing bound, not a design value. |
| Switch, port to port, including the switch's PHY/FEC on both links | **250 ns** | Tomahawk Ultra BCM78920 product brief: "250 ns latency", 64 B at line rate [B1]. Broadcom MUG'25: "Switch latency ~250 ns with FEC", "E2E latency < 400 ns" [B3]. Press: "250 ns … at full load" [P1] | [vendor] | UALink target for 400G ports: ≤150 ns (25T), <200 ns (50T), <250 ns (100T) [U1] [vendor/consortium]. General-purpose Ethernet switches are slower: Arista 7060X6 (51.2T) "latency from 700 ns" [A2] [vendor]; Tomahawk 6 "600–700 ns" for small packets [P2] [press]; Tomahawk (gen 1, 100GbE) measured "always at least 600 ns" cut-through [T1] [meas, competitor-commissioned]. **No independent Tomahawk Ultra measurement and no NVSwitch port-to-port figure are published** [P2]. |
| Cable, 2 x 3 m passive twinax | **27.6 ns** (4.6 ns/m) | Arista MetaWatch measurement: twinax 4.60 ns/m, fibre 4.96 ns/m, 10^6 samples, ±2 ns [A1] | [meas] (vendor lab) | The SUE budget uses the same 4.6 ns/m [B2]. 3 m reaches the centre switch shelf of a 1–2 rack 96-die array (README §1). |
| **Crossing total** | **377.6 ns** | = SUE's 477.6 ns 3 m-copper budget [B2] minus its 100 ns bridge, which our measured RTL replaces | | Broadcom's own claim, end to end including the bridge, is "< 400 ns" [B3] |

**Media sensitivities that are not in the headline:**

- Active copper (AEC) needs retimers. No AEC vendor publishes a retimer latency. Point2 claims its own analog retimer is
  3 ns and "20x lower than available DSP-based PAM4 retimers" [P3]. That implies about 60 ns per DSP retimer
  (ours/derived) [vendor].
- Optics: a 100G/lane DSP module adds "~100 ns module DSP" per link [I2] [std].

## 3. Anchor: our own NVLink4 measurement

Source: `results/measured/h100_nvls_20261004/README.md` (ours/measured). Setup:

- 8 x H100 SXM5 HGX, 4 x NVSwitch gen3, NVLink4;
- `%globaltimer`, 20,000 iterations, two repeats that agree within 1%.

| quantity (H100 HGX, NVLink4) | measured |
|---|---:|
| Peer load round trip via NVSwitch (GPU0→1/4/7) | 488–496 ns |
| Local HBM miss round trip | 150–160 ns |
| **One way GPU→NVSwitch→GPU = (490 − 155)/2** | **≈ 168 ns** (ours/derived; about 85 ns a link including the switch share) |
| Remote store ping-pong, relaxed, one way | 762 ns |
| `multimem.ld_reduce` round trip (in-switch reduce), 2/4/8 GPUs | 870 / 880 / 896 ns |
| NVLS all-gather via `multimem.st`, relaxed barrier, 8 GPUs | 1,382 ns (128 B) – 1,590 ns (32 KB) |
| One-shot NVLS all-reduce, relaxed sync, 8 GPUs | 2,244 ns (128 B) – 2,597 ns (32 KB) |
| same, data part only (both barriers removed) | 783–1,136 ns |
| One-shot all-reduce with sys-scope release/acquire | 8,904–9,144 ns |
| NCCL `all_reduce_perf` (no CUDA graph), 128 B–32 KB | 32–36 µs |
| Kernel launch / CUDA-graph node / grid.sync | 2,672 / 1,014 / 1,097 ns |

**377.6 ns is about 2.2x the measured NVLink4 one-way switch path (≈168 ns).** The NVLink path has:
- board traces only and no cables;
- a light link FEC;
- a 64-port switch.

Our crossing adds two cables, KP4-class Ethernet FEC on both links, and a 512-SerDes switch. The 2.2x margin is what
pays for those, and each term is priced from the vendor budget in §2.

Published figures from NVIDIA systems agree with the measurement (repo record
`results/uarch/hbm_switch_latency_range_20261004/switch_latency_research.md`, read 2026-10-04):

- GB200 NVL72 one-way remote store: 0.792 µs [G1].
- H100 NVLink point to point: 822 ns [G2].

Both include the SM and L2 path. That path is the 762 ns class above, not the 168 ns hardware path.

## 4. Why GPU collectives cost 2.2–2.6 µs and ours do not

Our measured GPU collectives are barrier- and fence-dominated:

- The relaxed one-shot all-reduce is 2.24 µs. Its two barriers take about 1.4 µs (0.70–0.73 µs each), and the data
  path is 0.78–1.14 µs.
- Correct sys-scope fencing costs 8.9–9.1 µs.
- NCCL without graphs costs 32–36 µs.

Published small-message all-reduce figures, including kernel-side sync:

- 2.37 µs (new one-shot) and 11.0 µs (NCCL ring) on 4 x GB200 [G1];
- 1.5–2.4 µs from 2 to 64 GPUs at 128 B [G1];
- ~2.3 µs (H800/H200) and ~3 µs (B200) for nccl-tests at 8 B [G3] [press/user report].

Our collectives are issued by hardware from a compiled static schedule. There is no kernel launch, no flag or barrier
polling, no memory fence and no NCCL protocol. Completion is by arrival counting. The apples-to-apples GPU figure is
therefore the hardware path: 168 ns one way, or the 0.78–1.14 µs data part of the all-reduce. It is not the 2.2–2.6 µs
kernel figure.

At 377.6 ns our one-flit gather is about 0.64 µs (ours/derived):

| term | ns |
|---|---:|
| crossing | 377.6 |
| endpoint | 90.5 |
| one flit | 19.8 |
| tail | 150 |
| **one-flit gather** | **≈ 0.64 µs** |

That compares with 1.38 µs for the measured H100 NVLS all-gather. A 32 KB all-reduce is 1.21 µs, against 2.60 µs measured on H100. That 1.21 µs is from
`results/uarch/hbm_switch_latency_authoritative_20261004/README.md`, which priced it at the older 477.6 ns crossing
that still included the 100 ns bridge.

## 5. Backup: a conservative, fully sourced crossing and the sensitivity

How the conservative build replaces each optimistic term (ours/derived):

- **Endpoint PHY/FEC.** Host KP4 FEC 100 ns [I2], with +25.6 ns codeword storage at 200G ports [I1]. Add SerDes
  Tx+Rx 60 ns (the DSP-retimer class implied by [P3]) and 10 ns MAC/buffer, which is an estimate. That gives 170 ns at
  400G and 195.6 ns at 200G.
- **Switch.** 250 ns [B1], plus the gap between the conservative ingress decode and Broadcom-class optimised decode
  (100 − 62.6 = +37.4 ns at 400G, +63 ns at 200G [I1, I2]). That gives 287.4 / 313 ns.
- **Cable.** 27.6 ns [A1].

| case | build-up (ns) | crossing | 96 x 32: DS AR / MTP tok/s | 192 x 16: DS AR / MTP tok/s |
|---|---|---:|---|---|
| **Headline (vendor budget, §2)** | 100 + 250 + 27.6 | **377.6** | **2,006.8 / 3,485.5** | **1,777.7 / 3,040.9** |
| Conservative, 400G ports (96 x 32) | 170 + 287.4 + 27.6 | 485.0 | 1,914.0 (−4.6%) / 3,377.2 (−3.1%) | 1,704.5 (−4.1%) / 2,958.6 (−2.7%) |
| Conservative, 200G ports (192 x 16) | 195.6 + 313 + 27.6 | 536.2 | 1,872.7 (−6.7%) / 3,327.5 (−4.5%) | 1,671.7 (−6.0%) / 2,921.0 (−3.9%) |
| 192 x 16 with AEC on every link (5 m) | 536.2 − 27.6 + 46 + 4 x 60 | 794.6 | 1,688.8 (−15.9%) / 3,097.6 (−11.1%) | 1,523.6 (−14.3%) / 2,744.6 (−9.7%) |
| General-purpose switch instead of TU (700 ns [A2]) | 170 + 700 + 27.6 | 897.6 | 1,625.2 (−19.0%) / 3,014.5 (−13.5%) | 1,471.6 (−17.2%) / 2,679.7 (−11.9%) |

- The rows above come from `switch_sens_sourced.json`, a rerun of `tools/hgi_sim/ds_switch_sens.py` on this branch at
  32cc21908. It reproduces the 377.6 baseline exactly.
- `switch_sens.json` (README §2) has the 500, 575, 650, 675, 800 and 1,132.8 ns rows.
- The slope is about −4.3% DS AR and −2.9% MTP per +100 ns.
- The 96 x 32 vs 192 x 16 ranking holds in every row.
- Qwen3-8B is invariant, because its all-reduces stay in package.

## Sources

- [B1] Broadcom, BCM78920 Tomahawk Ultra product brief (2025-08-27): https://docs.broadcom.com/doc/78920-PB
- [B2] Broadcom, Scale-Up Ethernet Framework Specification RM104 (2025-09-26), Appendix A, Fig. 22, p. 31:
  https://docs.broadcom.com/doc/scale-up-ethernet-framework
- [B3] M. Kalkunte (Broadcom), "High Performance Ethernet Solutions for HPC/AI Clusters", MUG'25:
  https://mug.mvapich.cse.ohio-state.edu/static/media/mug/presentations/25/mug25-High-Performance-Ethernet.pdf
- [P1] ConvergeDigest, "Broadcom ships Tomahawk Ultra" (250 ns at full load):
  https://convergedigest.com/broadcom-ships-tomahawk-ultra-to-power-ai-scale-up/
- [P2] The Next Platform, 2025-07-17. Tomahawk Ultra 250 ns hop; "<150 ns" SUE Tx+Rx; Tomahawk 6 600–700 ns; "We
  don't know the latency on NVSwitch port to port hops":
  https://www.nextplatform.com/2025/07/17/broadcom-tries-to-kill-infiniband-and-nvswitch-with-one-ethernet-stone/
- [P3] eeNews Europe, Point2 P1B121 retimer (3 ns, "20x lower than DSP-based PAM4 retimers"):
  https://www.eenewseurope.com/en/retimer-integrates-eight-serdes-channels-looks-to-1-6tbit-s/
- [U1] UALink Consortium, "A Deeper Dive: … UALink 200G 1.0 Specification Webinar Q&A": https://ualinkconsortium.org/?p=822
- [A1] Arista, "Copper Faster Than Fiber" brief (MetaWatch measurement):
  https://www.arista.com/assets/data/pdf/Copper-Faster-Than-Fiber-Brief.pdf
- [A2] Arista 7060X6 quick-look datasheet ("Latency from 700ns"): https://www.arista.com/en/products/7060x6-series-quick-look
- [T1] Tolly Report, Mellanox Spectrum vs Broadcom Tomahawk, 2016-03 (commissioned by Mellanox):
  https://www.cl.cam.ac.uk/teaching/2324/L50/files/tolly-report-performance-evaluation-2016-march.pdf
- [I1] M. Brown, "MAC link latency considerations", IEEE 802.3dj, 2023-04-13 (brown_3dj_optx_01c_230413), slides 4
  and 6. Also cited in A. Ran, Ethernet Alliance TEF 2025-12:
  https://ethernetalliance.org/wp-content/uploads/2025/12/Ran_TEF_2512.pdf
- [I2] Yin et al., IEEE 802.3df, 2022-07 (~100 ns module DSP + ~100 ns host KP4 FEC):
  https://grouper.ieee.org/groups/802/3/df/public/22_07/yin_3df_01b_2207.pdf
- [I3] Lyubomirsky et al. (Inphi), IEEE 802.3ck, 2019-09:
  https://grouper.ieee.org/groups/802/3/ck/public/19_09/lyubomirsky_3ck_01_0919.pdf
- [I4] P. Sun (Credo), 50GE low-latency schemes, 2016-02:
  https://www.ieee802.org/3/cd/public/adhoc/archive/sun_021016_50GE_NGOATH_adhoc.pdf
- [I5] Nicholl and Jones, IEEE 802.3ck, 2020-01 (IEEE 802.3-2018 Table 80-5, 409.6 ns):
  https://ieee802.org/3/ck/public/20_01/nicholl_3ck_01a_0120.pdf. Brown and Ran, IEEE 802.3cd 2016-11 (codeword
  ~55 ns + error marking ~55 ns): https://www.ieee802.org/3/cd/public/Nov16/brown_3cd_03_1116.pdf
- [N1] NVIDIA, "Introducing NVIDIA HGX H100":
  https://developer.nvidia.com/blog/introducing-nvidia-hgx-h100-an-accelerated-server-platform-for-ai-and-high-performance-computing/
- [N2] NVIDIA, "GB200 NVL72 Delivers Trillion-Parameter LLM Training and Real-Time Inference":
  https://developer.nvidia.com/blog/nvidia-gb200-nvl72-delivers-trillion-parameter-llm-training-and-real-time-inference/
- [G1] Shen et al., "Every µs Matters", arXiv:2607.16100. [G2] MSCCL++, arXiv:2504.09014, Table 1. [G3] NVIDIA
  developer forum thread 352473. All three are as read in `results/uarch/hbm_switch_latency_range_20261004/switch_latency_research.md`.
