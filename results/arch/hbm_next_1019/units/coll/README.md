# HBM-NEXT-UNITS-COLL: COLL N-row message train and the 5th delivery lane (2026-10-19)

This is next-release work at P = 4, not a release gate. Branch `claude/hbm-next-units-coll-1019`. It is an isolated fork: no d4g/GEN2 files are edited, and every name uses the `hnx` prefix.

## Verdict

- **The on-die gather master runs an N-row record as ONE message train, and it is bit-exact.**
  - RTL: `rtl/hbm_next/coll/ot_hnx_coll_gq.sv`, a fork of the d4g `ot_hgi_coll_gq` (gq_issue / gq_land, the masters `hcollgi_<q>` / `hcollgl_<q>`).
  - It needs one fire and one 40-edge drain per record. Each further row costs **3K/2 edges** (K = ceil(F / R) ring indices a row).
  - The measured cost equals the CMTP price "COLL.* II = payload x N, fixed part once" (R4) for the on-die ring all-gather.
- **N = 1 reproduces d4g bit for bit.** The bench row set of `tb_hgi_coll_gq` runs unchanged on the fork. It passes with identical counts: 2,644 VM words, 3,104 reads and 5,288 writes, every one at its compiled (bank, edge), with 38 ISA pass-through checks.
- **Mutants:** all three FAIL. m6 (source ignores rs_A) has 10,872 errors, m7 (landing ignores rs_O) 20,909 and m8 (the row-local k never restarts) 22,037. The fail witnesses are committed under `witness/`. The d4g fault scenarios 1-4 and the new f5 (rs_O breaks the bank rule) all fault as required.
- **The 5th delivery lane (L = 5) is a DIE + COLL-body + SU change, not a gather-master change.** It is specified below. It touches the critical `ot_hgi_coll_ctl_v5`, so that part is report only.

## Mechanism

The descriptor row gains three fields. The payload is still 224 bits.

| bits | field | meaning |
|---|---|---|
| [104:101] | nm1 | N - 1 (N = 1 .. 16) |
| [120:105] | rs_A | source row stride (signed, VM words) |
| [136:121] | rs_O | destination row stride (signed, VM words) |

These are the ROWX nm1 / rs_A / rs_O of HGI-1R, as the COLL record adapter would hand them over.

- **Train index.** The train index is t = r·K + k.
  - t drives the issue slot {even, odd, idle}, the direction t & 1 and the tag t mod 8.
  - So the link, lp-slot and arrival schedule is the d4g schedule of one gather of N·K ring indices, and the link proof carries over.
  - Addresses use the row-local flit i = flit_i(k, ring) of row r: src + r·rs_A + ..., and dst + r·rs_O + s·stride + i.
- **Bank rule.** With N > 1, rs_O must equal R·K (mod 8). Under that rule every landing bank equals the single gather's bank. The descriptor check faults otherwise (fault scenario f5 PASS).
  - The bank rule is proven with zero conflicts for F < 200, N = 1..6, R = 1 and 2, plain and QBG (`bench/check_train.log`).
  - A wrong rs_O (for example 96 for the QBG F19 R2 shape) gives 88 bank conflicts in the model.
- **State.**
  - The pipeline entry is {row[3:0], k[9:0], t[2:0]} (17 bits instead of 10), on ld_ev_k.
  - ld_desc gains rs_O (53 to 69 bits).
  - Row-offset tables: soff[r] = r·rs_A in the issue leaf, and roff[r] = r·rs_O in the landing leaf. Each is 15-16 x 13-bit registers, loaded from the held descriptor.
  - The landing pre-stage gains one 13-bit addend. **Gate risk:** that path measured -323.9 ps before the d4g pre-staging fix, so the re-gate has to look at it.
- **QBG exponents need no per-row reset.** Every row has the same Bs, and its Bs exponent bytes are all rewritten by its own code flits before its first exponent flit leaves.

## Measured cycles(N) (RTL, fleet Verilator 5.050, ot-epyc4, bundle a2880082)

Span = fire to the last VM bank-write sample. The N = 1 columns of the set-1 shapes are the set-0 (d4g) runs. Every write is checked at its compiled edge, and the observed span equals the compiled span on every row. The data is in `bench/cycles_N.txt` and `bench/s2.log`.

| shape | N=1 | N=2 | N=3 | N=4 | N=6 | measured II a further row | price (c1 + (N-1) x payload) | N separate d4g gathers, N=4 |
|---|---:|---:|---:|---:|---:|---:|---|---:|
| plain R2 F64 (K 32) | 87 | 135 | 183 | 231 | 327 | **48.0** | 87 + 48 (N-1): equal | ~351 |
| QBG R2 F19, DS expert intermediate (K 10) | 54 | 69 | 84 | 99 | 129 | **15.0** | 54 + 15 (N-1): equal | ~219 |
| plain R2 F72 (K 36), set 1 | 93 | | | 255 | | 54.0 | equal | ~375 |
| plain R1 F19, rs_A = -24 (K 19) | 68 | | 125 | | | 28.5 (1.5 K) | equal | |
| QBG R1 F9, o_group (K 9) | 53 | 66 | | | | 13 (alternates 13 / 14, mean 1.5 K) | equal | |
| plain R2 F1 (K 1) | 41 | | | | 47 (N = 5) | 1.5 | equal | |

- **Further-row II = 3K/2 = 0.75 F (R = 2) or 1.5 F (R = 1).** It equals the issue part of the d4g pricer's `collq_span` for N·F flits (`tools/hgi_sim/d4g_quadrant_1017.py`). The one exception is odd F with R = 2, where the train costs at most 1.5 edges a row more.
- **Saving against per-row records:** -45 % for plain F64 and -72 % for QBG F19 at N = 4.
- The model price is in `tools/hbm_next/hnx_coll_gq_train.py price` (`bench/price.jsonl`).

## Collective bandwidth at P = 4 (from the Phase-1 runs, `claude/hbm-next-study-1019` runs/coll_lanes.json)

In the DS multi-user step at P = 4, COLL is busy for 492,543 of 1,099,571 cycles at L = 4. That falls to 461,240 at L = 5 and 430,269 at L = 8.

**Delivery share.** If the delivery term (G-1) f / L scales as 1/L:
- The L 4 to L 5 delta (-31.3k) gives about **156.5k delivery cycles** at L = 4.
- The L = 8 delta gives about 124.5k. The 1/L scaling is not exact, because of ceilings and nominal overlap.
- So delivery is about 25-32 % of COLL busy. The other ~336-368k cycles are fixed parts (741.7 cycles each: endpoint, the 377.6 ns crossing, the tail). That is about 450-500 collectives a step.

**Bytes and rates.**

| quantity | value |
|---|---|
| bytes delivered into a die | 125-157k x 256 B = 32-40 MB a step = 29-37 B/cycle on average (35-44 GB/s) |
| SerDes raw (32 x 100G) | 400 GB/s |
| average as a share of SerDes raw | 9-11 % |
| peak while delivering, L = 4 | 256 B/cycle = 307 GB/s |
| peak while delivering, L = 5 | 320 B/cycle = 384 GB/s: 96 % of raw, inside the 320-385 GB/s framed range |

**The network is not the ceiling. The fixed part is.** The message train is what keeps P = 4 alive: each MU or MTP record pays its 741.7 once instead of once per row. Without trains, each further row of the ~450-500 COLL records a step would pay another 741.7 cycles. That is an upper bound of about +1.0M cycles a step at N = 4, which would double the step.

## What DIE must widen for L = 5 (5th delivery lane, 64 B, +2.7 % aggregate)

The per-quadrant COLL parent `hb_coll_<q>` (`ot_hfd_coll_q3_hard_v8x` SW, `ot_hfd_coll_q2_hard_v8g` SE/NW/NE) has 4 delivery outputs today:
- `g_delivery` j < 4;
- `del_valid[3:0]`, `del_flit` 4 x 545, `hgi_del_obase` 4 x 40;
- each goes to `cxdl_<q><g>` (`ot_hbm_su_static_cxport_dl`, kit hbm_su_cx_dl_1017), then to `su_<q><g>.dw_*`.

The deliveries are replicated per quadrant, so the 4 lanes of a die carry 256 B/cycle of distinct data. L = 5 therefore means one more lane in **every** quadrant.

| item | change per quadrant | bits per face |
|---|---|---|
| COLL body switch | ND = NPT + 13 -> NPT + 14 (one more sink); every qslot output slice (17 x 32-b + 1 x 1-b, `ot_hgi_coll_qso_*`) gains one destination; sink_slot +1 b, sink_select +4 b a slice | inside hb_coll (re-gate of the qso slice kits) |
| control (CRITICAL: ot_hgi_coll_ctl_v5_*) | delivery_obase_pin 160 -> 200 b, dest_v ND + 1; the compiler's delivery-lane count 4 -> 5 | report only, no REVIEW / submit |
| hb_coll_<q> to new tile cxdl_<q>4 | del_valid 1 + del_flit 545 + del_obase 40 | **586 b** on the hb_coll face towards the SU band |
| cxdl_<q>4 to SU | dw_v 2 + dw_row 18 + dw_d 1,024 | **1,044 b** |
| SU landing | today 4 SU slices take 1 lane each; lane 4 needs either a 5th SU slice / RF write port, or a second dw port on one slice (2 rows/cycle -> 4) with a static calendar split | SU decision (HBM-NEXT-UNITS-SUDMA / DIE) |
| SerDes / links | unchanged count and flit widths (32 x 100G; 612-b link flits); 320 B/cycle <= framed SerDes | none |

**Die total:** 4 x (586 + 1,044) = **6,520 new die-level bits**, all quadrant-local. No cross-quadrant bits are added, so the ring cut is unchanged. Plus one new tile class instance a quadrant (cxdl, same kit with G = 4).

## Files

- RTL: `rtl/hbm_next/coll/ot_hnx_coll_gq.sv` (`ot_hnx_coll_gq_issue` / `_land` / `_gq`, `ot_hnx_coll_kq_share2(_leaf)`).
- Bench: `rtl/hbm_next/coll/tb/tb_hnx_coll_gq.sv`. Option `+set=0/1/2` selects the d4g rows, the trains or the cycles(N) scan. Option `+fault=1..5` runs the fault scenarios.
- Fleet script: `tools/hbm_next/hnx_coll_bench.sh OUT main|m6|m7|m8`.
- Model / proof / vectors: `tools/hbm_next/hnx_coll_gq_train.py` (check-train, vectors-rows, price). This is a fork of `tools/hgi_sim/collq_gather_1018.py`.
- Evidence: `bench/` (verdicts, logs, cycles_N, check logs) and `witness/` (mutant fail witnesses).

## Step 2 (10-19 restart agent): endpoint train, L = 5 landing, re-gate

### Off-die endpoint train: no RTL change (the critical `ot_hgi_coll_ctl_v5` is untouched)

The d4g COLL ISA already runs an N-row record as **one issuer loop**. The loop iteration is the row/flit counter, and the per-row steps are real RTL arithmetic: `iter_inj_idx_step`, `iter_inj_addr_step`, `iter_vm_step`, `iter_del_step`, `iter_rgx_step` and `iter_link_slot_step` in `ot_hgi_coll_iter_mul` + `ot_hgi_coll_q_static_ctl_v5`. A non-dense destination stride (rs_O) is handled by the compiler, which splits the delivery loop row at every row boundary. The endpoint, the 453-edge crossing and the tail are paid once, and the link sequence slots run on through the whole train. So ROW_GATHER, kv gather (the same shape) and ARGMAX_MERGE need only the compiler (`tools/hbm_coll_static/row_gather_rows.py`, `argmax_rows.py`).

**Measured (fresh, fleet Verilator 5.050, `tools/hbm_next/hnx_coll_rows_bench.sh`, `rows/`).** The bench runs the current die-bound native V4 quadrants (q3 SW + q2 host_v4, one die, SPMD loopback at W = 453). The ctl_v5 / issuer_v6 / hard_v8 parents are cycle-locked to them (+2 edges, `tb_hgi_coll_q_hard_v5`). Every flit's data and address is checked.

| record | N=1 | N=2 | N=3 | N=4 | N=6 | further-row II | price |
|---|---:|---:|---:|---:|---:|---:|---|
| ROW_GATHER, DS MTP verify bypass (96 ranks x 13 rows x 288 B, R = 623 flits a rail) | 1,113 | 1,736 | 2,359 | 2,982 | 4,228 | **623.0** (= R: payload only) | model row II 1,449: the measured II is lower |
| ARGMAX_MERGE G96 (q3 ARG fold) | 53 | 85 | 117 | 149 | 213 | **32.0** | priced 23.7: +8.3 a row (+42 cycles a 6-row record, ~0.2 % of the step) -> CMTP to use 32 |

- ROW_GATHER delivered 3,115 / 6,230 / 9,345 / 12,460 / 18,690 flits exactly.
- The mutants are rejected: row stride dropped (addr_err 9,345), link-slot step dropped (data_err 12,450), ARGMAX operand step dropped (data_err 3). The witnesses are in `witness/rows_*.log`.
- The bench copy `rtl/hbm_next/coll/tb/tb_hnx_coll_rows.sv` fixes the d4g ARGMAX lane-count verdict (it applied P x R to every lane).
- The script's anchored grep missed the padded ARGMAX verdict lines, so the logs were re-read with the corrected regex (`rows/verdict_reread.txt`). The script is fixed.
- The q3 TKM is the KMAX-64 copy, as in `run_q_hard_v5_bench.sh`: neither op starts the TKM.

**The other COLL ops are also compiler-only.**
- **TOPK_MERGE:** N rows = one gather train plus N serial TKM merges (TKM measured 2,834 cycles a merge). Each row's TKM start is its own programme row, carrying its own `tkm_cfg_obase`, plus a wait loop. That is 2 rows a TOPK row.
- **ALL_GATHER / GROUP_REDUCE_MCAST, x N payload:** the steady loop count grows by the payload. The prologue and epilogue are paid once, and the compiler writes the epilogue's link slots as absolute 16-bit sequences.
- **Limit:** the 64-row programme store. ROW_GATHER at N = 6 uses 33 / 31 rows (q3 / q2), and ARGMAX uses 64 at any N (a software-pipelined body).

### L = 5: the SU landing decision (RTL + bench)

**Decision: lane 4 lands in the free half of the existing SU slice ports.** There is no 5th SU slice and no new RF write port.
- Each pgslice already has two independent delivery write groups: `dw_v[HI]` writes banks 16HI..16HI+15 at `dw_row[9HI+:9]`, and `dw_v` = 2'b11 writes both.
- A d4g lane uses one of them a serial edge: 3 stream events per 4 stream edges, one 64-B flit each.
- **Lane 4 path:** lane 4 is a neighbour chain along the quadrant's SU band (`ot_hnx_su_cxdl_tap_s`). The tap registers one stream edge a hop and keeps the flits with ob[5:4] = s, using the unchanged d4g `dl_s` leaf behind a slice filter.
- **Serial leaf:** `ot_hnx_su_cxdl_q2` is the d4g `dl_q` with a second bank pair. Each half is own | lane 4 (AND-OR).
- **Schedule:** the compiler's static calendar puts every lane-4 flit where the own lane's flit of the same event is in the other half. A same-half collision is a compile error, and the leaf latches FAULT.
- **Faces:** the slice's dw face (1,044 b) is unchanged.

**Bench `tb_hnx_su_cxdl5` (fleet, `tools/hbm_next/hnx_cxdl5_bench.sh`, `cxdl5/`): PASS.**
- **Lockstep with the four d4g `ot_hbm_su_static_cxport_dl` leaves, lane 4 idle:** 3,060 serial edges, legal plus violation traffic. Every dw / fault bit is identical.
- **640-flit region:** L = 4 lands in 167 serial edges and L = 5 in 135, every flit exactly once. Net of the 8-edge start, that is x1.25 = 5/4.
- **Forced same-half collision:** FAULT.
- **Mutants:** 11 (collision unchecked), 12 (tap ignores the slice) and 13 (lane-4 halves swapped) FAIL. The witnesses are in `witness/cxdl5_m*.log`.

**DIE bits a quadrant at L = 5** (replaces the earlier "cxdl_<q>4 -> SU 1,044 b + new SU port"):

| link | bits | notes |
|---|---:|---|
| hb_coll -> tap 0 | 586 | lane-4 stream |
| tap s -> tap s+1 | 3 x 586 | neighbour hops across the SU band; DIE checks hop length <= reach at the stream clock |
| tap s -> serial leaf s | 1,065 a slice | abutted, the same seam as dl_s -> dl_q |

- No new dw port and no SU RF change.
- The COLL body side (ND + 1 sink, qso slices, ctl delivery_obase 160 -> 200 b, the compiler's lane count 4 -> 5) is still as specified above. The ctl part touches the critical `ot_hgi_coll_ctl_v5`, so it is report only.

### Re-gate (hnx kits, closure daemon)

- `physical/ref_tile/hnx_gq_issue_1019` and `hnx_gq_land_1019` are forks of `hcoll_gq_*_1018`.
  - Same outline (237.6 x 237.6) and faces; ld_desc is 53 -> 69 b and ld_ev_k 10 -> 17 b.
  - io_hold_margin is 0.03, and the reset landing is the current main flow.
  - The benches are `hnx_coll_bench.sh` main + m6/m7/m8, with committed witnesses.
- Both were SUBMITTED through submit_exact at be0562a05: `hnx_gq_land_1019-n1-be0562a05` and `hnx_gq_issue_1019-n1-be0562a05`.
- **Watch:** the landing pre-stage adder (+13-b roff).
- Neither is on a critical list, and ctl_v5 is unchanged.

### Closure verdicts n1 (collected 10-19 06:20, UNITS lead)

- `hnx_gq_land_1019-n1-be0562a05`: **CLOSED** TT +10.38 / FF +26.08 ps, DRC 0 (SS sensitivity -337). The daemon recorded it on `codex/closure-record-hnx_gq_land_1019-n1-be0562a05` (2d4230d39). Its auto-merge to main hit a conflict in 5 tools files; that is on the daemon side.
- `hnx_gq_issue_1019-n1-be0562a05`: **NEEDS_RTL** TT -111.78 / FF -14.47 ps, DRC 0. The worst path is `soff[13]` -> row base add -> `+ i` -> the 8:1 `rdw` select fanned to the 512 `p_d` bits: the hnx row-offset adder chain feeds a high-fanout select.
  - **The fix is owned by lane HNX-GQ** (`claude/hnx-gq-1019` @72d501b02: GQISSUE2 class ported to the train, FF hold included), submitted as `hnx_gq_issue_1019-n2-72d501b02`.
  - A parallel UNITS-lead fix (9042294f5) was reverted here and its job `-n2-9a3cc2166` cancelled as a duplicate.

## Next

1. **Collect the two closure jobs** (pending_results). On a timing fail of gq_land, check the roff adder path first.
2. **CMTP:**
   - set the ARGMAX_MERGE row II to 32 (measured) and ROW_GATHER to R (measured 623 at the DS verify shape);
   - emit COLL N-row records as issuer loops (row_gather_rows / argmax_rows are the reference lowerings);
   - add the lane-4 half calendar for L = 5.
3. **L = 5 COLL body:** fork the qso slices with one more sink (NDEL 5). The ctl_v5 delivery_obase widening (CRITICAL) is report only. Gate the tap and serial leaves (`ot_hnx_su_cxdl_tap_s`, `ot_hnx_su_cxdl_q2`) as hnx kits from `hbm_su_cx_dl_1017`.
4. **gq train:** the record-adapter decode of ROWX (nm1, rs_A, rs_O + the rs_O = R K mod 8 rule) into the gather descriptor.
