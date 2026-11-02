# Native k79 ROOT arithmetic fixture — preparation only

**PREP_ONLY_NOT_COMPILED.** The self-contained source packet is on intel1 at `/srv/opentallas-scratch2/claude/codex-qwen-root-native-1101/prep2/` (`.keep` protected). It contains36 selected module definitions /23,809,582 source bytes. The native scalar is the actual `qfd_dv_s5_sc2_leaf` wrapper and `qfd_dv_s5_sc2_k79` bounded netlist, not generic scalar2. Its21,201,395-byte body declares LA7/LM9 lineage and contains131,751 primitive instances, including42,429 plain and629 reset FF primitives (43,058 FF total). Helpers all use ID0, not131k unique parameter variants.

The packet preserves original source timescales; the timed fixture is1ns/1fs with an exact833ps clock. All modules belong to one nonhierarchical simulation context. Uncompiled prep1 is retained as a superseded extractor attempt that unnecessarily prefixed every module with1fs; use prep2 only. No native source, hierarchy, arithmetic profile or clock was changed.

## Exact source boundary

Live `qfd_dv_cmd_cal_mu` commands pass through native `qfd_dv_s8_fdn_arf1`, RP and `qfd_dv_s5_ctl_repair4_leaf` into the actual scalar leaf. The fixture performs SETID0 through that live calendar and runs four users explicitly sequentially. It feeds32 controlled FP32 PSUMs through native `red_we/red_addr/red_data` with W_SC bits23:22=11 and external indices0..31. No SU, eight-head datapath, reducer result, VM response or arithmetic output is faked. Inactive station/SU/stream planes are explicit idle inputs and are outside this fixture's claim.

The checker observes actual native scalar→CTL single-word write address/data. Expected data use the source golden's exact FP32 add/mul and three-step seeded RSTD: a32-leaf adjacent pairwise tree, then total×2^-12, +epsilon0x358637bd, then rsqrt. This is a scalar boundary arithmetic witness, not a checkpoint token or a claim that fixture PSUM dates are production dates. The supplied PSUMs and expected bits are committed with golden/vector hashes.

The live calendar relocates only private ROOT SS/RX result addresses:

| User | SS | RX |
|---|---:|---:|
|0|384|400|
|1|4480|4496|
|2|8576|8592|
|3|12672|12688|

The32 PSUM slots and count are shared, cleared by ROOT configuration. MU_NU4 tags argmax state; it does not make four PSUM arrays. Incoming W_SC indices stay0..31 for every user. The lease begins at configuration/first PSUM and ends only after fused publication/drain. Native busy starts at trig after all PSUMs arrive; busy0 during collection does not mean the shared slots are free.

## Same-source controls prepared, not executed

- Nominal: four sequential cases, distinct finite PSUM vectors, exact relocated RX and FP32 bits, no native/calendar fault.
- `+COLLECT_CFG`: a second live-calendar ROOT command24 cycles after the first clears partial collection while busy can still be0. The checker records the overlapping lease and expects failure through missing/incorrect actual publication.
- `+LATE_CFG`: a second ROOT command96 cycles after the first changes RX from400 to401 during in-flight arithmetic. The checker records the overlap and rejects an actual misaddressed or incorrect result.

The native fault predicate has no `cfg_v && busy` or partial-collection configuration guard. Neither control assumes that hardware raises a protective fault. They must be run and classified from actual native behavior. Current helper Python syntax passes; SV preprocessing, elaboration, native runtime and the two controls remain NOT RUN.

## One-build proposal for coordinator review

After admission RAM is chosen for this actual workload, use normal `ot-run` admission for one build, with standard nonhierarchical codegen splitting:

```sh
verilator --binary --timing -O0 -j 1 \
  --output-split 10000 --output-split-cfuncs 1000 \
  --x-assign 0 --x-initial 0 -Wno-fatal -Wno-lint -Wno-style \
  -Wno-TIMESCALEMOD -f defines.f -f source.f \
  --top-module tb_native_root --Mdir obj
```

Run from prep2 so the literal PSUM/golden files resolve. The nominal binary and its `+COLLECT_CFG`/`+LATE_CFG` controls use the same build. Output splitting limits generated C++ translation-unit/function sizes without changing RTL hierarchy, timeprecision, arithmetic or scheduling. No separate1ps child elaboration/cache is proposed. Admission RAM is deliberately unset: the3.8MB XA gate's15.75GB peak does not size this23.8MB/131k-primitive ROOT workload. No compile or additional fleet job was submitted.

Production TREQ, global ROOT leases, result visibility timing, actual final-residual PSUM arrivals, HEAD input/installation and physical/canonical adoption remain held. This packet is only the next minimum native arithmetic preparation.
