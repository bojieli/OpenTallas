Bounded independent review of the ORIGINAL e57e/3c99 verifier and 47b local-SU envelope.
No compiler correction, hardware, model-generator, legacy pinned-source or main edits.

Prerequisites (git objects, not prerequisite replay/cherry-picks):
e57e08aadb7baf9cf50526c1ad50698cd3eb479d compiler and ISA/demand helpers
3c99ce15f2435a59680183e1103378a91bf0896e persisted compiled_v2 catalog
47b715428069c730b0f263d2a24604d3bc828d62 local-home/calendaring source and frozen receipt
ce7f34f4509d0c95daf1c053d5709a8e3161bae0 original verifier failure receipt
1360ff9e12f130a656dbbca0b00c02de860584db corrected selector metadata
Additional transitive historical sources are read-only git objects; hashes are in review.json.

Reproduce from repository worktree root:
python3 results/quality/w10_crom_compiler_independent_review_20261001/reproduce.py /tmp/w10-crom-independent-replay.json
cmp /tmp/w10-crom-independent-replay.json results/quality/w10_crom_compiler_independent_review_20261001/review.json
python3 -m pytest -q tests/test_w10_crom_compiler_independent_review.py tests/test_w11_dsrom_crom_control_catalog.py

The generated canonical catalog's all-use replay passes; the original verifier's immutable-source binding is REFUTED.
Mutating predicates, emptying commands with expected0, changing the encoded source hash, and lying about command count all pass the old verifier.
Fermat owns the correction; this artifact does not review or promote a future correction.
The 6c7 software join remains unqualified until corrected immutable-source guards and negative controls pass.

Local11 is an SU-region Manhattan envelope, not actual placed coordinates or a legal route.
Cold2/4/128 partials exclude arithmetic, actual receiver stalls, port/deadline/provider/CTS closure.
The128-credit 164-home/7380-bank proposal displaces existing SU: REJECT_UNRESERVED_SU_DISPLACEMENT.
No historical75-route power subtraction. Local bidirectional control state704+768 bits is nonzero and still requires its own characterized join.
The separate a97775-cycle control cost ledger is not a local11 characterization.
Physical/provider/actual control runtime admission remain false. No headline or adoption; no jobs launched.
