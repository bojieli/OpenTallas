# MU-ADOPT-HROOT: the KV die host root and KV layer programme for 4 users (RELEASE_TREE K.STA.MU, MU.QW.KVATT)

Branch `claude/mu-adopt-hroot-1019`, based on `claude/mu-adopt-kv-1019` (3b4ffd169). This lane closes the three blockers
MU-ADOPT-KV found (`../kv/README.md` §3, §6):

- (a) the host-root endpoint faults on hc pos[17:13] != 0 and on a second step in flight;
- (b) the epoch allocator faults on positions >= 8192 and holds one token;
- (c) the KV layer programme runs one token at a time.

Every change is a new drop-in module with the original's ports and a `MU` parameter. With `MU 0` it instantiates the
unchanged original, so it is behaviour-identical by construction. **No existing RTL file changed**, so no pinned source
digest drifts. Static schedule only: nothing adds a ready, a credit or a stall. Faults are sticky and fail closed.

Benches ran on the fleet under Verilator 5.050, the closure daemon's version. The launcher is
`rtl/test/mu_qwen_1018/run_all_hroot.sh ROOT OUT`, and `run_mu_hroot.sh ROOT OUT CASE` runs one case.
`lists/<tb>.f` lists every file a case reads. The logs are in `runs/`.

## 1. Endpoint: `qkd_host_native_token_endpoint_cancel_mu` (the guard core's `u_rank__u_native`)

`rtl/qwen_sys/mu_qwen_20261018/qkd_host_native_token_endpoint_cancel_mu.sv`. Under MU 1:

**Admission.**
- The host step carries its user on hc pos[17:16]. The endpoint strips it, so positions are below 8192 per user and
  hc pos[15:13] must be 0.
- There are 4 contexts, one per user. A start for a user whose context is still owned is a protocol fault.
- The shared epoch must carry the step's user: epoch[1:0] == hc pos[17:16].

**Issue.**
- Requests issue in acceptance order, with the original's single request credit.
- `request_pos` is the stripped 13-bit position. The user travels in the TAG epoch.

**Results.**
- A result is matched to its context by the result TAG's epoch user, plus the full TAG59 and generation.
- Steps retire in acceptance order (the head), one per edge.

**Report.** `local_tk` uses the `ot_qfd_pkgctl` MU form:
- [92] done is sticky after the first retire;
- [91:90] is the generation of the last retired step, and pkgctl counts a die report when it changes with done && drained;
- [89] is drained;
- the token, value and cycles fields come from that step's own context.

**Drains (audit point).**
- The four die drain flags are global.
- With one step owned (a single user), retire waits for all four drains, exactly as the original.
- With other users' steps in flight, the die is never globally drained. A step's terminal result therefore retires it
  without the global drains: the static calendar emits that result after the step's last scheduled KV, VM and
  collective work.
- Recovery clear, cancel release and the wrap fence still require the true global drains.

**Where it goes.** `qkd_hr_core_guard` (not closed) through the existing member-wrapper mechanism, which needs no yosys
re-partition:

```
gen_cluster.py --wrap-only <dir> --wrap qkd_host_native_token_endpoint_cancel=qkd_host_native_token_endpoint_cancel_mu
```

- The result is committed as `rtl/qwen_sys/mu_qwen_20261018/host_cluster_mu/qkd_hr_core_guard.v`. It differs from the
  generated core in one line (plus a header).
- Sources add the `_mu` file.
- For the composition gate, `bench/flat_wraps.json` takes the same wrap.

## 2. Epoch allocator: `ot_qwen_tp8_token_epoch_allocator_mu` (die-0 coordinator, inside `qkd_hr_core_peer`)

`rtl/qwen_sys/mu_qwen_20261018/ot_qwen_tp8_token_epoch_allocator_mu.sv`. Under MU 1:

- **Epoch.** The epoch is {seq14[user], user2}, the MU-ADOPT-KV convention. The KV die reads the stage user from TAG
  epoch[1:0].
- **Request.** The user is the request position's [17:16]. The range check is on [15:0] < 8192.
- **One allocation per user.** Four are in flight. A request for a user who still owns an allocation is not ready.
  This is the original's host-boundary admission handshake, not a new one.
- **Wrap.** Each user has its own 14-bit sequence, so a user's epochs wrap after 16,384 steps. The original wrap fence
  clears all four sequences.
- **Terminal.** A terminal is matched to the allocation of the user in its TAG epoch[1:0]. It follows the same drains
  rule as the endpoint.
- **Grant.** `grant_*` shows the latest grant. There is one grant handshake at a time, as in the original.

**Not yet adoptable in peer.** The allocator sits at
`root__u_coordinator.u_lifecycle.u_lifecycle.allocator` (`qkd_host_tp8_coordinator` → `qkd_host_coordinator_services`
→ `qkd_host_lifecycle_collected`). Its neighbours are still single-step:

- `ot_qwen_tp8_token_cohort`: one cohort is active, and a second begin is a lifecycle_fault.
- `qkd_host_lifecycle_collected`: one terminal_pending / post_pending.
- `qkd_host_ctrl_token_service_packet_collected`: one retained request. It still checks `cq[cr][17:13] != 0`, which is
  a fault for users 1-3; under MU this must be [15:13].
- `qkd_host_peer_coordinator_codec`: one allocated identity in the class-9 frames.

Swapping the allocator alone would make the second user's begin a cohort fault. That is the remaining host-root MU work;
see §6.

## 3. KV layer programme: `qkd_static_kv_layer_programme_mu` (in `qkd_kvs_ctl`, an RTL-only parent whose kit is not closed)

`rtl/qwen_sys/mu_qwen_20261018/qkd_static_kv_layer_programme_mu.sv`. This is the KV analogue of compute-die R1. Under MU 1:

**Contexts.**
- There are 4 token contexts, one per user. The user is authority_epoch[1:0].
- All contexts share the one boot-loaded stage table, so every user runs the single-user programme.

**Static calendar.**
- A compiled per-user, per-stage **GAP table** (4 × 36 words) gives the idle cycles user u waits before stage s.
- User 0, the latency user, is compiled with all gaps 0. Its every edge then equals the original's (bench: lockstep).
- Two contexts with an event on the same edge (any root, stage_start or stage_done) is a sticky collision fault,
  `fault_code[4]`. The compiler must never emit such a calendar.

**Boot image under MU.**
- 0..323 are the rows, unchanged;
- 324 is digest64 and 325 is epoch16;
- **326..469 are GAP[u][s-1]**, u-major;
- 470 is the seal.

**Outputs.**
- The metadata outputs (epoch, token, position, ctx_t, generation, stage, layer, completed_stage, quiet, age) follow the
  context that fired the latest event.
- Every consumer that latches them at its event pulse therefore sees that user's stage. The user rides in epoch[1:0]
  to the writer and the PC calendars (MU-ADOPT-KV).
- One shared table read port: a second stage load on the same edge is already a collision.

**Adoption on the KV die** (KV die lane, open):
- the `layer_programme` role → `qkd_static_kv_layer_programme_mu` under `OT_KV_MU=1`;
- the boot loader / boot image emits the GAP block and the seal at 470, with the GAPs from `mu_calendar`;
- consumer audit: every reader of lprg `stage/epoch/token/generation` must latch at its pulse rather than hold the level
  across a stage. The writer programme `qkd_kv_native_programme` and the attention programme need the same multi-context
  treatment; they are still single-token;
- regenerate the `qkd_kvs_ctl` kit.

## 4. Verdicts (Verilator 5.050, fleet)

| case | verdict |
|---|---|
| `tb_mu_hroot_e2e` (MU 1, allocator `_mu` + endpoint `_mu` + KV lprg `_mu` + `qkd_kv_mu_wrow`) | **PASS**: 3 rounds × 4 users = 12 steps, all 4 in flight at once (4 endpoint contexts, 4 allocations). Allocator epochs are {seq14[user], user2}; requests go out in acceptance order with position[17:13] = 0 (stripped); 432 writer stages, each with the user's own epoch, layers in order, KV row = 64 + l + 256u, no range fault. Retires are in acceptance order with the pkgctl-MU report (generation change, done, drained, own token/value) within 12 cycles of the step's KV done; users 0-2 retire and terminate with the die drains low (the !alone path); allocator terminals are accepted; no protocol / identity / programme fault. |
| `tb_mu_hroot_collide` (negative control) | **PASS**: user 1 started on user 0's frame slot raises the programme collision fault (fault_code 0x10). |
| `tb_mu_lprg_lockstep` (seed 7) / `_s2` (seed 1234) | **PASS**: random legal 36-stage tables, 3 tokens. MU 0 equals the original on every output and every edge (5,597 / 5,102 edges). MU 1, user 0 with gaps 0, equals the original on every edge from the first start (5,593 / 5,098 edges, 804 / 807 events). |
| `lint_guard_mu` | **PASS**: `qkd_hr_core_guard` MU 1 core with its 105 member sources: no Error, PINMISSING, PINNOTFOUND or PINCONNECTEMPTY. |
| MU 0 identity: `ex_endpoint` / `ex_endpoint_mu0` | **PASS**/**PASS**: the existing `tb_qkd_host_native_token_endpoint_cancel` on the original and on `_mu #(MU 0)`, with identical results (checks 146, requests 27, credits 18). |
| MU 0 identity: `ex_lifecycle` / `ex_lifecycle_mu0` | **PASS**/**PASS**: the existing `tb_qkd_host_lifecycle_collected`, and the same bench with the lifecycle binding `ot_qwen_tp8_token_epoch_allocator_mu #(MU 0)`. |

Mutants (each applied to a copy of one RTL file by `run_mu_hroot.sh`; all FAIL; the witnesses are in `runs/mut/`):

| id | mutation | fail regex (witness) |
|---|---|---|
| ep1 | endpoint keeps the single-user position check (pos[17:13] == 0) | `ERR cyc \d+ endpoint protocol_fault` |
| ep2 | endpoint retire waits for the global drains while other users are in flight | `retire late \(waited for global drains` |
| al1 | allocator epoch without the user in its low bits | `allocator epoch != \{seq14\[user\], user\}` |
| al2 | allocator single-busy (the original rule) | `allocator never ready for this user` |
| kp1 | KV programme takes no user from the epoch (all starts in context 0) | `ERR cyc \d+ KV programme fault` |
| kp2 | KV programme metadata follow the previous owner, not the firing context | `user token without 36 writer stages` |
| kp3 | KV programme collision detection removed (collide case) | `FAIL MU_HROOT_COLLIDE: no collision fault` |

## 5. Tiles: where each change lands, and the re-closes the closed tiles need

| tile | state (10-19 00:45, closure_loop state) | this lane's change | action |
|---|---|---|---|
| `qkd_hr_core_guard` | not closed; route `qkd_hr_core_guard-r4-dc6000d53` RUNNING (MU 0) | endpoint `_mu` (one member wrap) | The next guard route takes `host_cluster_mu/qkd_hr_core_guard.v` (request block in lanes/HKV-HROOT.md). Do not kill r4: if it closes at MU 0, the MU 1 core re-closes with an `rtl_change` reason (draft below). |
| `qkd_hr_core_peer` | not closed; route `qkd_hr_core_peer-r3-40d82161e` RUNNING (MU 0) | allocator `_mu` ready, **not wired** (§2 chain is single-step) | The next peer regen after the coordinator chain is multi-step. |
| `qkd_hr_core_prompt` | not closed; route `qkd_hr_core_prompt-p5-0a8742a18` RUNNING (MU 0) | none here (pb2 MU_OUT / PLB 11 from MU-QWEN-HOST) | The next prompt regen takes MU-QWEN-HOST's MU 1 pb2 chain. |
| `qkd_kvs_ctl` (kit, not closed) | parent of lprg + writer | lprg `_mu` | The KV die lane binds it under `OT_KV_MU=1` with the boot GAP block (§3). |
| `qkd_host_ctl` | CLOSED `qkd_host_ctl-hc1-71ffdaf23` | none here | Re-close at MU 1 (MU-QWEN-HOST `ot_qfd_pkgctl` MU calendar + hc user). |
| `qkd_hr_core_order` / `_queue` / `_tx` | CLOSED (order r3, queue r4, tx r2/rr1) | none here | Re-close at the MU 1 cluster regen (pb2 / if_pins MU_OUT chain they carry). MU 0: no re-gate, because no file changed. |

**`rtl_change` receipt drafts** (submit_exact spec `reroute_reason`, used once the MU 1 sources are on the routed branch):

- `qkd_hr_core_guard` (if r4 closes at MU 0):
  `rtl_change: MU 1 (Qwen ROM 4 users, owner MU.DECIDE A 10-18): u_rank__u_native qkd_host_native_token_endpoint_cancel -> qkd_host_native_token_endpoint_cancel_mu (same ports; 4 user contexts, hc pos[17:16] user strip, in-order retire, pkgctl-MU report); bench results/rtl/mu_qwen_1018/hroot (tb_mu_hroot_e2e PASS, ep1/ep2 FAIL witnesses); MU 0 core unchanged`
- `qkd_host_ctl`:
  `rtl_change: MU 1 host plane (MU-QWEN-HOST 433d668c5): ot_qfd_pkgctl MU 4-slot static calendar + hc user on pos[17:16] at the tile's pin flops; benches results/rtl/mu_qwen_1018/host (tb_qkd_host_ctl_mu PASS, cm1-cm4 FAIL); MU 0 13/13 host benches identical`
- `qkd_hr_core_order` / `qkd_hr_core_queue` / `qkd_hr_core_tx`:
  `rtl_change: MU 1 cluster regen (MU-QWEN-HOST 433d668c5): the pb2 / if_pins chain these cores carry gains MU_OUT (in-flight FIFO, NSLOT 4, PLB 11); tb_qkd_host_mu_out PASS, hm1-hm4 FAIL; MU 0 = text-only drift, no re-gate`

## 6. Open (owners)

1. **Host-root coordinator chain, multi-step** (HKV-HROOT / a new MU lane). Make these 4-deep under MU: the token service
   (`[15:13]` check, 4 retained requests), `ot_qwen_tp8_token_cohort`, the lifecycle terminal / post queue, and the
   codec's allocated identity. Then wire `ot_qwen_tp8_token_epoch_allocator_mu` with `.MU(1)` through
   `qkd_host_tp8_coordinator` → services → lifecycle, and regen peer. An alternative to price first: under the static
   calendar every rank sees the same hc sequence, so each rank could compute {seq[user], user} locally (allocator `_mu`
   per rank). That takes the die-0 round trip off every step, but it gives up the coordinator's cross-rank identity
   check before admission; pkgctl still checks the results.
2. **KV die adoption of the lprg `_mu`** (KV die lane): see §3. Also the multi-context writer programme and attention
   programme.
3. **Compiler** (`mu_calendar`): emit the KV GAP table (4 × 36) from the KV service windows of the calendar of record.
   Assert user 0's gaps are all 0, and assert no event collision on the KV programme's own event set.
4. **Owner/coordinator audit:** per-step retire without the global die drains while other users are in flight (§1, §2).
