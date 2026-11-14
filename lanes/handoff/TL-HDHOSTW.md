# TL-HDHOSTW (HEAD hd_host_w form B)  2026-11-14 05:00 PST
Cause: DRT congestion. Kit attempt_3: DRT-0255 net62843 at (231,382), 76k viol after iter0, GRT usage only 7.8%/0 overflow, util 24% at PLACE_DENSITY 0.5.
Form A (HEAD-99): OT_CONS_UTIL=0.25 on the old 648x570.24 outline: cells 86.7k um2 / 0.25 = 347k > free die (~299k after macros) so density 0.25 cannot be met there.
Form B (mine): outline 648 x 570.24 -> 648 x 740.88 (+30% north, +170.64 um), cores/W/E windows/N pin x windows unchanged, N-edge sites (clock sink_sites, start_capture, landing xy, reset k3/k4) +170.64; reset local tap [276.48,324.0]->[276.48,326.16] (collided with the regrown tap grid); plus same item env as A (OT_CONS_KIT=1 OT_CONS_UTIL=0.25).
Files: epyc10 /srv/opentallas-scratch2/claude/tl-hdhostw/{plandir/source_plan.json,source_sidecar.json (edited), gen_b.sh, grow.py, rt.py}
Run: intel1 /srv/opentallas-scratch3/claude/tl-hdhostw/gen/hd_host_w, run_kit.sh route 64 16 via ot-run from intel2 (log intel2 ~/tl-hdhostw-run.log, started 2026-11-14 05:00)
BLOCKED 2026-11-14 05:20: see queue line; form B needs plan event.
