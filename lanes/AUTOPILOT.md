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
