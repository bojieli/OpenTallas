# Actual selected NB2 bank/shadow cadence

Supersedes the P512 spacing limit of the original component result in e58e7aa61. This extends that same actual XRT/XS4 → current 41-stage transport → CFIFO/native station/relays → CFG7 → native NB2 Q-pair vehicle. No RTL, plan, FF, GO-cycle or production-provider change.

| Source GO period | Actual original GB0 | Actual current GB1 | Native diagnosis |
|---|---|---|---|
|144|PASS|PASS|All five operations and three controls pass.|
|143|PASS|PASS|All five operations and three controls pass.|
|142|PASS|PASS|Closest tested safe consecutive period; all ten independent checkpoint partials, five architectural tags 1,2,3,0,1, no native fault.|
|141|FAIL|FAIL|Q fault=1 while CFG7 fault=0: GO arrives before native shadow replay settles. All ten literal partials still present.|
|128|FAIL|FAIL|Q fault=1 and CFG7 fault=1. Third GO=1019 coincides with last CFG=1019; st=3. All ten literal partials still present.|

Original and current cases exactly match CORE_GO, partial words/tags/dates, real bank/shadow/walking feedback, 125 CFG words and 400 stream words at every tested period. P142 returns each partial at external CORE_GO+171. The native production guard in `ot_v41_elem_pq_tags.sv` is `go_e && (walking || sh_full || settle != 0)`; CFG7 rejects `go_x && (pend_x || ld_run_x || c_v || cfg_go_x)`. P141 isolates the former, P128 triggers both. The arithmetic values alone would miss both unsafe schedules. The earlier P144 replay-end observation was not itself the arithmetic GO deadline: actual pin/FAST stages delay arithmetic GO after the observed wrapper boundary.

The source programme contains the real phase0 from current CAP-safe 0L01 fields, five repeats, actual independent checkpoint norm-scale activation and WQA images, with existing XS admission tags 0/2 and independent architectural operation tag OPTAG=1. Every P142 partial matches the independent e58 checkpoint gold. 142 edges =118286ps at833ps per edge. This is a selected-pair empirical consecutive-period boundary, not a universal minimum for all shapes, field phases or dies. The source calendar already rejects stream overlap/tag reuse; it does not by itself prove Q shadow timing. No new global calendar period is adopted.

Native jobs reused the already built real-arithmetic binary under normal ot-run 2GB/1 thread, no source recompilation or wholeframe run:
- P144 Epyc2 unit3996346-1793609559 exit0, remote scratch2/claude/codex-ds-native-cadence-0110.
- P143 unit4003342-1793609607 exit0, remote codex-ds-native-cadence-0114.
- P128 unit4017790-1793609681 checker exit1, preserved failure remote codex-ds-native-cadence-0128.
- P141/P142 unit4036883-1793609736 simulation exit0; per-case checks explicitly FAIL/PASS, remote codex-ds-native-cadence-0141/P{141,142}.

`check_native_go_pair.py` now reports the actual programme period instead of hardcoded512; P144 original check remains on remote checked/ and corrected derived-period report is retained here. Raw P141/P142 native logs and P128 failure log are committed unchanged. `check_cadence.py` applies the existing independent checker to the two boundary cases; raw full programme/controls remain in remote scratch. No failed verdict overwritten.

This remains constant checkpoint activation, one native NB2 pair, controlled common-phase/reset startup. Fresh operand versions, SRAM leases, actual production clock/reset phases, other eleven provider classes, fullframe/token and capturefold are NOT qualified. No under_TEST bypass. Native-provider and production flags stay false. The earlier proposed +4FF tag retime is rejected: original native architecture intentionally starts at tag1 and both original/current agree.
