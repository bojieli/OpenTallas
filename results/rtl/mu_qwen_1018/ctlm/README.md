# MU-ADOPT-CTLM 2026-10-19: the 4-user calendar adopted into the DV control cluster

This is a sub-lane of MU-QWEN-ADOPT (coordinator decision 0jc: fold the multi-user RTL into tiles that are not yet closed,
before they close). It adopts MU-QWEN items R1, R2 (token part) and R5 into `qfd_tt_ctlm_dv` (DV compute die, instance
`u_cal`) and into its landed cluster `qfd_tt_ctlm_dv_lpf` / `_lpf_lp`. The landed cluster is the kit top, owned by HF-4.

## What changed

**`rtl/qwen_dv/qfd_tt_ctlm_dv.sv`** (the reference block; default `NU = 1`):
- `u_cal` is now `qfd_dv_cmd_cal_mu #(NU, UVM_STRIDE, PIDX_STRIDE, UTAG_LSB, UFOLD = NU > 1)`. At `NU = 1` it is
  lockstep-identical to `qfd_dv_cmd_cal` (MU-QWEN-SEQ C1).
- **New input `dh_user[1:0]`.** It is the user of the dh stage start: `qfd_sys_face` `seq_dh_user`, from the R3 USER
  prefix event. It is pin-registered beside `dh` (0 added edges) and ignored at `NU = 1`.
- **Per-user token / position bank** (R2, token row part):
  - a start latches tok/pos into its own user's slot;
  - a LOCAL SEG entry starts the ME segment with its own user's token/position;
  - LOCAL EMB sends its own user's token.
- **The dh start runs the decode ME programme for user 0 only** (base 0, which also starts the XPF schedule). Fillers'
  ME work runs as LOCAL SEG entries in their own calendar segments.
- **The head's SU accepted count (`x_oacc`) and the XPF SU observation count only user 0's SU commands.** The hard
  head (closed h16c / h17) and the XPF therefore see exactly the single-user event stream.
- **No new outputs.** The slices see the user in the cmd word.

**`rtl/qwen_dv/qfd_dv_cmd_cal_mu.sv`** gains `UFOLD` (opt-in, default 0, so the MU-QWEN-SEQ benches are unchanged):
- **STN** (kind 2): `cmd[52:51]` = user.
- **AMAX** (kind 6): `cmd[9:8]` = user.

These are exactly the fields that the R4 per-user LM-head argmax (`rtl/qwen_dv/mu/qfd_dv_amax_mu.sv`) reads. The image
leaves them 0; a non-zero value raises `fault_code[3]`. They are set on the same register edge, so the change adds 0
latency.

**Landed cluster** (the HF-4 kit top):
- `qfd_tt_ctlm_dv_lpf.sv` and `qfd_tt_ctlm_dv_lpf_parts.sv` (`u_gi`) get the same changes, with default `NU = 4`.
- Spec `tools/landed_parent/specs/qfd_tt_ctlm_dv_lpf.json`:
  - child source `qfd_dv_cmd_cal_mu.sv`;
  - `NU 4`;
  - `port_regions dh_user: core`.
- The landed parent was regenerated with `lp.py gen`. HF-4c's hand edit (`u_hr` without `#()` under SYNTHESIS) was
  re-applied, so `qfd_tt_ctlm_dv_lpf_lp.sv` equals claude/hf4-1018 c0b7638d7 plus the NU parameters and the `dh_user`
  port.
- Landed-parent results:
  - landings, pads and reset depth are unchanged: 20 landings, 0 pads, reset depth 3, 3,490 landing flops, audit PASS;
  - `dh_user` lands at 0 edges, like `dh`;
  - output offsets are unchanged (+3 edges on every output).
- The eq bench `tb_qfd_tt_ctlm_dv_lpf_eq.sv` now runs both sides at `NU 4` with a random `dh_user`.

**Compiler** (`tools/qwen_static_schedule/mu_calendar.py`):

| Constant | Value | Why |
|---|---|---|
| `DV_UVM_STRIDE` | 4096 | the slice VM is 16,384 words (`qfd_dv_vm` addr[23:14] = 0), shared by 4 users |
| `DV_PIDX_STRIDE` | 128 | the SU PROG store is 512 entries (9-bit pidx), shared by 4 users |
| `DV_UTAG_LSB` | 6 | |

- `dv_user_fields()` returns the field map and the rules.
- Test `test_dv_user_fields_match_rtl` pins these values to the RTL defaults. 12/12 tests PASS.
- The MU-QWEN-SEQ bench used `UVM_STRIDE 0x4000`. That is outside the real slice VM, which faults on addr[23:14] != 0.

## Rules for the compiler (and limits of this adoption)

- **VM footprint.** User 0's VM footprint of every relocated write and landing region must stay below 4,096 words. The
  single-user DV bench layout uses up to word 0x3008 (12.3k words). The DV lowering therefore has to fit the per-user
  residual, staging and landing regions in 4,096 words per slice per user, or the VM must grow. **This is a compiler /
  area item that is not solved here.**
- **SU programme.** User 0's SU programme must fit pidx below 128. The per-user copies at pidx + 128u are loaded per
  user. QW-CLAYER2's PROG is 72 entries per layer, which fits.
- **Image user fields.** XC tags must be below 64 (user bits 0). STN `cmd[52:51]` and AMAX `cmd[9:8]` must be 0 in the
  image.
- **Calendar timing.** A filler's first entry needs T_0 ≥ 4 + (NU − 1) = 7. No two users may have entries, or segment
  ends, on the same edge.
- **Filler ME work.** Fillers' ME work uses LOCAL SEG entries at a non-zero base. It must not contain SU o-sync waits,
  because the head's SU accepted count belongs to user 0.
  - The hard head is one context. Per-user ME head contexts (R1, core part) would need a re-hardened h16c and are not
    in this adoption.
  - `x_oidle` (`!ag su_busy`) is die-wide.
- **`dc` is die-wide status.** `coll_busy` reflects any user's XC, and `tok_seen` / `ntok` / `nval` reflect the last
  status token. Under the static calendar, the user of each result is a compiled fact, read by the sys_face at its
  compiled edge.

## Benches (fleet, Verilator 5.050): see the lane file `lanes/MU-QWEN-ADOPT.md` section CTLM for verdicts

`rtl/test/mu_qwen_seq/run_mu_ctlm.sh WORK [mu ctlm prog lp eq seq]`:

- **`mu`** (`mu_ctlm_bench.py` + `tb_mu_ctlm_dv.sv`): 4 users through `qfd_tt_ctlm_dv`.
  - **Schedule.** Each user runs token start, 3 decode layers and the LM head, at shifts 0 / 1,722 / 3,443 / 5,165 of
    the 6,886-cycle period, with its own token and position. The segments overlap.
  - **C1.** No faults.
  - **C2.** User 0's commands, ME starts, head-side outputs (hr, native_cmd / tok / pos, command_stage,
    layer_context_v, control_stores_ready, program_obs, cf) and SU count are identical across NU1-solo, NU4-solo and
    NU4 with 4 users.
  - **C3.** Every user's words equal the image relocated for that user: PORTS / STN-VM + 4096u, SU + 128u, XC tag,
    STN `[52:51]`, AMAX `[9:8]`.
  - **C4.** Per-user EMB token, SEG base / token / position, and ME starts on user 0 only.
  - **Mutants.** 16 (UFOLD off), 17 (SU count of all users), 18 (shared tok/pos) and 19 (every user starts ME) must
    FAIL.
- **`ctlm`.** The existing ABI / calendar / SETID benches at NU 1 (identity).
- **`prog`.** The compiled-image bench with `--hard 1 --landed 1`: the NU 1 flat block in lockstep with the NU 4 landed
  cluster (`dh_user` 0). `--mut 1` must FAIL.
- **`lp`.** The regenerated landed-parent lockstep: NU 4 with random `dh_user`, plus mutants and the audit.
- **`eq`.** `lpf` against `qfd_tt_ctlm_dv` at NU 4.
- **`seq`.** The MU-QWEN-SEQ calendar benches. `UFOLD` defaults to 0, so they are unchanged.

## B1 (MU-ADOPT-TOK F-TOK-2): op-granular playback. NOT in this adoption; the spec follows

The calendar of record (14,054 tok/s) interleaves users at op level: users 1 / 2 / 3 wait 29 / 638 / 622 times inside a
layer over 6 tokens. `qfd_dv_cmd_cal_mu` (this adoption included) plays one rigid segment per start, chosen by stage
class. There are 4 descriptors: token / decode / head / boot. That fits 2 users (9,291).

What the successor needs. It is opt-in, `OPSEG = 1`, and `NU = 1` / `OPSEG = 0` stay identical.

1. **Descriptor table.**
   - `NDESC` ≥ 16 segment descriptors `{first 10, cnt 10}`:
     - about 12 decode-layer ops;
     - an L0 variant of the ops the L0 cold fill shifts (F-TOK-5);
     - token start;
     - head-chunk first / middle / last (F-TOK-4: first = AMAX clear + chunk, last = chunk + emit);
     - boot.
   - The DW face has only 8 words (DW5 / 6 must be 0 today). The table therefore comes from reserved PW meta words,
     captured into flops at load (about 16 x 20 = 320 flops), or 3 descriptors per DW1..6 word (18). The compiler and
     the sys_face loader choose.
   - The seal checks every descriptor, as `seal_bad` does today.
2. **Start face.**
   - A start carries `{user 2, segment id 5}`. The segment no longer comes from the stage, and the stage stays the
     running stage for the ROM / KV relocation.
   - `dh` carries no free bits: `dh[43]` is the only spare and the T event arg is full. The candidates are:
     - (a) widen the `dh` face from `qfd_sys_face` with `seq_dh_seg[4:0]` beside `seq_dh_user` (R3 patch, closed
       tile);
     - (b) the calendar self-chains ops. A LOCAL `NEXT` entry (dst 14, kind 3, `{seg id, wait}`) starts the same
       user's next op segment `wait` edges after its last entry. The per-instance waits (they differ by layer and by
       user) then come from a per-user wait table in the image: 36 x 12 x 3 users ≈ 1.3k x 12 b. That does not fit the
       976-PW store, so (b) is only viable if the record's waits repeat per layer.
   - **Option (a) is recommended.** The T calendar then emits one start for each user op: about 12 x 36 per filler
     token. Check this against `qfd_sys_face` NE 64, the T calendar's period programme depth.
3. **Unchanged.** Per-user playheads, relocation, the UFOLD fields, the read-port priority (user 0 is never delayed),
   faults that never stall, and the head running-stage latch on LOCAL SEG.
4. **Bench.** The `mu_tok_cases.py` record variant through `qfd_tt_ctlm_dv` (this bench's harness, extended start
   events). User 0 must be identical to solo, and every user's op events must equal the record's cycles. Mutants:
   wrong segment id, and a start of a playing op faults.

**VM stride conflict.** The MU-ADOPT-TOK T1 spec says "VM region base + u x 0x4000". The RTL and the compiler now use
4,096 words (`DV_UVM_STRIDE`), because 0x4000 is outside the 16,384-word slice VM. T1 must use `mu_calendar.dv_user_fields()`.
