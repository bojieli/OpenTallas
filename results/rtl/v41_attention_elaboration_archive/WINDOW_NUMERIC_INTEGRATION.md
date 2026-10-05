# Next numeric WINDOW composition gate

Use the same window128 synthetic golden arrays already prepared for the
fullgeometry numerical gate. `window_blocks264.hex` exactly reconstructs
all128 rows from the golden `kv.hex`, with16 groups perrow. It feeds the actual
`blk_*` producer interface. No HBM memory preload is permitted.

## Connections and ownership

* Stream owner: `ot_chip_v41x_window_attn_source`, parameter STREAM_II1=1,
  delayed-completion HBM sector model, generation descriptor.
* Numeric owner: `ot_v41_window_numeric_bridge` around unchanged
  H16/D512/TD32/NL4/T640 `ot_hdc_v41x_attn`.
* Golden input Q is loaded from16x8192bit words. Probabilities are64x512bit
  words for128rows. Their source is the software golden; this gate does not
  claim live SU softmax or checkpoint projection arithmetic.

## Required sequencing

1. Submit all2048 FP8 blocks through actualwrite port and wait for all4096
   sector writes to complete (including scales' read-modify-write as applicable).
2. Submit matching128row descriptor only when numeric descriptor_ready.
3. WINDOW source refills from real delayed-response HBM, then staged_v.
4. Bridge captures rows, accepts numericaljob on next available edge, pulses
   stream_go afterjobacceptance. Engine q_ready/kv_ready govern consumption.
5. Consume every sourceKVbeat through actualengine ready; score credits must
   come from the bounded checker. Check2048 QK outputs exactly.
6. Feed64 goldenBF16probabilitywords afterscorebarrier; check8192PV outputs,
   faultbits andfullreadback. Engine's own packedstaging provides PV replay.
7. Deliberately corrupt anHBMwrite and confirm exactcheckerfailure. Keep
   originalimagehash; identifycorruption as anexplicitnegativeexperiment.

## Scope distinction

The numericalengine's combined job retains packedKV from QK throughPV.
The current coreattentionadapter issues separate QK/PV descriptors and may
refill theWINDOW twice. Therefore aonefill combined-engine pass is NOT evidence
that the adopted adapter removed its secondrefill. Later integration must
exercise actualadapter semantics or adopt/verify anexplicit retained-lifetime
contract. Record bothrefillcycles andnumericfirst/last cycles separately.

## Compilation

Do not modify/rebuild the currentlyrunning PVE2 standalone numericgate.
Once its verdict is known, reuse verifiedsource andhierarchy boundaries for
the integratedtop; do not substitutezero-arithmetic stubs in numericresults.
