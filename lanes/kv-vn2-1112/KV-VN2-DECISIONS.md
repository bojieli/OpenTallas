# KV vN2 hand floorplan, draft 2 (DIE-KV-99, 2026-11-12)

History: draft 1 by DIE-KV-98, 05:14 PST (GEOM-VIS-3 05:14 verdict CHANGES (1)-(5)). This draft 2 answers those changes on the composed plan vN2c.

Plan rendered: epyc4:/srv/opentallas-scratch2/claude/dkv99/vN2c/plan_c.json (md5 0c73e553). It is the vN2 base plus items 7, 8 and 3, composed 3-way with 0 conflicts.
- vN2 base = vN 52a724781a52 + the ft_nudge class fix + the census exemption + the SerDes bump rects.
- The re-site, REACH-FIX taps and insertion balance are NOT yet applied; they produce vN2d.

Figures (the script re-runs on vN2d: `cd /dev/shm/dkv99/main && python3 -P /srv/opentallas-scratch2/claude/dkv99/draw/draw_vN2.py PLAN OUTDIR`; the numbers behind them are in draw_data.json next to the PNGs):
- `kv_vn2_floor.png`: the die to scale, axes in mm.
  - Each slot is coloured by fill, i.e. kit std-cell area / (outline - hard cores). Hatched means no kit data.
  - Hard cores are grey. The new W streets in hg/hgi show as the wider core-free W margin; in the E columns it is on the die E side because those instances are mirrored.
  - The die clock trunk is drawn in red, with the 128 region roots as squares and the root (star) at hub_C.
  - The die io windows are drawn in magenta.
- `kv_vn2_taps.png`: the worst tap sinks per type at cap 1,200, from the plan sink inventory (a lower bound), before REACH-FIX.
- `kv_vn2_cuts.png`: the worst partition-segment cut ratio per slot under two models: main G0 (a core blocks up to its LEF top layer) and M7-free (a core blocks M6/M7 only where its LEF OBS covers more than 50%; the core_obs class COORD approved). The hgi column has a thick outline.
- `kv3_hg_v1p3_vN2_wstreet.png`, `kv3_hgi_v7_vN2_wstreet.png`: type zooms of cores, W windows, bands and ft stations before and after the W street.

## Structure (unchanged from draft 1, approved by GEOM-VIS-3 (a))
- 9 columns x 16 rows, mirrored: phy | pc | hg | hgi | pv | hgi | hg | pc | phy.
- The hub band (hub_Wo, Wi, C, Ei, Eo plus 4 hroot) sits between the S and N arrays, with the io/sys row on top.
- 88% of the 598,087 crossing bits stay inside the 5 array classes, and every hub flow is under 4.3k bits.
- hroot keeps its stacked 1,901 x 838 pair under an ASPECT EXCEPTION (2.27). sys_c takes an ASPECT EXCEPTION too (2.08).

## Channels and cuts
- No new die channel (GEOM-VIS-3 (b)).
- Under the M7-free model, NO slot is over 0.6:
  - hgi N column: 0.37-0.50.
  - hgi_EN_0 at y=25,500: 0.36.
  - Hub band: 0.32-0.45.
- Under main's G0 model, 16 slots are over 0.6, all in the N hgi column:
  - hgi_EN_1..6: 0.94.
  - hgi_WN_7: 0.94.
  - hgi_WN_0..6: 0.84-0.85.
  - hgi_EN_0: 0.68.
- The difference is the model. The kv3_head_eighth_e0/e1/e5/e6 detail LEFs name M7, but their measured OBS covers M5 97-100%, M6 1.4-3.4% and M7 1.2-4.1%.
- Main's model blocks the whole 216 x 216 core on M6/M7, so the column loses about 1,700 of 5,468 tracks per segment.
- The fix is a checker class (COORD 11-12: option (a) approved; DIE-KV-99 READY to follow). Per COORD, no hgi bundle re-route for this artifact.

## Decision table
| # | item | numbers | decision / result | status |
|---|---|---|---|---|
| 1 | dead forwarded-clock census | 31 census errors = 1,024 bits over 32 phy-pc pairs, by design | exemption line in the plan census map (v35) | DONE: G0 census 31 -> 0 |
| 2 | SerDes PG bump rects | 2 pg_domain errors (sys_SW, sys_SE) | bump rect clipped to the VDDPHY domain rect of the grown sys_SD_v1 outline; 45-um lattice unchanged | DONE: G0 pg_domain 2 -> 0 |
| 3 | hgi_EN_0 cut y=25,500 | 3,623 b; 0.66 (M7-free) / 0.96 (main) | lane L2075 (slg_EN_4.rsp, 1,056 b): its hgi_EN_0 W / pv_N_0 E window raised 1,036.8 um (60 x 17.28) into a free gap, so the drop happens in pv_N_0. kv3_hgi_v3 ft27 and kv3_pv_v8 ft0 re-sited (ft_corridor, same stations); 1 instance each | DONE in vN2c: 2,567 b = 0.47 (M7-free) / 0.68 (main); 0 cycles; die worst hop still 401.8 um; no M8 grant |
| 4 | hroot aspect | 4 x 1,901 x 838, aspect 2.27, about 190 sinks/tap | ASPECT EXCEPTION, stays stacked, not re-shaped (COORD 05:19, GEOM-VIS-3 change 1) | DECIDED |
| 5 | merge 21 near-duplicate types (-11) | dedup.py plan key: 56 -> 45 | NOT exact for any group. pv_v1..v5 pair merge strict bind RC 1, 78 errors: 72 R8_STRAP_PAD (N/S pads 25-93 deep vs a 15-deep bank), 5 TYPE_SPLIT (as-built N/S leaf wiring differs), 1 EMIT. pv_v6: also the count-aligned start relay. pc, pc_v1, hgi_v1, hgi_v2: deliberate reset-cohort clones (different reset-forward children and rst_o_N / start_o_N ports, different R8 strap sets) | DROPPED from vN2 (0 types saved); tool item: union reset-forward form or wavefront parent override, needs COORD |
| 6 | clock taps, cap 1,200 | pre-REACH-FIX: 46 of 54 soft types have a worst tap over 1,200 (hgi_v8 5.6k on 16 taps, needs 32; pv_v6n 4.8k on 161; pc_v1 x3 / pc_v3 2.7-2.8k on 12). Only hgi_v8 is short of tap count; the rest are placement | density-weighted re-site by REACH-FIX-2's reach_fix.py at compose, hgi_v8 min 39 taps, plus clock INSERTION BALANCE (COORD 06:4x; DIE-PROTO-2: KV late insertion 0.372 ps/um vs root distance, r 0.987) | IN PROGRESS (vN2d) |
| 7 | hg + hgi W-face pin pockets | GEOM-VIS-2/3/4: W pockets at local density 1.385, no W street | Cores move only. W street from W-face bits: need = max(43.2, bits x 0.048 / (3 x 0.6)), on the 8.64 lattice. hg (8 types, incl. base kv3_hg): W column +43.2, W street 60.48 for 2,173 b. hgi (11 types): W 77.76-86.4, internal streets 60.48-95.04, E margin 43.2-69.12 kept >= need(E bits). One W pin-spread step for both: windows = bits/rho at 0.5 fill, worst centre shift 107 um, bundles <= 72 um, pin density about 4x lower. EX slot 0 is already soft (nothing to drop). Then ft_corridor + ft_nudge --no-snap | DONE in vN2c: street_rule hg/hgi violations 8 -> 0; G0 +6 = ft hops 415-466 um on L2245, L2259, L2311, L2349, L2363, L2415 (+1 station at re-site, cycles pre-approved); 709 re-site rows for vN2d |
| 8 | stations in PHY / sys_c keepouts | 160 street_die_leg rows, not 40 (G0 lists only 40): 84 PHY, 71 pv macros, 5 sys_c | sys_c: ft1 regs_um from its bit-site corridor; it was never over the UCIe macro, 0 cycles. PHY: the 4 host.hbm_rst_n lanes (L668/L678/L689/L699) sit in kv3_phy_v1's own glue band (x 432, about 125 um E of the PHY body), and G0 flags them against the partition's own bump-field rect. A pc-side re-route costs +1-2 boot cycles and gains nothing physically | sys_c DONE. PHY: ASK COORD (checker exemption for a station inside a PHY io rect equal to its own partition rect, prototype ready) vs re-route. The 71 pv-macro rows are open (outside item 8) |
| 9 | drawing + table | this file and the 5 PNGs | fill: 47/56 types measured, 0.004-0.094, all under the standing 0.15 slot-fill exception; 9 no data (hg_v1p2, hg_v1p6, hgi, hgi_v1 cl42bc8b12, hgi_v3-v6, hub_Wo). The trunk is from DIE-PROTO-3's vFk tree (vF outline; only the sys_SE region shifts in vN2) and is re-drawn from the vN tree when its chain is done | DRAFT 2 (final on vN2d by 11-13 12:00) |

## GEOM-VIS-3 05:14 changes, answered
1. hroot stays stacked under an aspect exception (row 4).
2. hgi_EN_0 option A: L2075 moved off the hgi_EN_0 descent (row 3). No M8 grant.
3. hgi pin pockets: the W street plus the W pin spread for every hgi type, and for all hg types as well (row 7).
4. Tap cap 1,200 (row 6, figure kv_vn2_taps.png).
5. Fill per slot, the clock trunk and taps are drawn. The tap positions after re-site come in vN2d. The hop margin is held: die worst 401.8 um after items 3 and 8; item 7's 6 hops over 405 get +1 station at re-site.

## Still open (vN2d, then READY)
- Re-site once for the 709 rows (338 die clock islands, 186 collector relays, 97 ft regs, 63 landing bands, 25 moved windows): landing tool, collector re-solve plus re-attach, and a reset tree republish.
- REACH-FIX-2 taps plus insertion balance.
- G0 and the hop check, then a STRICT BIND from a FULL (non-sparse) checkout, then the package (every file <= 95 MB, large inputs .gz).
- core_obs coverage checker READY (approved class).
- PHY exemption ASK.
- Merge: dropped (tool item).
- The 71 pv-macro station rows.
- The hgi_v8 tap count.
- hg/hgi build to place and route only after a visual verdict on the new form.
