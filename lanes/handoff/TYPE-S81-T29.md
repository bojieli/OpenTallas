# TYPE-S81-T29 (2026-11-14 00:43 PST)
Target s81/slice_station__t29__cl2e5c855a. Wave a14 (src_pgL, launched 11-14 00:24) runs independently.
Finding: a13 job 22b1d0cfbf46 RSZ-0060 was only caught per hold chunk (5_1_grt.log, "caught per chunk; continuing"); real abort was after GRT finished (1:42 h): write_ref_sdc.tcl missing + python "No module named encodings" in the sealed job = infra tail, not buffering. a13 left 4_cts.odb on epyc7 (attempt_13/gen/...).
Die util is 2% (31.5k um2 in 1.77M), so outline +15% adds no useful room; and gen rejects a per-type outline change (plan invalid: seam port geometry in the die frame) = die-plan change, not a private form.
Form A (private, running/queued): epyc7 /srv/opentallas-scratch2/claude/type-s81-t29/fa/gen/slice_station__t29__cl2e5c855a, a13 kit minus run/, config.mk + GPL_ROUTABILITY_DRIVEN=0, OT_GPL_SPARSE_UTIL=0.05, OT_MAX_BUFFER_PERCENT 400, route goal via ot-run (client log intel2 ~/type-s81-t29-fa.log).
On pass: add AUTO-RESIGN row (s81 / type / epyc7 / .../fa/gen/<type>/run/i* or signoff dir) + RESULT line.
