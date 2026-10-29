DIE-HEAD-26 2026-10-29 07:25 PDT: HEAD die clock duty fix + HEAD stage refit + spread OCV/droop add-on (plan hk4 RX/TX, 327 regions)
via the ONE die clock tool: tools/clk/ot_clk.py kit tools/clk/configs/head_hk4.yaml (run dir intel2 /srv/opentallas-scratch2/claude/die-head-26/clk,
run.sh = kit -> combo GRT0 TT+FF (DIE-HEAD-25 grt.sh recipe) -> duty.py -> spread.py).  All numbers CHECKED own (logs/json here).

ESTIMATE (12.14b) before build: DIE-HEAD-25 l1 (inv2 pairs, rep 250) fall-rise grows ~0.3-0.7 ps/stage (TT/FF), 154 stages max.
A "shallower feed" cannot fix that: the far tile corner is ~13.3 mm Manhattan from root sp3, so even a direct path is >=8 inv2
stages/mm x 13.3 = ~106 stages -> FF fall-rise ~65-80 ps > 39.5 ps (55 % at x1.055).  Root cause is the stage form: an inv2 pair is
an UNEQUAL pair (inv 1 drives inv 2 at ~0 um, inv 2 drives the 250 um leg), so the per-pair (tpHL-tpLH) difference does not cancel
and adds up along the path.  Equal single-inverter stages (each CKINVDCx16 drives one equal leg) cancel edge by edge (KV form,
duty 47-53 % on KV).  -> V1 built as a config-only stack change (inv, rep 150), not a feed change.

variant  stack/rep  stage model          cells  stages med/max  duty out 45-55 TT/FF  fall-rise max TT/FF  spread x1.05 TT/FF  GRT0 ov TT/FF
l1 (25)  inv2/250   inv2_ndr_qc_trial24  5472   68/154          88 / 226              49.5 / 98.7          128.5 / 119.7       0 / 0
i250     inv/250    inv_ndr_kv21_treeb   -      54/116          142 / 208             65.9 / 94.2          179.0 / 153.6 FAIL  0 / 0
i150     inv/150    inv_ndr_kv21_treeb   -      86/210          0 / 0                 11.4 / 9.3           96.9 / 91.5         0 / 0
i150r    inv/150    inv_ndr_head26_i150  5825   (see duty)      0 / 0                 11.6 / 9.8           100.0 / 82.3        0 / 0   <- config of record

(i250: a single inverter driving 250 um has rise/fall slew asymmetry -> unequal again; 150 um is the equal-stage form.)
HEAD REFIT (ot_clk refit on i150 routed legs): inv_ndr_head26_i150, 1143 legs, rms TT 6.35 / FF 5.70 ps (kv21 model on the same legs
8.20 / 8.47) -> tools/clk/stage_registry.json entry + inv_stage_cal_head26_i150.json.  QC's inv2 model is no longer used on HEAD.
i150r (built on the HEAD entry): duty TT 48.6-51.5 %, FF 48.0-51.2 %, MPW est fail 0, odd-parity taps 0, max tap slew 22.9 TT / 18.8 FF,
insertion TT 672-8279 / FF 589-7317 ps (CA unshared clock = HEAD-006, not this gate).  GRT0 incl clock 50 it overflow 0 TT+FF, usage 0.42 %.
ot_clk replay of head_hk4.yaml -> IDENTICAL to kit_i150r.  test_ot_clk 44/45 (QC fixture absent in sparse WT, as DIE-HEAD-25).

SPREAD incl OCV + droop (12.15c), spread_ocv.py (spread_ocv_i150r.json): per region every ordered tap pair, nominal = OpenSTA late x
SPICE_CLOCK_CAL_INV (0.9324/0.9380, the inverter factor of die_sta_related), + clk_aocv.branch_pessimism (approved g021 table, class
Ainv, branches below the cell-level last common node, distance = bbox diagonal), core latency not included (die tap spread).
  shared droop (same region -> 0):   worst TT 107.0 / FF 89.5 ps (sp1), 0/50 multi-tap regions >150
  stated droop bound (+droop always): TT 118.9 / FF 98.4;  with the x1.0485/1.0552 BUF factor instead: TT 129.9 / FF 107.6 -> PASS any way.
=> 12.17(1) clock check on hk4: GRT0 incl clock PASS + spread incl OCV/droop PASS + duty 45-55 PASS + MPW PASS + slew PASS.
