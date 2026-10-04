# DS-ROM correctness (2026-10-04)

Mandatory correctness work on the DeepSeek-V4.1 ROM accelerator. Owner: Claude:dsrom-correctness.

## 1. ROM element second-macro row decode

**Bug** (found by the power-gating stream): in `ot_v41_rom_elem_w10`, configuration entry `2NSEG+1+s` wrote `s_row[NSEG + a[SW-1:0] - 1]`. For `s = NSEG-1` the low bits wrap. As a result:
- the second macro's segment-7 row `s_row[2NSEG-1]` was never written;
- the first macro's `s_row[NSEG-1]` was overwritten;
- entries `a > 3NSEG` aliased onto `s_row` as well.

The image writers emit entry 24 whenever a pair holds 8 segments (`tools/v41_die_images*.py`, `tools/rtl_v41_rom_array.py`).

**Fix** (in place, every copy): `if (NB > 1 && a <= 3NSEG) s_row[a - (NSEG+1)] <= d[15:0]`. The fix is applied to:
- `ot_v41_rom_elem_w10`
- `_nv_w10`
- `_qt_w10`
- `_qp_w10` (and its QPIPE shadow `so_row`)
- `_qz_w10` (and its QPIPE shadow `so_row`)
- `_wake_w10`
- the pre-W10 `ot_v41_rom_elem`

The pinned prepared copies `_w10_rowfix_prepare` and `_w10_rne_wake_prepare` already carry the opt-in fix (`FIX_SECOND_ROW_INDEX=1`, used by `tools/w17_current_fastpp_rowfix_die_rt.py`) and stay byte-identical; their `FIX=0` legacy decode is a control.

The xneed copy already decoded correctly. The pinned watchdog snapshot is left unchanged.

**Test** `rtl/test/tb_v41_rom_elem_cfg_rw.sv` (`tools/dsrom_elem_cfg_rw.py`) writes every entry 0..31 and reads every decoded register back. Write orders: ascending, descending, emitter order, and 400 random writes. Result in `elem_cfg_rw.json`:
- **PASS** on all 11 fixed element builds (1,342–1,705 checks each, 0 errors), including both prepared copies at FIX=1.
- **Controls:** the pre-fix w10 and both prepared copies at FIX=0 FAIL with 60 errors each.

**Element exactness re-proved** on the fixed source (`element_gates/`, pinned commit 54cdd72f9). All four are now run with class/segment 7 live on both macros:

| Gate | Result |
|---|---|
| `w10_frontend_main_exact` | PASS (negative control caught) |
| `dsrom_qtiming_exact` | PASS (8 seeds + fix0; both mutants caught) |
| `dsrom_qz_exact` | PASS (pos / qz0 / xs0; all mutants caught) |
| `rom_stage_pg_sim` | power-aware exact PASS (13 sleeps, 325 restores; no_restore / no_iso / short_lead all FAIL as required) |

The PG bench now runs class 7 on both macros; it used to idle class 7 to avoid this bug.

The S81 1M field records (`results/rtl/dsrom_1m_allmeasured_20261004/field.json`) are not affected. In the worst region of every one of their 167 phases, a pair holds at most 3 segments, so entry 24 is never used.

## 2. Wavefront per-user cross-stage state (integration finding I7)

`rtl/dsrom_sys/integration/ot_rom_pkg_ctrl_wf_ps.sv` is the successor of the S81 controller copies, which stay pinned and unchanged. It adds `SIDE_PSL` (default 0 = as built):
- 2^SIDE_PSL SIDE staging slots per user, slot = position mod 2^SIDE_PSL, stride 2^SIDE_PSH;
- the message count is kept per (user, slot);
- `core_side_off` is the running job's slot offset, which the memory wrapper adds to staging reads;
- a generation bit per slot makes any other slot reuse fail closed (`proto_fault`).

The bookkeeping is `ot_rom_side_pslot.sv`, with a two-stage registered lookup and pre-decoded update enables.

**Bench** `tb_dsrom_pslot_reuse.sv` (`tools/dsrom_pslot_reuse.py`; record `pslot_reuse.json`, verdict PASS). It models one consumer stage (WAVE=1, WIN=6, NW 21, VWA 15) at position 1,048,575. Each job reads the staged top-512 selection three times, once per reuse layer.
- The first position uses the real golden: L2→L3..5, L20→L21..23, L24→L25..27 `ctx_in.sel`.
- Positions 1,048,576.. use labelled stand-ins.

| Case | SIDE_PSL=3 | as built (SIDE_PSL=0) |
|---|---|---|
| 2 positions back to back, SIDE ahead / lead-1, all 3 sources | PASS, 0 word errors | FAIL, 96 word errors (job 0's three reads see q+1's list) |
| 6 positions back to back (slots 7,0..4 wrap) | PASS, 0 word errors | FAIL, 480 word errors |
| hop relay (selection in the HIDDEN payload, the S81 controller's mode) | — | PASS for 2 and 6 positions (per position by construction) |
| q and q+8 both outstanding | proto_fault (fail closed) | — |

Six positions start every 402 cycles with a 400-cycle core, so the hand-off adds 2 cycles.

**Unvalidated:**
- the reuse-layer arithmetic (a behavioural core reads the selection);
- the stand-in positions;
- the upos preset.

**SS/FF screen at 833 ps** (pre-layout; SS 60 ps setup, FF 25 ps hold; `screens/`):

| Block | SS setup | FF hold | Area |
|---|---|---|---|
| `ot_rom_side_pslot`, MAXU 866, in a registered-input frame | +107.1 ps | +2.5 ps | 21,848 um2 |
| `ot_rom_pkg_ctrl_wf_ps`, SIDE_PSL 3, MAXU 16, stage params | +3.9 ps | +5.8 ps | 2,243 um2 |
| as-built controller reference, SIDE_PSL 0 | −117.1 ps | — | — |

In the SIDE_PSL 3 controller, the worst path is the pre-existing core-start cone, not the added state. The as-built reference's −117.1 ps sits on the same core-start cone, which the dsrom-wf-close stream owns.

At MAXU 866, VWA 15, per-user SIDE staging does not fit the vector memory at all. That holds with or without slots, so S81 full shape must use the hop relay or stage in HBM.

## 3. Baseline

- `dsrom_baseline_flags.svh`: `DSROM_BL_SIDE_PSL 3`, plus notes.
- `selection_baseline.json`: `baseline.correctness_20261004`, plus a `not_in_this_die_yet` entry.
