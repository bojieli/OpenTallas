# QW-G5STA 10-20: g5 compute-die STA classification, E_sta re-derivation diagnostic, slice landing-channel successor (dv2f20g5l / g5lb)
Scripts: cls2.py (classifier), mk_diag.py (STA-only tcl with land-plan MCPs), setup.sh / drive.sh (successor run dirs on ep6). Raw: ep6 /srv/opentallas-scratch/claude/mu-die-qw/dv2f20g5/{chain,diag_g5sta}.
### (1) g5 failing endpoints by class (one worst path per endpoint, chain/sta_r22k_*/grt_*_summary.rpt; classifier scratch/qw_g5sta/cls2.py)
TT setup (42,694 failing):  landing window (E_sta 2 from the STALE dv2f15 bi plan < measured) 38,414 worst -3640.6 (dv_rsi/q3h_col/st_wi/dv_rs) |
  reset tree 635 worst -9036.3 (rstt_rst_d2d -> lnk_fwd_epoch en; rstt_rst_field -> rstt_rst_field x504 -7772, launch/capture insertion 8.7 ns vs 0.7 ns = region crossing reg->reg) |
  clock-boundary model 3,645 worst -1356 (~2.4k stream__early -> d2d_rom/ucie_kv ~-290 = early tap Q.STA.GEN.2; ~1.2k rly_serdes* <-> io_collective serdes face -1356/-1100) |
  owed unlanded 0 | real data path 0.
FF hold (setup FF WNS -7201 = same reset paths):  slice<->slice owed crossings (dvs_X -> dvs_Y direct, 182 rows) 25,973 worst -64 | landing window 25,772 worst -2374 |
  reset tree 1,664 worst -6406 (rstt_rst_field -> rly_dv_x0_* en/rs) | clock-boundary model 3,431 worst -6661 (io_ucie tx_up -> io_collective ucie_up: collective ucie pin given a 6.8-ns stream arrival) |
  hard-tile -> hop-0 relay hold 1,424 worst -270 (sys_face / embed_prov / rstseq_rom deep insertion) | lnk_fwd_lrst landing with no MCP 1 at -7351.
SS (ideal die clock, sensitivity): landing window 2,535 worst -3266 (st_wi 22->23: 22.7 ps wire, forwarded clock 4.58 ns, MCP 2).
### (2) STA-only diagnostic on the g5 GRT checkpoint with E_sta re-derived from g5's OWN STA (chain/land_plan.json; hold MCP D-1, D 4/8)
ep6 dv2f20g5/diag_g5sta/sta_{tt,ff,ss} (units oth-ubuntu-68128/68131/68073-1792527734, exit 0; generator mk_diag_g5sta.py):
  TT TNS -43.99M -> -3.11M, WNS -9036 unchanged (reset); landing class 38,414 -> 0.  FF setup TNS -22.65M -> -1.87M; FF hold landing 25,772 -> 0 (D8 rows assume D8 landings: NOT bound in g5).
  SS WNS -3266 -> -1498, TNS -4.26M -> -1.50M.  Residual TT = reset tree 635 + clock-boundary 3,645 only.
  E re-derivation: 399 lanes; 80 raise E_sta (2->3:34, 2->4:24, 2->5:10, 1->2:6, 2->6/7:4, 7->8:2) = +138 lane-cycles, max +5 (dv_rsi_W2_3 / dv_rsi_E5_3 2->7,
  dvw_st_wi total 13->17).  These are priced by the successor GEN (OT_SPLIT_LAND_PLAN: E = fwd_e_est(n) + E_sta - 2) and its phase2 layer_compile.  40 lanes need D8 (Q.STA.LAND600.3.1 bind owed).
### (3) Structural successor (data-only GEN input, opt-in, composable with QW-G5F3 809a1651f)
915e95212: tools/qwen_split/dv_xgap_plan.py + dv2r8f7r_qdv_p2462_xg864.json = 86.4-um full-height channel at the 10 abutted slice boundaries (columns shift together,
  die w 31730 -> ~32594 um < 33000 reticle) + OT_SPLIT_LAND_LIST_IN_FACE='' -> the 182 slice rows get die-level one-frame forwarded landings (4-slot ring at the receiver);
  core feed x 16848 -> 17280 (stays in the W0|E0 seam).  Codex D8 SRAM receiver (codex/qw-landing-1255-1020) stays the in-slice alternative where width needs it.
LAUNCHED ep6: dv2f20g5l (land plan = g5 self, E rows) unit oth-ubuntu-94670-1792528315; dv2f20g5lb fallback (bi plan as g5) unit oth-ubuntu-94671-1792528315.
  drive.sh = setup -> pre.sh (GEN, reset_sync, strict bind) -> follow.sh (reset projection -> phase2 relay export + layer_compile + RELAY_CHECK -> phase3 die chain, DIAGNOSTIC_ONLY).
NOT DONE: 8 noroot / 3 BUMP straps (bump straps are static package straps: declare static in the regional judge, not ring-land); reset-tree region crossings = Q.STA.GEN.7 (LEAD8-QW);
  clock-boundary model (serdes/ucie face pins, stream__early tap) = Q.STA.GEN.2.
### COORD 12:15 answer (g5 GRT, chain/grt_r22k/grt.log)
Overflow 0 on every layer, so the macro-channel vs over-macro overflow share is 0 / 0.  Usage M4 3.79% M5 4.35% M6 2.97% M7 0.29% M8 1.33% M9 0.01% (total 1.66%; M2/M3 not routing layers,
min layer M4).  Macro derating (resource reduction) M4/M5 29.9%, M6-M9 5.4-5.6%: the dv array macros block mainly M4/M5; M8 already carries die signals (1.33%); not boxed in like S81.
### 13:40-19:10 GEN tries (ep6 dv2f20g5l self plan / g5lb bi plan), all diagnosed from the GEN's own failure receipts
 try1 xg864: 'tree pads: no free spot dv_st_E2_st_u_st' (N/S 1088-b frame 186x60 > 86.4 channel) -> b3e959583 opt-in E/W frames (OT_SPLIT_FWD_LAND_EW_MASTERS=qfd_dv_slice2)
 try2: 20 nets >405 (st_u placed last, 400 um off pins) -> b9d0f9189 widest-first;  try3: 129 nets >405 (one column crowded) -> e915c1f56 xg1296 (9 boundaries, E0|E1 share a root; die w 32897 < 33000)
 try4/5: 130 nets >405 (channel refused as 'field' / centred column) -> b23a11d9d channel sites + 6b3206fb3 W/E column snap -> 19:06 GEN rc=0 BOTH (relays 1080, max p2p 377.6, over_reach 0, die 32.897x24.289 = 799 mm2).
 19:10 FOUND QW-G5REACH (18:35) already carried b23a11d9d + the same 2-column fix (cfc5a82ac) to chains dv2f20g5r2/r2b (bind PASS): my 19:01 g5l/g5lb were DUPLICATES -> killed (own pgids on ep6) and deleted. 6b3206fb3 = redundant with cfc5a82ac (not to be merged).
 Owner of Q.GRT / Q.STA.GEN / Q.STA.GEN.10 = QW-G5REACH. Lane ENDED.
 FLEET NOTE: ep6 ot-heavy queue had ~575 waiters / 27.6 TB (hbm-die*/planA/syn hbfd_rly_* syntheses, ~400 of them): a 64-GB non-die request was not admitted for >5 min; die-priority 96 GB was admitted at once.
