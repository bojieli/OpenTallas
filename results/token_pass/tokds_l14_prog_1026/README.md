# TOK-DS L14 programme on the strict-bound S81 carve (2026-10-26)

What this is: the L14 programme compiled with the current compiler, plus a bound-port stimulus and expectation spec for the
96-partition L14 carve of the strict-bound S81 top (main 877cfdeb28, re-bind v2, bound top sha 1c11db22). It is **not** a token pass.

## Compile (dv_layer_compile.py, branch claude/tok-ds-prog-0105)
- **Against the 877 source (OT_S81_SELECTED_SOURCE_ROOT = 877 rtl): BLOCKED.** xr_timing.source_contract rejects the current
  ot_s81sl_xrt.sv (sha d09cf3f6, which has FACE_LAND, pin stations, PDSK and QREL since cfc3feb9). The selected-XRT model
  list holds only cfc3feb9 and ec43bb. See compile_877src_blocked.txt. I did not add the sha: that would be a timing
  qualification claim, which needs a selected-XRT V-CTL injection proof.
- **Against the fc31 legacy selected source (root30 s81_dv copy, SVCQ_ENG_FG3, tree_fc31, checkpoint fixture L14): PASS.**
  92 ops: 18 LOWERED / 54 PARTIAL / 20 GAP (s_0S), and 15/57/20 (s_6S). Runtime 14 min, 0.7 GB.
- **Priced L14** (the schedule.json price = dv_layer_price facts on the tree_fc31 geometry, + 1 VSW LR1 edge):
  span **26067.4**, critical path 26013.5 cycles.
  The 28082.9 figure is the p4l-plan price (dv_layer_price default plan: span 28081.9 / crit 28028.0; Codex's LR1 +1 =
  28082.9; file dv_layer_price_p4l.json). Both prices use legacy geometry. Neither uses the bound 877 ages: bound_stages
  differ from the as-built stages, e.g. attn__svc_11__s_4S_C 37 -> 24.
- The L14 entry H from entry_engram is MISSING. The compiler does not consume it (only norm_quant.golden takes
  entry_engram_inputs). Its sidecars (inputs_L14) and the checkpoint snapshot were on epyc3, which is retired, and no
  live fleet host has them. Regenerating them needs the DeepSeek-V4.1-Flash checkpoint on a fleet host.

## Bound-port spec (tools/s81_dv/layer_prog/bound_l14_stim.py; summary.json)
- **Inputs (184):** CLOCK 1, RESET 14, LOOPBACK_FT 11 (carve-internal producer relayed through outside FT stations),
  **DERIVABLE 1**, **MISSING 157**, IDLE_BY_SCHEDULE 0.
  - The derivable input is xtier__bk_sel__s_4S_C: 142 words, from the compiled u_s_4S.vi landings minus the link age, at
    +41 stations.
  - MISSING by producer: frames 82, slices 35, svc 26, bk_sel 5, off-die 9 (phy_hbm, lk_EN/ES).
  - Why so many are missing: the compiled programme encodes boundary events only on the bind9 instances it lowers
    (u_gunit, u_eng, u_bk_sel, u_s_*S, u_s_7N). It has no events for frames, svc_rs/ctrl, the N slices or the PHY/link models.
- **Outputs (169):** CLOCK_RESET 42, UNSPECIFIED 127. The compiler encodes no producer-pin events inside the carve.
- **Timebase:** words are in compiled layer cycles (layer 0 = KS + 5). t0 is UNRESOLVED: it needs the measured boot/KS
  phase on the bound replay. So no .ev files are written yet; the tool writes them with --t0 --ev-dir.
- **Programme load map (s_6S compile):** 61 files. 46 have their consumer inside the carve, 11 partly outside, 4 outside.
  - host_boot.memh is a HOST_STREAM. In the compiler's model it enters u_seqhost.f_host; in the 877 die f_host reaches
    u_seqhost (bound seqhost.u_core) over u_s_7N.u_lep and u_s_0N.u_hbc. It is not a $readmemh image.
  - xs/frame images are ROM macros. **BLOCKED:** all 84 carve ROM macros (ot_rom_4096x72_m8) are emitted with
    INSTANCE(""). ot_rom only reads +OT_ROM_DIR/<INSTANCE>.viamap.hex when INSTANCE is non-empty, so no image loads in a
    bound simulation. The bind emit must carry the elaborated INSTANCE string.
