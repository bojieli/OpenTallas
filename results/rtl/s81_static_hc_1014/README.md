Static HC source component, 2026-10-14

This opt-in source mechanism reduces four absolute-rank FP32 records in the
legacy engine's exact order: `RN(RN(p0+p1)+RN(p2+p3))`. It supplies 16 scalar
lanes, each containing three existing `ot_s81ph_fp32_add_rne_preexp` adders with
`SPLIT=7, KS=1`. No legacy collective slab selects this source.

`reduce.slot` is a compiler reservation. All four rank valids must be present
on that edge. A missing rank faults and produces no output; an unsolicited
rank valid also faults. The upstream gather must already have checked actual
rank identities, tags, sequences and last flags. The reducer delays its
companion `{tag,seq,last}` alongside the arithmetic; no ready, credit, FIFO,
retry or dynamic arbitration exists.

The reducer contains 18 register stages. Input sampled at edge t appears at
the word output after edge t+17. An assembler connected directly to these
flops captures that result on edge t+18. The compiler reserves a pack write
edge and word index explicitly, followed by a separate emit edge; earliest
complete-row emit is t+19 for the row's last source word. Every other word
has to have been captured already. This distinction between register count
and sampled-edge difference is intentional and asserted in the bench.

The assembler contains one 16x512-bit assembly register and one 8192-bit
output register. A complete bitmap, matching tag, and separate emit slot are
required for emission. Missing/unsolicited/duplicate/error words, mixed tags,
partial emits, wrong emit tags, and write/emit overlaps fault. Compiler emit
clears the assembly bitmap even on a failed transaction, so a bad scheduled
row cannot cause a variable wait. The HC receiver must capture exactly on
`row_valid`; static clock-domain and destination pin bindings remain open.

Reproduce with `python3 tools/s81_static_hc/preflight.py` and
`python3 tools/s81_static_hc/check.py`. The unified analytical preflight is
`tools/uarch_model.py:s81_static_hc_source_model`. It fixes 48 FP32 adders,
256 input bytes and 64 output bytes per record. The existing FMT1 cadence is
4/4/8 cycles, so the source mechanism needs 48 input bytes/cycle and 12
output bytes/cycle on average. No new PHY format or bandwidth is assumed.
The bench uses 320 source records (the D5120 cardinality), producing 20 HC
rows, then 512 consecutive records to stress II=1 and arithmetic error
propagation. This verifies mechanism capacity; it does not prove a native
HC production trace, the six-value/rank HC gather, or layer throughput.

`verdict.json` records source hashes, baseline exactness, and two actual
synthesizable RTL mutants: change the arithmetic tree and change the row's
word destination index. Both must be killed by the golden bench. The
assembler's separate fixed-slot fault suite must pass. The word oracle is
`ot_fp32_rne_pkg::fp32_add_rne`, composed in the legacy pairwise order,
including canonical positive zero, gradual underflow, nonfinite rejection
and overflow errors from either inner addition.

Status: SOURCE COMPONENT ONLY. Outline, slot/pin faces, area/tracks, SS/FF
closure, insertion, clock epoch, physical transport flight, real source
reservations, HC consumer schedule and whole-layer price composition are
unqualified. No route was submitted, and no existing performance claim or
qualified collective view is replaced by this evidence.
