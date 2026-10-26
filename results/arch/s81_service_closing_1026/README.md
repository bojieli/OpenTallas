# Closing service calendar (2026-10-26)

The real H16/D512/T128 service programme with ALLQ+SMT, native hcores, CTLA and timed reset passes on two HBM-latency seeds. Each replay checks all 2,048 scores, 2,048 exp operands, 2,048 on-die P values and 8,192 P.V values, plus both SO/gather paths. All numerical, fault and calendar checks pass. The fixture uses the production numerical golden with controlled inputs; this is not a released-model or bound-top token pass.

The old FG3 calendar on the same closing RTL fails with 1,136 P.V errors. Its first P reads precede the exp writes on heads 9/11; its first head-0 P.V drain underflows (fault 19, observed at cycle 2086). The original failure and all 128 exp-row production edges are preserved in `baseline.log`/`baseline.json`.

The explicit `closing_allq` calendar uses PIO297/PO407/PVO517, compared with FG3 285/395/482. GO remains1555; P.V begins2128, and W/E completion is3166/3133: +35 cycles each. All following SO frames and SOT write/read/retire/gather windows shift coherently by35. The canonical model remains unchanged pending adoption; `calendar_delta.json` records the +35-cycle service correction without double charging SO. No RTL cycles or numerical behavior were changed.

The actual kernel source is `7b910ca728`; the two completed protected libraries are reused. The observer and image generator are `dc6dc1fdd2`; later commits add compiler profile propagation/guards only. The generated image matches the independently rescheduled positive replay across all nine payload hex files. The default legacy generator preserves those same nine baseline payload files byte-for-byte. Compiler drivers pass a profile explicitly, and the compiler/bench reject mixed source calendars before doing work.
