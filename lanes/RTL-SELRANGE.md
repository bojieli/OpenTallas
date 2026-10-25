# RTL-SELRANGE: out-of-range part-selects and indices in synthesised RTL (2026-10-24)

The lane ran on rtx-pro. The gate branch is claude/selrange-gate-1024@fc4d5fa9c.

**Trigger.** In `rtl/dsrom_sys/s81_dv/eng/ot_s81eng_rr_n32.sv`, the function `csa31` reads `a[31:24]` of a 31-bit operand at k=3. The ORFS Yosys slang frontend dropped `csa31[30:24]`. Every eng netlist therefore tied 11 request address bits to 0, and every Verilator bench still passed. The fix is claude/s81-kits-1024r@ab4ad9f68 (commit 16241c6cb).

## 1. Which tool sees this bug class

These are probes on fleet tools: Verilator 5.050 and Yosys 0.68 for read_slang and read_verilog.

| Pattern | Verilator `-Wall` (SELRANGE) | `read_slang` | `read_verilog -defer` + `hierarchy -top` |
|---|---|---|---|
| csa31: `a[8*k +: 8]` partly out of range inside an unrolled function loop | silent | silent; logic dropped (SAT: netlist != a+b) | WARNING `Range [31:24] select out of bounds` |
| Read, write or bit index out of range inside an always-block loop | silent | silent | WARNING (all three cases) |
| Constant out-of-range select at module or generate scope | SELRANGE | hard ERROR (-Wrange-oob) | WARNING |
| Out-of-range select on the dead branch of a constant `?:` | SELRANGE | builds | silent (branch folded) |

What the probes show:
- **Verilator lint cannot find the dangerous class.** It flags only generate-time constant selects, and slang already rejects those. Over the whole sweep it found 3 sites, all benign, and missed csa31.
- **slang gives no warning, and both frontends lose data.** In probe p4 (`q ^= a[k]` for k up to the width), slang folds the x to `q = 0`; read_verilog is also wrong.
- **read_verilog is the detector.** It unrolls loops and evaluates functions for each instance with the real parameters.
- **A guard that is constant false is harmless in both frontends.** Examples: `k < 256 && x[k/8]` and `i < V-1 && w[i+1]`. Probe p1 proves slang, read_verilog and a hand-written reference equal.

## 2. Sweep

**Scope.**
- Every kit dir (kit_rtl.f + kit_rtl.json, or an ORFS config.mk) generated in the last 3 days on epyc1, epyc2, epyc3, intel1, intel2 and rtx-pro.
- Kits were deduplicated by content signature: all source bytes plus top plus defines.
- That gives 1131 kits: s81 / s81_head 616, qwen_kvsys 146, qwen_compute 91, HBM cores (core-hbm, elem-hbm) 276, other 2.

**Variants run on each kit.**
- `snapshot`: the kit's own sources, which is what was synthesised.
- `main`: every rtl/ or physical/ source replaced by origin/main@a11334b98 (by relative path, else by unique basename).
- `s81k`, `vm`, `su`, `idx`: main plus the changed files of claude/s81-kits-1024r@ab4ad9f68, claude/hbm-bind-1024r-vm@19cfa3d9c, claude/hbm-bind-1024r-su@cc8b2b937 and codex/hbm-bind-idx-r2-1024@8d607ca2e. These run only on kits that contain one of those files.
- Verilator `--lint-only -Wwarn-SELRANGE` on snapshot and main.
- The non-test files that a branch changed and that no kit contains (the HBM VM, SU, IDX and HC files) were elaborated alone, with every module as top. They are clean.

**Results.** Yosys runs, PASS / FAIL / ERROR. ERROR means read_verilog could not elaborate the kit, so it is NOT RUN; see the notes below the table.

| design | main | snapshot | branch overlay |
|---|---|---|---|
| s81 / s81_head | 576 / 32 / 4 | 326 / 26 / 255 | s81k 115 / 10 / 0 |
| qwen_kvsys | 143 / 0 / 3 | 117 / 0 / 29 | none (no kv kit names a branch file) |
| qwen_compute | 91 / 0 / 0 | 90 / 0 / 1 | none |
| HBM cores | 276 / 0 / 0 | 276 / 0 / 0 | idx 9 / 0 / 0; vm 1 / 0 / 0 |

Notes on the table:
- **s81 main** counts 16 svc_rs kits as PASS. They first failed to parse on `inside` and passed once it was rewritten.
- **Remaining main ERRORs:**
  - read_verilog limits: defparam into a generate block (`dsdv_gunit_l5`, `ot_s81hd_tile`); `dsfd_engram_lkp_ra640` package width; `qkd_embgw_boot_s.sv:48` package import inside a module body.
  - 1 duplicate `ot_reset_sync`.
  - 2 kv-cores eco kits whose sources are gone.
- **The 255 s81 snapshot ERRORs** are the binder4 b3r8 kit_rtl.f files. Each names `ot_reset_sync.sv` from two different snapshot dirs. Their `main` run is clean.
- **Still running:** the `main` variant of 14 elem-s81 kits48b C-slices on intel2 (read_verilog derive of ot_s81sl_xs4 takes 1 h or more). The same slice types already passed `main` from the b3r8 kits. Results will land in intel2:/srv/opentallas-scratch/claude/selrange-intel2/out/remote.redo.jsonl.
- **SIGNED kits:** the S81 station405 kitsB t12, t15, t16, t17, t20 and t21 are identical in content to codex-s81/station405_c1, and they PASS. There are no qwen, kv or HBM SIGNED kits.

Data:
- Per-host results: <host>:/srv/opentallas-scratch/claude/selrange-<host>/out/*.jsonl.
- Merged results: rtx-pro:/home/ubuntu/scratch/selrange-1024/final_now.txt.
- Probes: epyc2:/srv/opentallas-scratch/claude/selrange/probe{,2}.

## 3. Hits and triage

### Real bug (logic dropped in synthesis)

**B1. csa31 in `rtl/dsrom_sys/s81_dv/eng/ot_s81eng_rr_n32.sv:406-407` on origin/main.** Module `ot_s81eng_head_n32`, function `csa31`.
- **Status:** still present on main@a11334b98. It is fixed on claude/s81-kits-1024r@ab4ad9f68, where the s81k variant is clean.
- **Where it is used:** S81 plan type `eng__t1`, through hard core `dsdv_eng_rr_e`. Kits:
  - physical/die_plan/s81/cores/eng/kits/dsdv_eng_rr_e__345.6x466.56 (the main config.mk lists the file)
  - epyc2:/srv/opentallas-scratch2/claude/elem-s81/hc/s81sl_xrt1/.../dsdv_eng_rr_e__*
  - epyc2:/srv/opentallas-scratch2/claude/s81-kits/rtla/r2/e6
  - A snapshot kit also hits line 408, the older form of the same function.
- **SIGNED:** none. eng_rr is NOT SIGNED.
- **Fix:** merge claude/s81-kits-1024r. The fix zero-extends the operands to 32 bits inside the function. Then re-synthesise every dsdv_eng_rr_e netlist or view made from main's eng RTL, because those have request sector bits [29:19] tied to 0.
- **Checked with the gate in the real image** (openroad/orfs:asap7lock, e6 kit): the fixed RTL passes in 2 m 16 s; main's file FAILs with 6 hits on lines 406/407 and rc 1.

**No other real bug was found.**

### Benign: reported, but harmless in both frontends

Waive each one on its source line with `// selrange-ok: <why>` before the gate lands, or rewrite it as an explicit generate `if`.

| file:line (main) | module / kits | why it is benign |
|---|---|---|
| rtl/dsrom_sys/s81_dv/slice/ot_s81sl_xrt.sv:348 | ot_s81sl_xrt1/3, 19 slice kits (c1x/c3x/iq/kv512 C) | `(k < 256 && rsv_c[k/8]) ? vb2[16+k] : ...`: for k >= 256 the guard is constant false (probe p1 equivalent) |
| ot_s81sl_xrt.sv:497 | same kits | `(i < V-1 && pvs_c[i/16]) ? pair_word[i+1] : ...`: constant-false guard |
| rtl/dsrom_sys/s81_dv/slice/ot_s81sl_kv_bank.sv:251/253/255 | s81p_ot_s81sl_kv_leaf__t2 | `(b < 4 && ikr_vv[12+b]) ? ikr_*[..*b+:..] : 0`: constant-false guard for b >= 4 |
| rtl/dsrom_sys/s81_dv/slice/ot_s81sl_slice_lep.sv:725 | lepe_mu / lepe_nh_mus / lepw_mus LP slices | `rpb ? ring_meta_regions[8+:4] : ...` at NL=2 (AB_EN 0): `relp[1]` is tied to 0, so `rpb` is constant 0 |
| rtl/dsrom_sys/s81_dv/idx/dsdv_idx_tree.sv:108/109 (Verilator also :120) | dsdv_idx_txm D=1024, SRAM_MACRO=1 (bk_sel__t1) | `NB == 1 \|\| ra[AW-1:10] == b`: constant-true short-circuit (`1 \|\| x = 1`); the `bs` load is `(NB == 1) ? '0 : ...` |
| ot_s81sl_xs4.sv:825/864-866 (Verilator only) | 14 C-slice kits | dead branch of a constant `gj < 4 ?` / `FB ?` in generate |
| rtl/qwen_sys/host_integrated_20261014/ot_host_if_pb2_observed.sv:391 (Verilator only) | qkd_host_root_admission_obsx | dead branch of the constant `(FMT != 0) ?` |

Earlier forms of xrt (lines 270/383/395/419/532/551) and kv_bank (236-240) exist only in snapshot sources. They are the same patterns and equally benign.

## 4. Permanent gate (READY): claude/selrange-gate-1024@fc4d5fa9c

**`tools/die_plan/selrange_gate.py KITDIR`**
- Reads config.mk (VERILOG_FILES, VERILOG_DEFINES, DESIGN_NAME; /work maps to KITDIR).
- Runs `read_verilog -sv -defer` on each file, then `hierarchy -top DESIGN_NAME`. Writes selrange.json.
- Exit codes:
  - **1 (FAIL):** any `Range ... out of bounds` warning on a line without a `// selrange-ok: <reason>` waiver.
  - **2 (ERROR / NOT RUN):** read_verilog cannot parse a slang-only construct, or the checker crashed.
  - **0:** PASS.
- Input handling:
  - Hard-macro and std-cell model files are skipped, because their liberty view is what gets synthesised.
  - A file named twice is read once.
  - Source dirs are added as include dirs.
  - `x inside {a, b}` is rewritten on the same line.
- Also has a `--top T --filelist F` mode.

**gen_phys.py RUN_KIT**
- Kits get selrange_gate.py.
- run_kit.sh starts the gate beside synth (2 h cap) and joins it right after synth, before face_guard.
- rc 1 stops the kit. rc 2 or a timeout prints `SELRANGE NOT RUN` and the kit continues.
- The gate runs beside synth because the large S81 slices need up to 1 h of read_verilog elaboration.

**Tests**
- `tools/die_plan/test_selrange_gate.py` has 7 tests: csa31 old FAIL / fixed PASS, parameter context, waiver, exit codes, `inside`, and run_kit order.
- test_cp2, test_face_guard, test_sdc_lint and test_signoff pass.
- The generated inner script passes `bash -n` and was dry-run with a fake make for rc 0, 1 and 2.

**Not wired (lane-owned generators that ship their own run_kit).** Each needs to copy selrange_gate.py and add the same three lines:
- physical/die_plan/s81/cores/{eng,svc}/gen_core_kit*.py
- physical/die_plan/hbm/cores/harden/gen_core_kit.py
- physical/die_plan/hbm_arch_cores/gen_core_kit_hbm.py
- physical/die_plan/qwen_kvsys/cores/harden/gen_core_kit_kv.py

## PARKED 2026-10-24 23:23 PDT

- **Delivered:**
  - This report.
  - Request lines in S81, QC-A0, KV-G3 and HBM-ARCH.
  - READY in COORD-REVIEW-QUEUE for claude/selrange-gate-1024@fc4d5fa9c.
- **Redo status at park:**
  - intel2 redo: 14 results so far.
    - 11 PASS: serdes t1-t6 and hgi xload.
    - 3 ERROR: kv3_head_eighth e1/e3, whose eco sources are gone, and gunit defparam.
    - 0 FAIL.
  - The 14 kits48b C-slice `main` runs are still elaborating. They run under ot-run with sweep PID 165316 on intel2; output goes to intel2:/srv/opentallas-scratch/claude/selrange-intel2/out/remote.redo.jsonl.
  - The epyc2 local redo is sweep PID 554299; output goes to epyc2:/srv/opentallas-scratch/claude/selrange-epyc2/out/local.redo.jsonl.
  - The same slice RTL already PASSes `main` through the b3r8 kits, so these runs only add confirmation.
- **Next:**
  1. When those runs finish, run `python3 rtx-pro:/home/ubuntu/scratch/selrange-1024/bin/final.py <outdir>` and check that FAIL is 0.
  2. Delete /srv/opentallas-scratch/claude/selrange-<host> on epyc1, epyc2, epyc3, intel1 and intel2, and epyc2:/srv/opentallas-scratch/claude/selrange. The latter is on the root FS.
  3. Lanes merge the csa31 fix and the waivers, then root-merge the gate.
  4. Lane generators wire in the gate.

## CODEX notes 2026-10-25 02:43 PDT
Standalone approved checker fc4d5fa9c supplied to KV cores and CLOCK/CP1 runner integration. Whole-runner adoption waits source-local S81 benign-select waivers; csa31 real fix already merged. Old redo paths absent and PIDs gone; no live job duplicated.

2026-10-25 02:54 PDT CODEX source waivers ready codex/selrange-waivers-1025@3fb680539 basedbatchf19254160:4files9 source-local comments, eachselect+constantguard+triage section3 reference; comment-stripped tokenexactnessPASS. Source/runtime semantics unchanged. Sentroot+commonrunner owner.
