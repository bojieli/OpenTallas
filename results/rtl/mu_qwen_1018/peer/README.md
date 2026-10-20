# MU-KV-PEER: the die-0 coordinator chain for 4 users (RELEASE_TREE K.STA.MU; follows `../hroot/README.md` §2, §6.1)

Branch `claude/mu-kv-peer-1019` (from origin/main f3647da82). Lane decision (MU-KV): keep the die-0 coordinator and make
its chain multi-step. Local per-rank epochs are **not** adopted, because they would give up the cross-rank identity check
before admission.

All changes are new drop-in modules with the original's ports and parameters plus `MU`, which defaults to 1. **With `MU 0`
each one instantiates the unchanged original**, so it is identical by construction. No original RTL file changed. Three
files are generated from the unchanged originals by `tools/qwen_kv_die/mu_peer/gen_peer_mu.py`, with each listed edit
applying exactly once: the coordinator, the class9 codec and the token service.

Static schedule only: no ready, credit or stall is added. The existing host-boundary admission handshakes (`request_ready`)
and the result credit stay as they are. Faults are sticky and fail closed.

The user is TAG epoch[1:0] (TAG59[44:43]). On the host side it is hc / step pos[17:16], and pos[15:13] must be 0.

## 1. Modules (`rtl/qwen_sys/mu_qwen_20261018/`)

| module | MU 1 change |
|---|---|
| `qkd_host_ctrl_token_service_packet_collected_mu` (generated) | **Die 0:** the START check is `pos[15:13]==0` (was `[17:13]`), and the 18-bit position goes to the allocator. The grant must carry the step's user in epoch[1:0]. There are **4 retained requests**, one per user, each holding its job tuple and granted epoch. An abort cancels the retained users one at a time: the live allocation, or the already-terminated identity. **Peers:** a token frame needs `pos[15:13]==0` and `epoch[1:0]==pos[17:16]`, and epoch freshness is **per user** (seq14 strictly increasing per user). |
| `qkd_host_tp8_coordinator_mu` (generated) | Binds codec_mu and services_mu. The codec's terminal identity is the lifecycle's accepted terminal (`acknowledged_*`), not the latest grant. |
| `qkd_host_peer_coordinator_codec_mu` (generated) | **Per-user allocation table:** each new identity on `allocated_*` is recorded under its user. A class-1 rank request must name its user's live allocation, or that user's queued terminal; in the second case it is returned with abort=1, as in the original. **Terminal queue (4 entries):** the head is broadcast as class5 and released by class8, exactly as the original single terminal. POST retires the head once its barrier finishes. Only that user's queued requests are discarded against it. |
| `qkd_host_coordinator_services_mu` | Binds lifecycle_mu and post_collector_mu. The POST collector's terminal identity is `acknowledged_tag`. |
| `qkd_host_lifecycle_collected_mu` | Binds allocator_mu (from ../hroot, now wired) and cohort_mu. **Terminal queue** in arrival order. The head is presented to the allocator (and to the cohort, if that user's cohort was begun) only when the allocator accepts it on that edge (all drains, or other users in flight), so both pulses coincide; one idle edge separates presentations. **POST queue:** POSTs retire in acceptance order. A user is admitted again only after its own POST (`request_ready` per user). A cancel that names a user's last retired identity is acknowledged (the stale retained-request case). |
| `ot_qwen_tp8_token_cohort_mu` | 4 cohorts, one per user. Dispatch follows begin order. The outputs show the waiting cohort, or else the last dispatched one. A matching terminal (presented by the lifecycle) is consumed without a separate drain check. |
| `qkd_host_post_collector_mu` | 4 owned steps. Ownership opens on a **new** allocation identity. HOST issue / retire / CQ are matched by pos[17:16]. POSTs happen in acceptance order, and the head POSTs on drains **or other users' steps still owned**. |
| `qkd_host_native_token_endpoint_cancel_mu` (edited, from ../hroot) | The class5 terminal-barrier release of an **already-retired** step follows the retire rule (drains, or other contexts owned). A pending release now blocks only its own user's request issue. Without this, 4 pipelined users drain the die on every step (mutant ep3). Releasing a **live** step (cancel) still needs the global drains. |

## 2. The MU 1 peer core

`host_cluster_mu/qkd_hr_core_peer.v` is `gen_cluster.py --wrap-only <dir> --wrap qkd_host_tp8_coordinator=qkd_host_tp8_coordinator_mu
--wrap qkd_host_ctrl_token_service_packet_collected=qkd_host_ctrl_token_service_packet_collected_mu` applied to the main core. Two
instance lines differ. Its sources are `rtl/test/mu_qwen_1018/lists/lint_peer_mu.f` (114 files). `lint_peer_mu` passes.

**Physical composition (open; HKV-HROOT / HKV-PROMPT6 own the live peer route r3/r4).** The r4 kit on the unmerged
`claude/hkv-peer6-1019` wraps these members in `_rr` reset relays. Its token service `_rr` binds the `_pd` fork (registered
RX queue head). The MU 1 physical core is therefore:

- `qkd_host_tp8_coordinator_rr` with the inner `qkd_host_tp8_coordinator` replaced by `_mu`;
- `qkd_host_ctrl_token_service_packet_collected_rr` with the inner `_pd` replaced by `_pd_mu`.

The generator already makes `_pd_mu` from that fork: `gen_peer_mu.py ROOT --pd <..._pd.sv> <dir>`, and every edit applies.
No MU 1 kit or gate was launched here. The pre-r4 main core would re-gate the r3 timing path that `_pd` fixes. A request
block is in `lanes/HKV-HROOT.md`.

## 3. Verdicts (Verilator 5.050, fleet ot-epyc8; `run_all_peer.sh ROOT OUT`, `run_mu_peer.sh ROOT OUT CASE`; logs in `runs/`)

| case | verdict |
|---|---|
| `tb_mu_peer_e2e` | **PASS.** 4 users × 3 rounds, **pipelined**: each user starts its next step when its own previous step POSTs, and user 3 is held back 3000 cycles in round 1. The whole chain runs as RTL: host cmd → die-0 token service _mu → coordinator _mu (allocator_mu epochs {seq14,user}) → local hc + 7 peer token services _mu → 8 endpoints _mu → 8 rank codecs (class9) → codec _mu → cohort _mu → dispatch → KV lprg _mu (36 writer stages, row 64+l+256u) → engine result → class3 to 8 ranks → endpoint retire → lifecycle _mu terminal queue → class5 / class8 barrier → HOST retire + CQ → POST _mu. Counts: 12 POSTs, 96 rank requests, 84 peer starts, 432 writer stages. Overlap: 10 dispatches and 10 POSTs overlapped other users' KV work. 1 grant epoch was below the previous one (out of global order), and the peers accepted it. **Max POST after KV done: 34 cycles.** No fault anywhere. |
| `tb_mu_peer_abort` | **PASS.** The same run, followed by a package abort with 3 retained users: u0 has already POSTed (terminated identity), and u1 and u2 are dispatched but never run. All 3 cancels are issued and acknowledged (u0 against its last retired identity). u1 and u2 become fault terminals, are released on all 8 ranks, get a HOST fault CQ, and POST. Nothing is left over. |
| `lint_peer_mu` | **PASS**: the MU 1 `qkd_hr_core_peer` with 114 sources, with no Error, PINMISSING, PINNOTFOUND or PINCONNECTEMPTY. |
| MU 0 `ex_peer_lifecycle` / `_mu0` | **PASS / PASS**, identical lines. This is the existing coordinator + 8 rank bench. `_mu0` binds **every** `_mu` at MU 0: coordinator, codec, services, lifecycle, POST collector, allocator and cohort. |
| MU 0 `ex_lifecycle` / `_mu0` | **PASS / PASS** (the existing lifecycle bench; lifecycle, allocator and cohort `_mu` at MU 0). |
| MU 0 `ex_tsvc` / `_mu0` | **PASS / PASS**, identical. This is the existing 8-die token-service bench on the collected token service, and on its `_mu` at MU 0. |
| hroot suite re-run (endpoint edit) | All 16 verdicts unchanged (`runs_hroot_recheck/summary.txt`). |

Mutants. Each is applied to a copy of one file by `run_mu_peer.sh`, and all FAIL. The witnesses are in `runs/mut/<id>.log`:

| id | mutation | fail regex |
|---|---|---|
| ts1 | token service keeps `cq[17:13]!=0` | `ERR cyc [0-9]+ token service fault` |
| ts2 | peers keep one global epoch freshness | `ERR cyc [0-9]+ token service fault` (die 1) |
| co1 | cohort single-active | `ERR cyc [0-9]+ coordinator fault` |
| lc1 | lifecycle presents a terminal only on the global drain | `POST late \(waited for a global die drain` |
| cd1 | codec holds one terminal | `codec 1 post 0` |
| cd2 | codec checks requests against the latest grant only | `ERR cyc [0-9]+ coordinator fault` |
| pc1 | POST collector POSTs only on the global drain | `POST late \(waited for a global die drain` |
| ep3 | endpoint retired-step release waits for the global drain | `POST late \(waited for a global die drain` |
| sv1 | services hand POST the latest grant as the terminal | `codec 0 post 1` |
| ab1 | lifecycle refuses a cancel of a terminated identity (abort case) | `abort: not all three retained users cancelled` |

## 4. Audit points (owner / coordinator)

- **Per-step completion without the global drains.** The terminal (allocator + cohort), the terminal-barrier release and
  the POST all complete without the global die drains while other users are in flight. This is the rule the endpoint and
  allocator `_mu` already follow (../hroot §1, §6.4). The single-user path still waits for all drains.
- **POST order.** POSTs are serialized in acceptance order through the codec terminal queue. A user is re-admitted only
  after its own POST. In the bench, a POST lands at most 34 cycles after its KV done.
- **Abort.** Cancels go out one user at a time, and their acknowledgement still needs the global drains (exceptional path).
