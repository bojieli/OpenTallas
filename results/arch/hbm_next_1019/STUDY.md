# HBM-NEXT Phase 1: re-check of P = 4 position lanes (2026-10-19)

This is next-release work, not a release gate. It is an isolated fork: branch `claude/hbm-next-study-1019`, this directory, no d4g/GEN2 edits, no release element ids.

The base is the D1 model (`tools/hgi_sim/hbm_plane_model.py`, unchanged; `results/arch/hbm_mtp_next_1018`). Each check re-times DS MTP (N = 6) and DS multi-user (N = P users) on that model with one knob changed. The runs were on ot-epyc5 and the records are in `runs/`.

**Verdict: P = 4 holds.** It is the largest P that keeps every user at or above 1,000 tok/s and still fits the reticle. There are two conditions. The HC row engine must reach a further-row II of about 950 cycles or less; the measured static engine's 4,385 does not hold the floor. And the SM column has to be re-shaped (taller tiles), because x-only growth does not fit the reticle.

## Verdict table (DS, tok/s; MU = P users at 1M)

| check | knob | P=2 MTP / MU agg / per user | **P=4 MTP / MU agg / per user** | P=6 per user | P=4 verdict |
|---|---|---|---|---|---|
| D1 base | — | 3,143 / 3,060 / 1,530 | **3,364 / 4,365 / 1,091** | 859 | reference |
| (a) COLL delivery lanes | L = 4 (d4g) | = D1 (reproduced exactly) | 3,364 / 4,365 / 1,091 | 859 | OK |
|  | L = 5 (widest the 400 GB/s SerDes feeds) | 3,227 / 3,132 / 1,566 | 3,460 / 4,482 / 1,120 (AR 1,950) | 889 | +2.7 % agg, +2.3 % single-user AR: adopt |
|  | L = 8 (on-die only, not SerDes-feedable) | 3,312 / 3,198 / 1,599 | 3,559 / 4,599 / 1,150 (AR 2,012) | 919 | info only |
| (b) VM capacity | VM as built (column swaps) | 3,071 / 2,927 / 1,464 | 3,281 / 4,225 / 1,056 | 837 | OK either way; grown VM worth +2.5 % / +3.3 % |
| (c) HBM capacity, P users x 1M KV | arithmetic | — | 3.7 GB KV a die (worst case, replicated) of 128 GiB | — | OK (~110 users a die at 1M) |
| (d) HC row II | 250 (HCP x6 measured; D1) | 3,143 / 3,060 / 1,530 | 3,364 / 4,365 / 1,091 | 859 | OK |
|  | 600 | 3,004 / 3,049 / 1,525 | 3,187 / 4,273 / 1,068 | 815 | OK |
|  | 1,000 | 2,765 / 2,989 / 1,494 | 2,919 / 3,967 / **992** | 742 | below floor |
|  | 4,385 (static engine as measured) | 1,651 / 2,322 / 1,161 | 1,704 / 2,473 / 618 | 423 | fails; the compiler falls back to per-position HC |
|  | no HC rows (per-position fallback) | 2,687 / 2,967 / 1,484 | 2,832 / 3,867 / **967** | 719 | below floor |
| (e) floorplan, two SM bands | x-only column growth | fits (21.0 x 31.8 mm) | **does not fit** (26.6 mm wide > 25.5) | no frame | must re-shape |
|  | re-shaped columns (lattice width, same column area) | 20.4 x 32.2 mm, 656 mm² | 23.2 x 32.4 mm, 750 mm² (or 23.8 x 31.5, 752 mm²) | no frame fits | OK |

The DS single-user AR is 1,905.4 at every P with L = 4: multi-user and MTP lanes take nothing from single-user.

## (a) Collective / network ceiling

The d4g die delivers off-die collectives over 4 COLL delivery lanes at 64 B a lane a cycle: 256 B/cycle, which is 307 GB/s at 1.2 GHz. The die's SerDes is 32 x 100G, 400 GB/s raw a direction and about 320-385 GB/s after framing.

At P = 4 multi-user, COLL is busy for 492.5k of the 1,099.6k step cycles (44.8 %). Even if every busy cycle carried a full 256 B, the die would need 0.448 x 307 = 138 GB/s. That is at most 34 % of the raw SerDes (43 % of a 320 GB/s framed rate). The real byte rate is lower, because the busy time includes each collective's 741.7-cycle fixed part (endpoint, 377.6 ns switch crossing, tail).

The switch plane is single-tier and every die has its own port, so the per-die bound is the plane bound. The 192 dies stay on one plane. **The network is not the ceiling at P = 4.**

One wider COLL lane (L = 5, 320 B/cycle, still under the SerDes) buys +2.7 % multi-user aggregate and +2.3 % single-user AR. We recommend it for the next die. L = 8 would be port-drain bound in bursts, so it is recorded as information only.

## (b) VM capacity

The D1 headline grows the VM by (N - 1) x ~30k words so that N verify or user columns stay resident. With the VM as built, the columns are swapped per layer. That costs 2.5 % of MTP and 3.3 % of multi-user aggregate at P = 4, and the per-user rate stays at 1,056. The VM is therefore not a blocker. Growing it (about 2^18 -> 2^18.6 words over the 4 quadrant slices) is worth doing if the area is free in the re-shaped frame.

## (c) HBM capacity for P users x 1M KV

The model is DeepSeek V4.1-Flash. The global KV is 890 B a token: a 288 B FP4 latent plus a 68 B index key, owned by layers 2/8/14/20 (`configs/models/candidates/deepseek-v4.1-flash.json`). That is 0.93 GB per user at 1,048,576 positions. The sliding-window rings (528 B x 128 x 40 layers) are 2.7 MB, and the MTP 256-slot ring adds 128 rows a layer, which is negligible.

As a worst case, assume every die holds a full replica. Then P = 4 users take 3.7 GB a die (P = 8: 7.5 GB).

The busiest die is an Engram home die: 98 GB / 4 = 24.5 GB of Engram table. It also holds about 1.6-3.2 GB of streamed weights (about 311 GB of non-Engram weights over 192 dies, x2 if a plane replicates). That totals about 31 GB of the 128 GiB the E-HOME map uses (144 GB physical). Capacity allows about 110 users at 1M a die. **Not binding.**

## (d) HC row speed

The D1 price uses II 250 for a further HC.HC_MIX row (HCP W256 x6 mode, measured: (1,578 - 328) / 5). The static HC engine (`codex/hc-static-engine-1014`, 128 MAC lanes) measured 4,385 a further row.

At 4,385, P = 4 multi-user falls to 618 tok/s a user. That is worse than dropping HC rows altogether (967 a user), so the compiler would emit per-position HC. Both are below the 1,000 floor.

The per-user rate is linear in II at about 216 cycles of step per cycle of II. It crosses 1,000 tok/s at **II ~950**. At II 600 it gives 1,068, within 2 % of D1. **The next die needs an HC engine in row mode with a further-row II of 600 or less (950 at most).** The HCP W256 x6 form is the measured design that meets this. This is a Phase-2 kit alongside the SM and attention lanes; it is not a P = 4 blocker.

## (e) Die area and floorplan aspect (`frame.py`, `frame.json`)

The base is the d4g plan: die 20,200 x 31,773.52 µm, two SM bands of 8 columns each (1,939.68 x 6,955.2 µm), 961 µm side margins, and a hub band between the SM bands. Each lane adds 345.6 µm to the column width (D2: +86.4 µm a tile x 4 tiles across). The reticle limit with a 500 µm margin is 25.5 x 32.5 mm.

- **x-only growth** (the D2 form at P = 2): at P = 4 the die is 26,572 µm wide. That is over the reticle.
- **Re-shaped columns** (the column width on the 43.2 µm lattice, the same column area, the hub band re-packed at the same density):
  - P = 4, cw 2,548.8: die 23,151 x 32,406 µm = 750 mm², SM tile about 610 x 1,890 µm (aspect 3.1). This is the smallest frame, but it leaves only 594 µm of vertical margin.
  - **Recommended:** cw 2,635.2. Die 23,842 x 31,536 µm = 752 mm², margins 2.2 / 1.5 mm, tile about 632 x 1,824 µm (aspect 2.9, which is squarer than today's 3.16).
- **P = 6 and P = 8: no two-band frame fits** (the column area is too large for 8 columns a band under 32.5 mm). P = 6 would need a new band structure, and it also misses the per-user floor (859).

**The P = 4 die is about 752 mm² against D1's 742.9 mm².** The extra ~9 mm² is lattice rounding plus the hub re-pack. The SM tile becomes taller: the leaf arrangement must change (for example, stacking the extra lane's block-dot and BF16 column vertically). The closed leaf views are reused, and the arrangement is the Phase-2 SM-tile kit question.

## Why P = 4 and not another P

- P = 2 has the best tok/s per mm² (D1), but its aggregate is 3,060 against 4,365.
- P = 6 drops to 859 tok/s a user (below 1,000) and has no reticle frame in the two-band layout.
- P = 8 is over the reticle (876 mm² before any frame).
- P = 4 is 1,091 a user (1,120 with L = 5 COLL), 4,365-4,482 aggregate, and 3,364-3,460 MTP, with single-user AR unchanged. It has two conditions: HC row II of 950 or less, and re-shaped SM columns.

## Phase 2 floorplan (P = 4)

- **Die:** 23,842 x 31,536 µm, two SM bands of 8 columns (cw 2,635.2, ch ~7,856), hub band re-packed at d4g density. **Quadrants** stay aligned with the 4 HBM stacks / channel groups (d4g plan (b)). Each quadrant has 4 SM columns a band, its COLL/VM/IDX slice, and its HBM PHY edge.
- **COLL:** 5 delivery lanes (L = 5), so each quadrant COLL gets one more 64 B lane. SerDes are unchanged (32 x 100G). Links are landed (4-slot ring, fixed latency, forwarded half-cycle hops on long lanes).
- **New element types, highest risk first** (namespace `hnx_*`, dirs `rtl/hbm_next/`, `physical/hbm_next/`):
  1. `hnx_sm_tile_p4`: the SM P = 4 lane tile. It is the release generator at P = 4 with the closed bdc / tcl / tct / xs leaf views x4 a leaf position, the per-lane broadcast tree registered (+1 cycle), re-shaped to about 632 x 1,824 µm.
  2. `hnx_sm_attn_p4`: the P-query (4-slot) KV-line-stationary attention lane (pv_merge / sum_capture / pstore x4, line-mask issue).
  3. `hnx_hc_row`: the HC engine in row mode at II 600 or less (HCP W256 x6 form, + 2 Sinkhorn), P = 4 rows.
  4. `hnx_sm_col_p4`: the parent column cluster (16 tiles, landed regions), after 1 and 2.
- About 14 tile types change in control only (D2 §4 list, with N = 4 in place of 2). Every other element is unchanged.

## Records

- `coll_lanes.py`, `hc_ii.py`, `vm_cap.py`: the sensitivity drivers. They use an explicit `fork` multiprocessing context. The first runs on 10-18 were invalid: the fleet's Python 3.14 defaults to `forkserver`, so the knob patches never reached the pool workers, and every L / II gave identical results.
- `runs/*.json`, `runs/*.log`: fleet outputs (ot-epyc5), rerun 10-19 ~00:00.
- `frame.py`, `frame.json`: the floorplan arithmetic.
