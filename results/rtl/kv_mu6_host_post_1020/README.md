# KV-MU6 10-20: HOST MU POST / release proof on the KV die HOST root configuration

Die binding (GEN9 d22bu, ep5 kvs14r-ccc9418ac-gen9d22bu, OT_KV_MU=1 + HOST_OBS/OBSX): the HOST root is
qkd_host_root_admission_obsx, generated from qkd_host_root_admission_mu = the whole MU 1 HOST family (prompt MU1,
packet bundle _mu, token service _mu, native endpoint _mu, guard _mu, record port _mu, tp8 coordinator _mu with
POST_UID_SLOT 1). This bench runs the die-0 coordinator chain (token services x8, coordinator/codec/services/lifecycle/
allocator/cohort/POST _mu, 8 rank codecs + endpoints _mu, KV layer programme _mu) in that configuration:
UIDSLOT 1 = coordinator POST_UID_SLOT 1 with RAW positions + the real slot on the HOST step/CQ faces (as the real
observer ot_host_if_pb2_observed exports them).

New check (all cases): every POST needs the 8 rank releases of ITS OWN terminal (release TAG names the user's current
epoch), so the collector's single global release_seen vector cannot mix or reuse releases of overlapping users.

Verilator 5.050, ot-epyc5, sources = origin/main 92cfdd6e7 + this branch's tb/run edits (rtl/test/mu_qwen_1018).

| case | expect | result |
|---|---|---|
| tb_mu_peer_e2e (UIDSLOT 0) | PASS | PASS, 12 POSTs release-checked, 96 rank releases, overlap_post 10, max POST after KV done 34 |
| tb_mu_peer_abort (UIDSLOT 0) | PASS | PASS |
| tb_mu_peer_e2e_uid (die config) | PASS | PASS, identical counts |
| tb_mu_peer_abort_uid (die config) | PASS | PASS (3 cancels, 15 POSTs) |
| uid0: raw positions + legacy POST decode | FAIL | FAIL (coordinator fault cyc 547) |
| pr1: release_seen not cleared at POST | FAIL | FAIL "POST before all 8 rank releases of its own terminal" cyc 2933 |
| pr2: POST ignores release_required | FAIL | FAIL same check cyc 2933 |
| pc1, sv1 (existing mutants) | FAIL | FAIL |

pr1 shows the hazard is real (with users overlapping, a kept vector would let the next head POST early); the release RTL
clears it at each POST, and the bench shows each POST waits for its own 8 releases.
Not covered here: the full qkd_host_root_admission_mu packet->scheduler->package->observer integration (model step 4),
which still needs its own bench.
