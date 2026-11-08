# Codex KV types takeover 2026-11-08 02:22 PST

## CODEX notes

- io_ft_v1 lockup pilot finished FAIL before DRT: GRT TT -50.83 ps, hold -185.66 ps; exact intel1 `/srv/opentallas-scratch2/claude/kv-types-3/ioft/kit/gen/kv3_io_ft_v1/grt_policy.json`. Preserve failure; no retry. Density and congestion PNGs viewed from `run/layout_review/grt`. SMELLS: dense west ft0 landing-ring cluster, east ft2 landing-ring cluster, mostly empty outline with long station chains and dispersed clock loads. Need endpoint diagnosis before structural next form; own read-only bounded TT probe at intel1 `/srv/opentallas-scratch2/claude/codex-kv-types-0222/ioft-probe`.
- hroot ring-density pilot is alive at GRT congestion iterations (last read 6/30), intel1 `/srv/opentallas-scratch2/claude/kv-types-3/hroot/kit/gen/kv3_hroot`. Do not duplicate or restart. Next: collect GRT and view new images, then if pass collect route/signoff.
- phy maxwire pilot remains FAIL TT -65.23 at GRT; known falling-edge hard-macro outputs to distant capture flops. Proposed local capture +1 pin cycle needs a plan event; not adopted. No third maxwire knob trial.
- pv_v1n START placement remains FAIL: 190/731 raw/reader/writer sites inside hard macros. Storage-band sizer cannot move these fixed START 4.32um boxes. Need macro-aware path generation (private class tool fix can be prepared); no POR edit or build until actual geometry/hop budget is valid.
- sys_SD/sys_SD_v1 SEL_CHUNK8 wave rows already released by KW-FIX-32 at 00:09; active wave owns collection. No private duplicate.
- HGI pilot waits for e2/e6 M5 signed views (parent KV agent collecting them).
- sys_c remains an open redesign task; collecting latest exact class and geometry before a new form.

No merges, tags, plan-of-record changes, deletion chains or owner-overridden ECOs by this lane.

## 02:4x substantive diagnosis and next form

io_ft_v1 exact TT probe reproduces -50.83ps and identifies five failures in forwarded-ring status control: ft3_i written[3] -> lap_ok447.49ps vs396.66required; ft3 rv-32.21; ft1 lap_ok-25.11; ft3 ghi0-2.60; ft1 rv-1.66. These are the existing STATUS-REG class, not a new failure of lockup station data. The private lockup plan was based on main and **omitted** the previously private `landing_status_reg=true` event; the prior SR form had TT+85.03. No route or ECO of this failed kit.

Combined SR+lockup private form: epyc4 `/srv/opentallas-scratch3/claude/codex-kv-types-0222-ioft`, own source `/srv/opentallas-scratch3/claude/codex-kv-types-0222-src`, branch `codex/kv-start-obstacles-0222` base dd6a126a29 (contains landed STATUS-REG support). Only kv3_io_ft_v1.landing_status_reg=true changes from the lockup plan. PIN CYCLES0data; rv/lap fault+1clk; guards unchanged per existing approved SR proof. Strict bind queued through ot-run16GB/2T E4; intel2 log `/home/ubuntu/codex-kv-types-0222/ioft_bind.otrun.log`. Next: bind0 -> generate and inspect actual image -> ONE PLACE pilot. No batch release.

Current wave SD a7 and SD_v1 a13 both genuinely alive in GRT congestion iterations (10/26 last read), no private duplicate. hroot pilot alive iteration8.

Remaining family ownership: hubs/PC source and clock class `/root/kv/types/hubs`, lane CODEX-KV-HUBS-0222.md. SYS_C/basePHY realization and hub_C PLL `/root/kv/types/realization`, lane CODEX-KV-REALIZATION-0222.md. Historical hold text is not fresh evidence: prior 1551 read found SYS_C101rawFF/23branches and basePHY W2D3 reset+epoch already correct, so that child verifies current kw32 canonical context before any action. Latest SYS_C actual PLACE is a severe macro-wrap/recovery miss, not assumed stale96rawFF. HG/HGI physical pilot still waits for e2/e6 M5 signed child views; parent owns cores. PV family remains held for macro-aware START route/site redesign. io_cor/io_cor_v1 follow a signed SR+lockup pilot; no blind relaunch. phy_v1 follows actual phy timing read; +1 local macro-output pin capture remains an unadopted proposal.
