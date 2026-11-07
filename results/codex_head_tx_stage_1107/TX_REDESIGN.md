# HEAD TX encoder: routed review and next RTL form

Reviewed kit: intel1:/srv/opentallas-scratch2/claude/dh77serdes/tx/ot_s81hd_sc_tx_vB/eco_dh77/i2.
Actual final placement, clocks and congestion images were viewed at
`/tmp/codex-head-tx-review-1107/{placement,clocks,congestion}.webp`.
The third late ECO `eco_dh80` remains stopped. No new build or source edit.

GEOMETRY: this is a compact486×120.96um standard-cell encoder, no macros or
narrow macro channels. Logic fills most of the useful rectangle. The central
and southern area has the highest routing heat, but routed DRC is0 and the
four remaining failing nets do not establish a global congestion problem.
Native related-pair skew is62.99psTT/60.07psFF, below80ps. No clock redesign
is justified by the remaining slew failures. SMELLS:5, long shared driver
reach despite fanout4. Data and control are distinct families.

Measured native nets (TT9pins/FF8pins total):

| Family | Net / driver | Loads | Measured geometry | TT worst slew |
|---|---|---:|---|---:|
| Control | net11430 / wire11431 BUFx16f |4f0vD|driver227.286,24.3 → captures350.8..359.4,54.8..62.1; up to170um Manhattan|346.08ps|
| Data | net11358 / wire11359 BUFx16f |4cq[r][128]D|driver119.448,22.95; capture span72.576×43.47um|337.79ps|
| Data | net11343 / wire11344 BUFx16f |4cq[r][98]D|driver122.472,17.28; capture span57.456×44.28um|332.94ps|
| Data | net11416 / wire11417 BUFx16f |4cq[r][113]D|driver122.796,27.0; capture span59.022×44.28um|332.02ps|

Native SPEF cap totals respectively33.7442,31.6688,32.3421,34.4596fF
(`*C_UNIT1PF`). These explain why a fanout bound alone did not prevent the miss.
The control net is f0[4]DFF at214.002,22.41 → reset NOR2x1 at215.568,22.14
→ BUFx3 at227.07,23.49 → final BUFx16f. The data nets are the shared
10-way chunk-select mux OR5 outputs `ch_n[128/98/113]` aroundx120,y9..22,
then BUFx3/BUFx16f, then the four kept parity input copies.

Source: kit `rtl/ot_s81_kp4_enc_la.sv`, module `ot_s81_kp4_enc_la`, LA2/FF1.
`g_ff.cq[0:3]` currently all capture common `ch_n` in one edge. `g_la2.f0v[3:0]`
all capture f0[4] through one shared reset gate. The flop copies do not give
their D cones independent local drive.

REDESIGN recommendation: an opt-in extra chunk stage, not a fourth late ECO.
Add one kept520b `ch_mid` bank between `ch_n` and existing `cq[0:3]`.
The shared OR5 now drives one D; `ch_mid`Q drives four local D pins. Home this
new boundary between the current mux and capture banks and review its actual
placement. The target is to split the existing~100–170um loaded hops into
segments around60–85um, with fanout≤4. A kept hierarchy boundary must prevent
the new state being optimized away. The control companion is a kept four-copy
`f0_mid/fv_mid` stage before the existing f0v/fv capture, so control and data
both advance one edge. Do not both add that explicit stage and increment its
input flag tap index.

Concrete LA2/FF1 schedule changes for that explicit-midstage implementation:

1. `ch_mid <= ch_n`; existing `cq[r] <= ch_mid`.
2. `f0_mid <= {4{f0[4]}}`, `fv_mid <= {4{fe[4]}}`; existing f0v/fv capture
   the mid banks. Keep current f0/fe input indices4. LA1-only f0w stays unchanged.
3. Extend f9 by one state and advance parity capture condition f9[5]→f9[6].
4. Add beat-delay d8; LA2/FF1 output data uses oa=d8,ob=d7 instead ofd7,d6.
5. Extend so throughso[7]; sw tapso[5]→so[6], o_v/p_v start tapso[6]→so[7].
6. Delay the output header h0s by one edge for wsrc[0]. Keep the input-side
   chunk-header h0s unchanged. This prevents the next frame's header overtaking
   its delayed payload at the ten-beat frame boundary.
7. Declare p_d/p_v +1PINcycle, unchanged one-beat-per-cycle sustained throughput.
   For a uniform output contract, delay exported fault by one edge too while
   keeping the internal sticky fault state unchanged. Confirm reset behavior
   explicitly in the bench. No parent plan or compiler contract is changed yet.

PIN CYCLES: proposed TX PMA data/valid +1 (existing9edges→10edges), fault+1 if
the uniform output contract is selected. Header, payload, parity, frame phase
and valid must move together; adding only a payload register is incorrect.

The current four f0v/fv copies each control75remainder bits. A later conservative
variant should further replicate the complete local flag pipeline to≤8rem bits
per flag, rather than creating a new shared38-load D net. That is additional
RTL work, not a reason to claim the targeted stage form is already safe.

Smallest proof vehicle: one full-width encoder, not the SerDes parent. Compare
old LA2/FF1 with the new opt-in form; p_v and exported fault match old delayed
one edge, p_d matches when valid. Send continuous10beat frames, randomized512b
input words, reset/restart, missing-beat fault cases and enough frames to cross
the sequence wrap. Check one output per input cycle after warm-up. Mutants:
omit f0_mid delay, omit fv_mid delay, use old f9 tap, omit output-header delay,
omit output valid delay and flip a parity bit. Existing reference bench is
`rtl/hbm_accel/cores_split/reform_1104b/tb_kp4_enc_la.sv`.

This is a recommendation only. New RTL, proof, estimate and one PLACE pilot
are required before route. Existing DO_NOT_COUNT and stopped-ECO status remain.
