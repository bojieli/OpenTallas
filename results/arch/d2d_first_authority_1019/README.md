# D2D first-authority diagnosis: HOLD

Read-only source diagnosis of exact mapped SHA c5449c82545c3b1a978965e608d8cc31fa546983f71979d5bbec48fbfc78cfe0, following arbitrary-old-Q witness a1e609a806. No new constructor, integration, synthesis, simulation, or physical run was performed. The source-qualified startup partition remains HOLD.

The first-edge witness must be preserved. It is not a demonstrated post-reset release failure. The actual mapped source permits its RESETN/SETN-high premise before reset arrives, even with primary por_n/rst_n held low: both primary resets first traverse two UNRESET face FFs. Only then do they asynchronously assert the two synchronizer FFs. Two further UNRESET regional FF stages deliver local assertion. Thus choose initial face/regional outputs high; at clock E1 the consumer can capture divergent D while both roots converge from their common D. This is an admissible pre-reset state extension of the analytical witness, not an RTL waveform or a proof of legal application admission. All 91 prior cone boundary values are FF outputs, so direct primary reset-low does not itself constrain them before the mapped landing reset reaches them.

## Exact reset frontier

For reset held low before E1, with ck running and arbitrary initial unreset pipeline states:

| Edge | Guaranteed update |
|---|---|
| E1 | face stage0 becomes0; new source/clone Q agrees after this edge |
| E2 | face stage1 becomes0; asynchronous s0/s1 assertion follows |
| E3 | regional first stage becomes0 |
| E4 | regional family final stage becomes0; downstream ASR reset asserts |

This is digital source ancestry, not physical POR pulse/phase/recovery/removal qualification. A continuously low reset through E4 guarantees local assertion after E4. A first-clock reset assertion cannot be presumed. For a clean release starting with all these stages low, the face2 + synchronizer2 + region2 chain takes six rising-edge updates; a consumer first samples active D on the next rising edge. The actual primary POR/local-reset relation and application admission must satisfy this chain, not a guessed quiet interval.

For the witnessed txcal.rep[0], RESETN is fam_all[17] and SETN is tie-high _28840_. The exact ancestry includes the kept final copy ot_rrs__u_ot_pr_core_u_core_u_reset_regions_g_fam_g_c_1__qv__c5, regional g_c[1].d, s1, s0, and rst_n__ot_rl1/0. Other consumer reset families are enumerated in reset_ancestry.json and consumer_partition.json.

## Consumer partition and persistence

| Root | Transparent logical endpoints | First sequential endpoints |
|---|---:|---:|
| q_sf_seg[0] |37|19|
| q_sf_seg[4] |36|19|
| q_sf_start[0] |48|34|
| q_sf_start[4] |48|34|
| begin_now |31|37|
| ebc[1] |48|48|
| ebc[2] |48|24|
| ebc[9] |49|34|

Every first sequential destination is DFFASRHQN; there is no macro, unreset FF, or external output before the first state boundary. These are graph facts, not Boolean masking or equivalence proofs. All exact pins and shortest paths are retained in consumer_partition.json.

The q_sf_seg roots reach calendar cur/rep/bcur/fault state. Their witnessed first-edge divergence is reset when the appropriate regional reset actually asserts; this alone does not prove downstream observation or persistence is excluded before that assertion.

The q_sf_start roots additionally reach running and run_c. Exact TX path includes _53660_/A1; RX includes _53484_/B then _53485_/B. Those controls gate UNRESET calendar table e and sel1 writes through cfg_we && !running in the exact source. Thus "all first consumers have reset" is insufficient: an edge1 run-state divergence can condition a later unreset-state write before edge4. This is a source-level possible propagation mechanism, not a claimed actual selected-boot counterexample. Input cfg authority, exact clone endpoint choice, and later compiler overwrite must be proved. The recovery roots similarly require their actual reset/epoch/landing lifetime proof, not merely their reset-capable first consumers.

The implementable conservative partition under unrestricted startup semantics is to preserve canonical roots on all currently affected logical endpoints. No nonempty clone partition has been certified; this leaves fanout closure unresolved. For a qualified release partition, first retain canonical q_sf_start paths feeding running/run_c (and their reconvergent cone). Then separately prove every proposed redirected endpoint has either actual reset domination at its first use or complete erasure of prior effects before observation, including all unreset storage, real SRAM writes and epoch/poison state. Do not label that candidate partition safe until those obligations pass. Adding a reset, initializing clone Q equal, or masking a monitor would change the problem.

## Selected-source limit and next step

This packet diagnoses the mapped private safe-FO source family (dies8cc1bca3, leaf9b369435). Captured GEN8 currently selects qkd_d2ds FRAME with bind=null, rather than this native gate source; its real first application-use time is not established by this packet. No GEN8 adoption or timing/PG closure claim follows.

Next owner decision: retain HOLD; commission a minimum exact source component proof with original arbitrary initial state and real reset landing, coupled to actual boot/configuration authority, for a proposed endpoint partition. Check unreset compiler-table/sel1 identity through first authorized start, and first real SRAM/epoch mutation. Preserve canonical first-edge consumers until that proof exists. No new source construction is authorized by this evidence.
