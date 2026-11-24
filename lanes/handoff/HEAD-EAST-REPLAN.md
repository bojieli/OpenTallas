# HEAD-EAST-REPLAN handoff (updated 2026-11-24 03:45 PST)

Lane dir: epyc11 /srv/opentallas-scratch2/claude/head-east-replan (clone/, tmp/, trees/s81_head_east_r1 = ot-tree-fork of head-r18 s81_head_r18e_recovery).

## State
- Probe kit LIVE: hd_lep0N plan prep_east_r6 sha bbc1f3416194, rt 937906f6e0ba (has 4676043 tap window, 81e6524c4b alpha-default reset attach, 9dbd20ffb1 LEP-RSPLIT-REPAIR-1), goal grt, host epyc11.
  spec intel2 ~/coord/autopilot/private_specs/HEAD-EAST-REPLAN/s81_head_hd_lep0N_1124034307/spec.json, unit runitem-hd_lep0N, log intel2 ~/head-east-replan/east_r6_launch.log.
  work epyc11 /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81_head/kit-wave/s81_head/head_rp21z20NF15f_r18gw/private/HEAD-EAST-REPLAN/hd_lep0N_1124034305
- Chain r6 (tmp/chain_east_r6.sh, out bind_east_r6): PRE baseline-only FAILs (ISTPRICE no as-built; ENTRYFOOT STALE-EXPORT-TAP hd_ctl/hd_host_w/hd_serdes = HEAD-R18 FWDTAP; RSTREACH hd_lep0N_w 410/405 = HEAD-WEST), identical on live s3w with same rt. Strict bind, cohort, LATCHECK, native release, G0 PASS (0 errors).

## Rows (tmp/east_rows.py on rscap a0b11fee2817, then landing_remap)
- S: drop 10 stale relay_sites (g_rfan g_leaf[32,33,53,56-60,62].leaf_r, u_rstr g_local[1].local_r).
- L: both core taps SIGNED vE28s budget 558.17 TT / 451.18 FF.
- R: clock.tap_reset_split_repair true (repair_design after tap reset split; E1/E2 what-if: 0 reset endpoints < -42). No RTL stage needed.
- K: LEP-KSHELF-1 tmp/kmoves7.json (ksearch3.py: tap clear 8.64, landing bands as obstacles, no rx[3] moves - they broke rst_rl_215 remap): rx1 row 622 gaps 9.5, rx0 row 622 21.6, rx2 row 712 21.6; rx1/rx2 row 667 unchanged (~3 um, no legal room: bands at x 375-410 y 650-665).
- Render reviewed: scratchpad img/east_kshelf_r6.png. Risk: row 667 / y 660-690 stripe (rc138) not re-spaced.

## Next
1. CTS post-hook: reset classes >= -42 (E1 u_srl_302->u_rrl_303, E2 u_rstr root->group RESETN); E3 hold rg3 pair-in (predicted ~-41 with L row).
2. Final 5_1_grt.odb: overflow < 50 per cluster (K-shelf x340-380 y620-680; E4b x980-1000 y360-400).
3. If row 667 stripe still hot: re-site landing stage bands near x 375-410 y 650-665, then re-space row 667.

## CODEX notes 11-24 06:3x PST
- The accepted r7 c9ead4cccd9a source and r7 tie audit 345049b521c7 are present on epyc11 and intel1. The epyc8 copy failed at the temporary destination and that host is draining. The first intel1 copy hit an SSH transport reset and the second completed. E11 r7 is running placement only as head-east-r7-place. Spec autopilot/private_specs/HEAD-EAST-REPLAN/s81_head_hd_lep0N_1124062218/spec.json, work r18gw/private/HEAD-EAST-REPLAN/hd_lep0N_1124062216. The r6 epyc11 exploratory run remains for CTS/GRT diagnosis, with exact viewed geometry showing tight central K-shelf channels. Any r7 route needs the r7 placed render and verdict.
- East r7 gate PASS for strict bind, cohort, 334/334 LATCHECK, native release, G0 and corrected observed-input LEC. Four controls failed as expected. No direct adoption. East block is in combined HEAD w6 b3507e628de6.

## 11-24 07:31 PST exact r7 placement evidence

- E11 r7 `c9ead4cccd9a` mapped `1_2_yosys.v` carries two I3 and three O0/O3 station instances with literal chained input/output wires. Live `ot_face_flops.txt` records 514 cells in each I3 bank and 513 in each O bank, 2,567 total FIRM, zero misses. The following native stage population is still active, before final view.
- r6 diagnostic post-CTS worst −158.99 ps is the two-bank rne_addr control leg g_rx[2].g_nonempty_regions.addr_nz to g_rx[3] local SRAM read/bypass capture prev_q, after a ~300 ps wiring leg and adverse clock skew. It is a separate pre-repair class from WOPENREG and reset. r6 GRT still running and stays diagnostic.
- Prospective native leaf lookup cache pushed lane branch `claude/head-r18-latpkg@03d8ffcdcf0e`. Keeps ordered exact membership and fail-closed empty selectors; reuses guard membership through placement and capacity counts. Twenty focused tests passed. E9 `head-r18/native_lookup_1124` subset of 14,741 actual r7 trace names and eight exact selectors gives same 1,569 ordered matches, one uncached pass 1036→593 ms. The current sealed r7 keeps its pinned helper.
