# MU-QWEN-HOST: the 4-user host plane (RELEASE_TREE MU.QW.KVATT, under K.STA.MU)

Branch `claude/mu-qwen-host-1018`. Every bench ran on the fleet under Verilator 5.050 (the closure daemon's version).
The launcher is `rtl/test/mu_qwen_1018/run_all.sh NEW_ROOT HEAD_ROOT OUT`, and `run_host_mu.sh` runs one case.
`lists/<tb>.f` lists every file a bench reads. The logs are in `runs/` (`run_all.out`, `summary.txt`).

## What changed (opt-in; all parameters default to 0, which is today's behaviour)

- **`ot_host_if_pb2` / `ot_host_if_pb2_observed`, `MU_OUT`.** Up to NSLOT steps outstanding, at most one per slot.
  - An in-flight FIFO names the slot of each retired step, in issue order.
  - The issue path requires event-queue room for every outstanding step.
  - A done with no step outstanding is a sticky fault. The design never stalls.
- **`qkd_host_if_pins(_observed)`, `MU_OUT`.** Under `MU_OUT` the pin-leaf `$fatal` shape check allows NSLOT = ENG_CTX = 4 and PLB 11.
  - The prompt SRAM address stays 13 bits: {slot2, pos11}.
  - eng_done is taken without the start guard, because every pulse is one retired step.
- **`ot_qfd_pkgctl`, `MU`.** This is the 4-slot static calendar:
  - the 2-bit generation is the step tag;
  - each die reports each generation once, in issue order;
  - the oldest step retires with a one-edge eng_done pulse once all 8 dies have reported it;
  - faults are sticky and flush every outstanding step with eng_fault (fail closed);
  - these are faults: a fifth start, an out-of-order or unknown die report, a token or value disagreement, and the watchdog.
- **`qkd_host_ctl` (`ot_qwen_host_ctl.sv`), `MU`.** The step's user rides on hc pos[17:16] (user = kv_base / 1024).
  - The 182-bit hc contract keeps its width.
  - Positions are below 8192, so those bits are zero today.
- **Wrappers.** `qkd_host_ctl_service_pins(_rr)`, `qkd_host_fullcontrol_observed(_rr)`, `qkd_host_control_prompt_observed(_rr)` and `qkd_host_if_pins_observed_rr` pass `MU` through.
  - fullcontrol sets NSLOT 4 and PLB 11 under MU.
  - Its CSR decode-done becomes 'no step outstanding'.
- **New `rtl/qwen_sys/mu_qwen_20261018/qkd_kv_mu_rowoff.sv`.** It holds the per-user KV row on the KV die: row = 64 + layer + 256·user.
  - The user is a pure bit insertion into row[9:8], so there is no adder.
  - row[7:0], the closed read-return tag, is unchanged.
  - `qkd_kv_mu_wrow` is the writer side. `qkd_kv_mu_rrow` is the calendar-command side; it offsets only KV descriptors (op 0/3) on KV rows.
  - These are leaves only. They are **not yet wired** into `qkd_kvs_ctl` or `qkd_static_kv_pc_path_nc`, which are RTL-only parents.

## Verdicts (Verilator 5.050, ot-epyc4)

| bench | verdict |
|---|---|
| MU 0 identity: the 13 existing host benches that reach a changed file, run on the MU tree and on the pre-MU tree (HEAD a9c36f2aa) | 13/13 PASS on both trees. All 13 logs are **identical** apart from the Verilator run-statistics lines. |
| `tb_qkd_host_ctl_mu` (qkd_host_ctl MU 1) | **PASS**. 4 users × 100 positions = 400 steps, 8 dies with random monotone latencies, max 4 outstanding. Every retire is in order, a one-edge pulse, after all 8 dies, with that step's token and value. hc user = pos[17:16]. Five fault runs each name their cause first and flush every outstanding step: die skip, disagree, fifth start, watchdog, unknown generation. |
| `tb_qkd_host_mu_out` (qkd_host_fullcontrol_observed MU 1, end to end) | **PASS**. 4 SQ requests (prompt 2/3/1/4, max 3/2/4/3) take 18 steps with 4 outstanding. Each user's input token is correct (prompt token, or that user's own previous output). The 12 CQ entries are correct per user in order (slot, tag, pos, 18-bit token, ngen, TOKEN/LAST, LENGTH). There is no fault. |
| `tb_qkd_kv_mu_rowoff` | **PASS**. 4 users × 36 layers × 8,192 positions through the production `qkd_kv_static_writer` (VMAP 1): 9,437,184 sector writes, all unique, each inverted exactly to {user, layer, pos, K/V, dim} plus raw bytes. Read rows match the written rows, and tag row[7:0] − 64 = layer. Embedding, go and write commands are unchanged. With MU 0 both leaves are plain wires. |

Mutants (each applied to a copy of one RTL file by `run_host_mu.sh`; all FAIL; witnesses in `runs/mut/`):

| id | mutation | fail regex (witness) |
|---|---|---|
| cm1 | pkgctl retires when ANY die reported | `ERR retire 0 at` |
| cm2 | pkgctl: no in-order generation check | `ERR fault mode 1 bit 87 first 0001` |
| cm3 | hc user field dropped | `ERR start 1 gen .* user 0/1` |
| cm4 | eng_done held (not a pulse) | `ERR retire 1 at` |
| hm1 | retire attributed to eng_slot, not the FIFO head | `ERR retire slot` |
| hm2 | a slot with a step outstanding is picked again | `ERR start user 0 pos 0/0 busy 1` |
| hm3 | no per-user kv_base | `ERR start user 0 .* busy 1` |
| hm4 | pin completion guard kept under MU_OUT | `ERR retire slot 2` |
| rm1 | user not inserted into the write row | `FAIL user0 layer0 pos0 .* nalias8` |
| rm2 | read leaf offsets embedding rows | `FAIL non-KV command changed` |

## Closed tiles the MU 1 change would touch (nothing re-gated or submitted here)

- **`qkd_host_ctl`**: `ot_qwen_host_ctl.sv` and `ot_qfd_pkgctl.sv`. MU 1 replaces the package controller with the 4-generation calendar.
- **The host-root cores whose sources include the changed files**: `qkd_hr_core_prompt`, `qkd_hr_core_guard`, `qkd_hr_core_order`, `qkd_hr_core_peer`, `qkd_hr_core_queue` and `qkd_hr_core_tx`.
  - They carry the fullcontrol_observed, if_pins_observed, pb2_observed and service_pins chain.
  - Under MU 1, pb2 gains the in-flight FIFO and the prompt address loses bit 13.
- At MU 0 these tiles are behaviour-identical, but the source text, and so the source digest, changes. If the daemon pins source digests, these 7 tiles show source drift without any netlist change.
- KV die (when the rowoff leaves are wired): `qkd_kvs_ctl` and `qkd_static_kv_pc_path_nc`. Both are RTL-only parents, plus whatever hardened parent contains them.

## Open items

1. **The compiler and RTL base forms differ.**
   - `mu_calendar.kv_user_bases` gives sector base (u·36 + l)·1024, i.e. row u·36 + l.
   - The RTL row is 64 + l + 256·u, inserted as a bit field.
   - Both are 144 disjoint bases at a stride of 1,024 sectors. The compiler must emit the RTL form, or the RTL must take an absolute base.
2. **The die side must use hc pos[17:16].**
   - Every die consumer of hc pos must mask [17:16] to the position.
   - The KV writer and calendar must hold the user for the stage.
   - This is part of R1–R5 in `../README.md` §3.
3. **Wire `qkd_kv_mu_wrow` and `qkd_kv_mu_rrow`** into the KV die parents (KV-PLAN lane).

## MU-KV-HCTL2 (10-19): pkgctl MU two-stage die reports

- **Why.** Route `qkd_host_ctl-mu1-50169ecef` ended NEEDS_RTL at TT −48.75 ps (FF +20.55, DRC 0).
  - The only TT-failing path ran `tk_q` → `u_pkg.disagree` through 21 levels.
  - The cause is logic depth: the 8 dies were handled one after another in a single cycle (capture the first token, compare each later die).
  - Fan-out and IO were not the problem: input→reg had +317 ps and outputs +343 ps.
  - The pin registers stay opted out: the RTL already registers every pin.
- **Fix (`ot_qfd_pkgctl` MU only; MU 0 is unchanged).**
  - Stage A, on the report edge, keeps the new-generation detect, `m_last`, the in-order/outstanding check and `d_fault`. It registers each accepted report (`r_v`/`r_g`/`r_tok`/`r_val`, 8 × 52 flops).
  - Stage B, on the next edge, sets `seen`, captures the first token and checks for disagreement, in parallel over the dies.
  - A disagreement is a reporter that differs from the captured value, or two same-edge reporters of one generation that differ. That gives the same verdict as the serial chain.
- **Cost: +1 edge from a die's report to retire.**
  - This applies to `eng_done`, `eng_cycles` (+1) and the disagree fault.
  - The die-skip, unknown-generation and die-fault checks keep their edge.
  - Throughput is unchanged: a die may still report every edge, with no backpressure.
- **Benches (Verilator 5.050, ot-epyc7), `runs_hctl2/`.**
  - `tb_qkd_host_ctl_mu` PASS, `tb_qkd_host_mu_out` PASS, `tb_qkd_kv_mu_rowoff` PASS.
  - cm1–cm5, hm1–hm4 and rm1–rm2 all FAIL. The new cm5 drops the compare against the captured token, and its witness is `ERR fault mode 2 bit 84 first 0000`.
  - The 13 MU 0 host benches give logs identical to origin/main.
