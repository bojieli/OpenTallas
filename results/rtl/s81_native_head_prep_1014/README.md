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

## Native embedding handoff integration

`chain_glue.py mtp0 --native-embedding-dir <embedding gate records> --main-token-file <one hex token>` calls the native embedding publisher, verifies the source-pinned passing gate and failing mutant records, checks every output lane against the MTP oracle, and copies the actual RTL HIDDEN bytes into all five stage-0 input packets. It does not construct an embedding in Python. The main-token file must come from the actual native head in the full system; the integration component test used token 21946 as a declared boundary stimulus.

Integration check: all five M0 row handoffs passed against the real MTP `h_in` fixtures using native bankgate21946 and bankgate128799 outputs. A mutated payload was rejected with `native embedding dump hash mismatch`. This closes the Python expansion/framing substitution at this handoff, subject to integration with the actual head token producer and real die transport. Embedding tiles' physical qualification is tracked separately by their owner.

The initial flat real-FP head-prep builds exceeded their 96 GB / 64 GB memory caps and terminated with systemd `Result=oom-kill`, before any numerical verdict. The replacement `head_prep.vlt` preserves actual HC/FP module boundaries during Verilation; it substitutes no behavior. Baseline and mutant are being verified using that hierarchy.

## Native final-gain producer

`ot_s81_head_gain_stream` reads 320 consecutive words on the existing HCP tail parameter ROM port and emits 320 full 512-bit VM rows (16 BF16 gain values expanded to FP32 per row). `head_gain_image.py` extends the existing four 4096x72 mask images: main final gains at addresses512..831 and M2 final gains at832..1151, preserving coefficient parameters0..343 and all other mask rows. The HC home owner confirmed the allocation is free. No additional memory macro is allocated.

Production reserves the shared ROM and VM ports statically. The module has no ready, credits, or runtime arbitration. For fixed commit latency WL=4 it finishes exactly326 serial cycles after start, checking every expected VM commit without extending that timeline. The physical HCP parent still needs the compiler-owned ROM/VM port selection; conflicts must fault. Gain-set ownership and the actual HC GAIN command remain compiler responsibilities.

Actual mapped-ROM component evidence in `gain/`: both real main/M2 gain vectors PASS640 VM rows with zero mismatches at326 cycles each. Missing commits set fault without stretching execution (mutant1). The RTL gain-bit mutant2 FAILS640 rows, an observed numerical negative control. The ROM models are the existing `ot_rom_4096x72_m8` functional models, loaded with the extended actual resident parameter images. This proves the producer component; integrated parent physical closure and token qualification remain open.

The temporary `--debugi1` head-prep compiler diagnostics generated818GB of AST `.tree` dumps. Those owned debug dumps were removed after bounded diagnostic preservation; complete child libraries and objects were retained. The option is removed. Native head-prep builds now resume with those partials at256GB without AST dumping. No RTL or arithmetic substitution was made to reduce simulation size.
