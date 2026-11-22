# OPUS-FIX-KV-HGI-R6 handoff (Opus; KV hg/hgi family owner; successor of R5). Updated 2026-11-21 18:3x PST.

Work dir: epyc8 /srv/opentallas-scratch2/claude/opus-fix-kv-hgi-r6 (W). Client logs: intel2 ~/tmp/opusfixkvhgir6/*.log.
Codex-era (14:23-18:1x) work under this lane: epyc9 W9=/srv/opentallas-scratch2/claude/opus-fix-kv-hgi-r6 (hg_d26_read/local_tails: hg/hgi reset
replays, hgi_sync sim proof PASS + 2 mutants caught, place1 kv3_hg place-only), intel2 /srv/opentallas-scratch2/claude/opus-fix-kv-hgi-r6
(d27d3_hgi_v8_face_exact: v8 FT11 reseat, generated_v8_followup strict unit 519100).

## Facts
- EMIT reset-relay class = fixed by KV-PLAN-R6 (landing_remap OLD=D26 NEW=D27d, generator step). Private plans: landing_remap must run with
  both plans INSIDE a plan_of_record dir (taps.input_path reads sink_bins/ from the plan folder) -> chain_r6b.sh pattern.
- D26 hg -559.80 = 23-level 1730 um reset chain via one fallback NK-lockup copy -> main f9c3591c98 reset_replicate lockup_regions.
- D26 hgi_v2 -738.66 = score reset async-clear recovery -> tail_clear sync (COORD 18:1x APPROVED: async assert at input sync, sim ordering
  proof, LEC clean apart from intended reset diff; 5-clock release, assert +3, spine >= 64 clk).
- Main has lockup_regions + tail_clear sync/sync_output + schema (d951181530, dcda12c20d). rt 7b6af7dd0449 has them; 3a68739125f4 / D27d3 tree tools do NOT.

## Plans / binds
- plan_r6 48ff8b2795b1 = D27d2 + R6 regenerated rows (kst_xstreet_v2 hgi, v3 hg soft halo, v8 taps t81/t82, v8 fs_ft11_o stage by xy) + landing_remap
  (317 names). R6b strict bind GREEN (bindgate27: BIND 0, LAT 0, G0 0; R8 32 unequal + BPC 1 pc_cl5a95b461 inherited).
- plan_r6c = D27d3 48b92c30c8f6 + R6 rows + reset rows (lockup_regions on 19 types, tail_clear sync on hgi). Rows file W/ana/hgi_r6c_rows.json.
  chain_r6c.sh: tree27c over sealed D27d3 (kw45/src_kv_pin_eb1e73448bd0_hg15_48b92c30_t4e46a7ec_d27d3), launch27c on rt 7b6af7dd0449,
  g0gate27c, bindgate27c. ot-run unit oth-ubuntu-3223289-1795314633 (client intel2 3465703, log chain_r6c.log).

## Next
1. R6c green -> kit_wave.py private-spec qwen_kvsys kv3_hgi_v1__cl141fc26e --plan W/ana/plan_r6c.json --tree W/tree27c
   --bind-out W/tree27c/physical/die_plan/qwen_kvsys/plan_of_record/bind_of_record --src-manifest off --rt 7b6af7dd0449 --host epyc8|epyc7
   (on intel2), run-item; kit_pin_site_check before place; measure placed ectl hops q->hst2_g/hst3_g (station only if >405); post-hook CTS;
   final 5_1_grt.odb; LEC (reset diff only) + reset ordering sim.
2. Rows to KV-PLAN-R6 for D28 (hgi_r6c_rows.json). Proof must be rebuilt from a manifest tree to export (or carried by D28).
3. Claimed FAILED-NO-RELAUNCH hg, v1p3..v1p6, hg_v3: relaunch on current rt once D27d3 is applied (KV-PLAN-R6 apply_d27d3_guarded.sh).
