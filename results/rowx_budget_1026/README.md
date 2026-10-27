# ROWX-BUDGET (2026-10-26): static per-owner budget B for the S81 held-row export

Analysis only, no RTL. Spec: `~/coord/lanes/S81-ROWX.md` (claude/s81-rowx-1026@ee24aba28). Base of this branch:
claude/tok-ds-6-1026@4997aa68d7 (the ledger and the TOK-DS-6b composition).

## 1. Real selections: none exist

There are no real-prompt DeepSeek indexer top-512 selections in the repository or the fixtures.
- The only top-512 selections are the CPU golden 1M-context reference token (`results/inputs/ds_v41_1m_golden_s20260930`,
  seed 20260930, `ref/ctx1048576_LNN.json` `ctx_out.sel`). It uses the released V4.1-Flash weights, but its KV and
  index-key state is SYNTHETIC: i.i.d. normal rows (`rtl_v41_fullshape_layer_campaign.py synthetic_state`). It is one
  token. So it is a fixture, not a distribution.
- No V3.2 / V4.1 indexer traces, no GPU oracle for DeepSeek, and no real-prompt golden exist. The Qwen oracles do not apply.

What would be needed for real evidence:
- The V4.1-Flash released checkpoint (the golden's model). V3.2 traces would only be a proxy: top-k 2048 and no 2:1
  compression, so g would be a token position.
- A GPU forward over real long prompts (>= 32K-128K tokens; long-document QA, code and chat), with a hook that dumps the
  `index_select` of the 8 indexer layers for each decode token. These are L2/8/14/20/24/28/32/36. L24-36 also need
  the L20 candidate-block mask.
- Then map each g through `tools/v41_selection_global_ids.owner()` and count the 16 owners.
- The CPU golden cannot do this. It decodes one position at a time (19.9 s per layer at 1M, even with synthetic state),
  so a real 128K prefill over 40 layers is infeasible.
- Sample size: with zero overflows in n tokens, p < 3/n (rule of three). To show p < 1e-4 per token, about 3e4 decode
  tokens are needed.

## 2. Distribution numbers

**Fixture token** (`fixture_counts.py` -> `fixture_counts.json`; CHECKED: recomputed here from the golden files, and
the L14 d0s0 count of 36 matches the lane):

| layer | L2 | L8 | L14 | L20 | L24 | L28 | L32 | L36 |
|---|---|---|---|---|---|---|---|---|
| max held per (die, stack) | 43 | 42 | 41 | 43 | 46 | 49 | 43 | 47 |
| min | 18 | 25 | 23 | 19 | 22 | 19 | 22 | 21 |
| owners > 40 | 1 | 1 | 1 | 2 | 1 | 1 | 1 | 3 |

On this fixture token, all 8 of 8 indexer layers exceed B = 40 (fault 26), and none exceeds 80 or 128.

**Uniform i.i.d. reference** (`uniform_ref.py` -> `uniform_ref.json`, 2e6 layer samples). This is a LABELLED
REFERENCE, NOT EVIDENCE: real selections cluster, and clustering only widens the tail.
- Per owner: mean 32, sd 5.48. P(> 40) = 0.064, P(> 80) = 2.3e-14, P(> 128) = 1.4e-42.
- Maximum over the 16 owners of one layer: mean 42.4, p50 42, p99 51, p99.9 55, p99.99 58 (largest of 2e6 = 66).
- Overflow probability for B = 40: 71 % of layers, and 99.996 % of tokens (8 layers).
- Overflow probability for B = 80: 3.6e-13 per layer and 2.9e-12 per token (union bound).
- Held-list overflow (> XN = 128): about 1.8e-40 per token.

## 3. Price of each option (`price_options.py` -> `price_options.json`)

Method: the composition of TOK-DS-6b (`compose_tok_s.py`). The base token path is combined with every non-superseded s81
ledger row. The SVC.ROWS_INGRESS A (L2/8/14/20) and B (L24/28/32/36) rows are re-priced with `accepted_cost.py compute`,
with their measured value 3809 replaced by the option's ingress. That is 8 runs a token, and all of them are critical.

Ingress per half = 60 B words + 1 header for each pass. This is 15 peer owners x B rows x 8 tile halves / 2 halves per PK2 word.
- B = 40: 2,401. B = 80: 4,801. Two passes of B = 40: 4,802.
- Data-exact: 476 x 4 + 1 = 1,905.
- These match the spec (CHECKED arithmetic).
- The ledger row of 3809 counts neither the export nor the cross-die transport, and neither does the main price below.
- The "+export" price adds the 8 x NXW export cycles serially, as an upper sensitivity.

The baseline reproduces TOK-DS-6b exactly (AR 1,259.6 / MTP 3,655.3), so the tool output is CHECKED. In the table, the
ledger-% column is my sum of the A + B rows' e2e % (UNCHECKED, not independently number-checked).

| option | ingress per half | AR tok/s (delta) | MTP tok/s (delta) | MTP + export | S81 ledger % |
|---|---|---|---|---|---|
| ledger now (bench pair format) | 3,809 | 1,259.6 | 3,655.3 | - | 17.05 |
| data-exact (a per-token schedule, not static) | 1,905 | 1,280.1 (+20.5) | 3,722.7 (+67.4) | - | 15.24 |
| **B = 40, 1 pass (NXW 20)** | 2,401 | 1,274.7 (+15.1) | 3,704.9 (+49.6) | 3,699.2 | 15.71 |
| **B = 80, 1 pass (NXW 40)** | 4,801 | 1,249.2 (-10.4) | 3,621.1 (-34.2) | 3,610.2 | 17.97 |
| B = 40 x 2 passes | 4,802 | 1,249.2 (-10.4) | 3,621.0 (-34.3) | 3,610.1 | 17.97 |
| B = 120 (NXW 40 + 20) | 7,202 | 1,224.7 (-34.9) | 3,540.9 (-114.4) | 3,525.3 | about 19.7 |
| B = 160 (above XN = 128) | 9,602 | 1,201.2 (-58.4) | 3,464.2 (-191.1) | 3,444.3 | about 21.1 |

Every option keeps MTP above the 3,000 floor (OWNER 10-15).

## 4. Recommendation

**B = 40 is not schedulable.** It faults on all 8 fixture layers. Even the uniform reference puts its layer maximum at 42,
and real clustering is worse.

**B = 80, as one pass with NXW = 40, is the minimum safe static budget.**
- It costs -34 MTP / -10 AR tok/s against the current ledger, about +0.93 pp (17.05 -> about 17.97 %, UNCHECKED). MTP is
  3,621 against the 3,000 floor.
- Two passes of B = 40 cost the same 4,802 cycles and buy nothing, because a static schedule books both passes every
  token. Use the single pass.
- B = 80 is 2.5x the mean. To overflow it, one owner must hold more than 15.6 % of the selections, against a fair share
  of 6.25 %.
- The uniform tail is negligible (about 1e-12 per token). The real-prompt tail is UNKNOWN until the traces in section 1 exist.

Owner items:
- (i) Accept B = 80 on this evidence, or wait for the real-prompt traces.
- (ii) Decide what fault 26 or 24 does at run time: fail the token, or host replay with a larger B.
- (iii) Optional, not built, UNCHECKED: a structural fix that cannot overflow. Every die already holds the identical
  sorted SEL_IDS list, so the export slots could be assigned in global rank order rather than per owner. That gives about
  512 x 4 + 1 = 2,049 q cycles and no budget. It needs per-owner export at the full ingress rate, an RTL and transport change.
