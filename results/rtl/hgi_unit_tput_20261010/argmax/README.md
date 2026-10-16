# ARGMAX.LOCAL production-shape throughput (hgi-1010/tput1-argmax, 2026-10-10)

Elements: `ot_hgi_argmax_record` (rtl/hbm_accel/generic/adapters) + `ot_hgi_argmax18_m` (GENERIC18 1). Bench
`rtl/hbm_accel/generic/adapters/tb/tb_hgi_argmax_tput.sv` (`run_argmax_tput.sh <qwen|ds> OUT <LPS> <MUT> <GAP>`), vectors
`tools/hgi_unitrate/argmax_tput_vec.py`, reports `tools/hgi_unitrate/argmax_tput_report.py`. Each run uses the real
ARGMAX.LOCAL dispatch, taken bit for bit from the sequencer contract (`hgi_seq_vectors.Ref`). Qwen3-8B TP4 rank 0: A = STREAM, n 37,984, imm_a 37,984. DeepSeek-V4.1
TP96 rank-0 head (g25_proof program): A = STREAM, n 1,347, imm_a 1,347. Both programs feed STREAM, not VM. The logits arrive as STREAM beats at the bus's full rate, one beat a
cycle. The bench checks the {value, id} it reads back from the real VM, and the nan_flag, against numpy argmax: 6 row kinds x 2 ranks =
12 records per model.

| model | price / record | LPS 8 (closed build) | ratio | LPS 16 (opt-in) | ratio |
|---|---|---|---|---|---|
| DS   | 142.7 (walk `su:argmax_local`) | 207 | 1.451 | 124 | 0.869 |
| Qwen | 2,394 (20 + n/16)              | 4,786 | 1.999 | 2,413 | 1.008 |

The bottleneck was the per-beat issue width. The closed build takes 8 lanes (one 523-b STREAM beat) a cycle, but the
price charges 16 compares a cycle (`ARGMAX.LOCAL.per_elem` 1/16), and DS needs 9.4 elements a cycle. The fix is opt-in
`LPS = 16` (default 8 keeps the closed RTL bit for bit). It makes the STREAM port 16 lanes wide (3 + 65 x 16 = 1,043 b) and runs the engine at LP 16. A VM-sourced row is read as sector pairs, with id = engine id - (A.base mod 16).
Gates: tput PASS at LPS 8 and LPS 16. MUT 1 (last beat dropped) FAILS with 4 errors, and MUT 2 (beat halves swapped,
tie-break) FAILS with 12 / 10 errors, on both models and both widths. The VM-path regression `tb_hgi_argmax_record` (52 cases, `vm_record/`) PASSES at LPS 8 and 16,
and MUT_OFFSET FAILS at both.

Measured latency: dispatch -> first beat 3 cycles, last beat -> retire 36 (LPS 8) / 37 (LPS 16) cycles. That is the
engine's 14-15 edges, plus the adapter's pin flops, plus two serial VM O-word writes. The cost fits as 40 + ceil(n/16) at LPS 16
(DS 125 vs 124 measured, Qwen 2,414 vs 2,413).

Open items:
- The token schedule ends a STREAM consumer at producer end + `STREAM.tail` ARGMAX = 20, but the measured tail is 37 (proposal: 37).
- Feeding 16 lanes needs a 16-lane producer. The SU's STREAM out (ot_hgi_su_unit, D1 and WIDE ctlw) sends 8-lane beats with
  one sector read in flight. The die's argmax stream is 523 b (8 lanes).
- LPS 16 has not been routed yet (it needs an engine LP 16 + adapter closure).
