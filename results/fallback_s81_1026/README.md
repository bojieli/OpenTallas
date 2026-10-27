# FALLBACK-S81 2026-10-26: bottom-up landed fallback plan for the S81 die (all numbers UNCHECKED unless marked)

Owner 10-26 16:5x: the bottom-up landed fallback runs in parallel with the master-plan path, and the first to pass the
12.4a freeze gate wins. This is the S81 die lane. Input plan: PATH-S81 B2 g0fix
`epyc1:/srv/opentallas-scratch2/claude/path-s81-taps-1026/src/physical/die_plan/s81/die_plan_phyfit_g0fix.json`
(398 partitions / 210 types / 2,368 ports / 873 lanes). Latency of record: `physical/die_plan/s81/lat/s81_latency.json`
(869 lanes, all matched).

## 1. Plan

**Root cause the fallback avoids.** 216 col partitions hold ROM-elem cores (552 ps TT) and bf_col cores (645 ps). bk_sel
holds a 430-ps core and gunit a 520-ps core. Under 12.8 these need core rebuilds to 250 ps, and the die clock cannot be
built without the 1,322 banned early taps. The fallback keeps every core as it is.

**Clock structure.**
- Each partition closes its own tree from one partition root. The cores in a col/bk_sel/gunit partition are fed by that
  partition's own CTS instead of by die early taps (plan delta: `clock.core_taps` off on 30 types). So its boundary
  flops sit in a core-led latency class.
- Classes: `core640` (216 partitions), `core520` (gunit), `core430` (bk_sel) and `std` (180 partitions, 250 ps).
- A clock REGION is the set of same-class partitions inside one GxG block of the partition lattice that are connected by
  plan ports. One equal-leg local tree feeds the partition roots of a region, and those related pairs are timed.
- The hard PHY (`phy_hbm`) cannot host a ring, so it shares one region with all 7 of its neighbours (svc_2/4/6/8/10/12
  and eng). That region is about 8.7 x 3.7 mm, the largest local tree in every option (see risks).
- Every plan port between regions is LANDED. A forwarded clock runs beside the bus, and an `ot_dp_clk_landing` ring
  (DEPTH4/OFFSET2/RDREG1) sits in the sink partition. That adds +3 cycles at a fixed static latency, with no credits.
  This is the existing main contract (`clock_landings.py`: data_cycles_per_crossing must be 3).
- FT reading `face`: ft stations run on the crossed partition's clock, so a lane lands at every landed face. This is
  what the existing tools build today.
- FT reading `fwd`: ft stations run on the lane's forwarded clock (half-cycle forwarded hops), so a lane lands once at
  its sink. This needs a new forwarded-clock ft-slot feature that no tool implements yet.

**Price** (compose_tok_ds on main 63f0898a3). The base reproduces 784.9 AR / 2,749.3 MTP per user. The partition rows
reproduce the 11:19 FALLBACK-LAND k3_face / k3_port rows exactly, with a different tool (CHECKED by reproduction).

| Region option | Regions (max parts) | Landed ports / bits | Lane cycles added face / fwd | AR tok/s face / fwd | MTP tok/s face / fwd | Ring area (4.66 um2/bit, UNMAPPED) | Types after compose |
|---|---|---|---|---|---|---|---|
| partition (G=1) | 391 (8) | 2,323 / 1,078,704 | 6,969 / 2,502 | 758.1 (-3.41 %) / 771.9 (-1.66 %) | 2,662.0 (-3.18 %) / 2,707.6 (-1.52 %) | 5.03 mm2 (0.64 %) | 222 |
| class G=2 (<= 2.9 x 2.5 mm, except the PHY region) | 172 (8) | 1,206 / 574,571 | 3,618 / 1,761 | 767.7 (-2.19 %) / 773.9 (-1.40 %) | 2,693.8 (-2.02 %) / 2,714.1 (-1.28 %) | 2.68 mm2 (0.34 %) | 244 |
| class G=4 (<= 5.8 x 4.9 mm) | 80 (16) | 679 / 325,296 | 2,037 / 1,170 | 771.9 (-1.66 %) / 773.9 (-1.40 %) | 2,707.4 (-1.52 %) / 2,714.1 (-1.28 %) | 1.52 mm2 (0.19 %) | (not composed) |

**Recommended fallback: class G=2 with face landing**, because the existing tools build it end to end. For TOK-DS to
price, the delta is **AR -2.19 %, MTP -2.02 %**, a LOWER BOUND: measured field records keep their old embedded wires
and are not re-landed. On top of the owner-accepted 17.0 % S81 ledger that gives about 19.0-19.2 %, so it needs owner
OK if the fallback wins. The strictly per-partition form costs -3.4 / -3.2 % (about 20.4 % ledger). The fwd-FT form
would cost -1.4 / -1.3 % but needs new tooling. G=4 saves only another ~0.5 % and has 5.8-mm local trees.

## 2. Die GEN with the landed-crossing tooling (existing main tools)

- `tools/die_plan/fallback_regions.py plan` (new) writes the region map and `landed_crossings.json`, in the
  die_clock_mesh `write_landed` format with one box per partition. It also writes `lat_face.json` / `lat_fwd.json` and
  a summary. It has 2 unit tests.
- `clock_landings.py` requirements: see `regions/*/requirements.json`. Partition mode needs 9,472 new scalar pins and
  5.41 M live ring FFs. G=2 needs 4,944 pins and 2.88 M FFs.
- `clock_landing_plan.compose` (main, unchanged) is driven by `compose_plan.py`. The observer is the reset-wavefront
  root `s_4S_L3`. It produces the real fallback plans, with fclk/ready/fault pins, ring storage bands, a reverse
  wavefront monitor and `clock.landing_network`:
  - partition: 222 types, 3,505 infra edges, boot ready 476 cycles, **186 ring storage-band placement FAILs**;
  - G=2: 244 types, 2,239 infra edges, boot ready 455 cycles, **126 ring storage-band placement FAILs**.
  - Both plans are on `epyc1:/srv/opentallas-scratch2/claude/fallback-s81-1026/plan_{partition_g0,class_g2}.json`
    (125 MB, not committed), with matching side_*.json.
  - The FAILs are all "no macro-free clock landing storage band" on wide svc/slice inputs (svc_hi/lo_rs, slice_c1x,
    pvso_entry, lep*, bk_sel). Those types need band reservations or outline growth in the plan before any kit.
- G0 (main check.py, plus the S81 explicit-tap schema support cherry-picked from codex/s81b2-0733 9917e9a37e). The
  plan-dir inputs were copied from the PATH-S81 src tree and are untracked. Results are in g0/*.summary.txt and the gz
  reports:
  - base g0fix: G0 FAIL, 24 errors. These already exist on the main tools (8 cut-capacity errors and others); the
    PATH-S81 src tree reported 0.
  - G=2 fallback: 611 errors = the same 24 + **587 latency-table errors, exactly the 587 landed lanes**. Each reads
    "table says N, plan gives N+3k": the composed plan's latency.lanes is not regenerated yet, and that table is
    lat_face.json. 244/244 types are G0C clean, with no landing-contract, pin or schema error.
  - partition fallback: 858 = 24 + 834 (its 834 landed lanes). 222/222 types are G0C clean.
  So the die GEN is consistent. The remaining G0 work is mechanical (write the lat_face lanes into latency.lanes), plus
  the 126/186 ring storage-band placement FAILs (plan outline / band reservation).

## 3. Die GRT / die STA: NOT RUN (stated, not hidden)

- **Die GRT.** The signal nets are the B2 g0fix nets plus 1-bit fclk/ctl infra edges (G=2: 2,239). The inherited
  signal-only GRT (`path-s81-taps-1026/die_g0fix_i50`, not owned by this lane) was at iteration 47/50 at 17:14.
- **Clock.** The fallback clock (per-region local equal-leg trees to one root per partition, plus a reference
  distribution to the region roots with no skew constraint) needs a region-list builder. die_clock_mesh `--regions`
  only makes power-of-two geometric regions. The plan is die_clock.py run per region sub-plan.
- **Die STA.** Real views do not exist: 4/171 types are signed, and every type with a landed input changes (rings + pins).
  The 30 core-class types also need a partition-internal CTS rebuild. So the 12.4a gate for the fallback sits behind
  partition rebuilds, as the master plan does, and saves only the core rebuilds and the die-wide 12.8 clock.

## Risks / asks
- The PHY region (8 partitions, ~8.7 mm span) is one local tree. Alternative: sender-side landing for svc->phy, which
  is a tool extension.
- Partition-local CTS feeds the 552/645-ps cores early inside the partition. That is standard macro-latency CTS, but
  COORD must rule that this is the fallback's own tree and not a 12.8 early tap.
- 2.9-5.4 M ring FFs are added clock sinks, inside the partitions.
