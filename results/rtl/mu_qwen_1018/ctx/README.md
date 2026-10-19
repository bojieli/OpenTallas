# MU-QW-DIE (2026-10-19): Qwen compute-die MU RTL ready for the die GEN

Lane MU-QW-DIE. Branch `claude/mu-qw-ctx-1019`, based on main after the ROOT merge of `claude/mu-qwen-all-1019`
(main 3fd57606f / fc6c3fa25). Every bench runs on the fleet with Verilator 5.050. Logs are in `runs/`.

## 1. Filler initial context (coordinator 0ka)

- The OPSEG fillers' prompt token and position are loaded at boot as a context record. The bench-only preload
  (`QFD_CTLM_MU_BENCH_PRELOAD`) is gone.
- Transport: the calendar image words DW5 and DW6, which were reserved 0. They reach the cluster as dh DW rows, the
  same boot word path as the rest of the image (no port change).
  - `qfd_dv_cmd_cal_mu #(CTX_DW 1)`: the seal accepts non-zero DW5 / DW6. `ctx_dw` = {DW6, DW5} (its own `dwr`
    registers). `ctx_load` = the accepted seal edge.
  - `qfd_tt_ctlm_dv` OPSEG: CTX[36(u-1) +: 36] = {tok 18, pos 18} of filler u. CTX[110:108] = load mask, CTX[111] = 0,
    CTX[127:112] = tag 16'h4D43. A good record loads the masked fillers' banks. A bad record sets a sticky `op_fault` and
    loads nothing.
  - Compiler: `mu_opcal.ctx_words` / `with_ctx` (tests in `test_mu_opcal.py`).
- **Open (coordinator 2nd message):** a host-context leaf BESIDE the closed face, written by the host config plane. On
  this die the only boot word path into the ctlm is the face's image replay (mask config ROM under host BEGIN/AUTH),
  so this record is image content. No host-written producer exists on the compute die
  (`static_link_bind.py`: "cfg_* (HOST config writes) ... no producer port exists on the compute die yet").
  - The consumer side (`ctx_dw` / `ctx_load` into the banks) is the part a host-context leaf would drive. Moving the
    source to such a leaf changes only the transport.

## 2. QW-DIEFIX / QLB-C4b contract taken into the MU ctlm

- **hr pack** (509af6b5e + 788bef159, cherry-picked): `qfd_tt_ctlm_dv` hr = {pack(ib_q), xpf, v}. In lpf the pack sits
  in the wires-only `u_thru`, because lp.py refuses a clock-less parent instance. `hr_contract.py` follows a
  child-port pack (+ test), and every variant is packed (`check` PASS: ctlm, lpf, lpf_lp).
- **tl / TLOAD** (d8b6a157e): `qfd_dv_cmd_cal.sv` is taken. TLOAD is ported into `qfd_dv_cmd_cal_mu`:
  - the block read takes the shared read port, and no playhead is granted on the issue edge;
  - same checks;
  - MUT 4 / 5.
- `qfd_tt_ctlm_dv` gets a `tl` port (MUT 30 / 31; QLB-C4b's 9 / 10 clash with HARD_HR's 9). lpf routes tl through
  `u_thru` (one more landed crossing, 1,088 b).
- Not taken: the GEN16 die work and redstn2 (a slice change). Those belong to the die and slice lanes.

## 3. Landed form (lpf) takes OPSEG

- `u_gi` holds the leaf `g_op.u_leaf` (`qfd_sys_face_mu_dhuser` OPSEG 1, with the ROM inside), plus op starts, the
  filler result bank, the dc user-0 gate and the context record.
- `op_fault` rides the dcs `start_fault` bit, so both feed `core_fault` as in the flat cluster.
- The spec sets `params.OPSEG 1`. lp is regenerated: 21 landings, audit PASS.
- Landing flops rise from 3,490 to 8,943 because of tl.

## 4. Benches (Verilator 5.050)

| bench | result |
|---|---|
| `run_mu_opseg.sh pass mut` | `MU_OPSEG_PASS`. Cases: red, ctx_part (mask {1,3}), neg_drift, neg_coll, neg_ctx (op_fault at the seal edge 1035), and full F16x36. Red frame-1 measured rates equal the compiled ones. Mutants 21-29 FAIL (27 = record never loaded, 28 = rotated, 29 = unchecked). |
| `run_mu_ctlm.sh mu prog lp eq seq` | PASS. prog 84/84 plus LANDED_LOCKSTEP; lp MUT 0 PASS, 1/2 FAIL; seq: the NU 1 lockstep vs `qfd_dv_cmd_cal` now includes tl, with C8 BOOT TLOAD words; MUT 4/5 FAIL. |
| eq (`runs/eq`) | OPSEG 0: DMUT 0 PASS, 5/6 FAIL. OPSEG 1 with directed good and bad record loads and a bank comparison: DMUT 0 PASS, 5 and 29 FAIL. |

`run_mu_ctlm.sh ctlm` (the nsl12 suite) was still running at hand-off (pending_results).

## 5. B5 per-user goldens (`../b5/`)

- Users 1..3 are the released prompt at positions 8190 / 8189 / 8188 (tokens 15 / 13 / 20). User 0 is P8191.
- The CPU ISA oracle runs history-seeded from fx/history_l3 (real L0..L2 K/V).
- Control: the seeded P8191 run reproduces the committed gold (`qwen_hbmacc_p8191_20261004`) 12/12 for the L0..L2 x,
  kv_pre and kv_at_P digests.
- L35 and the head need the full 36-layer history. The P8191 CPU gold is still running (pid 1583528 on ot-epyc5).
  When it finishes, run the same command with `--layers 36 --head` and the full history (pending_results).
