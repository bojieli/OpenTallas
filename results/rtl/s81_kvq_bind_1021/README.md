# S81 production KV source integration (2026-10-21)

This is a default-off source candidate, not an adopted token implementation or
physical closure. It connects the existing production D512 KV arithmetic to a
real slice VM extension, rather than substituting new normalization arithmetic.
The selected source overlay enables one bank at s_3N leaf0 and selects existing
XRT typed-V/local RD transport in normal slice parents. Changed parents have no
aliased closed view.

The bank retains four KVT quarters,64 KVE (last8 RoPE),four NE16 QNH,one
NE4/NV1/D512 QNR and16 KVQ at LM5/LA4, with the existing ERL3 links. The bridge
issues74 VM pair reads for five parameter rows plus512 FP32 operands (GK66).
Twenty-five distinct512b result addresses produce26 write events:16 BF16-y,
eight code rows andtwo masked exponent fragments at one address. The previous
73-row interpretation was incorrect for this actual source. Every event is
retained independently in16 SRAM banks (144 actual32x64 macros) and drained in
104 fixed edges /52 VM pair writes at the compiler's explicit DRAIN_AGE.

Opcode15 uses a0=parameter128b-rowbase, a1=operand128b-rowbase, n=32;
imm[3:0]=kind1 or7,[5:4]=gainset,[13:6]=jobid,[31:16]=DRAIN_AGE. Bounds,
alignment, shape, output-event counts and complete-input-before-output are
checked. For the proposed scratch region, KV parameters672..691 and operands
692..819 are consumed before outputs672..771; descriptor obase=168 in512b rows.

MODEL.json and TRANSPORT.json under tools/s81_dv/kv_bank_1021 price the counts,
port widths, SRAM area and existing measured transport ages. Existing arithmetic
reference outlines total2.188mm2 before the reducers/relay/clock overhead; SRAM
adds0.0797mm2. Exact bank slot/native/clock qualification is still required before
any physical gate or adoption. Actual configured DENSE2 CAP producer programs,
aligned frame ownership, TP4 KV128 exchange, dispatch and service output carriage
remain explicit integration obligations, owned with the token lowerer.

Checks so far: actual G8 overlay smoke enables exactlys_3N, KV_ENABLE1, no view;
fleet Yosys source syntax passes with transport off and on atf33994055. Existing
XRT source and its upstream census/positive/mutant evidence are pinned in the
transport receipt. A minimal actual D512 bank+bridge versus existing SU golden
bench is live on gold2 at run_8efb2ce9b (source8efb2ce9b); it also exercises a VM
consumer dropping exponent writes as an expected failure. That source is before
the normal-slice selector and added alignment/bounds guards; those later changes
are not yet claimed as end-to-end validated. No physical gate was launched.

## First measured functional result

Source8efb2ce9b actual D512 bank+bridge PASS (gold2unit2269851-1792602287):26events,
52VM pair writes, zero mismatches/faults; first result1421 versus last input read1232,
a189-edge lifetime separation. FixedDRAIN_AGE1024 plus104 drain edges worked. The
negative VM consumer dropping exponent writes failed with8 mismatched32-bit words;
this is an observation-path negative, not a claimed arithmetic RTL mutant.
Exact source hashes/argv and original logs are committed in kv_8ef_*.

Current-source follow-up286841a83 is live at
`ot-gold2:/srv/opentallas-scratch/claude/codex-s81-kvq-current-1021/run_286841a83`,
unit2331998-1792603162/session4772. It preserves/reuses the completed object cache
and adds current address guards plus fixed job/result age reporting. No live
older source or result was edited. The native row-invalid controls are additional
checks for the new guards; this remains one minimal KV bank vehicle.
