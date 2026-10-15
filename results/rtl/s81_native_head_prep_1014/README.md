# S81 head preparation: native computation boundary

`tools/s81_ftok/native_head_prep.py` replaces Python-generated head activations with output from the actual S81 HC hierarchy. It reuses `dsfd_sp_hc` with HIER=1, HALF=1, CSPLIT=1, TAIL_SPLIT=2, NG=256, CNL_PIN=1, CHAIN_STEP=6, LANE_SPECIALIZE=1. All arithmetic sources are RTL, not DPI. No additional arithmetic leaf is invented.

The four commands load the final normalization gain, load the four-copy residual from the actual final hop, load the final FFN's four pre coefficients, and execute NORM with YOUT=1 and QUANT=0. The output is 5120 scalar-order BF16 values in `xf.mem`, together with `xf.npy` and `xf.provenance.json`. Main and draft head use the same operation with different gain ROM contents. The existing HC_PRE rounds to BF16 before final normalization, matching both paths exactly.

The component bench uses fixed command cycles 64, 512, 1536, and 1792. Completion never selects an issue cycle. These conservative reservations are a diagnostic schedule and do not qualify the head/token performance price. Every command and the produced rows must complete correctly; hardware NORM-skip mutant 3 must fail. The artifact contains source hashes and refuses to reuse a compiled executable after its source changes.

```
python3 tools/s81_ftok/native_head_prep.py prep --work W \
  --hout hin_L40.mem --pre pre1.actual.mem --gain norm_weight.fp32.mem
python3 tools/s81_ftok/native_head_prep.py run --work W
python3 tools/s81_ftok/chain_glue.py head --hout hin_L40.mem --native-prep W
```

`--pre` is four 32-bit hexadecimal words from the actual coefficient engine; `--gain` is 5120 32-bit hexadecimal ROM gain values; `--hout` is the actual 641-flit upstream hop dump. Golden computation only produces expected values, never the DUT's output activation. `chain_glue --native-prep` consumes the actual RTL dump and verifies the upstream hop hash and binary output consistency. The historical default path is explicitly labeled as Python reference computation.

## Qualification boundary

This is a native **HC arithmetic component** bridge, not an all-native token. The VM pin boundary remains modeled here; actual VM service, native coefficient production, native head field roots and the digital collective/hop composition must still be connected and cycle-qualified. The initial real-token fixture takes the actual continuous hop output but historical reference pre coefficients; that fixture tests the component and cannot prove hardware coefficient provenance. The initial expected vector agrees bit-for-bit with the released 1M head `xf` (5120/5120), before simulation.

No timing/physical closure claim is made. Existing HC physical owners must qualify any production gain reload and stage-boundary command changes. The implementation introduces no new tile or clocks.
