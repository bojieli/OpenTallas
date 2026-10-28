# PG-ACTIVITY-4 (2026-10-27): KV below-M7 re-solve, PSM explicit-load finding, QC .672 and HBM 14-case runs (pending)

Deck: canonical full-die bump-survey deck (150-um bumps, 70-um pads, VDD drop + VSS bounce co-located, <= 35 mV).
Below-M7 split: every M7 node ideal (-source_type FULL with the PG pins on M7), so M7 lateral spreading stays in the
above-M7 deck only (no double count).

## 1. PSM finding (CHECKED by EM currents): set_pdnsim_inst_power ADDS to PSM's own STA instance power
On e1 with sources on M7, the current through the M6-M7 vias (= all injected current) is:
* STA-only (no explicit loads): 0.25961 A = 0.1817 W / 0.7 V.
* Explicit measured loads 0.1168 W: 0.42646 A = (0.1168 + 0.1817) W / 0.7 V, i.e. explicit + STA, not explicit alone.
* Earlier A/B on the same session: explicit = exactly 2.00x internal when the explicit values equal the STA values.
Consequences: (a) every PDNSim run that loads REAL cells with set_pdnsim_inst_power is overcharged by those cells' STA
power: the earlier e1 "explicit" slices (bm7c 12.10, bm7m 11.24 mV) and the QC qc_orig_full rerun (Codex 0.672 W +
coll_ftm STA power). They are conservative, not wrong in sign. (b) The exact load-only answer is superposition
(linear network, same PDN and sources): drop(load) = drop(explicit+STA) - drop(STA-only), per terminal
(tools/pg_activity/pg_colo_superpose.py). (c) Upper-stack window decks load placeholder cells, whose own STA power
is small; their numbers are not re-checked here (UNCHECKED for this effect).
Also: with the e1 kit pins on M5, "-source_type FULL" made the M5 pins ideal (0 A through M5-M6/M6-M7). Below-M7
runs must put the PG pins on M7 (kv_below_m7_m7src.tcl moves the bpins to the M7 straps). QC coll_ftm pins are on M7 (checked).
PSM's internal power ignored the measured activity after setRC (meas and vectorless probes both charged 0.182 W, identical maps).

## 2. KV below-M7, independent re-solve (task 3)
Vehicle kv3_head_eighth_e1 signed 6_final.odb (+spef), no ripup; signed core PDN M1/M2/M5 kept; plan partition straps
added (gen_phys PDN: M6 0.288@4.32 off 1.968, M7 0.288@8.64 off 4.128); PG pins on M7; FULL; PG_CHECK OK both nets.
| load | total W | colocated max | worst cell | VDD / VSS at that cell |
|---|---|---|---|---|
| STA power (PSM internal, = old 6.05 basis) | 0.1817 | 6.095 | clkbuf_7_42__f_g_t_2_u_l8__clk[0] | 2.868 / 3.227 |
| measured activity (superposition, exact) | 0.1168 | 5.479 | clkbuf_7_9__f_g_t_2_u_l8__clk[0] | 2.687 / 2.792 |
The 6.05 mV (ripup + assumed straps + STRAPS sources, 0.182 W) is REPRODUCED within 0.05 mV by a different method
(signed PDN, M7-ideal sources): CHECKED. At measured activity the part is 5.48 mV.
KV total (PG-ACTIVITY-3 edge-fit worst corner LR 25.394 above M7): 25.394 + 6.095 = 31.49 mV PASS (conservative basis);
25.394 + 5.479 = 30.87 mV PASS (measured basis). Both CHECKED.

## 3. QC .672 (task 1): pending
intel2 /srv/opentallas-scratch2/claude/pg-act-3-1027/qc_orig_full (explicit 0.672 W + STA, VDD/VSS separate jobs,
started 17:16, ~2h17). Superposition term launched here: intel2 /srv/opentallas-scratch2/claude/pg-act4-1027/qc_sta_only
(same deck, no explicit loads; started 17:52, ~2h17). Collect:
  python3 tools/pg_activity/pg_colo_slice.py .../qc_orig_full            (conservative upper bound, explicit+STA)
  python3 tools/pg_activity/pg_colo_superpose.py .../qc_orig_full .../qc_sta_only   (exact Codex-load-only)
Verdict = 30.403 (CHECKED above M7) + worst same-cell VDD+VSS <= 35 mV, i.e. the below part must be <= 4.597 mV.
If the conservative number already passes, PASS; otherwise use the superposed number.

## 4. HBM 14 cases (task 2): running
tools/pg_activity/hbm_sm_activity_cases.sh: tb_hgi_sm_e2e patched (hbm_tb_dump_patch.py) so +C0/+C1/+DUMP/+VCD/+DUMPMAX
switch the g_sm[0].u_sm VCD on per case (Verilator 5.050 ignores $dumpoff/$dumpon and a second $dumpfile -- tested --
so one process per case, window = record issue .. min(retire, 4000 cycles), then $finish). One build; a no-dump run
checks all 14 cases (HGI_SM_E2E PASS); 14 dump runs -> act_SM per case, act_SM_mean (cycle-weighted) and act_SM_peak.
Defines = path-hbm-sm kit set minus OT_SMH_GROUP_TRANSPORT / OT_SMH_WEST_SPLIT: the group transport now requires the
production shape (TAGW 16) and the bench SM is RMAX 256 (MODMISSING SMH_GROUP_PRODUCTION_SHAPE_REQUIRED); the
non-group compact transport carries the same registers.
ot-run unit oth-ubuntu-473444-1793147036, intel2 /srv/opentallas-scratch2/claude/pg-act4-1027/hbm (otrun.log ends ALL_DONE).
Next (successor): collect_hbm.sh power step on act/act_SM_peak.txt (+ mean), make_hbm_map.py, canonical-deck PSM;
the HBM 30.4 mV x1.202 stays UNCHECKED until then.
