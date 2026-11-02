# Native GO/TAG retime mechanism; architectural oracle unresolved

**Superseding correction:** this packet establishes the measured producer and
retime mechanics. It does **not** establish a native architectural tag bug.
f85fce6c4's claimed expected sequence0/1 was the CFG7 port's pre-increment
sequence, not a proven architectural CAP/return oracle. Existing
`frame_return_plan.py` explicitly sets OPTAG=1 for its first bench operation,
and CFG7 documents a counter advancing from0 on each broadcast. Original
GB0 with its direct tag path may therefore intentionally consume1/2, exactly
as current GB1/advance1 does. The proposed four-FF retime remains disabled;
source/cohort/physical adoption is on HOLD until original directGB0 and the
actual capture/return contract resolve that authority.

No measured sample or native log has changed. The original check, including
its erroneous architectural interpretation, is retained verbatim in
check_preincrement_hypothesis_ORIGINAL.json. Current check.json supersedes
its interpretation; cases.json retains the old preincrement-hypothesis status
alongside an explicit unqualified native-semantic status. No provider,
capture-fold, source-cohort or physical qualification is granted.

The executable source cut is actual XRT target2 CTL decoding, actual XS4,
current41-stage1104-bit input, CRS4(E2/LFACE0/LGATE0), actual station/relays,
actual CFG7 with current0L01/C0 masks, actual two-stage qbank_S GO, and the
unchanged extracted GB/RSTP capture logic. The real XRT producer matches all
booked issuer words/dates with its3-edge local stage. No direct is_v/is_d
oracle or under_TEST guard drives the producer.

At833ps, current advance1 emits CFG7 GO at760/1272 with port tags0/1;
qbank GO is762/1274 while the direct tag is1/2; GB capture is763/1275 with1/2.
A counterfactual parallel two-edge tag pipe instead captures0/1 at the same
dates. The reference in this experiment is GB0 **with that proposed tag
retime**, not unmodified original directGB0. That distinction invalidates the
original native-bug assertion. All50 CFG words and160 XS stream words/dates
are identical across the five experiments, and all observed faults are0.
The date/tag mutations are detected against the preincrement hypothesis;
they do not by themselves establish the architecture's intended first tag.

Passing Epyc2 unit3270885-1793604621 exited0. native_run_receipt.json and all
five original logs are retained. Two source-intake failures (wrong wrapper
port and incomplete readset) were corrected without model/guard overrides.
No native rerun was performed for this status correction.

The DISABLED mechanism delta is precisely two2-bit pipeline registers:
4 reset-free FF,4 clock pin loads,0 reset pin loads,2 tag-path edges, and
0 additional GO/CFG/XS/issuer/data edges. It is a counterfactual source event,
not an adopted repair. The two-FF GO-latched hold is a separate conditional
512-spacing idea; no legal native Q-bank cadence is inferred from it.

The exact unapplied diff specializes only fW0_p1_b0/e0. The shared original
type has five replicas, so a type-wide patch would add20 FF rather than4.
Other four replicas remain untouched. Any broader change requires actual
per-path identity/depth and architectural tag authority; a uniform864-pair
cost3456 is conditional arithmetic only. No canonical RTL, plan or active
cohort is changed by this packet.

This is a producer/GO-tag boundary cut with controlled EF idle/free and a
controlled common-phase/L3 forwarded-clock startup. Arithmetic Q cores and
real walking/bank_free/sh_free feedback are absent. Calendar spacing512,
regional startup, legal bank cadence, full frame/token, capture folds and
production epochs remain unqualified. Experiment dates are not production
epoch assignments. Smallest full-NB2-pair preparation will use real feedback,
checkpoint row/data gold, and original directGB0 to resolve the tag oracle.

Full original logs/images/binary remain at
`epyc2:/srv/opentallas-scratch2/claude/codex-ds-native-go-2310/retry3`.
Private disabled generated source remains at
`intel1:/srv/opentallas-scratch2/claude/codex-ds-native-go-2310/candidate_part_DISABLED.sv`.
