# S81 BF tag distribution and core/station continuation, 2026-10-29

BF G2 V1 is NOT SIGNED. Its CTS critical path is the shared BF16 tag line
`g_bf.g_fqt.u_bf.u_pt...line[102]` to lane 11 `acc_r[26]`: data arrival
863.13 ps, required 752.74 ps, slack -110.39 ps at TT. About 650 ps is in
an 11-buffer distribution ladder, followed by four small accumulator control
gates. A separate FF GRT incremental repair creates net15370 and fails
GRT-0183 after the initial route has zero overflow. The placed image was viewed:
the two ROMs occupy the left side, with a narrow horizontal throat between them.
No new physical build is authorized by this packet.

`TAG_GROUPS=0` retains the original source. The opt-in `TAG_GROUPS=4` or `16`
replaces the one final tag-delay stage with four or sixteen independent copies
on the **same original clock**, distributed to groups of four lanes or single
lanes. The shared prefix has D-1 stages. The total delay remains D; no cycles,
ports, reset semantics, arithmetic or clock edges change. The source generator
also forwards this optional parameter for newly generated column RTL.

The existing `ot_v41_kreg` hierarchy is required: a first experiment with kept
reg variables was merged by Yosys, retaining only 104 bits. This failed control
is recorded here; it was not accepted as a physical fix. Current synthesis
retains all four/sixteen register instances. At production tag width 13 and delay
8, the register totals are 143/299 bits versus 104 original: +39/+195 FF, or
0.072%/0.362% of the V1's 53,852 clock sinks. This is a small cost estimate,
not timing closure. Tag-driven load per final driver falls by 4x/16x; actual
placement, local fanout and routed TT/FF remain required before adoption.

Checks: source lockstep PASS for 8,192 cycles on W13/D8 and W8/D5, both group
counts and all sixteen lanes, with gated-clock pauses and repeated reset.
The wrong-final-stage mutant is caught. Yosys post-optimization hierarchy
count confirms 4/16 independent final-stage registers and 143/299 state bits.
`good.log`, `mutant.log`, `synth4.log`, `synth16.log` retain evidence. The tests
exercise the actual helper source in `ot_v41_bf16_lanes3.sv`.

Run: intel2:/srv/opentallas-scratch2/claude/codex-s81-ce12-tag-1029,
ot-run unit oth-ubuntu-2211290-1793288077 (terminal PASS). The inherited
ce10-lecrb64-bf and ce10-lecrb64-rom jobs remain untouched and are distinct
full-column/ROM reset-contract LECs.
