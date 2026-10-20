# KV token retirement + fault/reset plane — KV-RETIRE 10-19

Branch `claude/kv-retire-1019`. Base: codex `f4c8c9053` (retirement candidate `670cefef6`). Cherry-picked unchanged:
reset plane `4b2f0b411` (+`e3e9e090d`, `dd8735318`), fault inventory `4072f9d57`, DCAL fault model `a1c24018d`+`103049e43`,
host terminal `4a9d0b4b2`, host model `430996d1e`+`0268e9374`, host producers `afee37b56`, reset ownership `019551968`.
This implements the owner's 10-19 09:39 contract. It covers logic only: no physical receipt exists yet, so every stage is `qualified=false` and
`compile_all` still refuses a delayed production STATUS.

## Contract: `tools/qwen_kv_die/kv_retirement_contract.py`

- **Operations.** These come from the canonical die programme (`compile_all`, die profile: RX_CMD 2, TX_FIRST 1752,
  service_end 1779) plus the controller RTL ages. The operations are cmd_rx, q_rx, service, result_tx, done and tx_slot.
  Each has a nominal check, a registered missing check and a drain. **Functional cutoff = 1785** (RESULT drain,
  done/slot missing checks). The cutoff equals the legacy STATUS age, so the legacy STATUS has zero fault-path margin.
- **Sources.** All **357** are covered: 351 landings, 4 KC, existing UFH (+36 AHUB hf→ufh edges) and **DCAL**
  (successor tail join; KV-DCAL's alternative ks_af_ufd sink is priced with `--dcal-relay N`). Each source has the full
  ordered path source→collector, ufh, AFR (1), face (0), TX capture (1), TX landing (1), link (11), consumer (1).
  Worst = 197 edges.
- **STATUS age = 1982** (`compiled_end` 1983, STATUS_DELAY 197). `prove()` refuses 1981. Continuous health is never
  gated, cleared or masked.
- **Price** (link calendar recompiled; slot tables unchanged, only STATUS moves):
  - **Per-layer** (`670cefef6` form, 36 tails): +7,092 edges/token unpadded, +7,680 padded to 768.
    Token period goes 249,600 → 257,280, a **2.985 %** loss.
  - **Token retirement** (one delayed STATUS per token): +197 edges, **0.079 %**. Health is sticky, so the last layer's
    STATUS covers all 36 layers. Intermediate per-layer STATUS then means progress only. Recommended, but it needs OWNER
    acceptance and compute-consumer semantics, plus an L35-only compiled_end or a token-run retirement slot.
- **Reset.** Required sink release = max(clear depth + diagnostic skew 64 + propagation) = **263** edges. This is above
  the 8-bit HOLD range, so a **9-bit** hold counter is needed (see RTL below). HOLD128 is refused by `prove()`.

## RTL

- `qkd_rst_region.sv` / `_pr.sv`. Counter widths now come from the parameters: IW = max(9, clog2(IGNORE+1)),
  HW = max(8, clog2(HOLD)), and a DW strap/calendar width. Default parameters give bit-identical widths and values.
  Previously HOLD 273 loaded 16, and an IGNORE above 511 never went live.
- `qkd_host_service_guard_wh.sv` is a wrapper; the closed guard is unchanged. It fixes the warm-reset hole: a
  POR-domain `warm_lost` is set on warm `host_rst_n` if health was raised up to the last pre-reset edge, or if a
  POR-retained context was live. It vetoes abort, TK88, status.bad/ready and service_ready from the first reset edge,
  with no added output edge. It clears only on POR, or on `recovery_certified` (host recovery_clear after global
  drains) with no retained context.

## Fleet evidence (Verilator 5.050, ot-epyc5, `oth-ubuntu-2020292-1792436030`, run.sh)

`logs/summary.log`: **KV_RETIRE_ALL_PASS**
- 14 planner/contract unit tests.
- Whole-path bench `tb_kv_retire_wholepath`: real programme/static_ctl (LAND=1, RETIRE_STATIC=1) and real AFR, on the compiled ages.
  - Healthy run, plus late (earlier STATUS stands; health stays live; the next op is refused).
  - Missing done, missing RESULT beat 31 and missing Q beat 31 all PASS at STATUS 1982.
  - Every one of the 357 sources injected **at the cutoff** with its own edges PASS (logs in `logs/sources.tgz`).
  - Early injection PASS.
- Boundary sweep (worst source D=182): the smallest safe STATUS is **1968** = cutoff + 182 + AFR 1. The contract age
  1982 adds the 13-edge suffix plus 1. Fail witnesses: STATUS 1967 and legacy 1785 both let a healthy STATUS escape
  (`witness_*.log`), and the checker refuses 1967 (`fail_boundary_minus1.log`).
- `tb_qkd_rst_region` and `_pr` regressions PASS. `tb_qkd_rst_region_wide` PASS: HOLD 273 held 273, IGNORE 600, 580-deep
  random chain, dly 300, release +882 exact. The MUT 4 legacy-truncation mutant FAILs.
- `tb_qkd_host_service_guard` regression PASS (201 checks). `tb_qkd_host_service_guard_wh` PASS (17 checks), and
  WH_MUT 1/2/3 FAIL (WARM_CERTIFIED_CLEAN / WARM_VETO_NOT_LIVE_IN_RESET / RECOVERY_WITH_RETAINED).

## Still open (needed for production qualification)

Measured native lane ages and clock phase for every path stage, loaded reset STA, and a measured cross-root skew to
replace the diagnostic 64. Also: the native DCAL fault pin, export of the collected-packet POR `retained_request` as
the guard's `retained_ctx`, and regenerated bound link/cal images. All of these come from die GEN/STA (KV-GEN8).
