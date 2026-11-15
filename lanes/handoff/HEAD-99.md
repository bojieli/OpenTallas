
# HEAD-99 handoffs (11-14 00:2x PST)
## -> TYPE-HDCTLN (hd_ctl_n)
- Wave: hd_ctl_n runs on the pgcap src (kw45/src_head_rp21z_pgcap1d724b73, OT_PG_TRACK_TRUTH=1), plan rp21z5, retry key hd_ctl_n@14 in place.
- Private proof (HEAD-98 pgtt kit, epyc8 head-98/ctl_n/gen/hd_ctl_n): DRC 0, antenna 0, TT -32.62/12 ep (passes -42), FF hold -18.32/61 ep (5 core-owned at -17.67, rest port), DRV TT slew 341 (advisory).
- Late ECO route-keep (eco99_ctl_n_b) FAILED DRT-0206 checkConnectivity (hold cells on port nets); same failure as HE-EPC try 1. What worked on HE-EPC: eco_loop.py run --from grt --owner-override (one extra iteration COORD-approved for near misses <= -10 ps; second iteration took -3.27 -> +2.3). Tools: src .../tools/die_plan/eco_loop.py (needs physical/common_flow next to it; copy on epyc8 at head-99/src_tools). ot-run needs the python3 -I eco_loop.py run --kit K --runner RUN_KIT.sh --out NEW_DIR --from grt --mem 64 --cpus 16 --owner-override (--out must not exist).
## -> TYPE-HDSERDES (hd_serdes)
- The 202.449 > 200 secondary-clock radius check is NOT in the plan or the wave src: it is the private bundle head-97/serdes_primary/secondary_bundle/tools/die_plan/secondary_clock.py (spec radius_um <= 200 hard-coded) + secondary_clock_taps.tcl 'exceeds declared local bound'. The plan's hd_serdes clock.tap_radius_um=200 only feeds density taps.
- Private pd3 kit epyc7 head-97/kitsserdespd3/g_hd_serdes/hd_serdes: kit-side spec radius_um 210 (orig .pre_h98_r210), primary overlay clk Y 20.384 (LEC proof 7bd77a1b). CTS+GRT done, in detailed route; log intel2 ~/tmp/h98_serdes_pd3_route.log (unit epyc7). If it signs off, the secondary bundle + 210 must reach the wave src (new snapshot over src_head_rp21z_pgcap1d724b73 on epyc7/intel1/epyc10 + kit_wave.json s81_head src/kit_rtl, via KIT-OPS-3); recipe = what I did for FLOW-PGCAP-1 (cp/rsync -a --link-dest snapshot, patch, rsync to gen hosts; never cp -al, results/ has a self-symlink loop).
- BMQ provider (SerDes SC child): routed DRC 0, TT +31.79, FF -7.57 (DRV slew + io_hold advisory only), kit epyc7 head-97/serdes_primary/sc_successor/bmq_provider_prep/gen/ot_s81hd_sc_bmq_head; posted to the PROFILE-1 RE-JUDGE as candidate; follow it.
## I keep: host_e, hd_lep0N release, mesh pregrt hold rebuild, HEAD die-level (DIE-PROTO-1).
# HEAD-99 / TYPE-HDSERDES handoff (hd_serdes secondary clock)
- Taken over from HEAD-98 by TYPE-HDSERDES 2026-11-14 00:46 PST.
- Form A (pd3, r210, target 1000): epyc7 head-97/kitsserdespd3/g_hd_serdes/hd_serdes, ot-run unit running since 18:55; CTS PASSED (SECONDARY_CLOCK_APPLIED sinks=13524 leaves=87 max_radius 202.449 <= 210); now in GRT repair stage (DPL NegotiationLegalizer 2409 violations remain, still running, CPU growing).
- Form B (r220, target 950 = more taps): epyc7 /srv/opentallas-scratch2/claude/type-hdserdes/r220/g_hd_serdes/hd_serdes (copy of pd3 post-place, CTS and later removed), log intel2 ~/tmp/hdserdes_r220_route.log; queued on epyc7 load gate.
- Overlay for the wave src: lanes/overlays/HEAD-SERDES-SECONDARY (README, apply.sh, gen_phys patch).
- When A or B passes (DRC0, TT>=-42, internal hold>=0): AUTO-RESIGN row + RESULT line.

# HEAD-99 successor 11-14 19:55
- hd_spn_end attempt_6 cancelled (exact scope). z18d prep running epyc7 head-99/prep21z18 (prep21z14.sh PW=prep21z18). TODO: die bind driver for HEAD (none exists), u_epc input-latency tap + PG cut, hd_mesh_e +10 percent, HDCTL-REGS stations, then z19 event.

# HEAD-99 successor 11-14 evening: rp21z19 composition + HEAD-REMAP-1 coupling notes
- Tool patch: epyc7/intel1/epyc10 kw45/src_head_rp21z19 = pgcaplec_c327 + new type key phy_pg_floor_um (gen_phys.phy_pg_west_notch, schema.py, die_plan.schema.json). Overlay of the same 3 files only.
- Scripts (epyc7 head-99): z19_delta.py (host_w pairs, serdes, lep0N [SKIP_LEP=1], mesh [SKIP_MESH=1], mesh_e cells), type-hdctl-regs/hdctl_regs_delta.py, z19_lat.py (34 lanes fixed_cycles) then gen.py latency --inplace; prep = prep21z19.sh (D=src_head_rp21z19, remap19.py). Current build: SKIP_MESH=1 SKIP_LEP=1 -> rp21z19q.json, prep21z19, kits21z19. Gate chain waiter intel2 ~/tmp/head99_z19_chain.sh (log ~/tmp/head99_z19_chain.log): G0 + head_bind_latcheck z19.
- LATCHECK pricing: ALL 34 lanes are priced (chE0-5_h +2, chW0-5_h +1, chE0-5_r +4, chW0-5_r +5, sp_x1-5 +6, sp_b1-5 +6 = 6+6+6+6+5+5 = 34). My earlier "29 of 34" was wrong; no lane is missing. Result still unproven until head_bind_latcheck z19 reports 329/329.
## Couplings for HEAD-REMAP-1 (rp21z20), all MEASURED from prep errors
1. hd_host_w: any local reset tap or relay xy change renumbers the reset tree: hd_host_w.coll_i0 reader START raw reset rst_rl_25 has no registered wavefront driver (clock_landings.py:1322 looks up an ot_dp_rrelay whose .q is the stage raw_reset name). Explicit tap clk and local reset tap [276.48,324.0] sit 8.64 from the pair-2 right member: member +8.56 failed taps.py:919 (halo > 8.64 by ~0.06), +7.92 passes. 
2. hd_mesh: moving the 256x64 right members (x 103.68/224.64/345.6, all 12 rows, +17.28) ends with hd_mesh.coll_ib reader START raw reset rst_rl_60 has no registered wavefront driver (same class: density-derived reset tree renumbered). Fix needed: a remap19-style pass over landing branch stages raw_reset names (reader/writer START stages in clock.landing_contract) to the relay now at the same xy/depth.
3. hd_lep0N: corridor y 529-660 holds fixed points: core clk taps pp[2] (428.192,547.584), pp[0] (1365.6,552.736), pp[1] (467.04,626.4), pp[3] (1347.36,626.4); reset local taps (1340.28,552.96) (1885.272,570.24) (915.84,596.16) (17.28,604.8) (1287.36,626.4) (406.08,626.4) and (915.84,293.76); die clock islands y 591.84-600.48 at x 38.88, 466.56, 712.8, 980.64, 1413.71. Stack of two tx rows (y 529.2 and 558.36, pitch 186.368 x 22.5.., slit 17.0) needs the 4 taps in y 547-570 moved to y 604.8 (done in z19_delta.py), rx column +7.2 (915.84 tap halo), and reset tap (1149.12,8.64) nudged to (1166.4,8.64) (duplicate with a density-derived tap). Then gen fails: "hd_lep0N: forwarded clock source clk_t218 is not a planned physical tap input": density tap numbering shifted with the macro move; edge/forwarded clock sources in landing_contract name clk_tNNN and must be re-mapped to the new tap names (by xy).
4. u_epc (hd_host_e) per-core input-latency target + PG cut: tap_balance.tcl tb_core_report judges effective = pin + internal L with L = single largest output latency (421); measured u_epc/clk clk_t6 pin 42 + 421 = 464 vs target 450 OK, while input arcs need ~330-400 ps at the pin. PG-AWARE-1: every 12th M6 pin at the u_epc W face x 423.2-423.5 lies in a parent M6 VSS stripe (64 DRC).
5. hd_tile re-time with new libs: ECO 2 (intel1 eco99_tile_c) still running at 20:4x; STA-only job after it ends.

# HEAD-99 successor 11-15 05:10 open items (for the next owner)
- rp21z20NC (epyc7 head-99/rp21z20NC.json, sidecar_rp21z20NC.json): waits for the partition-origin both-edge regions_ca file from DIE-HEAD-ROUTE-1 (0 relays, frame_clock_regions + start_pins, 18 freg, 427 ports). Waiter intel2 ~/tmp/head99_po_chain.sh (log ~/tmp/head99_po_chain.log) then rebinds (ca4_rebind.py), form B (hostE_formB.py), latency, prep21z20NC.sh, G0 + head_bind_latcheck z20nc (~/tmp/head99_z20nc_chain.sh). On pass: READY+ADOPT to KIT-OPS-5, then queue hd_mesh_e / hd_ctl_e re-sign with HOLD_SLACK_MARGIN 10.
- kp4_dchn: stopgap DROPPED (COORD). Put +1 cycle (OT_S81_DCHN_FACE) into the HEAD plan lane for hd_serdes when S81-RESIGN-DEEP LEC + equivalence pass; then regen latency and re-run bind/LATCHECK.
- hd_host_e S/A private builds: chain ~/tmp/head99_epc_chain2.sh waits for prep21z16e (restarted after count_frame fix).
- hd_tile: keep 717.12, re-sign via wave a9. hd_tile re-time with new libs pending (no ECO 2 DB).

# HEAD-CLKFEED-1 -> HEAD-99 (11-15 02:0x): new HEAD die clock feed feed_hk6 (epyc2 head-clkfeed-1/cfg) cuts DEPTH-8 rings 165 -> 38 and deepest tap 8992 -> 6913 ps; re-bind K/DEPTH/latencies on it after adoption. See lanes/handoff/HEAD-CLKFEED-1.md

# HEAD-CLKFEED-1 RESULT (11-15 02:5x): feed_hk6 on rp21z20NC: strict kit PASS, both-edge CA PASS 427/427 depth4 427, TT lo 204.9 FF lo 132.3 (old feed 211.9/151.2); deepest tap 8992 -> 7001 ps TT. File epyc2 head-clkfeed-1/cfg/feed_hk6.json for rp21z20NF. NC intra FF skew 271.6 ps needs HEAD-99 look. Details lanes/handoff/HEAD-CLKFEED-1.md

# HEAD-CLKFEED-1 -> HEAD-99 (11-15 04:2x): lep0N fix for NC and NF = region.actual_max_region {lep0N: 300}; see COORD-REVIEW-QUEUE.md and handoff HEAD-CLKFEED-1.md
