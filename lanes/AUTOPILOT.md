# Lane AUTOPILOT -- deterministic kit chain on the ot-run hub (epyc1)

Code: tools/autopilot/ on claude/autopilot-1025@af3f62215 (READY in COORD-REVIEW-QUEUE). Running copy on epyc1:
~/.local/lib/autopilot/autopilot/ ; systemd --user autopilot.timer (every 10 min at :02/:12/...) -> autopilot.service
-> `autopilot.py tick`. Not an LLM; it never alters a design (owner 2026-10-25): it submits GEOM-PASS kits, adopts
hand-launched runs, classifies, archives SIGNED, renders + records failures, resubmits infra crashes once, deletes failed data.

## How lanes enqueue (one row per kit; coord/state autopilot/queue.tsv)
    cd <any checkout with tools/autopilot> ; python3 tools/autopilot/enqueue.py \
      --die s81 --type slice_station__t5 --kit epyc2:/srv/opentallas-scratch2/claude/<lane>/.../<kit> \
      --src claude/<branch>@<sha> --geom PASS-COND --geom-ref "GEOM-REVIEW [S81/KITS 01:14] reply 01:20" \
      --mem 24 --cells 120000 --lane <LANE> [--goal route|finish] [--threads 8] [--mode submit|adopt]
  (rtx-pro: the worktree /home/ubuntu/wt/autopilot-1025 has it until merged; it commits via coord-commit.sh)
- submit (default): placed or fresh kit; launched via ot-run with your --mem. Routed / signed-off / FAIL_* kits refused.
- Queue BEFORE the verdict: --geom REQ --geom-ref "<your GEOM REQ tag>" -> submitted within one tick of a GEOM-REVIEW
  REPLY/VERDICT [<tag>] that names the kit (type, __suffix or sha) with PASS/PASS-COND. Mixed/unclear verdicts never submit.
- adopt: you already launched it by hand; the autopilot watches it and does the tail (classify/archive/review/delete).
- Honest --mem; --cells <= 400000; kit under /srv/opentallas-scratch*/claude/.

## Outputs (epyc1 ~/coord/autopilot/, rsynced to rtx-pro ~/coord/autopilot/ at :04/:14/...)
- log.txt (every action, timestamped), state.json, LOOP-GAPS.txt (overwritten each tick, oldest first)
- signed.tsv -> archive <host>:/srv/opentallas-scratch2/claude/autopilot/closed/<die>/<type>@<sha> + mirror (epyc3)
- review.tsv (NEAR-MISS: TT/FF WNS in [-30,0), overflow 0, DRC <= 50) and structural.tsv (STRUCTURAL / CRASH):
  for the owning lane -> visual review + structural fix. Routed failures carry a bundle in
  <host>:/srv/opentallas-scratch2/claude/autopilot/review/<id>/ (paths.png, paths_zoom.png, floorplan/density.png,
  paths_tt_setup.txt, paths_ff_hold.txt). Rows with no GEOM REQ / fix line naming the type in lanes/<LANE>.md after 60 min
  show up in LOOP-GAPS.txt.
- Status: ssh epyc1 python3 ~/.local/lib/autopilot/autopilot/autopilot.py status

2026-10-25 04:49 PDT AUTOPILOT: tests 31/31 (fake hosts/units); read-only classify on 6 real kits matched hand verdicts (t12 SIGNED, t15 +
  qfd_dv_s5 NEAR-MISS, s8x_btab GRT STRUCTURAL, hd_turn_b routed-not-signed, gunit flow-error); real review render via
  ot-run 22 GB on t15 (both paths drawn, zoom OK; test bundle deleted); dry tick on real coord files; live tick via the
  service ADOPTED 3 PROTO routes (m5 hd_turn_a/hd_turn_b 24 GB, coll_ftm 32 GB; launched by PROTO-KITS 04:33/04:37).
  The live SUBMIT path is covered by tests + dry run only: no unowned GEOM-PASS kit was waiting (PROTO routed all 12 by hand).

## PARKED 2026-10-25 04:49 PDT
- Branch claude/autopilot-1025@af3f62215 (READY posted). Deployed copy = same files (md5 match). Timer enabled on epyc1.
- Live: autopilot adopted epyc1 proto1025 m5/{hd_turn_a,hd_turn_b} + kits_qwen_compute/m5/coll_ftm (routes owned by
  PROTO ot-run clients; the autopilot only watches). Next ticks classify them -> signed.tsv / review.tsv / structural.tsv.
- rtx-pro crontab: rsync of hub outputs (backup /tmp/ct.bak.autopilot2).
- Next: lanes enqueue instead of hand-launching; after merge, the service runs ~/OpenTallas/tools/autopilot (hub-git-sync)
  else the installed copy. Deploy update = scp tools/autopilot/*.py *.sh to epyc1 ~/.local/lib/autopilot/autopilot/.
- OWNER?: none.
2026-10-25 05:15 PDT GEOM-REVIEW-2 -> AUTOPILOT: please keep 6_final.odb/.spef/signoff for review.tsv+structural.tsv rows until the post-route verdict is posted (or 24 h); 2299f18f684e/436d78c0f105 were deleted at record time. Verdicts are in lanes/GEOM-REVIEW.md.

## PASS-RECON 2026-10-25 05:26 PDT -- the 16 GEOM-PASS-NOT-ROUTED gaps (05:12 tick): 0 enqueued, 3 adopted, 16 verdicts resolved
Marker: coord/state autopilot/resolved.tsv (tag, verdict time, resolution, kits, lane, recorded, note); loopgaps skips
exactly that verdict once claude/pass-recon-1025@191864172 is merged + deployed (READY posted). Until then the adopts clear
S81/KITS + QC-RP1 by tag; the other 9 lines stay in LOOP-GAPS.
2026-10-25 05:26 PDT PASS-RECON: HBM-ELEM 10-24 19:57 | B2l 9 families @c6d07a7a0e | SUPERSEDED: face_guard-FAIL families deleted -> B2n face shells; svc h9b/hc_bankq0/hc_bankq/idx n12 routed NOT SIGNED -> rebuilds; xcal GRT fail
2026-10-25 05:26 PDT PASS-RECON: S81/KITS 10-24 21:30 | legacy r6 dsfd_node LLfd/LLfu/NNfd/NNfu_c + dsdv_gunit_l4r_c | SIGNED (views on main)
2026-10-25 05:26 PDT PASS-RECON: KV-CORES 10-24 21:45 + 22:36 | qkd_ahub fp plan/r2 | NOT-ROUTE (place+CTS only; r2 kit stopped at face_guard preflight shared=4)
2026-10-25 05:26 PDT PASS-RECON: S81/LEAFPLAN 10-24 21:55 | eg_c pin revision | SUPERSEDED (r7 -> LEAFPLAN r9 + S81-CORES/LEGACY eg_c, live)
2026-10-25 05:26 PDT PASS-RECON: HBM-CORES 10-24 22:13 | bankq_ft 43d2a3/d7bcdf/1d3df8 | ROUTED by hand: 43d2a3 FAIL (GEOM-REVIEW-2), d7bcdf+1d3df8 died DRT at 25 GB; needs new kit
2026-10-25 05:26 PDT PASS-RECON: S81/KITS 10-24 22:25 | c3 x7 | ROUTED: rr_h1 signed, hcpost+rxsb signed (Codex ECO runs), rr_h0 FLOW rebuild row, rxsf waits RTL, vsw_t22 live, vn_c split
2026-10-25 05:26 PDT PASS-RECON: S81/KITS 10-24 23:13 | eg_c r7 | SUPERSEDED (legacy eg_c kit live, needs its own post-CTS REQ)
2026-10-25 05:26 PDT PASS-RECON: S81/DEC12 10-25 00:26 | die plan d206dfb226 | SUPERSEDED (DEC12R -> adopt178 on main)
2026-10-25 05:26 PDT PASS-RECON: S81/KITS 10-25 00:49 | slice_station x24 | ROUTED by hand, 0 signed, superseded by kits_s81_178; t24 live -> ADOPTED 5ead1de2248f
2026-10-25 05:26 PDT PASS-RECON: HBM-CORES3 10-25 01:06 | gq_land@4d3dd24bd7bf | SUPERSEDED (routed NOT SIGNED -> gq_rr19 REGIONS(19), at CTS, needs post-CTS review)
2026-10-25 05:26 PDT PASS-RECON: S81/KITS 10-25 01:20 | slice_station x6 | ROUTED NOT SIGNED / retired (t15->t46, t16->t47); all in kits_s81_178
2026-10-25 05:26 PDT PASS-RECON: S81/KITS 10-25 03:33 | split ve_m/ve_s/vn_a/vn_b | ROUTED NOT SIGNED (Codex); ve_m/ve_s FLOW rebuild PASS rows queued; vn_a/vn_b rebuilds live
2026-10-25 05:26 PDT PASS-RECON: HBM-CORES 10-25 04:37 | argmax r2 re-run + gq_land REGIONS(19) | NOT-ROUTE yet: argmax_s1_rc0665/0700 + gq_rr19 stopped at CTS for post-CTS review
2026-10-25 05:26 PDT PASS-RECON: QC-RP1 10-25 04:39 | qfd_dv_s8_crh_rp1 | NOT-ROUTE (rebuild); 05:06 route clearance -> live f56a/f56b ADOPTED 05002e6c9ab8 / dfd30ddd5d84
2026-10-25 05:26 PDT PASS-RECON: CLOCK-RESET/relay2 10-25 04:42 | payload536_r2 + rstg_r2 | SIGNED (results/s81_relay2_1025/signoff on main)
2026-10-25 05:26 PDT PASS-RECON: for owners (not acted on): (a) S81 x24 t6 (epyc1 ot-run 2078719/2079925, 4.4 h GRT hold loop) + t11 m5 (2095697) route superseded types -> kill?; stray intel1 container dpkit-slice_station__t24-786393 (t24 m0, no client, 4 h); t27 has no kit in kits_s81_178 (PROTO skipped it as 'live', those runs were killed 05:14). (b) HBM-CORES argmax_s1_rc0665/rc0700 produced the same 4_1_cts.odb: the asap7 image ignores SET_RC_TCL (CLOCK.md:88), use LAYER_PARASITICS_FILE; CLOCK-RESET argmax_struct kits failed CTS on cts.tcl:87 'la_d'. (c) a parallel branch claude/autopilot-owners-1025 also edits tools/autopilot: merge order matters.
