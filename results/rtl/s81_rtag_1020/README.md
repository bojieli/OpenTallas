# S81-RTAG 10-20: go-aligned BF output label tables (rate plan F4 + F2b) -- RTL, NOT contents-only

Branch claude/s81-rtag-1020 (on claude/s81-wqbp-1020 @36163250c). Collected and finished by S81-RATE3 after the 03:50 limit.

## Change
- New `rtl/v41rom/ot_s81_so_label_q.sv`, instantiated in `ot_s81_bf_front_roots` when `SOQ=1`
  (`dsfd_bf_front_roots` takes `` `DSFD_BF_SOQ `` / `` `DSFD_BF_SOQ_SWD ``, default 0 = byte-identical behaviour).
- What it fixes: the BF column labels a partial (so_row / so_idx / so_n) at output time, and the labels follow the cfg WRITES. The next phase's
  cfg lands while the previous phase drains. Below P231 a partial therefore got the next phase's label (the "BF segment-label floor").
- How: SOQ switches the labels SWD (160) edges after each go, from a 2-entry snapshot queue taken at go. The queue is static, and a go
  into a full queue raises a sticky fault (observation only).
- Revision 2 (this commit, sha a43e28d3): 16-bit chunks, each with its own kept enable / pop / pointer copy (<= 32 loads). The copies
  have no reset; reset stays on about 24 control flops.

## Evidence (Verilator 5.050, release frame exes, FSEQ vehicle tb_toksim_fgu_seq +RETIRE +PHASE_VM, L0 fixture rows; toksim_fgu_check seq bit-exact)
| build | op | frames | P129 | P130 | P231 |
|---|---|---|---|---|---|
| r160 (rev 2, SOQ=1 SWD160) | ffn.router (5 BF phases) | 0L00/0L01/0L02/0L03 (h9nx_e5/h10_e2/h9MX_e1/h9nx_e2) | PASS 857-861 | PASS 861-865 | PASS 1265-1269 |
| r160 | attn.wo_a (12 BF phases) | 0L00/0L01 | PASS 1771/1764 | PASS 1782/1775 | PASS 2893/2886 |
| rlate (MUT_LATE, labels 200 edges late) | router / wo_a | 0L01 | -- | **FAIL** (fault 4) | -- |
| t (SOQ=0, legacy) | router | 0L01 | -- | P145 FAIL | P230 FAIL / P231 PASS |
| s160 (rev 1) | router / wo_a | 0L00/0L01 | P120 FAIL | PASS | PASS |
- Runs: runs/*/res_seq_*.json (+ gz logs), runs/summary.json; builds/*/sources.sha256; scripts/rt_r2*.sh; rtag_r2*.otrun.log.
- Native census (tools/ref_tile/native_census.py, ASAP7 TT): unit ot_s81_so_label_q rev 2 **PASS max 32** (soq_unit2). Rev 1 FAILed at
  max 68. The WHOLE dsfd_bf_front_roots FAILs max 3224 both with SOQ=0 and with SOQ=1 (soq0/soq1). That failure is a pre-existing
  driver of the front, not caused by SOQ: census/summary.json.

## Rate effect
New BF floor P130 (P129 also passes; P120 failed on rev 1).
- wo_a: 2893 -> 1782 a frame (-1111).
- router: 1269 -> 865 (-404).
In the composer this replaces CALPIPE's wo_a P231 and router P231 (see claude/s81-rate3-1020).

## Adoption limit (OWNER 03:06 / LEAD5)
This is a NEW RTL block inside the closed BF front tile: 672 b of flops. The kit s81bf_front_five_roots_nlock_soq exists (36aa8d0e2),
but it was never gated. It is not contents-only and does not keep the closed views. It needs a BF-front re-closure (gate + route).
The front's own pre-existing census FAIL (max 3224) must be fixed first. Decision = COORD.
