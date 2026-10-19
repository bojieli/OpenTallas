# HBM-NEXT-UNITS-SUDMA2: SU.VOP row II, wide ARGMAX.LOCAL, programme-column row code

Lane HBM-NEXT-UNITS-SUDMA2, 2026-10-19, branch `claude/hbm-next-units-sudma2-1019`. Next-release work, not a release gate.
It follows `../sudma/README.md` (SU_DMA, 01:41), which measured SU.VOP II 44/72 and ARGMAX.LOCAL II 169 against prices of 7 and 6.

All benches ran on the fleet (ot-epyc4 = `regular-crane`; ot-epyc5) with Verilator 5.050 (`verilator.txt` in each folder).
They use `tools/hbm_next/hnx_sudma_bench.sh` from a `git archive` bundle of `f76f44b19` (stages w0 to w3, aw), `0ce18a1a7` (stage p)
and the synth script `tools/hbm_next/hnx_sudma2_synth.sh` (Yosys + ASAP7, area in um²).

## Measured row II against the price

| Record | cycles(N), first command to last write | Measured II | Before (SU_DMA) | Price | Verdict |
|---|---|---:|---:|---:|---|
| SU.VOP `AB`, n = 7,168 (nv = 14), split write phase | N1 152, N2 180, N3 208, N4 236, N6 292 | **28** | 44 | 7 | EXACT. Store write port no longer binds; VM fill bandwidth binds. |
| SU.VOP `ABC`, split write phase | N1 180, N4 348, N6 460 | **56** | 72 | 7 | EXACT. Same binding. |
| SU.VOP, wsplit 0 (d4g schedule on the hnx top) | `ab_n1` 160, `ab_n4` 292, `abc_n1` 216 | 44 / 72 | = stage s0 | | EXACT. These are the d4g cycles and writes, bit for bit. |
| ARGMAX.LOCAL, DS n = 1,347 (169 sectors), wide reader | P1 67, P6 177 (edges G to done) | **22** | 169 | 6 | EXACT on 3 seeds. Slice read bandwidth (8 banks) binds. |

### SU.VOP split store write phase (`wsplit`)

**Mechanism.** Each pinned store bank still has one write port. The new RTL time-shares it in a fixed phase, so the lane result no longer costs its own write edges.
- The fill writes the HI = 0 store groups on even bank-write edges and the HI = 1 groups on odd edges.
- The compiler puts each lane-write edge W on a fill-HI0 edge. HI = 1 banks commit the lane result at W, while the fill is on HI0. `ot_hnx_su_wsplit` defers the HI = 0 banks' result to W + 1, while the fill is on HI1. No queue, no ready: a collision faults (`st_conflict`, `clash`).
- Files: `rtl/hbm_next/su/ot_hnx_su_wsplit.sv` (one per pinned bank) and the forks `ot_hnx_su_pgslice.sv`, `ot_hnx_su_quarter.sv`, `ot_hnx_su_top.sv`. The `wsplit` parameter is 0 for the d4g behaviour.
- The compiler is `tools/hbm_next/su_rows_compile.py --wsplit 1`. Its schedule is II = 2·k·nv512, where k is the number of per-row VM operands. Before the change it was (2k + 1)·nv512 + 2.

**Why it stops at 2·k·nv and not at the price of 7.**
- The fill is now the only thing on the store write port. The 32 VM read ports deliver one 512-word vector every 2 edges.
- Reaching 7 would need about 4x the VM-to-SU fill bandwidth (k·nv / 4 edges a row), or a fill bypass straight into the lane operand.
- That is a VM/SU datapath change. It is not proposed, because the SU is not the bottleneck (about 157k busy of a 1.28M P = 6 verify).
- CMTP should price SU.VOP rows at II = 2·k·nv512.

**Area.**
- `ot_hnx_su_wsplit`: 17.99 um², 87 cells (`synth/area.txt`).
- One per pinned bank: 512 banks give about 0.009 mm² for the SU.

**Bench.** `rtl/hbm_next/su/tb/tb_hnx_su_rows_ws.sv`, a fork of `tb_hnx_su_rows` with the same independent NumPy golden.
- What is checked: every LG write (edge, quarter, port, sector, mask, data), the per-edge lane write count, zero DUT/rowx faults, and that every expectation is consumed.
- Positive cases (`wsplit/w0/verdict_w0.txt`), all PASS: `AB` at N = 1, 2, 3, 4, 6; `ABC` at N = 1, 4, 6; and wsplit 0 on the d4g vectors `ab_n1`, `ab_n4`, `abc_n1`.
- Fail witnesses, all committed:

| Witness | What it breaks | Result | Log |
|---|---|---|---|
| `ws_ab_n4_fw11` | schedule parity: lane writes on the wrong phase | FAIL, 1,742 errors | `wsplit/w0/run_w0_ws_ab_n4_fw11.log` |
| WMUT 1 | deferral dropped | FAIL, 942 errors | `wsplit/w1/` |
| WMUT 2 | the HI = 1 half deferred instead of HI = 0 | FAIL, 1,710 errors | `wsplit/w2/` |
| WMUT 3 | deferred address not captured | FAIL, 1,792 errors | `wsplit/w3/` |

### Wide ARGMAX.LOCAL (`ot_hnx_argmax_wide_rows`)

**Mechanism.** The reader takes one beat of up to WS = 8 consecutive sectors per edge.
- Sectors cs to cs + 7 sit on the 8 distinct banks of the SW slice, so a beat is one read per bank: the slice's full read bandwidth.
- The closed engine `ot_hgi_argmax18_m` runs at LP = 64 lanes. This is a parameter change only. The lower-index tie tree keeps `numpy.argmax` semantics.
- Row read period = max(ceil(ns / 8), PMIN). PMIN = 6.

**Why PMIN = 6.** A 5-edge period re-uses the hub write-tag slot too early.
- The PMIN 5 run FAULTS the hub on seeds 1 and 2 (rows 4, n 64). Witness: `argmax/pmin5_witness/`, bundle `6ca25c769`.
- `f76f44b19` sets PMIN to 6.

**The remaining gap to the price of 6.** 1,347 words need 22 beats on one slice. The price would need a row spread over about 4 slices; that is a compiler/VM placement question.

**Area.**
- The wide reader is 29,764 um², 220,524 cells.
- The 8-lane reader is 4,342 um².
- The difference is +0.025 mm² per instance.

**Bench.** `rtl/hbm_next/argmax/tb/tb_hnx_argmax_wide.sv` with vectors from `tools/hbm_next/hnx_argmax_wide_vectors.py` (seeds 0 to 2). Verdicts are in `argmax/verdict_aw.txt`.
- MUT 0 PASS on 3 seeds. The 4 faults are the deliberately illegal records.
- WS 1, PMIN 1 on the ORIGINAL vectors PASS. That is the original reader, edge for edge (`aw_mo_so.log`).
- Mutants, all FAIL on every seed:
  - MUT 1: A row stride;
  - MUT 2: O row stride;
  - MUT 3: id offset taken from row 0;
  - MUT 4: beat bank rotation dropped;
  - MUT 5: last-beat sector mask dropped.

### Row code as a programme column (next-list item 1 of SU_DMA)

**Mechanism.** The 20-bit row code moves into the spare top bits of column 9.
- The quarter line grows from SB 2422 to 2442 b, with the same 10 columns.
- `su_rows_compile.py` emits `prog_rc.mem`. The d4g compiler `su_programme_compile.py --line-bits 9768 --partition 4` builds the dictionaries.
- The d4g producers `ot_hbm_su_programme_part` (PIPE 2) are unchanged and run lockstep against the monolithic producer and the golden.

**Results** (`progcol/verdict_p.txt`):
- `ws_ab_n6` PASS: 296 edges, 52 macros (49 for the monolithic producer).
- `ws_abc_n6` PASS: 464 edges, 64 macros (60 monolithic).
- The template, pcoff and phase mutants FAIL, as they do in d4g.
- `rcdrop` (the image compiled without the row code, checked against a golden with it) FAILS.

**Not done.** `sfu_programme_store_r10` is a CRITICAL prefix, so no tile was gated or submitted for this item.

## Not done (next list, in risk order)

1. **Reducer row class**: red a/b/dst scratch and RF tag stride per row, for norm-style SU.VOP rows. Without it, each row's scratch words go into the image, and only the red column dictionary grows.
2. **SFU chain row stepping** (`ot_hgi_sfu_core_split3`, `sfu_lg_pair_tap_leaf*`): the address step per `start_loops` iteration.
3. **FUSED.QDQ rows** (`hb_quant_*`, n/32) and position-addressed **DMA.LOAD** rows. Neither has been measured yet.
4. **Gate the touched hnx tiles** with hnx kits: the `ot_hnx_su_pgslice` + `wsplit` slice and `ot_hnx_argmax_wide_rows`. Report the SU parent and the programme store as CRITICAL; report only.
5. **CMTP re-price**:

| Family | II to price |
|---|---|
| SU.VOP | 2·k·nv512 (`wsplit`) |
| ARGMAX.LOCAL | max(ceil(ns / 8), 6) = 22 for DS |
| DMA.KVWB_DS | 8, plus 28 per wrap (unchanged) |
