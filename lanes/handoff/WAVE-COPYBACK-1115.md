# WAVE-COPYBACK-1115 handoff (Sonnet lane)
Diagnosis: lanes/FABLE-PD-PLACE-0830.md (class A copy-back, class B Tcl global). Branch claude/wave-copyback-1115 (clone intel2:/srv/opentallas-scratch2/claude/wcb1115/repo, blobless sparse).

## Change (tools/autopilot/kit_wave.py, tools/die_plan/landing_placement.tcl)
- A1 ran_ok_host(): host of the last "ot-run: RAN on H ...: exit 0" line; copy_back_hosts(txt, default, hub) puts it first when no copy-back record, after the records otherwise; after_place probes there first and sets res["ran_on"].
- A2 RULES first rule place_rc0_no_odb: stage place + last KW_PLACE_RC=0 (or KW_PLACE_NO_ODB marker) = INFRA, reason never quotes the GRTM banner; free_place_no_odb(): infra_used reset to 0, COPYBACK_FREE_MAX=3 per row.
- A3 reclassify() (runs once per wave-code version in auto_rejudge): a recent (<36 h) false place FAIL becomes RETRY-INFRA uncharged; resume_source() adds the RAN host of the old place.log as a resume candidate so the relaunch resumes from the placed odb (relay), not from synth.
- B landing_placement.tcl: set cland_col_cursor {} after set cland_cursor {}.
- Tests: tools/autopilot/test_kit_wave_copyback.py (7), tools/die_plan/test_cland_col_cursor_init.py (3); test_kit_wave_copyback_host.py assertion follows the new default.

## Live
- B installed 11-15 ~09:1x by copy+mv (backup *.bak-wcb1115) into 23 die-src copies (KV kvgeom6_pgL, S81 src_rel2, HEAD, QC qc-s29-tree2, HBM) on the 6 hosts. Installed before any hold was needed (new gens copy it; kits already generated keep the old copy).
- A: kit_wave.py runs from the hub rt/current (read-only snapshot per main sha): it takes effect when the branch merges to main (MERGE-QUEUE-1) and rt follows.

## False-fail scan (since 00:00 PST 11-15)
scratchpad scan: 42 place FAIL rows with KW_PLACE_RC=0 and a RAN-on host different from the probed one (list in lanes/handoff/WAVE-COPYBACK-1115-scan.tsv).

## Numbers (place attempts that ended RC=0, by place.log, 11-15)
- Since 00:00: 203 finished (RC=0) places, 67 false-failed (33 %). Since 07:10: 58 finished, 42 false-failed (72 %). After the fix: target 0 (the probe finds the odb on the RAN host); measure after merge from the same scan (/tmp/wcb_rate.py on intel2).
- Re-judge dry run (reclassify on the real state, read-only): 17 recent FAIL rows flip to RETRY-INFRA at the next tick after the wave code changes (auto_rejudge); 20 rows older than 36 h (hbm q_*, old QC/S81) are relabelled only. Fable's named rows: hgi_v4 a14 (flip), sle_su_l1 a18 (flip), t17 a28 (superseded by later attempts), kv3_hgi (hgi_v7 a15, hgi_v4 a14 flip).
- Odb on the RAN host (probe): 25 of 42 scan rows still have 3_place.odb there, 17 are gone (old attempts cleaned): see WAVE-COPYBACK-1115-scan.tsv.

## Status
- READY posted with gate stamp (see posts/WAVE-COPYBACK-1115.md). Waiting for MERGE-QUEUE-1.
- After merge: confirm in wave log "KW_KIT_HOST ... 3_place.odb found on" / no "FAIL place" with RC=0, run /tmp/wcb_rate.py, and that RETRY-INFRA rows resumed (KW_RESUME ... start).
