# TOKSIM-S81C/WQBG: golden bit-exact check of attn.wq_b on the TOK2 fullsix vehicle (10-19)

**Result: every return word of the serial calendar (P600, P224) and of the pipelined S81-RATEFIX calendar (P126/cfg 52)
equals the model GOLDEN, bit for bit. Before this, those words had only been compared with the P600 baseline.**

Golden (`wqb_golden_check.py`, no RTL output used):
- Fixture: the released-checkpoint L0 rank-0 fixture `sid6_fixture` (DeepSeek-V4.1-Flash dba1be0a, meta sha d7f2eb61).
  x = `ops/attn.q_norm.scale`. W = `weights/wq_b` (F8_E4M3) with `wq_b.scale` (UE8M0). Rows 3072..3583, K 1280.
- Segment sums: `frame_return_plan.golden_vals`, i.e. `hdc_golden_v41.csum` (chunk8) over the 32-element block products
  of each of the 3 K segments (`v41_rom_ksplit_bankmap.segments(1280,3)`).
- Frame-root word: the tag carries the tree node (lo, k, n). Its golden value is `cap_model.golden_sub`: the golden-tree
  sum of that node, in `ot_v41_ret_pkg` order, with padding promoted and IEEE fp32 RNE adds.
  Word layout: tag w[34:3], data w[66:35], err w[67], frame_fault w[69].
- Per row, the returned nodes must partition [0,3). Recombined in golden tree order, they must equal
  `cap_model.golden_row`, and the BF16 RNE of that sum must equal the fixture's released-shard output
  `ops/attn.wq_b[3072+d]`.
- Self-check: the recomputed segment sums, accumulators and BF16 equal `retained_sid6_fixture_contract.json` for all
  512 rows, and the BF16 equals the shard for all 512 rows.

| run | calendar | words == golden | rows == golden (shard BF16) | bit_exact | first capture -> last frame-root word |
|---|---|---|---|---|---|
| P600 (TOK2 default) | serial, 1100+600 i | 625/625 | 512/512 | **true** | 1573 -> 10196 = 8,623 |
| P224 (minimum) | serial, 1100+224 i | 625/625 | 512/512 | **true** | 1573 -> 4932 = 3,359 |
| P126 / cfg 52 | pipelined (xs_calendar.compile_pipeline) | 625/625 | 512/512 | **true** | 1573 -> 3560 = 1,987 |
| s224, P130, P225..P400 | serial / pipelined | 625/625 | 512/512 | true | - |
| P223 (known FAIL) | serial | 44 words returned | 36/512 | false | - |
| P124/cfg 50 (known FAIL) | pipelined | 44/625 | 36/512 | false | - |

The two known-FAIL runs are negative controls: the checker rejects their missing rows and corrupted words.
Node patterns, identical in every passing run: 399 rows return one complete word (node 0,k2), and 113 rows return two
partials, (0,1) and (2,1), which the CAP pairs.
No mismatch was found, so the vehicle, fixture, compiler and RTL show no bug on this path.
Scope: frame-root words only. The CAP tree/CW and the VP hand-off are not run by this bench (the 195-edge tail is priced).
The golden recombination stands in for the CAP adds.
Files: `wqbg_compare.json` (per run: counts, mismatches, classification sha256), `wqbg_golden.otrun.log` (ot-epyc9
unit oth-ubuntu-566913-1792476603). Run dirs: ot-epyc9:/srv/opentallas-scratch/claude/{toksim-s81-field/p*,s81-ratefix/*}.
