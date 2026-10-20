# Qwen3-8B ROM decode rate composed from cycle-accurate RTL stages (TOKSIM-QW, 2026-10-19)

This answers the owner's request at 18:18 to measure the real decode rate with cycle-accurate RTL simulation instead of quoting prices.

- **Release RTL:** origin/claude/qw-gen3-1019 (221cf90b7, and e9879afda, which changes only tools) for the compute die (dv2f18dh2 -> GEN3 dv2f19g3). The KV die is kvs14 GEN9, which has not been built yet.
- **Clock:** 833 ps (1.2 GHz).
- **How the token is composed:** the static schedule makes cycles deterministic. `tools/qwen_layerbench/toksim_compose.py` runs `dv_layer.compose`, which builds one spliced decode calendar per layer and keeps the ctlm dependency gaps. Every priced stage is replaced by its measured RTL value:

  T = L0_cold + 35 x L_chained + 36 x die_edges + head + embedding fetch

- **Data files:** inputs are in `inputs.json`; the result is in `cycles.json`.
- **Grades:**
  - REL = RTL byte-identical to the release source.
  - NEWEST = newest bench-passing RTL of that element, labelled as such.
  - DIAG = measured on RTL that differs from the release source. It does NOT count as measured.
  - PRICED = plan price.

## Single user (1u): 233,497 cycles/token = 5,141 tok/s (composed), 67.5% REL-measured. Target is >=90%: NOT MET

Update 10-19 21:50: the DV families are now REL. TOKSIM-QW/STG re-ran the DV stage benches on the gen3 RTL (claude/toksim-qw-stg-1019 21bd29268, `stg/record.json`; copies of the ages are in `stg/`). The run used the tb_qfd_dv2 N12 build, all 31 build sources byte-identical to gen3, Verilator 5.050, and real L0/L1 P8191 operands.

- **Benches:** 16/16 stages PASS (resid/qk/silu/qkv/gu/od on L0+L1, lm, emb), and 8/8 mutants FAIL. This holds at both parameter sets.
- **Base parameters** (MU_NU 1, SU_LT 0) reproduce the committed qlb ages exactly.
- **Release slice kit parameters** (SU_LT 1, MU_NU 4) add delay:
  - +21 edges per vector family;
  - SiLU +67;
  - d2d rs +46;
  - STN ages are unchanged.
- **Composer input:** the composer now lowers on the release-parameter ages. That costs 261 cycles per chained layer (6,065 -> 6,326) and 9,417 cycles per token. The token was 5,357 tok/s at 39.8% REL; it is now 5,141 tok/s at 67.5% REL.
- **Mat-side fix:** the gen3 `cmd_stn` requires `kc`, so `dv_lower_mat.KC = 1` was added and the mat side re-run. The bench drives one final block per (round, j), and field 0 is the realstg encoding.

The price of record is 4,810.9 tok/s (249,431 cycles), so the composed rate is 6.9% above it. That does not count as a rate of record until the DIAG terms are re-measured on the release RTL.

Chained layer: 6,326 cycles, against 6,843 in the ctlm plan. L0 cold: 6,842 cycles.

| layer stage (critical path order) | cycles | plan | grade | evidence |
|---|---|---|---|---|
| RMSNorm SSQ + ROOT | 230 | 85 | REL | STG gen3 slice ages (rel params) |
| qkv matvec | 316 | 259 | REL | XT1 column slice on dh2: first rs 181, last final 244; 64/64 bit-exact on real ROM; MU_NU 1 and 4. STG qkv stage 769/769 |
| QK-norm / RoPE / D2D send | 451 | 235 | REL | STG gen3 ages; qk stage 7/7 bit-exact (span 1,015 rel) |
| attention round trip (C2K + KV + K2C) | 1,825 | 1,681 | DIAG | dh2 pair: round trip 1,840, 35 layers bit-exact. The KV service (1,779) runs on the kvs14c stand-in, not GEN9. The C2K 63 / K2C 62 D2D legs are REL |
| attention return | 98 | 16 | DIAG | QW-ATTNRET on pre-gen3 slice RTL. There is no gen3 attn bench. Re-lowered on the gen3 ages, the compiled span is 119 (composition gap) |
| o_proj matvec + AR words | 531 | 375 | REL | XT1 (o: 189..228); STG od stage 515/515 |
| all-reduce 1 (TP8) | 541 | 856 | REL | TP8 collective on gen3 RTL: E 286, LS 378. SerDes PHY is a model |
| residual 1 | 547 | 411 | REL | STG gen3 ages; resid stages 28/28 (span 1,085 rel) |
| gate/up matvec | 494 | 562 | REL | XT1 (gu: 429..436); STG gu stage 3073/3073 |
| SiLU x up | 338 | 114 | REL | STG gen3 ages; silu stage 2/2 (span 902 rel) |
| down matvec + AR words | 563 | 256 | REL | XT1 (down: 221..324, rounds of 48) |
| all-reduce 2 (TP8) | 541 | 714 | REL | as all-reduce 1 |
| residual 2 | 547 | 411 | REL | STG gen3 ages |

Terms outside the layer, all PRICED:

| term | cycles | evidence |
|---|---|---|
| per-layer die edges (landings, native59, ctlm) | 52 x 36 | TOK.QW.SCHED |
| LM head + argmax | 3,101 | head plan. The lm AMAX gather (26/26) and emb (4096/4096) functions PASS on gen3, but those benches report no head span. The measured TP8 argmax collective is 438 |
| embedding fetch | 272 | token path |

Token cycles by grade:

| grade | cycles | share |
|---|---|---|
| REL | 157,646 | 67.5% |
| DIAG | 69,308 | 29.7% (KV attention service + attention return) |
| PRICED | 5,245 | 2.2% |
| plan gaps | 1,298 | 0.6% |

The cycles are split by critical-path ownership.

## Four users (4u): 13,708.2 tok/s aggregate (NEWEST, link-schedule rate; not a full-token run)

These figures come from the codec2 OVL 4-user D2D pair fullframe run (TOKSIM-QW/LINK, `link/` on claude/toksim-qw-link-1019 cb8eb6b9a):

- **Frame:** H = 4,026,800 cycles; the four users get 16, 15, 8 and 7 tokens per frame.
- **Per user:** 251,675 / 268,453 / 503,350 / 575,257 cycles per token, which is 4,768 / 4,470 / 2,384 / 2,086 tok/s.
- **Exactness:** 63,098 C->K and 57,783 K->C frames exact; the one-playhead, collide, slot and user mutants FAIL.

The OVL hardware is not in qw-gen3, and its producers and consumers are modelled. The release die uses the serial MU calendar, and no paired 4-user test bench exists for it yet. The MU context real link is REL: slot->compute 18 cycles. The TP8 4-user window E is 286, the same as 1u.

## Measured-vs-priced and what is still owed to reach >=90% REL

1. **KV attention (kv/):** this is the largest gap, 1,825 x 36 = about 28% of the token. There is no full QK+softmax+PV16 measurement on current KV RTL. GEN9 is not built, and the KVJ-B2 unit build cannot be reconstructed. The KV-TOK3 G7 controlled_n vehicles (QK only) were still running at 21:45 on ep5 `kv-tok3-1019/controlled_n`, with `u*.log` full of `KVA_IDENTITY_ERROR unowned run`, so they are not folded yet. The KV-die attention vehicle needs retargeting to the GEN9 netlist.
2. **Attention return:** add an attn mode to `dv_lower_vec_bench` and run it on gen3 rel. The 98 measured on pre-gen3 RTL compares with 119 compiled on the gen3 ages.
3. **LM head + argmax:** the 3,101-cycle head span needs an RTL run. The lm/amax and emb function benches PASS on gen3.
4. **Rel stn calibration:** S0ST/S5ST fault bits 1000001 (any, port) are logged in the rel `cal_mat` calibration harness only, and every rel stage bench PASSes. Handed to QW-GEN3.
5. **Lane ages:** `dv_layer` still uses the dv2f14bi die lane ages, because the GEN3 layer_compile lane ages do not exist yet.
6. **Calendar clash:** one W5 command-edge clash (SEG base 14 against resid1 PORTS at 3739), because the SEG entries are not re-placed after the measured shift.
7. **4u on the release RTL:** needs the serial-MU paired test bench. The 4u figure is a link-schedule rate, and its per-user rates are independent of the 1u composition.
