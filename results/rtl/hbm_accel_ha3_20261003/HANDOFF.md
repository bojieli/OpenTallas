# HA3 clock-loop implementation milestone

Parent: `8564e79eaf906c820aec5eb92bfda1cca80ee43d`.
Branch: `codex/ha3-hbm-epilogue-20261003`.
Source run origin: `0554f2ea02eec3f0cc1fe3c28b31943b914b0d88`.
Clean remote export worktree: `ot-agidock128:/tmp/ha3-clock-0554f2ea0/src` at `e8f8d4a` (full export SHA in result.json).
Run supervisor PID **421530**, gate PID **421531**, both terminal. Result is `connected_0554f2ea0/result.json`.

## Implementation and integration API

- `rtl/hbm_accel/epilogue/ot_hbm_accel_issue.sv`: original `ot_gpu_issue` ports and sizing parameters, plus **ENABLE=0** by default. Off selects the unchanged original. On computes wave-valid flags ahead of cursor advance, stores end bounds and group-last metadata, and adds one setup state. Iteration issue remains one cycle; actual setup/phase exposure needs the next real-SM test.
- `rtl/hbm_accel/epilogue/ot_hbm_accel_bulk_copy.sv`: original `ot_gpu_bulk_copy` ports and sizing parameters, plus **ENABLE=0**. On carries registered current/next full flags with response forwarding. SRAM mode carries a registered output-space flag. Ring, tag allocation, outstanding count, descriptor queue, request acceptance and output handshake contracts remain the original contracts. The large look-ahead selection still requires timing measurement.
- `tools/hbm_accel_epilogue_compile.py`: `components()` selects original names by default; `components(enable_ha3_clock_lookahead=True)` returns successor names with `ENABLE=1`. HA8/Euclid must instantiate/wire in their own installer namespace. No guarded-SM or canonical factory files were edited.
- `tools/hbm_accel_epilogue_model.py`: additive sizing companion that extracts pinned literal constants from `tools/uarch_model.py`, avoiding import-time physical campaigns in a sparse checkout. Costs for both HBM targets and all new ports/boundaries are in `price_before_rtl.json`, committed **before** successor RTL. Unknown memory protection, service time, area, wire, CDC, corridor and composition constants remain unknown/ESTIMATE. ROM and HBM ablation are unchanged.

## Actual terminal result

**PASS_PROTOCOL_FIXTURE: 72 cases, zero accepted-record mismatches.** Both versions have identical completion cycles in every case (delta min/max **0/0 cycles**). Longest successor issue streak **1,152 consecutive cycles**. Runtime **96.12 seconds**; Icarus gate's observed simulator process was **8.4 MiB RSS**. Small campaign used `~/bin/admit.sh 1` on agidock128; no EPYC build or P&R was launched.

Connected fixture combines bulk copy and issue, real default ring depth1024 / max-outstanding512 / weight-line1024 bits, both register and SRAM modes. Rows1/2/7/8/9/17/43/384/4095, row-slot and group-slot schedules, stalls, out-of-order returns, held requests/output data, ring wrap, and a delayed response window exercise credit exhaustion. The SRAM model is behavioural **test-only**, and the response delays/refresh window are synthetic. The gate compares every accepted issue record (including row, slot, first/last/group-last, revolution end and x address), verifies ordered consumed weights, checks data/request hold and terminal inventories. No arithmetic was changed.

First connected case: **255 weight lines / 264 issue events, 474 cycles** on both versions; streak11.

Raw case/build logs are preserved in `raw-logs-r1.tar.gz`. The first raw-log packaging attempt failed (empty `raw-logs.tar.gz` retained); it did not rerun any simulation. The detached launcher's unquoted `printf` was split across lines after the gate completed, leaving its shell exit file empty and emitting `0: command not found`. The original launcher and run log are retained; `collection_receipt.json` records this failure. The terminal gate's explicit JSON PASS is the functional authority, not a fabricated shell exit code.

## Remaining gates and ownership

| Gate | Actual status |
|---|---|
| Accepted request/order/credit/data hold in connected fixture | PASS72, zero mismatches |
| Real per-layer/head golden through installed SM | UNMEASURED; HA8 installer next |
| Serial critical path including real wire/CDC/credit/refresh | UNMEASURED; synthetic fixture deltas0 do not replace this |
| Composed area/slot fit | UNMEASURED |
| Routed corridor / hub-layer check | UNMEASURED |
| SS setup60ps / FF hold25ps at 1.2GHz in context | UNMEASURED; no clock claim |
| Composed per-user gain >=1% | UNMEASURED; no adoption |

No rung is added to a published measured token-rate composition. The prior `2078c269c` issue/bulk-copy clock failures remain baseline evidence. The other clock-loop owners and all existing jobs remain theirs. Real SM integration is the next work, with HA8 installer files only after this functional cycle pass; no duplicate standalone screen/P&R is queued.

Numerical cut-through/TMEM epilogue remains excluded. `lower_fused_epilogue()` refuses lowering while the preserved Qwen nonfinite/wide-overflow FAILED gates remain unresolved. No finite-only exemption, reducer reassociation, transferred67ns adoption, or token/clock result is claimed. HA2 owns its endpoint and direct links; proposed handoff is tagged ordered valid/ready beats with retirement after producer completion and final consumer handshake, pending their actual API. No HA2 files were edited.

## Replay

From a pinned clean checkout containing the original source files:

```sh
python3 tools/hbm_accel_epilogue_clock_gate.py --work /absolute/new/run --out /absolute/new/result.json
```

The output path is exclusive; existing verdicts cannot be overwritten. Builds and simulations have no arbitrary runtime, process-memory or file-size cap. Replay is CPU RTL simulation, not model inference.
