# Staged HEAD HBC source candidate

The current full entry compiler required successful CSR timing before it could emit the HBC setup that enables CSR forwarding. The staged compiler emits the three HBC records and six HOST parameters first, from the measured ingress and an explicit clock/reset profile. It emits no CSR, RUN/GO or mission START authority.

This candidate uses the actual canonical component measurements: HOST0 launch600/604/608 reaches from_prev720/724/728, with HOST boot counter zero at global27 and reset release8. Header/body/commit receiver dates are693/697/701. The runtime context IDs tid0/token0/epoch0, user0/position1048575, stage81/rank0 were selected with the token lane; token0 is a context identifier, not expected token output. Programme identity hashes the actual activation scope and supplied clock profile. The original417-word HOST HBC book remains fixed and is distinct from80 activation beats.

The previous61-edge HOST-to-CTL observation is STATUS transport, not successful CSR forwarding. It supplies no CSR authority here. Actual context admission and downstream CSR timing remain to be measured. A separate control-origin correction may require remeasuring ingress; this candidate has no production transport, parent G5 or physical signoff credit.

Twenty targeted tests passed. Three full compiler outputs (AR, actual activation grammar and MTP) retain their exact pre-refactor hashes. The generated HOST wrapper passes GEN. Its complete non-parameter token stream equals the current exact6 native HOST source; only LOCAL_STAGE, LOCAL_RANK, PHASE_BOUND, CLOCK_RESET_ID, BOOT_HEADER_EDGE and BOOT_COMMIT_EDGE change. No RTL stages, boundary reset routes, clock ports or data latency are added.

`host0_peer_frames.hex` is three553-bit ot_s81hd_mesh_lane.tx_d words in launch600/604/608 order. Each has valid bit552, kind7 in bits3:0 and HBC payload in bits527:16. `peer_records.json` states the dates explicitly. The native wrapper is the generated published wrapper passed through the existing private-RAW emitter; it was not hand-patched.

Run source: epyc6:/srv/opentallas-scratch2/claude/codex-head-hbc-1106. Prepared plan153f6160826a / unchanged sidecar90d006a48f17. Only the HOST provider's six parameters are bound. This does not activate a global plan or authorize route.
