# S81-WQBP part 2 (row-batch pipelining of experts_gu / wo_a / down), 10-20

## attn.wo_a: serial 12-phase sum -> one static phase sequence
`run_woa_seq.sh` runs the 12 attn.wo_a BF phases of one frame as one go sequence. Go i is issued at go0 + i x P, with no
waits (GO_LATE 0).
- Vehicle: TOKSIM-S81C/FSEQ `tb_toksim_fgu_seq` with +RETIRE and +PHASE_VM, on the release 19bf4121e frame exes
  v_h9nx_e5 / v_h10_e2 (Verilator 5.050).
- Inputs: the TOKSIM-S81B/FWOA phase vectors (xs_place gen, released L0 fixture, real rank-0 rows).
- Check: `toksim_fgu_check.py seq` (per-row golden segment tree is bit-exact, plus row coverage and the cycle-exact
  calendar); the 64/64 rows are also tied to the fixture.

| P | u_f_0L00 (col_h9) span | u_f_0L01 (col_h10) span |
| --- | --- | --- |
| 352 (the serial schedule) | 4224 PASS (= FWOA) | 4217 PASS |
| 260 | 3212 PASS | 3205 PASS |
| **231** | **2893 PASS** | **2886 PASS** |
| 230 / 220 / 200 / 180 | FAIL | FAIL |

Below 231, the first phase's return words fail the golden check: the second BF go relabels the first phase's still-open
segment. This is the same RTL schedule constraint TOKSIM-S81C/FSEQ found for the BF router, so a static BF schedule
needs gos >= 231 apart.

Per instance: 2893 + the unchanged tail (584 r8 die wire + 28 + 26 CAP) = **3531**, against 4862 before (-1331 per wo_a
node, 40 critical nodes). Fleet job: ep9 units oth-ubuntu-2074714 / 2074715-1792489430. Evidence is in `evidence/run/*/woa`.

Composer: a scratch copy of codex/token-gl24-main-1020@d5fcf23d5, with only the FWOA wo_a cycles replaced
(`compose/FWOA_woa_p231_override.json`):

| composition | AR tok/s | MTP tok/s |
| --- | ---: | ---: |
| baseline | 834.0 | 2,649.1 |
| + wo_a P231 | 866.1 | 2,736.1 |
| + wo_a P231 + wq_b P126 | **901.8** | **2,832.0** |

Open: the die compiler's xs calendar has no BF window rows (FWOA's compiler gap). So this sequence is driven by the
bench's static go issue, not yet by a compiler-emitted slice calendar. Owed: a BF calendar in xs_bf / xs_wqb_die
generalised to the BF ops, with the 231 floor as a compile fault.

## ffn.experts_gu and ffn.down: already pipelined at their element floor
The measured numbers in the composer are already overlapped phase sequences on the release frame RTL. Each sits at the
element replay/lifetime floor, with the first FAIL just below:
- experts_gu: 24 phases at P145 (P144 FAULT), span 3680 (TOKSIM-S81B/FGU, S81C/FSGU, every layer class).
- down: 21 phases at P130 (P125 FAULT 11), 2889 + 195 = 3084 (S81B/FDOWN, S81C/FSDN).

The same mechanism therefore gives no further gain there. The open item is the same as for wq_b: emit those calendars
from the die compiler rather than from bench go issue. A further cut would need a structural change at the element
(replay length/lifetime), and that is RTL work.
