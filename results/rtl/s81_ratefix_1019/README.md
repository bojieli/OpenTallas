# S81-RATEFIX (10-19): wq_b phase (row-batch) pipelining in the XS calendar compiler

**Change (compiler only, no RTL).** `tools/s81_dv/layer_prog/xs_calendar.py` gains `compile_pipeline()`. Before, every
wq_b field phase (epoch: 64 stream words, one batch of rows) was compiled as its own calendar segment
(prime/start/.../retire/phase_end) on one tag, so 15 phases ran back to back with a minimum period of 224 edges
(TOKSIM-S81/FIELD sweep: 223 fails). `compile_pipeline` emits ONE segment for all 15 phases:
phase n launches at `tg0 + n*P`, keeps compile_phase's row offsets, alternates tags 0/2 (double-buffered element
configuration: phase n+1 is accepted and configured while phase n streams), cfg row = launch - cfg_lead, accept =
cfg - 10, retire = last stream row + ADDR_LEAD + 6, one phase_end. The compiler asserts that a tag is reused only after
its retire and that streams never overlap. `qf_producer/retained_xs_program.py` takes `--pipeline-period P --cfg-lead C`
(default keeps the serial calendar; `--epoch-period` names the old 600/224 serial spacing).

**Static schedule only.** No credits / ready / backpressure added: every row is a compiled edge; the only new cost is
the fixed period and cfg_lead, both chosen from the measured element lifetimes (Q_LIFETIME walk / DRAIN 127 / swap +22).

**Measured (Verilator 5.050, TOK2 fullsix exe = same RTL blobs as TOKSIM-S81/FIELD; field/frame RTL = release
19bf4121e; ot-epyc9, unpinned ot-run; runs/<tag>/ratefix_result.json, judged by ana_pipe.py):**

| calendar | period / cfg_lead | result | span (first capture -> last return) |
|---|---|---|---|
| serial s224 | 224 | PASS | 3,360 |
| pipeline | 90 / 48, 100 / 48 | FAIL (152 rows missing, cfg7 faults) | - |
| pipeline | 120..124 / 48..50 | FAIL (element Q_LIFETIME faults, words differ) | - |
| **pipeline** | **126 / 52** | **PASS** (625 returns, words == P600 baseline tag-masked, 0 faults) | **1,988** |
| pipeline | 130 / 56 | PASS | 2,044 |

wq_b per-instance 3,359 -> 1,987 edges (-1,372, 1.69x); 15 phases x (224 -> 126). The two tb counters that assume one
segment per phase (epoch attribution by LAST GO, END count) are re-derived in ana_pipe.py (reads attributed by stream
window: 24/epoch, as expected). Token impact: results/token_pass/ratefix_s81_1019 (compose_ratefix.py).
Open: CAP retire/numeric PASS still not exercised by the fullsix vehicle (as for the serial baseline); other field ops
(experts_gu, wo_a, down) need their own fullsix vehicles before the same calendar applies to them.
