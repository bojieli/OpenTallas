# Standalone pending/active epoch mask continuation

Source d53159bb5 on codex/qw-mu-epoch-mask-1019 extends the previous scalar proposal to four-bit publication and retirement masks. All named supported banks update independently on the same edge; distinct pending epochs remain distinct. Zero mask is a legal no-op, matching CTLM ctx_ok. ENABLE remains zero by default; no production top is edited.

The only API replacement is publish_user[1:0] → publish_mask[3:0] and retire_user[1:0] → retire_mask[3:0]. NU defaults to 4 and is guarded to 1..4. Acceptance, fetch, consume and release APIs remain unchanged. State remains 157 bits: 64 pending, 64 active, 8 validity, 18 resident identity, 2 reservation and 1 fault. There are zero payload bytes and zero added logical data edges. Physical landing, area, clock ownership and reset guards remain unmeasured and must be priced before adoption.

Filler publication mask is {ctx_mask[2:0],1'b0} at the actual ctx_ld bank update, whose source expression/loop and hash are in mask_source_binding.json. ctx_ok limits unsupported bits but does not require one-hot. Ordinary d_start/s_start and r_fill token updates do not publish epochs. User0 publication remains an independently bound explicit new-context INIT transition; no epoch ingress is proposed. Parent owns CTLM emb_user[1:0] and actual integration. Production event times remain null.

The accepted epoch lower-two-bit user guard is retained for this native ABI: actual accepted observer user_id=tag[44:43] and acceptance requires host_epoch=tag[58:43]. This relation is source-proven rather than assumed from the standalone fixture.

Faults are sticky diagnostics. Named publication without pending, acceptance/publication overlap, publication/retirement overlap, unsupported user bits, and publication/retirement of a resident/fetching/consuming bank fault. No diagnostic gates runtime data, stalls or creates credits. Residency always snapshots active epoch; accepting the next pending epoch does not replace active/resident ownership.

Fleet Verilator 5.050 unit oth-ubuntu-1804627-1792429204 passes actual native59/provider/SRAM numerical proof for three released rows × eight rounds and all 16 existing mutants fail. A separate mask witness passes zero-mask no-op and all 15 nonempty masks with initial publication, next-epoch acceptance during old residency, simultaneous multi-bank reload and retirement (110 checks); six mask mutants fail. Native mutant14 catches latest-pending substitution; native mutants15/16 catch reload/retire during residency. Exact logs/hashes are in mask_runs/out_r2 and mask_receipt.json. Initial attempt logs are retained separately, with its zero-mask rejection superseded.

This proves the standalone ledger and real native reader/provider component only. Actual shared compiler event times, full cap1 programme, production source association, landed ages and full-token/physical qualification remain open. No gate or adoption is requested.
