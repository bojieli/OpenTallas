# FABLE-PD-KV-0840 (2026-11-21 08:37-09:00 PST): KV physical-design review after the D27d red bind, and the D28 structural review

Reviewer: FABLE-PD-KV-0840 (Fable). Read-only: nothing launched, cancelled, signalled or patched; no ot-run job. Plans, logs and LEFs were
read in place with short python (seconds; epyc8, epyc9, epyc7, epyc10). Marking: **V** read this round, **R** reported by the owning lane,
**I** inferred, **P** proposal. Earlier reviews stand (FABLE-PD-KV-0730 and before). Scope: technical PD only.

State at 08:53 (V): no D28 input is bound. Still in bind: D27d bisect (a) and (b) (epyc8 kv-plan-r5/d27f, d26ctl; `bind.log` empty),
pv split 13 probe bind 8, hroot variant B bind B2, hgi `bindgate26b` (its G0 PASS, 0 errors), TAP-GRID-R4 tap-row gate. A strict bind takes 2 h 18.

## 0. Verdict

**D28 as planned does not close by construction.** Five things are missing from its scope, and each is measured:

1. **Plan rows name relay nets of an older bind.** `clock.landing_raw_branches` exists on 51 of 56 types and carries literal `base` /
   `original` net names (`rst_rl_N`, `rst_n_tN`). Every D28 row that changes a reset relay tree makes them stale. This is the D27d EMIT class.
2. **Three types are over or unmeasured on the 400k cap and G0 does not judge them.** hub_Eo placed at 450,499 non-tap cells (V). hub_Wo is the
   same form. hub_C has no measurement in its present 20-macro form. G0 lists 20 types as `cored_unjudged`.
3. **The D28 tap rows for hub_C, pc_v3 and hg_v3 were solved on placements of superseded netlists**, and the rows cap load only: 52 taps keep
   a radius over 200 um, worst 368.5 um. No pv half has rows.
4. **The pc core view blocks its own PG pins.** No plan row fixes it and no gate sees it before PDN.
5. **pv halves: the vport first hops (715 bits, 476-1,345 um) have no rows yet** (R3, R4 unbuilt), and the split is proven on one type of 15.

One class is closed in the plan: clock reserved-row walls (section 1.5).

## 1. Root cause per class

### 1.1 D27d rebind: RC_BIND 1, 27 errors (V: epyc8 kv-plan-r3/d27c/bindgate_d27d_r5 `gate.out`, `bind.log` lines 1207-1224)

| Rows | Types | Cause |
|---|---|---|
| EMIT `raw Q rst_rl_N: exactly one same-clk plain relay required`, 15 | hg, hg_v1, v1p2, v1p3, v1p4, hg_v3, hgi_v6, pc__cl254f2e73, pc__cl5a95b461, pc_v1__cl4ea58a5c (+3 variants), pv_v2n, pv_v5n | On 12 of 12 base types the failing net is a literal `base` or `original` of that type's `landing_raw_branches` row (V). The check is `landing_raw_branches.py:100`, the same line in the D26 tools. The rows are byte-equal in D26 and D27d; the relay tree under them moved. |
| EMIT `original ... D=rst_rl_316 != literal predecessor rst_rl_310`, 2 | hg_v1p5, hg_v1p6 | Same class: the literal parent chain no longer matches the emitted chain. |
| EMIT `relay_depth kv3_hub_Eo: 4 row(s) matched no internal sink` | hub_Eo | r14 rows name sinks (`u_seq_g_fan_2_u_fan.rst_n`, ...) that are not in this bind. Same class: a row keyed on instance names. |
| R8_STRAP_PAD 5 + TYPE_SPLIT 3 | pc_v1 x2, pc_v3 | Lane pads over the strap range: `slg.x__tep` pad 61 against capacity 15, 44 / 31, 60 / 26; `hsl3.fi` 29 / 26. Instances of one type then need different pads and bind as 4 and 7 variants. Plan diff D26 -> D27d: top-level `lanes` and `latency` changed (V). The pc_v3 `hsl3.fi` row is also in split bind 7 (R), so it comes with the lane table, not with a pc row. |
| PARAM_REGEN 1 | pv pair image | K 170/160/150 -> 174/162/155, HOST_REC_RT 156 -> 158. Mechanical: recompile on the bind that is kept. |

Plan diff D26 -> D27d (V): 30 types change `internal_stations` only; hub_Eo adds `relay_depth` + `relay_sites`; io_cor_v1 adds `bank_taps`.
pv_v2n, pv_v5n and the two pc__cl types have **no** type-level change and still fail, so a station row is not the only trigger: the as-built
hash also moved (118905421f0a against D26 78ec600897d7) and `lanes` changed. Which of tool, RTL or lane pads renumbers them is what the
running control bind (b) decides (I). The structural point does not wait for it: a row keyed on bind-emitted names breaks on any such change.

### 1.2 Place fails, OT_CLAND (V: epyc9 KV-D26 kv3_hg_v1 `3_3_place_gp.log` lines 347-350)

`OT_CLAND BAND FAIL u_cland_raw_fs_o_astk_Q_..._addr_3` and `u_cland_raw_fs_o_idhg_Q_N_y_2`: 2 cells, need 0.9 um2 of an 18.7 um2 band, no
legal row or site. Both are raw-branch stage bands (4.32 um windows). The blockers are station-bundle combs placed first at run time (R,
OPUS-FIX-KV-HGI-R5). Same class: sys_c place, hub_Wo and hgi_v8 preflight (static combs, fixed by a site row). The raw-branch stage sites are
solved without the station comb footprints. `OT_LAND_RESERVE=1` (bands reserved before the combs) is a placement-order fix, not a tolerance,
and is right. It is set on pv, sys_c, hub_C and hg x8 only; 51 types carry raw branches (several thousand stages).

### 1.3 kv3_pc_v3 PDN-0006 (V: epyc9 KV-D26 kit `2_4_floorplan_pdn.log`, `pdn.tcl`, `macros/qkd_kvs_pcc.lef`; epyc10 KV-HG5 kit)

The core view changed, the plan did not. Macro placement, `pdn.tcl` and `config.mk` are identical in the D25e3 and D26 kits.

| Kit | `qkd_kvs_pcc.lef` | M6 OBS | M7 OBS | PDN result |
|---|---|---|---|---|
| KV-HG5, 11-17 (placed) | 59d336cd4245 | 23,768 rects, 1,368 um2 | 2,032 um2 | PDN-0007 warning, VSS 3.9 % blocked |
| KV-D25e3 and KV-D26 | bf5c3c9c34c4 | 12,635 rects, 13,460 um2 (17 % of the core) | about 23,600 um2 (30 %) | PDN-0006 error, VSS on M5 blocked |

The PG pins are 67 full-height M5 stripes per net at 4.32 um pitch; the parent connects them to its M6 straps (`core_pg_M5`, M5-M6). The new
view's OBS is merged blocks up to 13 x 24 um on M7 and a 4.3 x 204 um M7 bar on the south edge, where the old view had thin wire shapes.
`qkd_kvs_pcf.lef` changed too (a4c5fe6cda94 -> 97c2b21d9e5e). Every pc type that takes these views fails the same way (I); pc_v3 has not
placed since 11-17. Not checked: which export option merged the shapes.

### 1.4 kv3_hub_Wi FAIL_PREFLOOR port_bind (R, KV-PLAN-R5 08:10)

Netlist 16,533 port bits against plan 16,530: `io_pad_die_id[0..2]`, a bound-only strap port with no plan pin. Plan-pin row, hub_Wo form.

### 1.5 hub_Ei GRT overflow and the clock detour

- hub_Ei (R, FABLE-FIX-KV-HUB-R2): 996 of 1,005 overflow gcells have capacity 0 on 7 rows that the D25e3 kit obstructs M1-M7 over their length.
- **Closed in the plan (V, my scan of D27d plan 07a462a13e91):** 17,031 `die_clock_tree` reserved rows across the die, every one
  `route_layers M1-M2` with `stack_um` windows; no full-stack window is longer than 20 um. The only longer full-stack boxes are 72
  `channel_keepout` rows on the three pc_v1 types (69 um wide, up to 115 um), a different kind.
- **Correction to the brief:** the 217-432 um detour, 510 ps spread and 39 ps on a 3-iteration GRT are hroot D25d attempt_5 tap t9
  (FLOW-CLKGRT-1121 06:56), not hub_Ei. hub_Ei has no clock reading at GRT. The mechanism is general: CTS nets carry an NDR and the
  congestion negotiation rips them out of deficit edges (R), so any tap with a wide sink box in a congested strip is exposed.

### 1.6 pv split 12 (R, FABLE-FIX-KV-PV-1121; bind 7 static read)

715 `u_vport_W` bits leave the output register for a first station 476-1,345 um away in one cycle; `u_vport_E` (811 bits) is bound in w with
its anchor rows in e; 4 `u_bout` buses have no plan row. Measured on the unsplit v7 at placement RC: 600 `sel_q` ends to -561 ps (one flop,
about 1,060 muxes) and 140 first-station ends to -541 ps. Size is not the cause: a half of 275k repeats it. Split 13 carries R1 and R2; R3 and
R4 are not generated.

### 1.7 Tap recount (V: epyc10 tap-grid-r4 `count_d27d_table.txt`, `d28_tap_report.json`, `compose.log`, `kvtapnet/odb/*.src`)

The recount is right in direction: the 11-05 bins predate the relay sites and stations. But the bins are placements of different netlists:

| Type | Bins from | Then | Now |
|---|---|---|---|
| hub_C | kvgeom7yhr, 11-17 | 3 macros, 788,468 non-tap cells at floorplan | 20 macros (6 landing-ring views hardened); no kit has reached floorplan |
| pc_v3 | KV-HG5, 11-17 | old core view | view changed (1.3); D27d moved `internal_stations` |
| hg_v3 | KV-D25e, 11-20 | 544 kst sites, 34 bits each, on core centre columns | D28 re-sites them into the x streets |
| hub_Eo | KV-D25e3 attempt_4, 11-21 | current netlist | valid |

So "hub_C 19,884 on one tap, 186,074 sinks" describes a netlist that no longer exists, and its +33 taps are solved on it.
The solver (`kvtn_solve.py`) is a nearest-tap split on load. It leaves 52 taps over the 200 um radius target: hgi_v2__cl2862d491 368.5,
hgi_v2__cle0015330 320.2, hg_v3 315.4, hub_C 301.2 (19 taps), hgi_v1 274.9, pc 238.1. The only measured KV failure of this form is hroot t9:
1,478 sinks, span 447 um, clean post-hook (47.7 ps), 510 ps after GRT. No KV kit has a post-hook reading of a tap near 3,000 sinks:
hub_C and hub_Eo have no `4_1_cts.log`. The D25e3 kits run `OT_TAP_MAX_SINKS = 1200`, so the row also raises the flow cap 2.5x.
No rows: pv halves, and the 7 unplaced types (hub_Wi, hub_Wo, pc__cl254f2e73, pc__cl5a95b461, pc_v1__cl4ea58a5c, pv_v6, sys_SD).

### 1.8 Cells (V)

| Type | Measured | G0 D27d |
|---|---|---|
| hub_Eo, KV-D25e3 attempt_4 | floorplan 382,104 non-tap; placed 613,021 instances - 162,522 tap/endcap = **450,499** | 356,775, `cored_unjudged` |
| hub_Wo | none; same form as hub_Eo (2 macros, `kv3_astk`) | 335,775, `cored_unjudged` |
| hub_C | 788,468 at floorplan in the 3-macro form; none in the 20-macro form | 1,208,291 with cores, `cored_unjudged` |
| hub_Ei, KV-D25e3 attempt_4 | floorplan 287,598 | 388,235 NEAR |
| unsplit pv | 639-769k at place (R) | 420-437k OVER |
| pv_v3 halves | 275k / 269k place (R, G0 estimate of the split) | - |

## 2. Does D28 close by construction?

| Check | Verdict | Basis |
|---|---|---|
| Placed hops <= 405 um | **No.** | pv halves: 715 bits at 476-1,345 um until R3 + R4 exist (1.6). hgi_v1 x2 `i_ectl_Q_N_tN` hop 4 stays 482 um in the plan (COORD: measure in the kit first). hroot variant B unbound (R: boxes <= 300). hg kst v3 rows max bit hop 383.4 (R). hub_C / sys_c chains <= 331 (R). |
| Taps <= 3,000 real sinks | **Not shown.** | Rows give 0 over on their bins for 26 types, but the bins are stale for hub_C, pc_v3 and hg_v3 and absent for the pv halves and 7 types (1.7). Span is not bounded. |
| <= 400k cells per type | **No.** | hub_Eo 450,499 placed; hub_Wo alike; hub_C unmeasured; only pv_v3 is composed of 15 pv types (1.8). |
| No clock reserved-row walls | **Yes, in the plan.** | 1.5. The pv halves re-derive their rows (split rule 7): re-scan the split plan. Proof = first D26 / D27d hub_Ei kit at GRT iteration 5. |
| No OBS / PG clash | **No.** | pc core view (1.3). |
| Rows survive the bind | **No.** | `landing_raw_branches` literal names on 51 types (1.1). D28 changes stations, relay sites and taps on more types than D27d did. |
| Landing bands placeable | Partly. | `OT_LAND_RESERVE=1` on 4 families only (1.2). |

## 3. Ranked fixes

| # | Fix (P) | Evidence | Owner |
|---|---|---|---|
| 1 | Re-derive `landing_raw_branches` (and any `relay_depth` row keyed on names) from the D28 bind itself, on every type whose reset tree the event touches: two-pass bind, as the pv split already does (rule 7). Longer term key the rows by depth and site, not by net name. | 17 EMIT rows; failing net literal in the row on 12 of 12 types; 51 types carry the rows | KV-PLAN-R5; generator owner RESET-RELAY-GEN-R3 |
| 2 | One composed D28 probe bind with `--all-gaps` as soon as the row sets exist, before the family lanes are each green on a different base (D26, D27d, split 12). | D27d: 27 errors sat behind R8 through every D27c / D27d bind; a bind is 2 h 18 | KV-PLAN-R5 |
| 3 | pv halves: R3 + R4 on split 13, gate `LEAF_FIRST_HOP` 0 / 0 on both halves, then one R8 refresh and the pair-image recompile on that bind. Tap rows per half on a placement of the half, with a sink-box bound. | 715 bits, 476-1,345 um; -561 / -541 ps on v7 | OPUS-FIX-KV-PV-R5; taps TAP-GRID-R4 |
| 4 | pc core views: re-export `qkd_kvs_pcc` / `pcf` with wire-shape OBS (the 11-17 form), or keep clear M6 windows over the M5 PG stripes. Add a kit preflight: each core PG pin has an unobstructed M5-M6 crossing on the parent strap grid. | OBS M6 1,368 -> 13,460 um2, M7 2,032 -> 23,600 um2; PDN-0007 3.9 % -> PDN-0006 | FAM-KV-IOPC |
| 5 | hub_Eo and hub_Wo: a size row in D28 (split, or harden the next block as the astk core was), judged on the placed census. Make G0 judge `cored_unjudged` types on parent cells. | 450,499 non-tap placed against 400,000 | FABLE-FIX-KV-HUB-R2; G0 change to PRECHECK-1119 |
| 6 | hub_C: one kit of the 20-macro form to floorplan census before any hub_C tap row or cap verdict. | bins are the 3-macro, 788k form | FAM-KV-HUBC-SYSC |
| 7 | Tap rows: re-solve hub_C, pc_v3 and hg / hgi after their D28 station rows, on plan sites (relay sites and stations are fixed coordinates) plus a current placement for the rest. Add the sink-box bound (<= 300 um) to the solver. Gate the 3,000 cap on one post-hook and GRT read of hub_Eo, the only type with valid bins and a large tap. | 1.7; hroot t9 | TAP-GRID-R4 |
| 8 | `OT_LAND_RESERVE=1` as the KV die default; raw-branch stage sites solved with station comb footprints as keep-outs (the hub_Wo and hgi_v8 rows are single cases of it). | 4 hg place fails, sys_c, 2 preflight fails | WAVE-FLOW-R2 (env); KV-PLAN-R5 (rows) |
| 9 | pc strap range: raise the strap capacity on `slg.x__tep`, `slg.x__tok`, `hsl3.fi`, or equalise those lanes so the pad fits. No type variants. | pad 61 / 15, 44 / 31, 60 / 26, 29 / 26 | FAM-KV-IOPC with KV-PLAN-R5 |
| 10 | hroot: variant B kit read at GRT, with the clock-first GRT arm on the same kit. | t9 39 ps on 3 iterations, 510 ps on 30 | FABLE-FIX-KV-HUB-R2; FLOW-CLKGRT-1121 |
| 11 | hub_Wi `io_pad_die_id[0..2]` plan pins; hub_Wo and hgi_v8 landing site rows. | 16,533 / 16,530 bits | FABLE-FIX-KV-HUB-R2; OPUS-FIX-KV-HGI-R5 |

## 4. Stop list for D28

- No `landing_raw_branches` or name-keyed `relay_depth` row carried from a D26 or D27d bind onto a type whose stations, relay sites or taps change.
- No hub_C tap rows from the 11-17 bins; no pc_v3 or hg_v3 tap rows solved before their station rows.
- No TAP-GRID-R2 kvcap rows (invalid on 17 types, R).
- Do not quote "hub_C 19,884 / 186k sinks" as the present hub_C.
- Do not quote the 510 ps / 39 ps clock detour as hub_Ei; it is hroot.
- No pc kit on the present core views; a relaunch fails at PDN each time.
- No plan PG-strap row for PDN-0006: the parent grid did not change, the view did.
- No w-half pv kit before `LEAF_FIRST_HOP` is 0 / 0; no unsplit pv kit (stands from -0730).
- No pair-image recompile and no second R8 refresh on D27d; do both once, on the D28 bind.
- No hub_Eo / hub_Wo volume as "under cap" on the G0 number; G0 does not judge them.
- hroot variant A, unchanged kst rows of 152d6c878972: still out (-0730).

## 5. Not checked

- The control bind (b) had no result at 08:53, so tool, RTL or lane pads as the trigger of the renumbering on the four unchanged types is open.
- No private bind of a D28 input had finished: split 13, hroot B, hgi 26b and the tap rows are reported, not read.
- Which export option merged the pc view OBS; whether pc_v1 kits fail the same way (same view, inferred).
- hub_Wo and hub_C parent cell counts in their present form; hub_Eo setup at placement.
- Whether a 3,000-sink tap closes at CTS and GRT: no KV measurement exists.
- The reserved-row scan covers the D27d plan, not the split plan or a kit's `reserved_sites.tcl`.
- Static count of raw-branch stage sites that fall on station combs (the hg combs are placed at run time).
