# L74 static two-beat component gate

PASS at production widths: NW3749/1875DATA+33CTL and NE2709/1875DATA+26CTL.
Exact native layout/masks are retained in native_layout.json. For each,134
complete words and268 cycle checks preserve every DATA and correlated CTL
bit at the compiled edge. All four high-half,stale-low,phase and held-valid
mutants fail. Wrong-slot DATA or CTL events produce a sticky fault and
suppress consumer event bits. NE duplicate corruption raises RX fault.

Source: rtl/hbm_accel/generic/transport/ot_hbm_static_2beat.sv.
One boot-only aligned start broadcast establishes a static two-cycle phase at both
endpoints before first HC root configuration. Repeated start raises sticky
fault and is ignored for phase; per-token launch must not be used. Before
start payload may be unknown, RX DATA/SIDE event bits are0, and startup
warmup rejects uninitialized channel beats. Accept words only on slot0; every event/valid bit in CONTROL_MASK
and SIDE_CONTROL_MASK must be0 on slot1. Payload may vary there. RX emits
one-cycle event pulses on completion, never repeats a held valid. DATA
and correlated CTL traverse the same number of registered channel stages.

NW has one spare high-beat bit, used for sticky phase fault. NE has1040
additional spare high-beat slots: TX fills them with registered copies of
the low payload and RX checks them. Each physical pin is functional in
both phases; no constant padding. The duplicate comparator costs1040XOR
plus balanced OR (up to11 OR levels); physical timing is NOT QUALIFIED.
Duplicate/phase fault is visible at the normal complete-word edge with no
extra data cycles. Payload flops have no reset; only phase/valid/fault
control resets synchronously. No ready,credit,queue or runtime reschedule.

Stage ownership was measured with actual external producer/consumer flops:
with three channel stations, the wide two-boundary-flop baseline captures
at consumer age6; the three-stage two-beat endpoint captures at age7.
Thus the old plan budget5=2boundary+3stations becomes6 at the endpoint,
plus the consumer's own capture edge: exactly+1 first-word edge, II2.
Use LINK_STAGES=plan_cycles-2, not the full plan budget. RX phase is
LINK_STAGES mod2 and startup warmup suppresses pre-initialization beats.
Odd/even channel depths3/4 both pass; TX-sample-to-RX-publication ages5/6.

The analytical sizing/cost contract precedes the implementation in
model.json: NW9439 endpoint payload FF including CTL, NE7345, plus small
phase/fault control. Existing channel stations are counted separately.
N consecutive logical words require2N-1 launch cycles versus N at II1:
price the N-1 exposed stream cycles and one extra first-word edge. A
sustained2180-bit TKM flit each cycle cannot cross1875w without stretching
the producer calendar to II2. Blanket+1 per operation is insufficient.

OPEN INTEGRATION: native emitter/consumer wiring; static producer period2
windows on every DATA/CTL event source; CTL pad-to-DATA latency and stage
ownership; all new cycles in token compiler/model; geometry review and
physical sign-off of the serializer/duplicate comparator. This component
PASS is not a native die token PASS or physical closure. The native lane
owns those composition steps. The initial bench scoreboard checked the
word one cycle late; corrected before this gate, raw FAIL retained in the
remote out directory. Successor gates use out_r5/layout, never overwrite it.

Run directory epyc3:/srv/opentallas-scratch/claude/codex-hbm-2beat-1025.
Generic suite run.sh; exact-layout and external-age gate run_layout.py.
