Native fc31 HOST entry replay: PASS_CUT_COMPONENT

Jobs15/16/17/20/21/22 each PASS at measured KS2297 with held payload/start-pulse producer model. Four jobs check817 outputs each; two check460 each. Every baseline has0 mismatches and0 fault cycles. Calendar-length corruption (hf_7N_l0 bit33) is CAUGHT with204 mismatches and absent column control streams.

Prior failed_null_mutant.json is retained: all six baselines passed but the extra bit13 mutation was MISSED. It changes unused padding in the first0x11 calendar-length CSR (dsdv_seq_host decodes only opcode[7:0] and length[39:32]); a null control is not a meaningful functional corruption. The successful fresh run uses the meaningful bit33 negative control. Default KS2296 and2298/2299 fail phase acceptance;2297 is the measured accepted phase of this exact cut/reset tree.

The underlying harness fix models the actual RX producer: payload[51:0] is held while start[52] pulses, so unequal two-lane ages do not tear the payload. No RTL changes or added model cycles. Unit tests test_dv_cut_replay ALL PASS.

Scope: minimum native-entry control cut on reconstructed fc31, not a full layer/token or current v4.8/v4.9 assembled die. Full-layer programs still need host boot/calendar construction and functional compiler gaps remain. Source jobs: epyc3:/srv/opentallas-scratch/claude/codex-s81/entry_qualified_fc31. Failed phase/null-control runs remain beside it.
