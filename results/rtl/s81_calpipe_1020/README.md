# S81-CALPIPE 10-20: pipelined multi-phase field calendars, compiled by the S81-DV die compiler

Owner 10-20 03:04: "Go with the compiler schedule gaps immediately" (rate-gap class S, results/arch/s81_rate_gap_1020 on
claude/s81-rate-gap-1020@540f0a0d4). Branch claude/s81-calpipe-1020, built on claude/s81-wqbp-1020@36163250c (wq_b P126
calendar plus the wo_a sequence bench).

## 1. Compiler (tools/s81_dv/layer_prog/xs_field_calendar.py, hooked into xs_place.lower_placed / lower_placed_bf)
Every multi-phase field matvec of a layer now gets a pipelined slice-xs calendar. Phase n+1's operand stream is issued
while phase n reduces. Phase n launches at tg0 + n*P, and the element configuration is double-buffered on tags 0/2. The
period P is the op's measured floor on the release frame RTL. A period below the floor is a compile fault (CalendarFault),
never a runtime stall. The calendar uses the layer's whole frame field (xs_place.compile_frame), so its phase indices and
stream bases are the die's global ones. wq_b (+ idx.q on sparse layers) keeps the WQBP emission (xs_wqb_die).

| op | fam | phases | P (floor) | first FAIL | compiled span | RTL span at P | serial span | evidence |
|---|---|---:|---:|---:|---:|---:|---:|---|
| attn.wq_b | fp8 | 11 (die) / 15 (fullsix) | 126 | 124 | 1483 | 1987 (fullsix 15 ph) | 3359 | WQBP |
| attn.idx.q | fp8 | 6 | 126 | 125 | 925 | 925 | -- | FSEQ |
| **attn.wo_b** | fp8 | 4 | **127** | 126 | 701 | **701 / 699** | 1268 | **this lane, wob/** |
| attn.wo_a | bf16 | 12 | 231 | 230 | 2893 | 2893 / 2886 | 4224 | WQBP pipe3 |
| ffn.router | bf16 | 5 | 231 | 230 | 1269 | 1269 | -- | FSEQ |
| ffn.shared_gu | fp8 | 4 | 146 | 145 | 798 | 798 | -- | FGU |
| ffn.experts_gu | fp8 | 24 | 145 | 144 | 3680 | 3680 | -- | FGU/FSGU |
| ffn.down | fp8 | 21 | 130 | 125 | 2889 | 2889 | -- | FDOWN/FSDN |

"Compiled span" is the compiler's static prediction, (n-1)*P + the measured tail. It equals the RTL go-sequence span for
every op at the die phase count, so the static schedule equals the runtime schedule. attn.cmp.wk has one BF phase per
layer (nothing to overlap). eng.wkv (L14, 25 phases) has no measured floor and stays outside this calendar (open).

Operand buffers: no STOP is needed. Every op already has the second buffer the overlap needs: double-buffered element
configuration banks (tags 0/2, cfg7 swap), and the op's x is resident for all its phases (FP8 uses one x; BF16 uses one
resident K segment per phase, with the PHASE_VM reload measured). There is no RTL change.

Static checks run on every emission:
- **Op level:** rows ordered and unique, <= 4096; streams disjoint; a tag is reused only after its retire; ROM bounds;
  is_d delay line <= ND; launch spacing == P; P >= the measured floor; the FP8 element window (P >= 88,
  2P >= 195 + cfg_lead); for BF, spacing >= 231 (segment-label floor).
- **Layer level:** op segments are in execution order with no overlap (first accept > previous last retire), and the
  is_d edges are unique.
- **MU:** user windows modulo the MU period are disjoint, and the field busy span is <= the slot.

Fleet ep9 runs (`compiler/run_fcal.sh`, evidence in `compiler/evidence/`):
- `dvc_L0` / `dvc_L2` (dv_layer_compile, real fixtures): all 7 (L0) / 8 (L2) field op calendars were emitted as
  prog/xs/<id>.calendar.json, with ROM images and is_d; static PASS.
- `die_nominal` (L0 L2 L14 L20): every op is static PASS. MU: 46 AR / 10+1 MTP slot calendar (calendar_{ar,mtp}_cal1,
  claude/s81-cal1-1019@152d70002), 0 collisions. The field busy span is 12,486 (L0) / 13,250 (sparse), against an AR slot of
  21,505.7. The windows are field-packed (ASAP). With the DAG start times the field windows sit inside the cal1 stage windows.
  Shorter op spans only shrink those windows, so the cal1 shift lemma (5,474 windows, 0 collisions) still holds unchanged.
- Negative controls: `die_neg_wob126` (wo_b P126) is a COMPILE FAULT; `die_neg_woa230` (wo_a P230) is a COMPILE FAULT on
  both the floor and the 231 segment label. The selftest has 23/23 expected verdicts (each op at floor PASS and at
  floor-1 FAULT, stream longer than P, family mismatch, injected op overlap, injected MU shift collision):
  `compiler/evidence/out_selftest.json`.

**FINDING (die integration, not a pipelining cost): the whole-layer field calendar does not fit the xs calendar ROM.**
The layer image needs 6,091 rows (L0) / 6,501 rows (sparse), against the 4,096 rows of ot_s81sl_xs pq_calendar
(ot_rom_4096x72_m8 pair, is_d base 12 b). Row counts per op: experts_gu 2,091, down 1,450, wo_a 829, wq_b 750. A serial
calendar needs the same rows, because there is one STREAM_REQ row per stream word. Each op segment fits alone. A die
with several layers per stage needs proportionally more. The minimal RTL change is posted to LEAD4-S81: a burst stream
action (one row requests nb consecutive words, about 6 rows a phase, about 700 rows a layer) or a deeper calendar ROM.

## 2. RTL bench: attn.wo_b (wob/run_wob_seq.sh)
- **Vehicle:** TOKSIM-S81C/FSEQ tb_toksim_fgu_seq +RETIRE, on the release 19bf4121e frame exes v_h9nx_e5 (u_f_0L00) and
  v_h10_e2 (u_f_0L01), Verilator 5.050.
- **Inputs:** the FWOA wo_b phase vectors p1..p4 (xs_place gen; released L0 fixture, real rank-0 rows; fp8 K 2048, nseg 2;
  10 rows per phase).
- **Check:** toksim_fgu_check seq (per-row golden segment tree bit-exact, coverage, cycle-exact calendar at the compiled
  spacing).

| P | u_f_0L00 | u_f_0L01 |
|---|---|---|
| 316 (serial) | 1266 PASS | 1268 PASS |
| 200 / 160 / 145 / 135 | PASS | PASS |
| 130 / 129 / 128 | PASS | PASS |
| **127** | **699 PASS** | **701 PASS** |
| 126 / 125 / 124 / 122 / 120 / 110 / 100 | FAIL (4 / 6 / 6 / 16-22 / 20 / 26 / 26 words) | FAIL |
| XCORRUPT (x sign flip) at P128 | FAIL 4 | FAIL 4 |

Run 1's XCORRUPT flipped bit 0. That bit lands in the unused low half of the word, so the control PASSED and was invalid.
It was replaced by a bit-31 flip (run 2), and the logs of both runs are kept.

wo_b per instance is 701 + 146 (r8 die wire) + 28 (die tiles) + 26 (owed CAP edges) = **901**, against 1,464 serial.
Fleet units: ep9 oth-ubuntu-2360330 / 2386115 / 2386128.

## 3. Composed rate (tools/toksim_s81_compose.py --scenario ..., records in scenarios/calpipe/CALPIPE.json)
| step | AR tok/s | MTP tok/s |
|---|---:|---:|
| measured now (cycles.json, --check PASS) | 834.0 | 2,649.1 |
| + wo_b P127 alone (calpipe-wob) | 846.7 | 2,683.6 |
| + wo_a P231 alone (calpipe-woa) | 865.4 | 2,734.4 |
| + wq_b P126 alone (wqbp-p126) | 867.1 | 2,738.9 |
| **wq_b + wo_a + wo_b (calpipe)** | **915.9** | **2,869.4** |

The projection for F1+F2+F3 was 897.8 to 943 / 2,867 to 2,989 (set B also includes top-k and window_load). These are
scenario files, PROPOSED, not cycles.json. Adoption into the headline is a COORD decision (TOK.DS.RATE). The remaining
MTP gap to ~3,000 is about 131 tok/s. Projected closers:
- top-k final F5 (S81-TOPK): about +81 MTP;
- router segment tag F4 (LEAD4-S81 RTL): about +22;
- window_load prefetch F8: about +16 (S81-CALPIPE-WINPF sub-lane);
- experts_gu / down / router / shared_gu: already at their floors, so no further compiler gain. Going further needs the
  F4 tag (BF P231 -> P145) or element-replay RTL.

## Open
- CAP cfg_d descriptors for the die shapes (only the fullsix 6-frame lowering exists). The rank-local row tags of the
  image writer.
- The layer calendar ROM capacity (finding above).
- The FSEQ benches are driven by the bench's uniform go at the compiled P. The compiled go times equal n*P by
  construction, and the spans match exactly, but no slice-xs vehicle has yet run the compiled ROM images for any op other
  than wq_b.
- eng.wkv has no floor. shared_gu is still off the DAG critical path (rate-gap note).
