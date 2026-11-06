# Active wc1 LP origin proposal — inactive

This proposal copies four actual generated LP wrapper types and inserts fourteen per-instance origin pairs from the actual wc1 reset-release graph. All eight C/LP source hashes match the retained receipt exactly. The actual bound top is also hashed, and every C/LP station-to-type association is checked before writing the proposal. Binder outputs are untracked and have no verified source commit, so proposal.json records source_binder_commit=null and the actual byte readset. Wave source2c705 is distinct and is not presented as binder provenance.

Typed map:
- s_0N: s81p_dsdv_slice_lepw_mu_LP__t2, u_u_lnl0..3 = KN5/NK3.
- s_0S: s81p_dsdv_slice_lepw_mus_LP__t2, u_u_lnl0..3 = KN5/NK3.
- s_7N: s81p_dsdv_slice_lepe_mu_LP__t2, u_u_lnl0..3 = KN5/NK3.
- s_7S: s81p_dsdv_slice_lepe_nh_mus_LP__t1, u_u_lnl0..1 = KN6/NK2.

Formula: KN=(reader_reset_release-writer_reset_release) mod8; NK is the reverse difference. The receipt includes each actual reset net and release age. D4/K2 and each reader's local rc/warm age remain unchanged. The change corrects epoch and read slot together. Zero data/pin/model cycles are added; no K change, clock change or reset-force workaround is included.

capability/ contains the exact default-zero source capability snapshot204f8dac0c9. It is required together with parents/: old unparameterized landing definitions cannot elaborate these named parameters. The existing smallest core exact/data/mutant outcomes and full-width parent proof are in ../ds_land_epoch_1106; the frozen native candidate cleared266/266 landings with zero faults and is separately exercising real HOST/KS. This proposal has not been activated, simulated as current die, mapped, routed or released.

Reproduce from a worktree containing the capability:

    python3 tools/s81/prepare_wc1_lp_origins.py \
      --receipt results/token_pass/ds_land_epoch_1106/wc1_all_LP_receipts.json \
      --source-root /srv/opentallas-scratch2/claude/die-s81-59/ev/bind/rtl \
      --capability-root "$PWD" --output /new/owned/proposal

Prepared copy: epyc5 /srv/opentallas-scratch2/claude/codex-ds-wc1-origin-1106/proposal_v2. No active source2c, ev/bind, wc1 or wave inputs were edited. Review this scoped source event before selecting an overlay into a current binding. Any future physical job remains subject to image review before route. The next current-die integration must rebuild the affected landing consumers from this selected cohort, rather than reuse zero-bias LP caches or graft frozen native libraries.
