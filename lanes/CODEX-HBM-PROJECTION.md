# CODEX HBM native projection

## Current step

Own branch `codex/hbm-projection-1106@3f6f0ee1b50`, worktree intel2 `/srv/opentallas-scratch2/claude/wt/codex-hbm-projection-1106`.

Implemented production K20480 / 24-row native NQ2/W128 projection image lowering, preserving default legacy NQ4 image bytes. Added explicit bank write-face extra edge to dependent projection launch; ingest controls/data stay unchanged. Added exact released-operand extraction and explicit NPZ input, plus projection-only qualification mode. No RTL changes, physical routing, sign-off or native token claim.

## Running job

Native canonical root + two W128 half engines component build/probe: intel2 alias localhost, unit `oth-ubuntu-2770563-1793952020`, client PID2769523, 32GB/4 threads via ot-run. Source stage `/srv/opentallas-scratch2/claude/hbm-projection-1106/stage`, log `~/hbm-projection-1106/build.otrun.log`; stage build.log/build.rc/probe.log/probe.rc. Source cohort87ced193e3a; no arithmetic stubs or replayed result pins.

## Results

- Default NQ4 programme, schedules and all vector files byte-identical to pre-change source. Existing metadata keys unchanged.
- NQ2 first launch4028 vs NQ4 2030; explicit write-face candidate launch4029 with identical ingest/wave data.
- Three exact subset-reader tests PASS (F32 row bytes, BF16 bit extension, invalid row rejected).
- Released real layer0/token1 inputs extracted from snapshot dba1be0a40aa45a94ad051997016db3960a90277: fn[24,20480], base24, scale3, repeated BF16 embedding row1. About2MB of data read; no full-shard load or downloads. NPZ/metadata under `/srv/opentallas-scratch2/claude/hbm-projection-1106/released_l0_token1.*`.

## Next

Collect build/probe, measure RAW0. Emit fixed scalar-pop schedule from actual core timing, run projection-only component on released operands and wave-mapping mutant; preserve every failure. Then package source/results READY to root. Current-die landed timings, bank-WFACE hardware adoption, full-layer producer/consumer/token qualification remain separate obligations.

## OWNER?

None. Full projection inputs for later layers must be actual residuals, never repeated embedding or fixture output substitution.

## CODEX notes — 2026-11-06 00:29 PST

First build failed INFRA at the exact32GiB cgroup limit during top frontend elaboration; completed leaf/bank libraries are retained. Failure receipt `stage/FAILED_INFRA_32G.json`, original log unchanged. No function/design verdict.

New source `190a8eaf145` adds qcen/tail hierarchy boundaries and a fresh exact833ps cohort with explicit selected SM_LAT4/OM_LAT5/NF_TIED1 (measured RS114/OV8 from I146). Fresh job unit `oth-ubuntu-3624669-1793953761`, client3620937,96GB/4threads based on measured OOM; source/cache `stage833`, log `~/hbm-projection-1106/build833.otrun.log`. Native qcen/tail frontends passed and their C++ is compiling. Completed native bank cache was copied, not removed.

The new gate will measure RAW0, check24 actual released-weight projection mixes, verify the one-edge dependent-launch guard and catch the weight-term-swizzle mutant. It refuses a binary lacking exact833ps/selected-profile markers. A guard pass is NOT WFACE hardware adoption. The TP96 rank0 fixture still owns no HC_MIX_ROWS; no global projection_open flag is cleared by this component work.
