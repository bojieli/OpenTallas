# ATTN whole-cone predicate partition: upstream registered sideband model

The concrete next candidate moves the **32 existing partial reserved-zero predicates to the registered D2D payload producer**, carries them through the actual payload relay chain, and lands them in ATTN beside the corresponding payload. Request, Q, fault, root acceptance and all published calendars retain their original edges. This is a source-pinned analytical design, **HOLD before RTL**. It has no new timing, equivalence, gate or adoption receipt. Original source ac6af215 still has1294.07ps arrival / TT−569.32ps. Individual reach328.171um passes independently of that timing failure.

This replaces the incomplete scalar-cut proposal in4763bee5d. It is not a claim that a flag sideband alone closes the whole block: the immediate health observer, remaining identity/ready/control cones and upstream producer paths must all fit. ROOT approved this direction for modelling and granted **no combinational-input exception**.

## Actual source and clock ownership

`selected_producer_path.json` records exact selected G7 die SHA18464a8b31042bea03b3fc5779d42803ab7b05bebbaab733a4d83d4a714c1ea6. It instantiates `d2d_kv:qkd_d2d_static`, NL2/NTX3/TXDP50529302, on `n_clk_core_c[0]`. PR is omitted and defaults to1. `selected_d2d_producer.sv` is the exact source from its frozen source tree; its SHA is in `model.json`.

At source lines771–774, the producer already has:

```
wire [547:0] c_rx_payload;
reg [547:0] q_rx_payload;
always @(posedge ck) q_rx_payload <= c_rx_payload;
assign rx_payload = PR ? q_rx_payload : c_rx_payload;
```

The proposed flags use **this exact internal D**, under this exact unconditional capture edge, rather than computing from the public ATTN payload input. No future ready, calendar, authority, expected identity or fault state is needed to compute raw payload-zero predicates. These flags are calculated after D2D reception/decoding; this proposal does not move malformed-link-payload checking to the remote sender.

The selected route is the source output, `__pinfix1`, then `__r1` through `__r10`, then ATTN's existing codec landing. Each of11 relay hops splits the548-bit payload into528+20 real bits; the upper relay currently has16 padding bits. All recorded relay and ATTN clocks are the same `n_clk_core_c[0]`. The D2D reset input is the link-region landed reset; ATTN uses the die-region landed reset. The payload output and payload relays have **no reset**. The new payload predicates must preserve that unconditional, unreset cohort. Resetting predicate flops independently would make them disagree with still-live payload words. ATTN's existing resettable `l_ev` and fault machinery continue to determine observation authority.

This G7 source/path is an actual producer proof, not a GEN8 native receipt. Current GEN8 source, hop list, forwarded phase, first-use and reset ancestry must be checked against it before source integration. A source interface extension invalidates reuse of an old hardened view. D2D's existing wide-macro pin-contact defects are a separate live dependency.

## Complete native frontier ownership

`frontier_ownership.json` maps every endpoint of all three full native frontiers back to the18862-cell original mapped source enumeration. The first516 FF operands are exactly codec `l_pl`; the second frontier consists of36 payload FF,34 expectation/event/codec-fault FF and the previous cut. The final125 non-cut FF operands are:

| Ownership | FF bits | Required treatment |
|---|---:|---|
| Old ctx hold feedback |1|Keep live at capture; never delay as command data |
| Held authority position |11|Keep exact guard state; original +1 already parallel |
| Continuous AFR health |12|8 D faults plus4 real landed C faults; keep live |
| Descriptor producer/guard health |26|Keep same source state and sticky fault equations |
| Controller sticky health |1|Preserve registered CMD/result/ready checks |
| Landed TX-slot health |19|Keep event/expectation/kind/beat cohort and sticky state |
| Result-face/service health |45|Keep result beat, epoch, window and sticky fault state |
| Root readiness |8|7 boot counter bits plus current running bit |
| Root sticky health |2|Keep local/io observation, reset and priority |

All counts include the actual native copies. The four `cprs` C-fault FF directly sample ufk_WS/WN/ES/EN under their existing landed-reset ancestry. They are not constants. Mapping those copies required checking their exact D/CLK/RESETN/SETN equations; no old all-fault exemption was inherited.

Unlike a paid admission pipeline, the chosen sideband candidate **does not shift any of these side operands**. It substitutes only an algebraically equal, original-edge reserved-zero summary for its expensive payload cone. Thus it does not introduce stale feedback, sampled-only health, ready reservations, speculative command state or delayed Q-window observation.

## Exact proposed source sites and equations

1. Add a distinct opt-in producer interface with32 registered output bits. For z=0..15, capture `C[z] = OR(c_rx_payload[32*z+:32] & CM[z])` and `S[z] = OR(c_rx_payload[32*z+:32] & SM[z])` beside `q_rx_payload`. CM[0]=0xfff80000, SM[0]=0xffffffe0, and all other masks are0xffffffff. These are the **existing** CMD data[511:19] and STATUS data[511:5] partitions. No data bit is replaced or assumed zero.
2. Extend the die bundle and every actual payload relay with32 real predicate bits. Every hop preserves the same edge, clock phase and unconditional update as its corresponding payload hop. Use actual32-bit transport; do not add tied placeholder bits or assume old padding is physically free. If cells are co-located into a real depth>=3 delay store instead of distributed wire relays, model ring/SRAM storage rather than a long delay-flop chain.
3. Add32 ATTN input pins with32 direct landing FF, captured every edge under the same unreset data-cohort rule as `codec.l_pl`. This preserves the registered first contact of every public input. Consume the landed C/S bits at the existing `cmd_nonzero/status_nonzero` source sites; no local raw-pin predecode branch is permitted.
4. Keep all header/range/direction/expected-field and timing comparisons at the present observer epoch. `l_ev,l_exp,l_ek,l_ee,l_el,l_eb` remain the34 resettable/event/fault state bits already identified in the second frontier. The expected kind/epoch/layer/beat are captured on the same edge as the incoming payload. They are receiver state and **must not be guessed in D2D**.
5. Preserve `rx_record_bad`, `rx_time_bad`, the two existing registered TX bad bits, `f_r/c_r`, `slot_chk`, guard/producer/service faults and `fault_cause` priority. For each observable edge E, bad(E), fault(E), rx_valid(E), request_valid(E), q_valid(E) and the controller's next sticky state must match the original observer. No additional sampled-only health veto is introduced.
6. Keep root acceptance and all state updates exactly at their original edge. `ctx <= position+1` is selected by the original request_valid&&request_ready; old ctx is its live hold input. Ep/layer/cal/pv_t/end_t/running/start_qk/age/cycles and all local/io fault writes retain their existing priority and reset. No prg/Q delay or calendar recompilation is needed for this candidate.

The raw-mask partition is associative OR and preserves four-state OR values when every flag matches its payload cohort. Full arbitrary-state/reset source equivalence has not been run. The first newly observed record after reset must not consume an uninitialised or differently aged flag. The design must not wait an invented fixed64-edge skew or use a tied initial flag to satisfy that obligation.

One additional source factor belongs in the complete predicate review: under **known asserted** rx_valid&&CMD, the record predicate already establishes data[511:19]==0 and data[18:14]==0. The controller's separate512-bit CMD equality can therefore compare only data[13:0] against `{pos[12:0],1'b1}` under the same enable and at the same registered local_fault write site. This preserves its separate observation edge; it does not move this check into record rejection. The conditional reduction is a two-state identity until X/Z/unknown-enable proof is supplied. Do not silently retain a second wide comparator when assessing the full cone, or silently claim its removal has been qualified. No such reduction has been implemented by this packet.

There is also an optional **two-state predicate specialization**, separately HOLD: actual KV_SIDE=1 permits RX CMD/Q only. STATUS/RESULT always fail direction, so their payload-zero test can be removed after proving the combined predicate. For CMD, reserved data[511:19]==0 and position data[18:1]<8192 combine to data[511:14]==0. This can reduce the sideband to16 groups. Preserve the exact generic32-bit version first; X/Z propagation, source parameter binding and causal mutants must qualify specialization before taking its area credit. In particular, do **not** absorb the controller's separate CMD data equality against held `pos`/enable into `record_fault`: that check sets registered local_fault, and earlier request suppression changes the original trace.

## Cost and complete schedule

The explicit generic architecture adds32 producer FF +352 relay FF +32 receiver FF = **416 plain FF /416 clock pins /121.3056um² master-box area floor**. It adds32 D2D output pins and32 ATTN input pins, and32 bits/edge on each relay segment, a5.8394% extension to the548-bit payload bus. There are no MACs, memory accesses or new external link payload bits. This count includes the entire selected path, rather than just the32 predicate FF. No FF area is deducted from the old source before exact synthesis establishes what becomes dead.

The producer has32 new <=32-input reductions. Each payload bit drives its original data D and at most one CMD and one STATUS predicate leaf in the proposed source; the full all-driver census must still check upstream ancestry, BUF/INV-transparent fanout and any required kept copies. Receiver reduction is at most16 flags per zero predicate, with real header/range/identity/health logic still present. Old placement RC, lib delay, slew, TT/FF spread and PG facts do not transfer to new cells or widened faces. Combinational area, capacitance, reset/control copies, clock tree, wire power, pin-face geometry and total area remain NULL; this prevents build admission. The old1294.07ps path remains the only measured path.

| Source event / consumer | Candidate edge change |
|---|---:|
| D2D decoded payload launch / every existing payload hop |0|
| Codec landing, expected fields, immediate bad/fault/cause |0|
| Request valid/ready, root accept, ctx/ep/layer/cal/targets |0|
| start_qk, running, age0, cycles |0|
| Every Q valid/beat/data and exact root Q window |0|
| CAL_PIPE cp_pv/cp_last/cp_cal and moved-calendar fault |0|
| start_pv, PV/compute/fin/result-face consumer slots |0|
| prg launch and ahs/pvst/pvfst/acal/arh outputs |0|
| Controller result_reserved/expected beat/identity/done |0|
| RESULT0..31, idle+32, STATUS+33 and existing TX launch |0|
| Continuous health, STATUS veto, host retirement/admission |0|

The exact current source driver in `selected_driver.svh` issues once at A[k]−8, runs once at A[k], sends one CMD at its compiled rxcmd, and sends32 Q records on the following32 slots. Exact staged programmes contain **u1:1 admission; u4cal:8 admissions; u4pack:4 admissions**, with the real run offsets recorded in `model.json`. This candidate adds0 edges to each. These are component programmes, not proof of32 actual admissions per full token. Full-token admission count, final MU occupancy and production throughput remain unmeasured; do not label u4cal's8 work items as8 users. A two-stage fallback would add2/16/8 work edges to these programmes, but its health/ready/Q-window contract remains unapproved and its MU wall-time is not the sum of those work edges.

## Why the paid scalar alternative stays rejected

Registering only c2168/c2343 and carrying217 metadata bits does not cover70/125 other operands. A complete command pipeline must separate live state from write intent, move every Q/programme/calendar/result observation coherently, reserve static admission slots, and retain immediate health. Keeping an unmodified source-time observer retains the unsafe original validation/state cone; delaying that observer changes first fault, fault-cause priority, root Q-window and retirement timing. Neither a hidden observer nor a delayed fault contract is an admitted repair. The upstream sideband is preferable because it resolves the wide predicate before the receiver's critical epoch while retaining the actual receiving D2D word and all current receiver state.

Next source admission requires a **single complete producer+bundle+receiver model** on the current generated die, actual sideband clock/phase/reset/first-use proof and all-driver/capacitance/face/area prices. After that review, the source owner must prove malformed CMD/STATUS/high-bit/epoch/beat/direction/timing rejection, wrong-mask/wrong-flag/wrong-relay-age/reset controls, and full immediate fault/ready/root/Q/TX/STATUS behavior. New source and physical qualification are required together; no existing failing log or native view is overwritten.

Reproduce the small read-only ledger with `python3 model.py` from this directory. It checks the exact selected source and programme inventory and regenerates model/ownership JSON; it does not simulate hardware or invoke EDA.
