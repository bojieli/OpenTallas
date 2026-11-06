QC EAST SU_c actual failure and measured tap-density candidate, 2026-11-06.
Candidate only; no POR, source-window, uncertainty or clock insertion changes.

Actual APf6a8a1576762 attempt2 spilled E5->Intel2 localhost, unit
oth-ubuntu-317305-1793972067, terminal exit4. LECexit0. Actual retained
4CTS FF overlay replay at Intel2 unit oth-ubuntu-2810285-1793977854 matches
-410.1634049ps /7425 aggregate endpoints. Worst crh1.q[87]->crh2.q[87]
is inverter-only soft-register data47.668ps, clk_t11->clk_t8; local insertion
209.420->509.740ps (300.320ps difference) plus declared120ps source window.
25ps uncertainty and12.512ps hold explain -410.164ps. Capture tap8 actual5518
sinks; tap11 2164, both over1200cap. This is same logical-clock paired-relay
skew, not early-core timing or a forwarded ring CDC/write failure.

Explicit actual FF census retained Intel2:
/srv/opentallas-scratch2/claude/codex-qc-tapsplit-east-1106/{probe.log,
worst16_ff.rpt,negative_paths.tsv,east_sinks.txt}. 7241 localclk->clk rows,
183clk->vclk and2vclk->clk. Aggregate STA count7425 and explicit7426 negative
rows kept distinct. Worst secondary reset-removal -72.634ps; no blanket
clock/timing relaxation follows from those paths.

Measured native east3_place inventory:38141soft clock sinks; one actual hard
RED root pin excluded from soft modeling. All9 actual macro bboxes match this
selected type including declared12nm track phase and RED physical_inst alias.
The west profile was not copied. Thirty-two old taps ->81 proposed taps,
actual-point modeled max cap load5531->1134, reach484.104->197.624um.
Existing1200cap/200umradius and120ps source window unchanged.

clock_patch.json is a complete-clock replacement only for this exact hashed
base type; apply_event.py refuses any changed type and changes nothing else.
Review and re-compose against current approved parent/native/reset/START/
clock-provider profile before adoption. New clock ports may change reset or
bootstrap bookkeeping; data cycles0 is not a bootstrap-cycle claim.

Actual tap_split_geometry.png viewed PASS-COND: legal existing macro channels,
all81 candidate taps outside macro bodies, exact placed inventory captured.
No CTS, PG, route, parent/native or hold sign-off credit. Literal crh/crl/twl/twh
per-bit paired-relay affinity is a separate default-off conservative B form;
it must satisfy exact clock identity, reach/load and no-new-boundary checks.

Separately tracked SLE FE source7305 TT forwarded capture miss -15.14ps:
x_su_l0_sc_i[38] input arrival513.92, falling capture508.85, setup10.07,
required498.78. This is distinct from local positive-register tap affinity;
FF policy was NOT RUN. START repair and forwarded-clock/data interface geometry
owner must retain this secondary TT gate; no FF label or localtap waiver.
