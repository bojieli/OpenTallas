# Composed rank-to-RESULT controller boundary

PASS: the actual historical controller drives two full position/user records through the real extracted rank helper and RESULT landing. Merge valid/row/bits/identity, full512b flit, pending/grant/overwrite edge and sticky fault state match the source reference. Both positions retain the original3edges merge-to-flit; this composition adds0cycles and0state. High-user-bit corruption, dropped live LEP fault and rank-row corruption mutants fail the corresponding full-data/state checks.

The rank helper now exposes original mg1 as check_valid. The composition uses it for original NaN/tag/copy checks, maps slot/RESULT overwrite to original fault bits8/9, and accepts live LP fault at bit10. The remaining12 event producers are explicit external inputs (original0..5 then11..16). Local NaN combines with rank NaN at original bit3. No live status producer is tied.

Own81-bit record, six HSF0 peer frames, destination header and sequencer grant remain caller inputs. Current mesh64 framing, single-spine own-record landing, HBC/START/issue authority and the complete controller remain outside this helper. This is not an hd_ctl/asbuilt provider or physical closure claim.

Runtime epyc1:/srv/opentallas-scratch2/claude/codex-head-ar-compose-1026/src/proof_0, source607b611c7f, admitted ot-run unit948414-1793013706. Reproduce with tools/s81_head/ar_control_bench.sh under ot-run.
