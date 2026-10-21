# KV-MU7 10-20: full multi-user HOST root bench (packet -> scheduler -> package -> observer -> POST), 4 users

Bench `rtl/test/mu_qwen_1018/hroot_full/tb_mu_hroot_full.sv`, runner `run_hroot_full.sh ROOT OUT CASE`,
Verilator 5.050 (closure-daemon version), fleet (ot-run). Source = this branch (claude/kv-mu7-hroot-1020) = KV-HOST9B
26aa2a496 (GEN9 d22bu MU children unchanged vs ccc9418ac + the closing PROMPT leaf) + the POST-collector fix below.
Every file a case read is in `<case>.files` with hashes in `<case>.sha256` (from Verilator's dependency file).

## What runs
Die 0, as the KV die binds the HOST MU family (d22bu, OT_KV_MU=1 -> qkd_host_root_admission_mu children):
- PROMPT leaf `qkd_hr_core_prompt_mu4p3_n32` (sha 4379dbb8, the native32 netlist KV-HOST9B is closing; zero-delay
  functional ASAP7 cells `asap7_func_cells.v`, exhaustively equal to the official models: `cells.log`), or its RTL
  source `qkd_hr_core_prompt_mu4_ps3` (case ps3). Host traffic enters as **packets** (ABI v1: BAR write/read
  0x01/0x02 -> 0x81/0x82, DMA read 0x12 -> 0x13, DMA write 0x14 -> 0x15; credits both ways) at u_axi; inside the leaf
  the real SQ/prompt DMA, the 4-slot **scheduler** (ot_host_if_pb2_observed ps3), the MU 1 **package** controller
  (ot_qfd_pkgctl), CQ DMA and the **observer** step/CQ faces (raw position + slot).
- token service `_mu` (cmd -> hc, tk8/kst8/boot8 collection) + 7 peer token services (frame router),
  `qkd_host_peer_root_mux` (ranks 1..7 share ONE physical port, bench link router), coordinator
  `qkd_host_tp8_coordinator_mu #(POST_UID_SLOT 1)` (allocator/cohort/codec/lifecycle/**POST** collector `_mu`),
  8 rank codecs (rank 0 gets the observer faces) + 8 endpoints `_mu`.
- die model: KV layer programme `_mu` (36 writer stages, row 64+l+256u) on cohort dispatch; engine result = the
  user's generated token -> endpoints -> tk8 -> package retire -> observer retire/CQ -> POST.
Users: prompt 2/3/1/4 tokens, generate 3/2/4/3 (18 steps, 12 CQ entries); users 0..2 arrive first, user 3 after
6 POSTs (per-user epochs reach the peers out of global order).
Fixtures (declared; not this mechanism): service-epoch bootstrap (leaf sees service_ready 1 / ready8 ff, no begin
credit; token services startup_allowed 1), program/image loader (rank codecs program_ready 1), service guard
(endpoint tk straight to the token service), rx/tx link-class mux + PHY.

## Results
| case | expect | result |
|---|---|---|
| n32 (release leaf) | PASS | **PASS** 18 steps, 12 CQ exact, 18 POSTs each after its own 8 releases, 144 rank requests, 126 peer starts, 648 writer stages, 4 users in flight, 2 out-of-order epochs, max POST after KV done 105 cyc, step cmd->POST avg 2468 / max 2520 cyc, 18 steps in 20154 cyc |
| ps3 (leaf RTL) | PASS | **PASS** same counts (max POST after KV done 117, avg 2473) |
| cells | PASS | PASS 38 combinational cells, 738 vectors == official ASAP7 models |
| nx0: POST collector as bound in d22bu (no next-issue hold) | FAIL | FAIL: post_fault at the first POST (cyc 3343) |
| uid0: coordinator POST_UID_SLOT 0 on the raw-position faces | FAIL | FAIL post_fault cyc 861 |
| pc1: POST only on the global die drain | FAIL | FAIL POST late 2452 cyc, then deadlock |
| ep3: endpoint release waits for the global drain | FAIL | FAIL POST late, deadlock |
| ts1: token service single-user START position check | FAIL | FAIL token service fault die 0 cyc 865 |
| ts2: one global peer epoch freshness | FAIL | FAIL token service fault die 1 at the first out-of-order epoch |
| cd1: codec one terminal at a time | FAIL | FAIL codec fault cyc 8166 |
| hm1 (ps3): retire attributed to the last issued slot | FAIL | FAIL observer retire/token of another user |
| cm1 (ps3): package retires when ANY die reported | FAIL | FAIL package abort cyc 3155 |
| pr1: POST keeps release_seen | (FAIL) | not provoked: with real timing every head's 8 releases precede its other POST conditions; stays covered by KV-MU6 tb_mu_peer_e2e pr1 (FAIL witness there) |

## Finding (RTL fix on this branch): POST collector _mu next-issue race
The scheduler issues a user's next step as soon as the package controller retires the previous one; the lifecycle
admits that user's next ALLOCATION only after its POST (`request_ready && !pp[user]`). So the observer's step_issue of
step k+1 reaches `qkd_host_post_collector_mu` between step k's retire and its POST (measured 10 edges after the
retire = the POST edge). The d22bu collector has one `issued` bit per user and faults on that issue: the bound HOST
MU family faults at the FIRST multi-step user (nx0 witness). Earlier benches hid it (tb_mu_peer_e2e drives the next
host command only after POST). Fix: a one-deep per-user held issue (client/slot/pos) taken when the user's owned
step has retired, promoted at its POST (directly on the POST edge); any other second issue still faults; no edge, no
handshake (MUT 4 = old behaviour). Regression of the existing POST benches on the fix: `REGRESS.txt`.
The fix changes the peer-core RTL (`qkd_host_coordinator_services_mu` -> `qkd_host_post_collector_mu`, inside
qkd_hr_core_peer): the PEER gate source must take it (COORD-REVIEW-QUEUE).
