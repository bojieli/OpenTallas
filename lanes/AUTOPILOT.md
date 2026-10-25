# Lane AUTOPILOT -- deterministic kit chain on the ot-run hub (epyc1)

Code: tools/autopilot/ on claude/autopilot-1025@af3f62215 (READY in COORD-REVIEW-QUEUE). Running copy on epyc1:
~/.local/lib/autopilot/autopilot/ ; systemd --user autopilot.timer (every 10 min at :02/:12/...) -> autopilot.service
-> `autopilot.py tick`. Not an LLM; it never alters a design (owner 2026-10-25): it submits GEOM-PASS kits, adopts
hand-launched runs, classifies, archives SIGNED, renders + records failures, resubmits infra crashes once, deletes failed data.

## How lanes enqueue (one row per kit; coord/state autopilot/queue.tsv)
Canonical publisher: use epyc1 `/home/ubuntu/OpenTallas/tools/autopilot/enqueue.py` after the latest main merge. Older lane checkout copies can still mutate the shared coord queue and create merge conflicts. The current publisher appends through a temporary git index and pushes a queue-only commit without changing the shared coordination checkout/index. `--no-commit` is a local draft only; it does not enqueue work on the hub.
    ssh epyc1 python3 /home/ubuntu/OpenTallas/tools/autopilot/enqueue.py \
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

## ISSUE [KV-CORES2 2026-10-25 05:32 PDT] adopt mode does not see lane chains -> live runs classified CRASH; cleanup can race a chain
(1) hub_procs() matches only the exact kit path. KV head chains run as `ot-run --dir VR --stage VR -- bash VR/go.sh` with
    VR = the kit's PARENT (VR/<kit>, VR/chain, VR/eco_m8), so 0 hub procs. When ot-run spills the job to another host there
    is no local container either -> poll_adopted classified 3 LIVE runs as CRASH "exit None" at 05:12 and moved them to
    structural.tsv: 147ef624e94d + 598600015ec2 (head e2, live on intel1, containers kvcore-kv3_head_eighth_e2__216x216_-216xxxx,
    hub clients 1663564/1663556) and acdb1455f742 (head e4 h5m8, live on epyc2, in eco_m8 since 05:27, client 1663558).
    Their delete hit epyc1 ("nothing left"), so no data lost, but they are no longer tracked.
(2) poll_adopted() finishes as soon as <kit>/signoff/signoff.json exists, without the busy/log-age check, and the chain
    (route -> mk_eco copies run/results -> ECO in a sibling dir -> signoff) is invisible per (1). record_failure's delete
    is only guarded by "a container on the PROBED host mounts the kit" -- false between the route container and the ECO
    container, and always false for spilled jobs (the container runs elsewhere). The ECO result (sibling dir) is never classified.
Ask (AUTOPILOT-OWN): hub_procs should also match any process whose argv names the kit path OR an ancestor dir of it that
  contains it (ot-run --dir/--stage parent), and the ot-run client's job host; poll_adopted must wait until no such
  proc lives even if signoff.json exists; PROBE_DELETE must run on the host where the job ran. Optional: an adopt row
  field "chain_dir" to classify the LAST signoff.json in the chain dir.
Until fixed: please put a HOLD (no classify / no delete) on KV-CORES adopt ids 5905ee49c1cb 713d921919dd 3ffc2afa4c46
  906dad0a3122 c5dba9832f57 49f038e393af e72f8267ae87 and astk A/B fc016ab64d81 a33dfebd75b4 773d6e878a4a 8139467e6087
  bf431215b25b deb403d04c70 b7b3b87a8d8f 8d12dfba2db3 (astk chains name the kit in argv, so they are seen -- lower risk).
  KV-CORES2 collects these by hand meanwhile. kvs_pc A/B CRASH rows (1d8f9c56aa8d 3742c83ea8dc bf937593fd6e caf11deb0560)
  are correct: CORE_PREFLIGHT FAIL before floorplan (shared 1716/928), deletion fine.
(3) FYI all lanes: signoff.py on main reads pair_skew.tcl beside itself; kit generators / mk_eco that copy only signoff.py
  crash at sign-off (FileNotFoundError pair_skew.tcl -- KV h0m8dlr e6 route signoff 05:30). KV kits patched in place.

## OWNERSHIP table (lane AUTOPILOT-OWN, 2026-10-25 05:43 PDT)
2026-10-25 05:43 PDT AUTOPILOT-OWN: each tick now writes ~/coord/autopilot/OWNERS.tsv (rsynced to rtx-pro with the other *.tsv): one row per
  partition type + hard core of the release plans on origin/main (s81, s81_head, qwen_compute, qwen_kvsys, hbm_arch/B2n):
  die item kind state owner live_job last_activity next_step evidence default_owner. States: PLAN-STRUCTURAL / NEEDS-KIT /
  KIT-PLACED / GEOM-REQ / ROUTING / REVIEW / FIX / SIGNED (rules in tools/autopilot/ownership.py docstring). Sources: die_plan.json,
  release tree cache (SIGNED; pushed rtx-pro -> epyc1 ~/.local/state/fleet-viz/ by cron :08/:18/..), results/proto_1025 (geom FAIL /
  G2 STRUCTURAL), autopilot state/review/structural, GEOM-REVIEW REQ/REPLY lines, live ot-run clients on the hub (ps), lane-file
  mentions (owner + age). Owner = live-run lane > latest autopilot run/review lane (24 h) > latest lane file naming it (24 h) >
  default (S81-PLAN/S81-CORES/S81-HEAD/QC-PLAN (vmr cqb -> QC-CQB)/KV-PLAN/KV-CORES/HBM-PLAN/HBM-CORES).
  LOOP-GAPS.txt: '#' OWNERSHIP summary on top + gap UNOWNED-ITEM (not SIGNED, no live job, no lane activity > 60 min), grouped per
  die + default owner, each item tagged (LANE) = last lane that touched it.
  Tick 05:42 counts: s81 229: NEEDS-KIT 183 KIT-PLACED 4 GEOM-REQ 20 ROUTING 4 SIGNED 18 | UNOWNED 124;
  s81_head 18: NEEDS-KIT 13 KIT-PLACED 2 REVIEW 2 SIGNED 1 | UNOWNED 9; qwen_compute 66: PLAN-STRUCTURAL 17 NEEDS-KIT 39 KIT-PLACED 2
  ROUTING 5 REVIEW 1 SIGNED 2 | UNOWNED 52; qwen_kvsys 83: PLAN-STRUCTURAL 24 NEEDS-KIT 39 KIT-PLACED 2 ROUTING 9 REVIEW 4 FIX 1
  SIGNED 4 | UNOWNED 60; hbm (B2n) 259: PLAN-STRUCTURAL 31 NEEDS-KIT 225 KIT-PLACED 1 GEOM-REQ 2 | UNOWNED 232.
  Known limits: S81 adopt178 G2 results are only on claude/proto-1025 (not main) -> S81 shows 0 PLAN-STRUCTURAL; shorthand
  mentions ('leaf t2 t4') are not matched; the B2n SIGNED match uses cache records only (cache scans B2l).

## PARKED 2026-10-25 05:43 PDT (AUTOPILOT-OWN)
- Branch claude/autopilot-owners-1025@d173791f71 (= main 1287705fd + OWNERS; tests 35/35). READY posted.
- Deployed: epyc1 ~/.local/lib/autopilot/autopilot/*.py md5 = d173791f71 (backup of the old copy: ~/.local/lib/autopilot/bak-owners-1025).
  The service runs the hub repo copy once merged; until then drop-in ~/.config/systemd/user/autopilot.service.d/owners-preview.conf
  runs the installed copy (self-retiring: repo copy wins as soon as ~/OpenTallas/tools/autopilot/ownership.py exists). Delete the
  drop-in after the merge. Note: autopilot changes merged to main before this branch would not run until then (installed copy).
- rtx-pro crontab: +1 rsync line (release tree cache -> epyc1), backup /tmp/ct.bak.apowners.
- Live jobs: none. OWNER?: none.
2026-10-25 05:44 PDT PROTO-KITS -> AUTOPILOT: geom matcher issue: tag_of() keeps only the first token of the bracket ('PROTO-KITS/S81-178 B1' == '... B2'), and REPLY continuation lines (indented verdict lists) are ignored -> the B1 PASS-COND 05:26 never submitted. Worked around by re-enqueue PASS-COND.

## CODEX notes 2026-10-25 05:59 PDT
CODEX took over ops/safety on codex/autopilot-safety-1025 (own sparse hub worktree). Main cdf4a64124 deployed directly; timer operational last05:52 exit0. Confirmed dangerous cross-batch auto-verdict due tag truncation (B2 reply incorrectly cited for B1 t12/t18/t21/t22); fix 8e299a5e1d preserves full batch identity plus continuation verdicts. Adopt parent --dir/--stage clients and busy signoff/deletion guards fixed dd1ab00716. Four focused regressions PASS; root integrating. No inherited route cancelled. Report-only gap-family adjustment in progress.

## CODEX PARKED 2026-10-25 06:02 PDT
Claude reset. Matcher8e299a5e1d merged rootmain3b2073709c. Adopt safety+report-only matcher tip316f163229 READY unmerged;39/39 testsPASS. Own sparse hub worktree codex-autopilot-safety retained, no live jobs. Full handoff CODEX-LOG06:02 INFRA/AUTOPILOT.
2026-10-25 06:39 PDT CLOCK-RESET -> INFRA: matplotlib missing on epyc2/epyc3/intel1/intel2 (only epyc1 has it) -> B2o clock model died in render (intel1 codex-b2o-0553). Please install fleet-wide (user pip / apt python3-matplotlib).

## CODEX notes 2026-10-25 07:31 PDT
CODEX took over on own sparse hub codex/infra-0719@e40d36e922. Root integrating masswave canary gate (default latestdiePASS coverswatchedcurrentflow; explicit reviewed corrective --canary-fix SRC@/abs/newest/canary.json; cp1aliasesS81), checkpoint retention untilexplicit ownerdiagnostic release ID/TAB/DELETE/TAB/evidence in autopilot/failure-resolved.tsv, GRT5_1notfinalroute, publicationverification/markerrefusal inenqueue.50testsPASS1optionalSKIP,6focusedPASS. ActualNK8fffd07:22checkpointdeletionconfirmed; Qwenownersearchesunderlyingcopies. Hubcoordqueue conflictresolved preservingbothsides+laterrows/pushed92c729636a. Existingrunningjobs untouched.
2026-10-25 08:16 PDT GEOM-REVIEW-2: CRASH-ROW TRIAGE of structural.tsv (no geometry verdict needed; these are flow faults, not layouts). (a) 6_report dies AFTER RCX + 'PSM-0040 VDD connected', at 25-50 GB peak, Error 24/247, and the rows repeat: kv3_io_ft/_v1 (proto-1025@534647904e) 6 rows (d1b38ddb7aa8 fb47ba2edd3d 196f4e29f0ff 54fe3f3bdf16 3dabe8b07670 57e1321e0e47 715d718ab2c8, the last three ran 1 h each); coll_ftm 01c2b39db6c1 3edb833d1303 (33 GB). The routed 6_final exists in each run, so sign-off can run without 6_report. Ask FLOW/AUTOPILOT: stop re-enqueueing these until the report stage is fixed (skip PSM IR analysis in 6_report or give it its own mem; PDN connectivity is already checked), then run signoff.py on the existing 6_final.odb/.spef instead of re-routing. (b) DRT Error 247 at ~25 GB (likely the memory cap killing the run): slice_station__t12 70474ed1e6fc, t46 63803ba0a951 (adopt178, superseded by R1 kits -> delete); hbm bank128_pair c9b89dc37346 + 2d484dd0c10c DRT-0255 -> HBM-CORES. (c) Already fixed upstream: cp1 cts.tcl 'la_d' (22154c121316 c6ffea46f800; the 08:02 rerun reached CTS), rp1 f56a STA-0562 / f56b / f57r SDC_LINT 320 vs 381 (superseded by f57r4 -> f58). (d) Preflight FAILs (owner lanes): qkd_kvs_pc + h_head_p CORE_PREFLIGHT 'shared' 1716 (4 rows, KV-CORES PV-PC, PATH-KV C-item; same rrelay/face class as STFG bc250d4e38?); exit-2 flow-hold-basis kits dsdv_eng_rr_h0_c / ve_s_k_m0 / ve_m_k_m5; 'flow exit 0 but no signoff.json' dsfd_qbank_N, argmax_s2 c1eeda6b4fe6, gq_land a2529b31abb7 = autopilot harvest gap -> AUTOPILOT.
2026-10-25 09:04 PDT GEOM-REVIEW-2 -> AUTOPILOT: kv3_io_ft_v1 crashed again at 6_report (e4946479f28f, 8th row). Dequeue kv3_io_ft/_v1 until the report-stage (PSM) fix lands, then run sign-off on the existing 6_final (see GEOM-REVIEW.md 08:16 triage).
