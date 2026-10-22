# MU-KV-CTX: filler initial context from the KV die host plane over the existing KV->compute d2d stream (Qwen ROM 4 users)

Lane MU-KV-CTX, 2026-10-19 (coordinator decision 0kg). Branch `claude/mu-kv-ctx-1019`, from origin/main f573a6d2b.

- Benches run on the fleet (ot-epyc8) under Verilator 5.050, the closure daemon's version.
- Launcher: `rtl/test/mu_qwen_1018/run_mu_kvctx.sh WORK [pass mut]`.
- Every file the bench reads is listed in `lists/tb_mu_kvctx.f`. Logs and summaries are in `runs/`.
- Static schedule only: no credit, ready or stall. MU 0 files are unchanged.

## 1. The stream and where it is produced

The KV->compute command/token stream that carries the token and position is **d2d port 1, the HOST record port**:
- per token run (segment 1), an S->C **kind 12 CONTEXT** at K cycle `PREC_K0 = 3`;
- at admission (segment 2), kind 13 BEGIN / AUTH.

On the KV die, the word is produced by `qkd_host_record_port` (inside the host cluster child `qkd_hr_core_prompt`, member
`root__u_records`, behind `qkd_host_record_port_rr`). Its `qkd_host_native_context_tx` builds the word from the guard
endpoint's native request (TAG59) and the allocator epoch. The KV d2d services map tx kind 12 to `send_kind 3`.

On the compute die, the closed `qfd_sys_face` record port decodes the word (`qfd_host_native_context_rx`). It then loads
the face token / position, which reach the ctlm on dh[35:0].

Two things rule out the obvious alternatives:
- **No spare bits.** The face checks reserved = 0, kind / layer / beat, DATA[511:142] = 0, TAG stage = 0 and segment = 0.
  BEGIN / AUTH and the embedding header are checked just as strictly.
- **No spare slot.** The compute RX port 3 is not exported by `qfd_d2d_static`. Any new S->C word therefore needs a
  compiled RX slot.

**MU blocker found (KV side).** Under MU the guard endpoint (`_mu`) issues the requests of all 4 users, and the allocator
(`_mu`) pulses one epoch per user step. The original record port holds only the LATEST request and epoch. As a result:
- the user-0 slot would carry a filler's TAG (corrupting the face's latency-user token / position);
- a request whose epoch is not the latest pulse faults the source check.

The new record port below fixes both.

## 2. Field spec (posted in lanes/MU-QW-DIE.md)

**Slot.** A second kind-12 slot in the token run, S->C **kind 12 beat 1 at K cycle 2**, one edge before the existing slot.
In the production image the C RX arrivals are 18 (MU slot) and 19 (existing slot).
- Compiler: `tools/qwen_split/d2d_link_calendar.py --mu`, or `D2D_MU=1 tools/qwen_split/d2d_cal_image_production.sh`.
- Image: `rtl/qwen_sys/d2d_static_20261015/d2d_cal_image_mu.svh`. Only the C RX and K TX images change (+1 entry each).
  Admission, first token (1176) and the period (249,600) are unchanged.
- The MU 0 image regenerates byte-identical to the committed `d2d_cal_image.svh`.

**Word.** The canonical opaque548 kind 12, unchanged:
- `{5'd0, 4'd12, 6'd63, epoch16, 5'd0, {370'd0, digest64, image epoch16, cap, gen2, TAG59}}`;
- TAG59 = `{epoch {seq14, user2}, 6'd0, token18, position13, 6'd0}`;
- **user = TAG[44:43]** (the MU-ADOPT-KV epoch convention).

**Content.**
- MU slot: the INITIAL context of one pending filler u = 1..3 (served in rotation 1 -> 2 -> 3), else a copy of user 0's
  record.
- Existing slot: user 0's current context. The face therefore ends every pair on user 0. Its token register holds the
  filler TAG for one edge only, at token-run cycle ~19, long before any h_start or EMB.
- **Audit owed by MU-QW-DIE:** native59's use of host_tag / host_gen on those edges.

**Initial context.** It is the first request of filler u after reset, or a request whose position is not the user's
previous position + 1 (a new request).
- It is kept in its own register, so the user's later steps do not overwrite it (bench: filler 3 steps before its slot).
- A second admission of u before its record was sent is a sticky fault. Compiler rule: at most one admission per user per
  3 token runs, and a filler's first start comes after its load (MU slot arrival + 2 edges).

## 3. RTL

| file | what |
|---|---|
| `rtl/qwen_sys/mu_qwen_20261018/qkd_host_record_port_mu.sv` | Drop-in for `qkd_host_record_port`, same ports. MU 0 instantiates the original. MU 1 keeps the original BEGIN / AUTH TX and WITNESS RX, and adds `qkd_host_native_context_tx_mu`: per-user epoch / request / initial context, the pair phase (first edge = MU slot; a broken pair or three slots in a row is a fault), and the original's request checks against the user's own epoch. MUT 1/2/3 for the bench. |
| `rtl/qwen_sys/mu_qwen_20261018/host_cluster_mu/qkd_host_record_port_rr_mu.sv` | The generated `_rr` wrapper, binding `_mu #(MU 1)`. Two lines differ. |
| `rtl/qwen_sys/mu_qwen_20261018/host_cluster_mu/qkd_hr_core_prompt.v` | MU 1 core. One line differs (`root__u_records` -> `_rr_mu`), the same as `gen_cluster.py --wrap-only --wrap qkd_host_record_port_rr=qkd_host_record_port_rr_mu`. |
| `rtl/qwen_split/mu/qfd_mu_ctx_rx.sv` | **Compute-side proposal for MU-QW-DIE:** an observer leaf beside the closed face. It reads the existing nets prog_context_slot, prog_rx_v and rx_payload[547:512] / [58:0], and drives `ctx_x[128:0]` = {load, record} in the `mu_opcal.ctx_words` layout the ctlm loader (811e75a88) decodes. User-0 records load nothing. Sticky mu_fault. |
| `tools/qwen_split/d2d_link_calendar.py`, `d2d_cal_image_production.sh` | `--mu` / `D2D_MU=1` (default off). |

**kv_static.py:** no change. The record port sits in the host cluster (`qkd_hr_core_prompt`), not in a kv_static
generated parent.

## 4. Bench (`tb_mu_kvctx.sv`, `mu_kvctx_bench.py`)

The chain under test:
1. The KV `qkd_host_record_port_mu #(MU 1)`, next to a reference `#(MU 0)` (the original port) that sees user-0 traffic
   and the single-user slot only.
2. The link, modelled as its fixed latency: send -> compute RX slot = 16 edges, as in the production image.
3. The face's own `qfd_host_native_context_rx`.
4. `qfd_mu_ctx_rx`.
5. `qfd_tt_ctlm_dv` NU 4 OPSEG 1. Its loader inputs `c_ctx` / `c_ctxld` are forced from the leaf; this stands in for the
   ctlm input MU-QW-DIE owes. The image DW5 / DW6 carry NO record here.

The ctlm half reuses MU-QW-B1's `mu_opseg_bench` case `red` unchanged (F16, 2 layers, 3 frames, 845,548 edges), with its
checks C1..C7:
- C2: user 0 is cycle-identical to the NU 1 reference;
- C5: every filler EMB / SEG uses a bank that starts from the KV-delivered context.

The bench adds these checks:

| check | what it requires |
|---|---|
| K1 | KV identity: on all 4 reference edges, the MU port's word equals the original's |
| K2 | 8 words, all observed |
| K3 | The face's receiver: no fault, and it ends every pair on user 0's current TAG |
| K4 | The leaf loads exactly users 1, 2, 3 with PRE[u], before the first filler EMB / SEG |
| K5 | No sticky fault anywhere |

| run | verdict | fail regex (witness in runs/) |
|---|---|---|
| pass (kmut 0) | **MU_KVCTX_PASS**: loads (1, 0x2111, 8180), (2, 0x2222, 8174), (3, 0x2333, 8168); 4th pair = user-0 copy, no load | -- |
| kmut 1 wrong user field | FAIL | `MU_KVCTX_FAIL kmut 1 .*C5 SEG.*K4 leaf loads` (`kvctx_k1.out`) |
| kmut 2 wrong slot (pair swapped) | FAIL | `MU_KVCTX_FAIL kmut 2 .*K1 KV identity.*K3 face pair end` (`kvctx_k2.out`) |
| kmut 3 producer off | FAIL | `MU_KVCTX_FAIL kmut 3 .*C5 SEG.*K4 leaf loads \[\]` (`kvctx_k3.out`) |
| rmut 1 leaf wrong user | FAIL | `MU_KVCTX_FAIL kmut 0 rmut 1: .*C5 SEG` (`kvctx_r1.out`) |

The same verdicts were also obtained with a link latency of 11.

## 5. Adoption / re-close (open)

- **KV:** the `qkd_hr_core_prompt` MU core (above) needs its kit regenerated and an `rtl_change` re-close of the closed
  prompt cluster view. The KV `qkd_d2d_cal_seq` must include the MU image (incdir swap of `d2d_cal_image.svh`).
- **Compute (MU-QW-DIE):**
  - `qfd_sys_face` (critical, closed) needs the MU image in its `qfd_d2d_cal_seq`: a constants-only change, re-close
    with COORD review;
  - the ctlm needs a `ctx_x` input (param CTX_SRC);
  - the die GEN must bind `qfd_mu_ctx_rx`;
  - native59 needs the host_tag one-edge audit.
- No gate was launched by this lane (pending_results lists the follow-ups).
