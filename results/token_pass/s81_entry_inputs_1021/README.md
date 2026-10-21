# Legitimate layer entry input compiler

`entry_inputs.py` compiles actual L0 `io/h_in.bin`, `io/pre_in.bin` and raw
checkpoint `weights/attn_norm.bin` into native XR target-5 payloads. No `ops/`
result is read. The actual source generation unit2083936 completed with exit0;
`generation_receipt.json` is a source-generation receipt, not an RTL PASS.

All16 actual SIDs and five leaves receive H32 rows at0..31, GAIN16 rows at64..79,
and delayed pre at GU_FFN1008:3,920 writes total. H uses the existing VP HLOAD
mapping: even/odd128b leaf rows join into a VN256b BF16 halfrow. Norm gains are
checkpoint BF16 expanded to the FP32 container read by GAIN; delayed pre retains
its four FP32 bit patterns. Hashes, input shape/type, BF16 representability,
actual SID membership and row aliases are checked before publishing output.

The artifact includes reader addresses and row lifetimes. Native job adoption,
actual target5/downlink/VP commit dates, HLOAD/GAIN/NORMR source proof and the
sixteen-slice NX/XQ collective calendar remain explicit obligations. A separate
bounded actual source mechanism run owns the first of these. No command ACK is
used as capture completion. No HOST/KS descriptor or full token is qualified.

Fleet source generation (existing selected source snapshot, no RTL build):

```sh
python3 tools/s81_dv/layer_prog/entry_inputs.py --tree ../../tree \
  --fixtures ../../fixtures/L0 --out ../entry_inputs_L0_current.json
```

`entry_boot.py` is the native host/walker job builder. It consumes this input
map, requires an actual source-qualified mechanism receipt for every selected
raw input port (`ri_w`, `ri_e`, `vi`), checks compiled production hashes, and
emits ordinary 515-bit host CSR words with real target5/HLOAD/GAIN commands.
Two leaves fit each real128-row job. The target5 cadence is two edges, matching
the source mechanism vehicle. V ACK remains issue+5; a separate fixed END
minimum carries local measured lifetimes plus the explicitly conditional die
route model. The builder refuses legacy compilers without END-fence support.

At this source milestone, only the actual SID5/leaf0 `ri_w` mechanism is known
to pass. Selected `u_s_2N` uses `ri_e`, and column4 uses `vi`; those are separate
required interfaces. The builder therefore refuses whole-entry generation
until their actual receipts exist. No write/command ages are copied from W to
E/V. Actual incoming descriptors, global clock/route phases, whole-entry
lifetimes and sixteen-slice norm/gather remain held even after local receipts.
No KS descriptor is fabricated in the emitted host programming words.

## 10-21 TOK-FUNC2-S81: all three entry ports qualified, native jobs generated
E/VI cut gold1 unit2183787 (codex-entry-vp-1021/run_ports1) terminal PASS: ri_e (u_s_2N SID5) and vi (SID9) leaf0
target5 store commit pin+10, HLOAD last hw pin+29, GAIN last wl pin+21; each port's payload mutant FAILs. With the W
cut run5 (ri_w, same ages) `entry_mechanism.py` composes `entry_mechanism_receipt.json` (PASS ri_w/ri_e/vi, 15 source
hashes checked against the compiled source tree). `entry_boot.py` then emits 40 native host jobs
(`native_jobs_r1/`: 2 leaves/job, 102 commands, 417 host words, END 351..372 each; sum END 13,587, host reload
83,400 edges). Jobs are generated, NOT yet executed on RTL; global route phases/KS descriptor stay held.
