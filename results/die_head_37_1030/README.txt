DIE-HEAD-37 2026-10-30. HEAD reader-START R2 first PLACE (Codex canonical GEN7 kits, src25q3 + current-main generator).
Run dirs: intel2:/srv/opentallas-scratch2/claude/die-head-37/{r2place,r2ft}. Read-only GEOM grt=false (geom_check.sh, main 3fc2fcf0d tools).
r2place: attempt 1 FAIL_PREFLOOR face_guard shared x3 (plan raw reset of reader stage 2 = rr_t10/rr_t7, the relay that drives port rst_o_0).
  Kit-local fix: that relay -> ot_dp_head_raw_export_pair (same d, same cycle), reader stage 2 takes export_q (raw_private_pair.diff). +1 flop, 0 cycles.
  Attempt 2: PLACE exit 0, face_guard PASS, LEC EQUIVALENT x3. origin->ring-arm captures 0 on all 3 (Codex st_str_first: 134).
  st_m r2r 10; st_str 519 / n3_transit 523 (504/506 ring dsel -> u_ft_*_s0, relay_collapse 504 with main landed-FT L*(j+1)/k).
r2ft: r2place + Codex st_str_first FT helper verbatim (head_ft_helper.tcl; first fraction .1725). LEC EQ; relay_collapse 0;
  st_str r2r 14 (max 1246.75), n3_transit 13 (max 1259.66). Residual classes: single cland_rst_<b> reset relay feeding origin +
  far-face up/fstart status (8-9); ring ready/fault -> loc/agg status relays placed at the far end (4); origin -> opposite fstart (1, W1 class).
r2r_list.py = exact geom_rules.r2r_metrics math, lists every capture > 405 um.
