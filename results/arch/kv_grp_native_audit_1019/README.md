# KV GRP / GRP_H source-native audit and successor model

**HOLD. Neither square clock variant is source-safe or release-qualified.**
This is an artifact-only audit. No RTL, gate helpers, constraints, review,
submission, cancellation, or schedule was changed.

The four live gates use source `7e6cbb4658e0fb8a7273b1bb29a7ef8c28fd255d`.
`live_runs.json` records exact local clients, ep7 container IDs/PIDs/mounts,
container process trees, source archive/manifest hashes and every kit file hash.
At collection their hold-repair loops retained **−74.905 ps** at `y__tep[0]`
(grp) / `y__tep[12]` (grp_h), while delay-cell counts continued above 11,000.
These are live diagnostics, not terminal results. No process was stopped.

## Actual native census

`dump.tcl` reads each **existing** `3_5_place_dp.odb` in its live container;
it does not synthesize or modify the database. `census.py` traverses every
non-PG native logical pin, transparently crossing all BUF/INV cells and
retaining actual endpoint pins (not physical contact multiplicity). No
fanout cap or FF-only filter is applied. Clock roots are reported separately.
Both runs used unpinned `ot-run --mem 3 --threads 1` with input data locality.

| Quantity | grp | grp_h |
|---|---:|---:|
| FF output roots >32 | 41 | 36 |
| Maximum FF endpoint fanout | 294 | 294 |
| Combinational output roots >32 | 194 | 194 |
| Maximum combinational endpoint fanout | 280 | 284 |
| Maximum top-input fanout | 18 | 18 |
| Maximum macro-output fanout | 1 | 1 |
| Maximum tie-output fanout | 5 | 9 |
| Nonclock top-input bits | 1,745 | 1,600 |
| Inputs reaching logic/output before a FF | 1,577 | 1,450 |
| FF additional copies, arithmetic lower bound | 140 | 127 |
| Comb additional useful copies, arithmetic lower bound | 550 | 550 |

The copy lower bound is `sum(ceil(endpoints/32)-1)` per existing unsafe root.
It excludes new reset/control loads and is **not** a fixed-point source plan,
area estimate or authorization. Copies must reproduce actual source equations,
remain distinct through synthesis, and satisfy a second uncapped native census.
Reset roots include `u_slg.g_hop[0].u_rsp.u.rn` (294 endpoints), the four
`u_ftd*.rn` (271 each), three response resets (256 each), and `u_lcal.rn` (199).
Buffer trees do not remove these logical fanout failures.

`grp_full.json.gz` and `grp_h_full.json.gz` contain **all** roots and **all**
endpoint identities, including safe, clock, tie, input, macro and comb roles.
The compact JSONs add source-manifest and placed-ODB hashes and retain every
unsafe root plus boundary results. The full JSON SHA is in each compact file;
the dump SHA pins the input TSV retained next to its fleet ODB. Gate layout
dump counts are not substituted for actual ODB root counts.

## Structural successor model, before RTL

1. **Boundary ownership fails.** Generated source lines 1202–1204 and
   1622–1624 directly alias `y__est__0_1`, `y__tok[17:0]`, and `y__tep[15:0]`
   to input words. This is 35 bits with a real input→output path. The loop's
   endpoint is exactly one of these aliases. Clock-topology variants cannot
   make these paths registered. A standalone safe tile needs an explicit
   face register contract or a boundary repartition that leaves these wires
   inside a registered parent. A fresh two-face wrapper costs 70 FF for these
   aliases alone and **+2 ck edges**; at the observed DFFHQNx1 area 0.2916 um²
   that is 20.412 um² before reset/clock/hold/placement costs. This is a
   bounded illustrative lower bound, not a selected production architecture.
   All other ports require exact clock-domain/producer/consumer ownership;
   simply registering every bus without its schedule is not legal.
2. **Reset copies require a fixed point.** Existing `qkd_kv_rst_land` has two
   async-assert synchronization FF followed by a kept registered child relay:
   release takes three edges, child assertion needs one running-clock edge.
   Internal reset-like ordinary FF roots still exceed 32. Preserve existing
   priced three-edge release; a split tree must charge its actual copies,
   assertion pulse and stopped-clock behavior. No <=256 exemption or implicit
   shortened reset stage is permitted.
3. **Delay storage fails the >=3 rule.** `u_ftd0..3` is a four-stage 271-bit
   delay (1,084 bits) and `u_ftu0..3` is four-stage 126-bit delay (504 bits).
   These require a ring/SRAM redesign despite each chain being <2 kb.
   Read-during-write collision, startup/reset validity, pointer lifetime,
   same-edge observable age and actual memory delay must be proved before
   selecting banks. No async-read or zero-cost SRAM replacement is asserted.
4. **Existing macro contact geometry fails.** Both kits select four
   `ot_sram_1r1w_128x256_m1_r2c2` macros (94.824 × 41.064 um), the same
   W410/E409-contact family identified in CTL: 9.984/9.960 contacts/um >6.
   Parent halo cannot fix immutable contact density. Require a truthful
   compiler family or lifetime-proven storage banking with complete timing,
   repair and PG/OBS views before any new kit. Macro origins remain 43.2-grid.
5. **Reach/depth/clock remain conditional.** Prior textbook 147 um and
   553/565 ps are diagnostics, not a complete new stage-cone proof. Current
   square 388.8 outlines alone do not prove every stage <=405 um. Native
   roots and actual combinational endpoints, legal pin locations, complete
   stage depth, reset phase and TT/FF neighbor references must be rederived
   after the structural boundary/copy/storage design. Do not retry a spine
   or pad knob as the source successor.
6. **Production static ages remain open.** Derive full source SU and MU
   phase/reset/first-use schedules from the selected generated parent. Price
   added face edges and SRAM access ages in compiler/die SU/MU token models;
   preserve fixed-rate flow and fault causal observation. No waiting/credit
   protocol, altered golden, deadline extension or full-token PASS is claimed.

## Corrected functional history

The old grp_h m0 failure (19,859 errors) used an incorrectly aligned reference.
The unchanged-source independent delayed-input oracle record
`0f2b0d5aef61cdf6d0c64469835a5e5af2edd7e6` records grp 575,509 and grp_h
571,518 checks PASS and all 16 mutants FAIL. Current sq2 jobs point at these
committed witnesses. This supersedes that bench diagnosis only; it proves
neither the native checklist nor production SU/MU timing. Keep the old failure.

Next owner: choose and size registered boundary + useful-copy reset/logic +
honest delay/storage implementation, then obtain source/native phase/age proof.
ROOT decides whether to cancel the four preserved failed-prerequisite gates
using `live_runs.json`; this audit authorizes no cancellation or new gate.
