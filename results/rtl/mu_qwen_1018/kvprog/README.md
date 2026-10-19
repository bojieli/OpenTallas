# MU-KV-PROG: KV-die consumers of the multi-user layer programme (Qwen ROM 4 users, RELEASE_TREE K.STA.MU / MU.QW.KVATT)

Lane MU-KV-PROG, 10-19, branch `claude/mu-kv-prog-1019`.

`qkd_static_kv_layer_programme_mu` (lprg_mu, hroot README §3) runs 4 users' stages interleaved. Its metadata outputs
(epoch, token, position, ctx_t, generation, stage, layer) follow the context that fired the latest event. This record
audits every consumer of those outputs on the KV die, and asks whether it keeps per-token state across a stage boundary.

Static schedule only: no credits, ready or backpressure. Closed tiles are untouched.

## 1. Result

- **Writer programme** `qkd_kv_native_programme`: no per-user context needed. It latches everything at its start
  pulse. It holds state only inside its window, which lies inside the attention window (§3).
- **Attention programme** `qkd_native_attention_programme`: no per-user context needed. It latches everything at its
  issue pulse. It is one operation at a time, and its own load-while-busy check faults on any overlap.
- **Ownership calendar** `qkd_static_kv_ownership_calendar`: this is the one consumer that **breaks** under MU 1. Its
  window is a whole token. A second user's stage-1 start inside it raised `bad[2]`, a sticky die fault, so 4 users could
  not run at all.
  - New drop-in `rtl/qwen_sys/mu_qwen_20261018/qkd_static_kv_ownership_calendar_mu.sv` (§4) fixes this. It has the
    original's ports plus `MU`; MU 0 instantiates the original.
  - It is wired under `OT_KV_MU=1`.
- **Other consumers**: every other consumer latches at its own pulse. Each holds state only inside its stage's KV-die
  window (§2).

Multi-context versions of the writer and attention programmes would buy nothing. The resources behind them (one d2d KVN
writer lane, one attention service, the per-group landing and front calendars) are single instances. Users therefore
take turns on the KV die stage by stage, which `mu_calendar` already models as the `kvs` resource.

## 2. Audit: what each consumer reads and what crosses a stage

Abbreviations: lprg = the layer programme; sticky = a fault flag that stays set until reset.

| Consumer (tile) | Reads from lprg | Latched at | State held after the pulse | MU 1 verdict |
|---|---|---|---|---|
| `qkd_kv_native_programme` u_wprg (kvs_ctl) | writer_start, stage, epoch, token, position, generation | start: pin flops `start_p` and metadata `*_p` on the same edge, then `identity_q` / `generation_q` / `stage_q` | window [writer_start, stop] = stage ages 642..654 (slots 4..7, stop 12): cycle, row times, identity. All are reloaded at the next start. Nothing survives `done` except the boot table, `configured` and `fault`. | Safe. The window lies inside the attention window. A start while active is a sticky fault. |
| `qkd_native_attention_programme` u_attn + producer + guard + static_ctl (kvs_attn) | attention_issue, attention_run, active, epoch, token, position, stage | issue: `authority_*_q`, `calendar_q`, descriptor tag (the `_ld` producer checks the copy landed at the issue edge) | one operation, busy from run to run + 1784. This is the window [606, 2395] of the stage, 1,789 edges. `loaded`, `busy`, `age`, `done_seen` are cleared per operation. | Safe. A load while busy, loading or loaded is a sticky `local_fault`, and so is a result epoch or layer that differs from the guard's. |
| `qkd_attn_cal_gen` u_attn_cal (kvs_attn) | stage_start (go), ctx_t, epoch | go: `t1` / `e1` | the 176-bit calendar and rx / tx / end, held **until the next go**. The programme reads them at issue, 606 edges after its own stage start. | Safe under the window rule. Another user's stage start in (B, B+606] would hand this user that user's calendar. That start forces the other user's attention window to overlap this one, so it is caught by the attention fault. `cal_epoch` is not checked at issue (see §6). |
| `qkd_kv_ownership_obs` u_oobs (kvs_ctl) | stage_start, stage | stage_start pin flop, then `go = stage_start & stage == 1` | none: a 16-edge quiet counter on the writer words | Safe. |
| `qkd_static_kv_ownership_calendar` u_own (kvs_ctl) | `go` from oobs | go | the token window [go, deadline]: enter 3, leave = quiet36 + 1, deadline = token cycles. A go while active is fault `bad[2]`. | **Breaks.** Replaced by `_mu` (§4). |
| `qkd_static_kv_phase_launch` ×32 (grp) | ctrl_go, kgo, vgo, ctx_t, epoch, layer | the go edge (`meta_q` / `go_q` on one edge, `held`) | held metadata for `META_HOLD_CORE` (8) edges | Safe. Different metadata within the hold window is a sticky fault. |
| `qkd_kv_landing_cal` / `qkd_kv_front_cal` ×32 (grp) | kgo, vgo, ctx_t, epoch, layer | kgo: `t_l`, `l_epoch`, `l_layer`, `have_layer` | **kgo → vgo of the same layer** (stage ages 227 → 1273). The V pass uses the K pass's T and epoch. | Safe under the window rule. Another user's kgo inside this span forces that user's attention window to overlap this one, which is a sticky fault. A pass start while putting is also a fault. |
| `qkd_static_k_issuer` ×32, pc_path calendars (grp, pc) | kgo, epoch, layer; and through the bridge cal_go, epoch, layer | the pulse | the operation's own stream | Safe. The user's KV row comes from epoch[1:0] (MU-ADOPT-KV). |
| `lp`, `kg`, `o_attn` exports (kvs_ctl) | {ctx_t, layer, attention_run}, {layer, epoch, kgo}, the attention face | the consumers above | n/a | Wires only. |

**Window rule.** Users' KV-die stage windows must be disjoint. The binding window is the attention programme's
[issue, run + 1784] = stage ages [606, 2395]. A legal calendar keeps these windows disjoint, which implies:
- the writer windows [642, 654] are disjoint;
- the landing and front kgo → vgo spans [227, 1273] are disjoint;
- no stage start of another user falls in a user's [stage start, issue].

The RTL enforces the rule with sticky faults: the attention controller's load-while-busy check, plus the landing and
front calendars' "pass while putting" check. The bench's `m_envelope` case starts user 1 1,000 edges after user 0 and
FAILs on `attention programme fault`. A violation is therefore never a silent pass. The fault is raised when the second
user's load arrives, not at the first user's issue.

## 3. Calendar consequence (for the `mu_calendar` owner)

`mu_calendar` models the KV-die attention service (`kvs`) as `kv_service = 1555` cycles, "measured-old-RTL".

On the current RTL, the exclusive per-user-layer window is the attention programme's busy span, about 1,789 edges:
- issue at 606;
- run at 610;
- `compiled_end` 1784 from the cal_gen with STRETCH=1 and SERVICE_END 1777.

Of-record call `compile_calendar(dict(users=4, occupancy='measured', head_chunks=8, kv_service=X), tokens=6,
policy='priority')`, run locally on main f3647da82:

| kv_service | aggregate tok/s | per-user tok/s |
|---|---|---|
| 1555 (of record) | 14,053.5 | 4,769.2 / 4,642.1 / 2,321.1 / 2,321.1 |
| 1788 (RTL attention window) | 13,967.9 (−0.6 %) | 4,769.2 / 4,642.1 / 2,315.2 / 2,241.3 |

At 1788 the frame lemma also reports `kvs` violations.

Recommendation: set `kv_service` to the RTL window. It is a modest loss, and the latency user is unchanged.

The bench calendar (`kvprog_cal.py`, production stage roots, round-robin fillers) shows the same KV-die limit. Fillers
progress at about 0.75 of user 0's stage rate (token durations 239,260 / 318,038 / 319,486 / 316,250 edges).

## 4. `qkd_static_kv_ownership_calendar_mu`: same ports + `MU`

**MU 0** is the unchanged original.

**MU 1 behaviour:**
- **Re-arm.** Every go re-arms the window: the cycle counter restarts at 0, `native_reserved` stays 1, and `native_mode`
  keeps its value. The KV die stays natively owned from the first token start until leave / deadline after the **last**
  start.
- **Checks only on transitions.**
  - Enter checks host quiet, upstream quiet and the drains only on the host → native transition (`native_mode` 0). With
    real drains, a later user's start falls inside another user's attention window, where the PC groups are not
    drained. Mutant 6 re-checks on every go and faults there.
  - Leave checks them on the native → host transition, which comes only leave_root after the last go.
- **One user** gives every edge equal to the original. The bench checks this: `identity ownership: MU 0 == MU 1 every
  edge`.
- **Boot roots under MU** (owned by the compiler and boot image, sibling MU-KV-BOOT):
  - enter = 3;
  - leave = max over users of (go → stage-36 quiet) + 1, plus margin;
  - deadline = max over users of (go → token end), GAP bubbles included.

  Every user that started before the last go is then covered. With the single-user roots, the window after the last go
  would end before a filler's last stage.
- **Consequence for the host.** While any user's token is in flight, host exceptional (non-native) admission stays
  closed: `native_reserved` holds it in `qkd_host_rx_class_admission`. Under continuous 4-user decode it opens only
  between bursts. In single-user mode it opens between tokens, as before.

**Mutants (MU 1):**
- MUT 5: one shared window. A go while active faults, as in the original.
- MUT 6: enter re-checks on every go.
- MUT 7: no re-arm.

## 5. Wiring and tile file

- `tools/qwen_kv_die/kv_static.py`, under `OT_KV_MU=1`:
  - `ROLES['ownership']` = the `_mu` file and module;
  - params `MU=1`;
  - `MU_DEPS` += `qkd_static_kv_ownership.sv`.
- `qkd_kvs_tiles_hroot_ff_k_mu.sv` was regenerated with `source kvs_kits_env.sh; OT_KV_MU=1 kv_static_die.py --rtl`.
  Exactly **one** line changed: `u_own` in `qkd_kvs_ctl` now reads `qkd_static_kv_ownership_calendar_mu #(.MUT(0), .MU(1))`.
- MU 0 tile files are byte-identical; none is touched. A regeneration of `_hroot_ff_k` at MU 0 still differs from the
  committed file only in the pre-existing `qkd_attn_cal_gen D_QK` line (57 → 28 in a fresh generation; noted in the kv
  README §2 and not from this lane).
- Lint (`runs/lint_kvs_ctl_mu.log`, files in `lists/lint_kvs_ctl_mu.f`): `qkd_kvs_ctl` passes `--lint-only` on 5.050.
- **Closed tiles:** none changed. `qkd_kvs_ctl` is an RTL-only parent whose kit is not closed. MU-KV-BOOT regenerates
  that kit and takes this change in the same kit.

## 6. Benches (Verilator 5.050, fleet ot-epyc4; `run_kvprog.sh`, `runs/summary.txt`; every file in `lists/tb_kvprog_mu.f`)

`tb_kvprog_mu` is lprg_mu feeding the writer programme (VMAP 1), the attention programme (LAND 1), its cal_gen (STRETCH
1, D_QK 57, D_RL 76, SERVICE_END 1777), and oobs → ownership `_mu`. The wiring is that of kvs_ctl / kvs_attn.

The bench drives the attention service face (RX CMD/Q, RESULT, TX slots) with the identity of the **calendar owner**,
not the DUT's. It checks every writer slot, every expected descriptor and every attention request against that owner,
and requires zero faults.

Counts per started user:
- 36 writer windows, 144 slots, 72 descriptors;
- 36 attention operations: 36 requests, 1,152 Q beats, 1,188 TX beats.

With `OWNCHK`: `native_mode` is 1 at every attention run and `native_reserved` is 1 at every writer slot. Records are
cycle-stamped into hashes per user.

| Case | Result |
|---|---|
| `mu0_u0`: MU 0 (original lprg, ownership MU 0), user 0 | PASS |
| `mu1_u0`: MU 1, user 0 alone, single-user roots | PASS. Writer, attention and ownership hashes equal `mu0_u0` on every edge. |
| `mu1_all`: MU 1, 4 users interleaved stage by stage, MU roots | PASS (end at cycle 336,223) |
| `mu1_a0` … `mu1_a3`: each user alone, MU roots | PASS. Each user's records equal its records in `mu1_all`, cycle for cycle. User 0 also equals MU 0. |
| `m_shared`: MU 0 lprg (one shared context), 4 users | FAIL as required: `layer programme fault code 08` |
| `m_epochbits`: context chosen by epoch[3:2] (bench XMUT 2) | FAIL as required: `layer programme fault code 08` (two users in one context) |
| `m_prevowner`: consumers see the previous event's metadata (bench XMUT 1) | FAIL as required: `attention calendar generator fault` (first stage gets the reset metadata) |
| `m_envelope`: bad calendar, user 1 at +1,000 edges (attention windows overlap) | FAIL as required: `attention programme fault` |
| `m_own5` / `m_own6` / `m_own7`: ownership `_mu` mutants | FAIL as required: `ownership calendar fault code 04` / `08` / `10` |

The fail regexes are in `run_kvprog.sh`. The witness logs are `runs/m_*.log`. `summary.txt` reads `ALL PASS`.

## 7. Open (owners)

1. Boot image MU form (MU-KV-BOOT, with the lprg GAP block): emit the ownership MU roots (§4) from the user calendar.
   `kv_static_programme.py` target 3 is single-user today.
2. `mu_calendar` `kv_service` to the RTL attention window, about 1,789 (§3).
3. Optional hardening, not done here because it needs the kvs_attn kit: check `cal_epoch` == authority epoch at issue.
   Window violations would then fault at the first user's issue rather than at the second user's load.
