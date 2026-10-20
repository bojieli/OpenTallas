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

## Single user (1u): 224,080 cycles/token = 5,357 tok/s (composed), 39.8% REL-measured. Target is >=90%: NOT MET

The price of record is 4,810.9 tok/s (249,431 cycles), so the composed rate is 11.4% above it. That does not count as a rate of record until the DIAG terms are re-measured on the release RTL.

Chained layer: 6,065 cycles, against 6,843 in the ctlm plan. L0 cold: 6,560 cycles.

| layer stage (critical path order) | cycles | plan | grade | evidence |
|---|---|---|---|---|
| RMSNorm SSQ + ROOT | 209 | 85 | DIAG | DV ages (qlb_c4b slice RTL) |
| qkv matvec | 316 | 259 | REL | XT1 column slice on dh2: first rs 181, last final 244; 64/64 bit-exact on real ROM; MU_NU 1 and 4 |
| QK-norm / RoPE / D2D send | 362 | 235 | DIAG | DV ages; realstg real-operand stages 14/14 bit-exact on the old slice RTL |
| attention round trip (C2K + KV + K2C) | 1,825 | 1,681 | DIAG | dh2 pair: round trip 1,840, 35 layers bit-exact. The KV service (1,779) runs on the kvs14c stand-in, not GEN9. The C2K 63 / K2C 62 D2D legs are REL |
| attention return | 98 | 16 | DIAG | QW-ATTNRET |
| o_proj matvec + AR words | 531 | 375 | REL | XT1 (o: 189..228) |
| all-reduce 1 (TP8) | 541 | 856 | REL | TP8 collective on gen3 RTL: E 286, LS 378. SerDes PHY is a model |
| residual 1 | 505 | 411 | DIAG | DV ages |
| gate/up matvec | 494 | 562 | REL | XT1 (gu: 429..436) |
| SiLU x up | 250 | 114 | DIAG | DV ages |
| down matvec + AR words | 563 | 256 | REL | XT1 (down: 221..324, rounds of 48) |
| all-reduce 2 (TP8) | 541 | 714 | REL | as all-reduce 1 |
| residual 2 | 505 | 411 | DIAG | DV ages |

Terms outside the layer, all PRICED:

| term | cycles | evidence |
|---|---|---|
| per-layer die edges (landings, native59, ctlm) | 52 x 36 | TOK.QW.SCHED |
| LM head + argmax | 3,101 | head plan. The measured TP8 argmax collective is 438 |
| embedding fetch | 272 | token path |

Token cycles by grade:

| grade | cycles |
|---|---|
| REL | 89,235 |
| DIAG | 128,302 |
| PRICED | 5,245 |
| plan gaps | 1,297 |

The cycles are split by critical-path ownership.

## Four users (4u): 13,708.2 tok/s aggregate (NEWEST, link-schedule rate; not a full-token run)

These figures come from the codec2 OVL 4-user D2D pair fullframe run (TOKSIM-QW/LINK, `link/` on claude/toksim-qw-link-1019 cb8eb6b9a):

- **Frame:** H = 4,026,800 cycles; the four users get 16, 15, 8 and 7 tokens per frame.
- **Per user:** 251,675 / 268,453 / 503,350 / 575,257 cycles per token, which is 4,768 / 4,470 / 2,384 / 2,086 tok/s.
- **Exactness:** 63,098 C->K and 57,783 K->C frames exact; the one-playhead, collide, slot and user mutants FAIL.

The OVL hardware is not in qw-gen3, and its producers and consumers are modelled. The release die uses the serial MU calendar, and no paired 4-user test bench exists for it yet. The MU context real link is REL: slot->compute 18 cycles. The TP8 4-user window E is 286, the same as 1u.

## Measured-vs-priced and what is still owed to reach >=90% REL

1. **DV families (stg/):** the gen3 N12 build is re-running on ot-epyc5 (`/srv/opentallas-scratch/claude/toksim-qw-stg/{base,rel}`). It re-derives the ages and runs 14 stages + lm/emb + 8 mutants. All 31 build sources are identical to gen3, so the results will be REL. When they land, update `inputs.json` dv/attn_return and re-run the composer. If the ages are unchanged, the DV terms become REL (about 47%).
2. **KV attention (kv/):** there is no full QK+softmax+PV16 measurement on current KV RTL. GEN9 is not built, the KVJ-B2 unit build cannot be reconstructed (uncommitted sources were reaped), and the KV-TOK3 G7 vehicles only cover QK. The KV-die attention vehicle needs retargeting to the GEN9 netlist. This term is 1,825 x 36 = about 30% of the token.
3. **LM head + argmax:** needs an RTL run on gen3. STG runs lm/amax as a DV bench; the head matvec over the full vocabulary is still priced.
4. **Lane ages:** `dv_layer` still uses the dv2f14bi die lane ages, because the GEN3 layer_compile lane ages do not exist yet.
5. **Calendar clash:** one W5 command-edge clash (SEG base 22 against resid2 PORTS at 5813), because the SEG entries are not re-placed after the measured shift.
6. **4u on the release RTL:** needs the serial-MU paired test bench.
