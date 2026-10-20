# MU4 POST UID binding (KV-HOST2 10-19) -- checked real-slot private decode in qkd_host_post_collector_mu

Model 164138243 (codex/kv-host-mu-binding-model-1019) found: the selected HOST observer exports RAW per-user
positions (<8192) plus the real scheduler slot, but `qkd_host_post_collector_mu` decoded the user from pos[17:16], so
slots 1-3 alias user 0.  Fix (default-off, preferred model option): `UID_SLOT=1` decodes the user from the CHECKED
slot (slot[7:2]==0), requires raw positions (pos[17:13]==0, pos[12:0]==TAG position) and indexes the owned step whose
TAG epoch UID was allocated, so slot UID != epoch UID faults.  `qkd_host_coordinator_services_mu #(POST_UID_SLOT)`
passes it through (default 0: existing MU benches/behaviour unchanged).  No register, no edge, public CQ untouched.

Bench `rtl/test/mu_qwen_1018/run_post_uid_slot.sh` (Verilator 5.050, ot-epyc7 unit oth-ubuntu-623696-1792456945):
| case | expect | result |
|---|---|---|
| exact (4 users x 3 rounds, overlap, terminals 2,0,3,1) | PASS | PASS posts=12 |
| neg_slot4 / neg_poshi / neg_uidx | PASS (sticky fault seen) | PASS |
| legacy_rawpos (UID_SLOT 0 on raw positions = the model's mismatch) | FAIL | FAIL fault=1 posts=0/12 |
| m2 (legacy decode in slot mode) | FAIL | FAIL |
| m3 (slot range check removed, consistent slot-6 alias) | FAIL | FAIL no fault |
Logs: out/<case>.log (fail witnesses: out/legacy_rawpos.log, out/m2.log, out/m3.log); source hashes source_sha256.txt.

Open (not done here): integrated HOST MU family selection (model steps 1-2: root/rank/control/packet/bundle +
generator HOST_MU), per-context terminal calendar + POST global release_seen identity proof (step 3), integrated
four-slot mechanism bench (step 4).  release_seen is safe only while the class9 codec releases the POST head alone.
