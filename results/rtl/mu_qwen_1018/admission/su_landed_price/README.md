# Opt-in landed W SU capture reservation

`su_landed_price.load` defaults to zero and requires the exact measured
SU_LT1/HD_W1301/MU_NU4/FACE1 source plus receipt hash to enable +6 result edges.
Receipt5753e895b compares candidatec4adbc1c3 to baseline9b41881fe, which already
includes the separately measured scalar+1. Input events match after explicit
boot8→10 normalization. All118 S0DD and7 S1SD values/order match and move+6;
46 input echoes and status/gather outputs retain their ages. Decomposition is
control1 + read roundtrip4 + result return1.

The compiler API reserves the caller's selected capture window with unchanged
span: five measured last captures183/134/104/64/190 become189/140/110/70/196,
spans96/86/16/16/16. Issue, status, gather and unrelated architectures do not move.
Missing/foreign/mutated receipts fail closed. Five unittest cases pass on fleet.

This does not adopt a final native45-bank/CFG/reset view and does not reschedule
the public F16 image. Scalar result+1, CFG setup+2 and reset-release/boot guards
are separate contracts. Seam source4ec4aa5f2 specifies post-reset guard16, but
its production reset→epoch dominance remains pending; it is not free timing
normalization or a per-token price.
