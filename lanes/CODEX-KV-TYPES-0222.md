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

## PV macro-aware draft progress

Own helper `tools/die_plan/start_obstacle_path.py` now routes Manhattan corridors around expanded actual macro boxes, excluding unplaceable narrow edge channels, and allocates relay cells outside reserved landing/clock bands. Seven focused tests pass locally, including a straight-line macro-collision negative control and an infeasible reserved-band case.

Actual private PV geometry draft solves35writer branches W8 and30reader branches R10 with no depth delta. It also solves all44 raw-reset branches by choosing earlier ancestors of the SAME original reset chain:151->194 raw relay copies, same original tail and same total reset depth. No data/START/reset cycles added; +43 raw relay flops inferred. All65START+44raw branch proposals have no macro-corridor solver failure. First viewed image exposed the impossibly narrow W-edge route; draft now blocks that edge corridor and detours through the true inter-column channel. New actual image and exact hop/site certificate are next. This is SOURCE/GEOMETRY DRAFT only: no adopted plan or bind/build yet; row legalization, final hop measurement and no-overlap placement remain open.

## 2026-11-08 02:45 PST source and running jobs

PV macro-aware source draft published to hub `codex/kv-start-obstacles-0222@873374c71c` (six new files only; no default behavior changed). Revised image `results/geom_review/kv_start_obstacles_0222/review.png` viewed: PASS-COND for private bind; no physical closure claim. Exact 109 corridor paths max 403.554 um, no off-path or macro-center collision. 10 shared centers, max 4 groups per center; actual cell allocation remains open. Private PV bind queued at epyc4 `/srv/opentallas-scratch3/claude/codex-kv-types-0222-pv`; intel2 log `~/codex-kv-types-0222/pv_bind.otrun.log`. Private combined ioft SR+lockup bind active at epyc4 `/srv/opentallas-scratch3/claude/codex-kv-types-0222-ioft`, unit `oth-ubuntu-3784446-1794133950`. No P&R launched by this lane yet.

## PHY exact diagnosis correction

Previous KV-TYPES-3 statement that o_phy_Q__sN_piN_d3 q[8..11] is pi3 data launched on a falling edge was wrong. The current bound concatenation maps those four bits to fh3[0..3]. Source tools/qwen_kv_die/phy_pc4_gen.py explicitly models fh/rh as combinational forwarded clocks; pi3 is rising-edge registered data. Exact current TT path starts at clk_t7 falling edge, carries the macro's combinational clk->fh arc, then reaches the bout D.

Own read-only GRT geometry intel1 `/srv/opentallas-scratch2/claude/codex-kv-types-0222/phy-geometry/geometry.log`: fh3[3] pin (306.624,994.296); q[11] capture (858.006,594.810); output face (864,596.640). End-to-end Manhattan distance about955 um, not one half-cycle reach. The other worst d2 q[0..3] is likewise forwarded-clock capture. A conservative three-flop transport at about320um hops would require two added output pin cycles, coherently padded across mixed bundles; the proposed one extra capture stage still needs a timed full-period buffered long hop. No native clock contract, delay constraint or PHY lib changed here; no PHY new physical run launched.

Existing ioft and PV private binds remain the next actionable pilots. Hubs child has one same-clock local-capture CTS screen queued on E4 (32GB/8T), source `codex/kv-capture-clock-0222@c894a42091`, actual transform572 clock endpoints/+88 buffers, no data-cycle delta; no route until measurements. SYS_C child private compact-D2D source form proposal `codex/kv-sysc-form-0222@371aa31b5d` is continuing toward implementation, parent unchanged. Hub_C physical PLL boundary question is written in CODEX-LOG OWNER?.

## 2026-11-08 02:54 PST NEWFAIL sys_SD_v1 a13

Actual current wave a13 finished GRT-0116 after30 iterations: total overflow8, allM6, max horizontal1/vertical0; routing use4.05%,59361 nets, wirelength1771294um. Exact intel1 `.../kw25-wave-1106/runs/qwen_kvsys/kit-wave/qwen_kvsys/event28w_c/items/kv3_sys_SD_v1/attempt_13/gen/kv3_sys_SD_v1/run/logs/asap7/dp_kv3_sys_SD_v1/base/5_1_grt.log`. No routed DRC/sign-off verdict exists. Congestion report concentrates at x1862–1865 along macro E/FDI edge, nets p_tx_d and cland_i_host_fdi. Actual GRT density/congestion PNGs viewed (local `/tmp/codex-kv-types-0222/sd_v1/`). SMELLS: narrow E channel, FDI edge pin fan-in and local FIFO/landing-ring clumps. Macro interior red is blockage coverage, not standard-cell density. No repeat, no allow-congestion override and no macro move started. The SEL_CHUNK8 source fix is present; this is a routing-channel class distinct from its earlier selector setup miss. Next structural form needs more E-channel capacity or localized pin/logic corridor reorganization; same-shape flow-knob trial is held. Base SD a7/hroot private still progressing at last read.
