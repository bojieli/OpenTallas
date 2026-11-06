# VP4 same-edge command control copies — source READY

`LOCAL_CTRL=0` is the unchanged default. Opt-in `LOCAL_CTRL=1` copies the six existing registered command predicates and CV into 17 groups on their original edges. Each group owns its local reload conjunction; payload, descriptor latency, absolute issue/drain dates, bank clocks and reset behavior keep their existing edge contract. The critical hbm_stride word uses group11. The 17 groups add119 RTL state bits, zero command/payload cycles. Soft controller parameters propagate through the banks, reset-split and CP wrappers. OT_DBK_HARD explicitly rejects this opt-in against an unchanged signed controller.

The original actual VP4 controller source SHA256 was a7022ed021e90407c48ef984a76f1d832b9c7a53f12a036e3d707cf640fab84e, matching the retained E5 hbm-reform-b13/vp4 kit. No active kit or default recipe changed.

Groups0..4 own match state and absolute date words; groups5..16 own lifecycle/index reset, counts, VM row/chunk, VM stride, HBM row, HBM chunk, HBM stride, drain row, drain chunk/column, pending sectors, WB bank/epoch, and WB reservation respectively. Their loading remains last in the original sequential priority. Nested conditional loading retains the original four-state conditional behavior. Original global predicates/CV remain available for fault, issue/drain and the small long-RT tag path.

Validation:

- Actual SRAM-backed VP4/cursor lockstep: opt-in and default both PASS20 valid cases,11 invalid descriptors,1921 checked cycles,6790 write beats, DESC_LAT4. Existing reference receives the command four edges later as before.
- Causal mutant disabling group11's local lead predicate: caught public write-beat mismatch cycle690. Causal mutant disabling group6's local CV: caught public request mismatch cycle14.
- Canonical ot_keep_regs hook plus ASAP7 mapping:14208 standard cells,3160 sequential cells,2081.41164um² total cell area. All119 local bits map to119 distinct actual DFF drivers, following only polarity inverters from DFF QN outputs. `mapped_survival.json` records every group and driver.
- Reproduction: `bash tools/hbm_v15_harden/bench_dma_vp4_local_control.sh OUT`. Mapping script and survival reader are retained here. The standalone Slang probe needed the production `--compat=vcs` option for an existing declaration-after-use; failed first probe retained in E5 logs, no source workaround.

No physical launch or timing improvement is claimed. Existing VP4 wd half-cycle and output virtual-clock failures are separate and remain owned by the physical lane. Before a new physical trial, measure actual local reload cone fanout/slew and place each payload group with its owning local control; retained119-bit survival alone does not qualify placement.

Artifacts: E5 `/srv/opentallas-scratch2/claude/codex-vp4-localctrl-1106`. Original E5 VP4 kit and timing reports remain unchanged. Topk's analogous canonical keep machinery is reused; no shared flow change.
