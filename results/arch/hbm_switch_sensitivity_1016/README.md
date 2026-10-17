# HBM arrays: one-tier switch feasibility and crossing-latency sensitivity (HBM-NET, 10-16)

Owner question: the HBM-accelerator arrays (96 x d4c, 32 SM / 4 stacks; 192 x d4f, 16 SM / 2 stacks) assume a
one-tier switch with a 377.6 ns crossing. The crossing is PHY/FEC 100 + Tomahawk Ultra 250 + 2 x 3 m twinax 27.6,
a VENDOR BUDGET. Is that crossing realistic? Is the one-tier fabric buildable? Does the 96/192 ranking hold?

Grade: schedule model plus analytic fabric arithmetic. No RTL or switch measurement is new here.

- `switch_sens.json` comes from `tools/hgi_sim/ds_switch_sens.py`. That script uses the same S2 schedule, stages and
  split transform as `hgi_sim.ds_die_split`, and it reproduces 2,006.8 / 3,485.5 and 1,777.7 / 3,040.9 exactly at
  377.6 ns.
- `planes.json` comes from `tools/hgi_sim/ds_switch_planes.py`.

## 1. One-tier fabric: port width, planes, chips, cables

**Public port modes**
- Tomahawk Ultra (BCM78920) is 51.2 Tb/s from **512 x 100G PAM4 SerDes** (The Register, 2025-07-15).
- Broadcom's own TU slide (MUG'25) shows an **"Example 256 XPU Pod"**: a multi-plane fabric with "256 x 200G = 51.2T"
  per chip, "switch latency ~250 ns with FEC" and "E2E < 400 ns". This is exactly the 16-plane form below.
- The 64x800 / 128x400 / 256x200 / **512x100GbE** port table is printed for Tomahawk 5 (same 51.2T and 100G SerDes
  generation). For TU, secondary sources list 64x800 / 128x400 / 256x200 only. 512 x 100G single-lane ports on TU are
  **plausible but not confirmed in a primary source**.

Each die has 32 x 100G lanes to the fabric. A chip has 512 lanes. A port of w lanes gives P = 32/w planes and
512/w dies at most. A one-tier plane must reach every die, so P must divide 32. The README's "at least 12 chips" for
192 dies cannot be built with an integer lane split: the minimum is **16**.

| port (lanes) | planes = chips | max dies | 96 dies | 192 dies | cables (one per die-plane) |
|---|---:|---:|---|---|---|
| 800G (8) | 4 | 64 | no | no | — |
| 400G (4) | 8 | 128 | **yes: 8 chips, 96/128 ports used** | no | 768 |
| 200G (2) | 16 | 256 | yes, 16 chips, 37.5% of ports used | **yes: 16 chips, 192/256 ports (Broadcom's pod)** | 1,536 / 3,072 |
| 100G (1) | 32 | 512 | 32 chips | 32 chips, 37.5% of ports used (mode unconfirmed on TU) | 3,072 / 6,144 |

Choice: 96 dies use 8 x 400G planes. 192 dies use 16 x 200G planes. 32 planes buy nothing: the per-receiver drain
is the same, FEC is slower and there are twice the MACs and cables.

**Endpoint MAC/PCS per die**
- P port MACs (8, 16 or 32), plus one host link. The SerDes count (32) is unchanged.
- Estimate: the MAC/PCS/RS-FEC plus per-port LLR/CBFC state is ~0.15–0.25 mm² per port in N5-class logic (ESTIMATE,
  no datasheet). That gives about 2–4 mm² for 16 ports and 5–8 mm² for 32: under 1.3% of a 618 mm² d4f.
- The measured COLL endpoint RTL stripes over 8 ports. A 16-port version must be re-measured before d4f claims the
  endpoint figures.

**Cable reach (assumptions)**
- Packages are 2 dies each (the uarch_model TU tier). 3 m passive twinax at 100G/lane. 32–48 packages per rack;
  racks are 0.6 m wide and about 2 m tall.
- The switch shelves (8 or 16 chips, NVL72-style 1RU trays) sit in the centre rack. A link to the centre rack or an
  adjacent rack is at most about 0.9 m horizontal + 1.2 m vertical + 0.5 m slack, which is 2.6 m: copper.
- A rack two positions away is about 3.2 m or more and needs AEC.

| array | packages | racks (32–48/rack) | links > 3 m |
|---|---:|---:|---|
| 96 x d4c | 48 | 1–2 | **0%** (all copper) |
| 192 x d4f, 2 dies/pkg | 96 | 2–3 | **0%** when there are at most 3 racks with the switch shelf in the centre rack; ~33% when a 4th rack is needed |
| 192 x d4f, 1 die/pkg | 192 | 4–6 | 33–50% |

A collective completes on its slowest path, so even a few long links set the crossing for every collective.

| long-link medium | added per crossing (die→switch and switch→die legs) |
|---|---|
| AEC, retimer ~20–40 ns a link | +40–80 ns |
| optics, DSP module ~50–100 ns each end plus host FEC | +200–400 ns |
| LPO | about +40–100 ns |

For scale: NVL72 is about 2,600 lanes of 200G copper in one rack. 192 x d4f at 16 planes is 3,072 two-lane cables
(6,144 lanes), about 2.4x NVL72. That is buildable in 2–3 racks with a central switch shelf, but it is the hardest
part of the array.

## 2. Crossing sensitivity (DS 1M context; MTP = the design point at τ 4.159)

The crossing rule (see the module docstring) charges dX only for crossings that a record's base price actually
contains: one for a gather or merge, two for the o-group reduce. Members of a merged collective train pay none, because
the train's head pays the crossing. The MTP draft's collectives take X through `perf.coll_cycles`.

Qwen3-8B AR (TP-4 on 96 x d4c, 940.2 tok/s; TP-8 on 192 x d4f, 934.1 tok/s) runs its all-reduces in package
(G ≤ 8): **0% at every X** by model construction. It would pay switch crossings only if its TP group spans packages.

| crossing X (ns) | 96 x 32: DS AR | DS MTP | 192 x 16: DS AR | DS MTP | 192 vs 96 at the same X (AR / MTP) |
|---:|---:|---:|---:|---:|---|
| 377.6 (baseline) | 2,006.8 | 3,485.5 | 1,777.7 | 3,040.9 | -11.4% / -12.8% |
| 500 | 1,901.7 (-5.2%) | 3,362.5 (-3.5%) | 1,694.7 (-4.7%) | 2,947.5 (-3.1%) | -10.9% / -12.3% |
| 575 (96 pessimistic) | 1,842.6 (-8.2%) | 3,290.8 (-5.6%) | 1,647.6 (-7.3%) | 2,893.1 (-4.9%) | -10.6% / -12.1% |
| 650 | 1,787.0 (-11.0%) | 3,222.2 (-7.6%) | 1,603.1 (-9.8%) | 2,840.6 (-6.6%) | -10.3% / -11.8% |
| 675 (192 pessimistic) | 1,769.2 (-11.8%) | 3,199.9 (-8.2%) | 1,588.7 (-10.6%) | 2,823.5 (-7.2%) | -10.2% / -11.8% |
| 800 | 1,685.4 (-16.0%) | 3,093.1 (-11.3%) | 1,520.8 (-14.4%) | 2,741.1 (-9.9%) | -9.8% / -11.4% |
| 1,132.8 (= 2-tier Clos, 3 x 377.6) | 1,496.5 (-25.4%) | 2,838.3 (-18.6%) | 1,365.3 (-23.2%) | 2,540.7 (-16.5%) | -8.8% / -10.5% |
| 2-tier, the `--extra-crossings 2` convention (every COLL record) | 1,056.7 (-47.3%) | 1,833.2 (-47.4%) | 992.1 (-44.2%) | 1,712.3 (-43.7%) | |

**Slope**
- The AR token has about 225 crossings on its critical path: 27.5 µs per +122 ns. The MTP step has about 357.
- AR therefore loses about **4.3% per +100 ns** and MTP about 2.9%. The absolute cost is the same for both arrays.
- So 192 x 16 is never relatively better by more than a point.

**Correction to the earlier "2-tier = -50%" figure**
- `ds_die_split --extra-crossings` charges a crossing to every COLL record. That includes the train members (the
  x_projections qa/kvraw/cmp/iwr gathers and the seven expert_intermediate gathers, priced at 126–383 cycles with no
  crossing) and the zero-cost engram and candidate-merge records.
- Priced against what the base prices actually contain, a 2-tier Clos costs **about -25% AR and -19% MTP, not -50%**.
- It is still a large loss, so the one-tier conclusion stands.

## 3. What the model leaves out, and a pessimistic crossing

**Incast and port oversubscription.** Gathers use one multicast crossing: every receiver port gets the fragments of
all G-1 sources. The compiler places them statically. A fragment of at least 256 B per plane is striped over all
planes; a smaller fragment goes whole to plane (source mod P). Then:

- **Balance.** Every plane carries G/P = 12 sources (96/8 and 192/16). Every output port of a multicast all-gather
  carries the identical load. No port is oversubscribed beyond its 1/P share, plane imbalance is 0, and the compile-time
  schedule can guarantee both. A plane failure breaks this and needs a recompiled schedule (degraded mode).
- **Small classes** (768 B – 12 KB gathered, the 4–128 B fragments behind ~97% of the AR token's 562 collective records):
  - Each fragment becomes a minimum frame: payload efficiency is 4–8% (192) and 8–76% (96).
  - Receiver-port drain is 25 ns at G 96 and 50 ns at G 192. The model's delivery term is 20 / 40 ns.
  - The gap is **about +5 to +10 ns a crossing**, and it is the same for any P.
- **Largest class.** The index TOPK_MERGE is 393 KB at G 96, rising to 786 KB at G 192 (4 KB per source, 256 B per
  plane at P 16):
  - Port drain is 1.05 µs at G 96 and 2.26 µs at G 192. The modelled endpoint delivery is 1.27 µs and 2.55 µs, so the
    drain is hidden behind it.
  - Unpaced, the burst needs up to about 5 MB (96) or 10.5 MB (192) of shared switch buffer per chip. TU's buffer is not
    published. The switch-link CBFC (flow control is allowed at off-die boundaries) or a rotated injection order bounds
    this without changing the drain bound.
- **Plane-skew tail.** The completion is the maximum over G x P paths (1,536 for 96; 3,072 for 192). At σ 20–50 ns
  per path, that is +60–150 ns (switch_latency_research.md §2). The model's 0.15 µs tail covers the low end only.
- **FEC and LLR.**
  - RS(544,514) codeword accumulation is 12.8 ns per Rx on a 4-lane port, 25.6 ns on 2 lanes and 51 ns on 1 lane.
    That is 2 decodes per crossing, so +13 / +38 / +90 ns against an 8-lane (800G) port.
  - LLR retry costs about one link RTT, 0.2–0.5 µs. A token moves about 4e7 link-packets. At a post-FEC frame error
    rate of 1e-12 to 1e-10 that is about 4e-5 to 4e-3 retries per token: the mean cost is negligible and it is a
    p99.9 tail term. At a marginal 1e-8 (AEC or optics) it is about 0.4 retries per token, about 0.04% of the mean.

**Pessimistic but plausible crossing**

| term | 96 x 32 | 192 x 16 |
|---|---:|---:|
| vendor budget | 377.6 | 377.6 |
| switch under full multicast load vs the 250 ns claim | +50 | +50 |
| narrow-port FEC (400G / 200G ports) | +13 | +38 |
| min-frame incast drain beyond the model | +10 | +10 |
| plane-skew tail beyond the 0.15 µs budget | +100 | +100 |
| long links: AEC on a 4th rack + longer cable | 0 | +60 + 18 |
| **pessimistic crossing** | **≈ 575 ns** | **≈ 675 ns** (≈ 600 with no AEC) |

At those figures:

| array | DS AR | DS MTP |
|---|---:|---:|
| 96 x 32 | 1,842.6 (-8.2%) | 3,290.8 (-5.6%) |
| 192 x 16 | 1,588.7 (-10.6%) | 2,823.5 (-7.2%) |

That puts 192 x 16 at **-13.8% AR and -14.2% MTP vs 96 x 32**. Optics on all long links (+200–400 ns) would reach
about 800–1,000 ns: -16 to -22% AR.

## 4. Verdict

377.6 ns is optimistic but not far off for the 96-die array. It is Broadcom's own SUE budget, with the endpoint
bridge replaced by measured RTL, and Broadcom's TU slide claims under 400 ns end to end. Realistic additions are
switch load, narrow-port FEC, min-frame incast and, above all, the maximum-over-paths skew tail. They put a plausible
pessimistic crossing at about 575 ns for 96 x d4c and about 675 ns for 192 x d4f.

The 192 x d4f figure is higher because it needs 2-lane ports (16 planes, 16 chips, 3,072 cables, about 2.4x NVL72
copper), and it needs AEC once the array spills past 3 racks.

Each +100 ns costs about 4.3% DS AR and 2.9% MTP in absolute time, identically for both arrays. The 192 vs 96 gap
therefore barely moves at equal X: -11.4% at 377.6 and -9.8% at 800. Under the pessimistic pair it widens to
-13.8% AR / -14.2% MTP.

**The ranking does not change: 96 x 32 / 4 stays ahead.** The one-tier requirement still holds, but the earlier
"2-tier = -50%" overstates it: a priced 2-tier Clos is about -25% AR. Qwen is unaffected, because its collectives are
in package.

Sources:
- [The Register: Tomahawk Ultra, 512 x 100G SerDes, 250 ns](https://www.theregister.com/2025/07/15/broadcom_ethernet_scale_up/)
- [Broadcom MUG'25 slides: TU 256-XPU multi-plane pod, 256 x 200G, E2E < 400 ns; TH5 port table](https://mug.mvapich.cse.ohio-state.edu/static/media/mug/presentations/25/mug25-High-Performance-Ethernet.pdf)
- Broadcom SUE RM104 App. A crossing budget; RS-FEC and LLR figures from `results/uarch/hbm_switch_latency_range_20261004/switch_latency_research.md`
