# KV commensurate PG candidate, 2026-10-27 13:51 takeover

This is an experiment and has no plan-adoption authority. KV plan/clock owner
requested the candidate under COORD 13:05: keep the actual 319.68um mesh lattice
and choose a PG pitch that divides it, with clock columns centred in PG gaps.

`tools/pg_activity/kv_commensurate.py` calls the unchanged canonical
BUMP-SURVEY/HEAD-5 `window_kit` source, copied to the runtime `src/` below.
It preserves the exact global stripe phase and first supply net when converting
the global candidate to the cropped window. Max-pitch crop snapping alone would
shift M8 by1.08um for the39.96/4.32 pair. Five net-labelled global-location
controls pass; crop-reset and wrong-first-net mutants are caught.

Candidate: M8 0.48@4.32 offset2.16; M9 12.96@39.96 offset13.77.
Fixed clock x=583.2+319.68k is exactly midway between alternate M9 supply
straps, leaving3.51um IDEAL centre-to-PG-edge. Actual validated driver axes differ by up to0.68um, giving a conservative2.83um lower bound; only the KV owner full-tree dry result can qualify those shapes. `pg_clock_phase.png` was viewed:
straight-column clearance is plausible; full H-tree/mesh dry validation remains
with the KV owner. No routing or STA was launched by this experiment.

Runtime on intel2:
`/srv/opentallas-scratch2/claude/codex-sta-pg-1351/kv_c39_w13`.
Canonical150um bumps/70um pads, actual q5b source plan99b9d6dd, measured type
map, same4761 load tiles, both VDD and VSS. Exact snapped window and source
hashes are in `c39_w13_input.json`. Final interpretation must use co-located
VDD drop+VSS bounce and include below-M7 allowance; individual net maxima or
process exit0 alone are insufficient. Inherited below-M7 full-power6.05mV is
conservative and is explicitly a reused result, not a new measurement.

No result was available at this initial source checkpoint. Raw failed results
are retained. Existing PG-ACT2 L8 light-M8 candidate was collected: same-load
drop+bounce42.868mV +6.05 below =48.918mV FAIL (independent number review
outstanding); therefore this candidate retains the stronger4.32um M8 pitch.

TERMINAL: nativeEXIT0/1558.25s/peak22122284KiB, CHECKEDFAIL44.546mVco-located +6.05below=50.596mV. Independent review attached; original unreviewed result.json preserved. Native sourcepads400/70um, bothPGchecksPASS,4761matchedloads. Worstbottomrow/source-localy gap91.323um and exclusion-onlydiagnostic inedge_diagnosis.json; NOedgewaiver/no secondsolve. Whole-diePG NOTRUN: currentnativePHY/glue provider remainsblocked. RerunRVToroldanalogmodelnotadopted. H8/L8 activity leftovers collected and steady-state1.0156758 scaling supplied separately.
