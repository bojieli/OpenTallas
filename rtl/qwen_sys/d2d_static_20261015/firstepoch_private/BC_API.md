Private BC first-epoch API

Source: qkd_d2d_cal_seq_pin_bc_fe.sv, copied from frozen 9c43 BC input. Public sources are untouched. Defaults ENABLE_FIRST_EPOCH_GUARD=0 and FIXED_IMAGE=1. FIXED_IMAGE identifies the frozen-image component family; it does not bypass epoch checks.

Additional inputs:
- bcfg_epoch[15:0], bcfg_valid: sampled with bcfg_tx_we/rx_we/address/data.
- epoch_id[15:0], epoch_valid: sampled on epoch_go alongside epoch_go_q; identity holds otherwise. Reload invalidates request_valid.
- pair_epoch[15:0], pair_ready, pair_poison: matching TX/RX receipts from the paired calendar guard. pair_ready certifies both receipts for pair_epoch.

Additional outputs:
- cfg_epoch[15:0], cfg_valid: registered on the exact existing cfg output edge. Boot writes use boot metadata; runtime writes use captured request metadata. cfg_valid is zero without a write.
- start_epoch[15:0], start_valid: registered on the existing cal_start output edge. No extra schedule edge is added.

Enabled behavior: epoch_go_q reaches the unchanged real qkd_d2d_cal_seq only when reset landing, matching valid pair/request epoch, no reload/halt, no poison, and no current or same-edge original fault all authorize it. A rejected request poisons the component; later uploads do not retry it. first_consumed and early_first clear only on raw reset through the independent two-edge guard reset landing. Subsequent epochs receive the same checks. Original COL/RUN/STALE/EARLY faults remain sticky and retain their source predicates. The inner sequencer receives halt on guard veto, and external start/config/event outputs are vetoed on the fault edge. Default-disabled original outputs keep their original logic and capture edges.

Added source state is exactly 72 bits: boot input metadata17 + merged config metadata17 + request metadata17 + start metadata17 + first_consumed/early_first2 + independent guard reset landing2. Functional/source count only; no synthesis/physical cost claim. No compilation or simulation performed by this source worker, per parent instruction. Parent owns shared-worktree commits and validation.
