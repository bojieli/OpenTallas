# MU-DIE-S81/MUREPLAY (10-19): multi-user mode of the cut replay generator

Gap (MU-DIE-S81/TOK, claude/mu-die-s81-tok-1019 @1e20a0406): `dv_cut_replay.py` had no multi-user mode, so MU traffic on
the die cuts could not be generated. This branch = TOK + the MU mode in `tools/s81_dv/dv_cut_replay.py`.

## What the MU mode does
`gen ... --mu PROG/prog/mu_slots.json|auto --users 0,1,2 [--copy A|B] [--mu-pass P] [--mu-win W.json]`
- Superposes the selected users' traffic. Each user gets the ONE compiled layer programme, shifted by its q4 calendar
  start (`mu_slots.json` rows; the tool refuses starts that are off the 4-edge grid, and refuses a calendar without lemma PASS).
  The bench shift is measured from the die's first selected user. `calendar_shift` is measured from user 0.
- Per-user data: the seq_host context `{user 10, pos 21, tok 21}` is spliced into every V beat whose calendar arg[8:7] is
  1 (body[159:108]) or 2 (pos only). These are the HLOAD beats under `--mu-ctx`, and the derived line copies at every
  stop carry the same splice. The templates are read from `prog/calendar.json`, per job, through its templates map. The
  bit layout is dsdv_seq_host `beat()`: beat bit = 47 + body bit.
- Seq_host cuts (`--host-boot` / `--idle-run`): one boot. Each user gets one `f_ks` start `{1, user, tok, pos}` on its shift.
- Copy A / B: one die runs one copy of a duplicated group, so a user that is not on `--copy` is refused.
- Per-user HBM bases (wb/sb/ikb) are recorded only. On this die the compiled svc job words are the same for every user
  (`svc_jobs.json` SU == MU).
- MU lanes: `mu_c` / `mu_rc` from seq_host to the end slices and `mu_rt` from the end slices are listed in `replay.json mu.lanes`.
  The compiler emits no dsdv_mu_hslot window / replay rows. A per-layer programme also has no stage h hop, because RD here
  is the a_allgather and is offdie. So the MU lanes stay as idle inputs and strict outputs, where a stray tag fails the
  check. `--mu-win` drives explicit hslot rows `{kind tx|replay, inst, edge}` with per-user `{land, ab}`, and that
  replay is DIAGNOSTIC until the compiler owns D.
- Mutants: `mu-drop:<user>` keeps the user's traffic away from the cut. `mu-offgrid:<user>:<n>` starts the user n edges
  off its grid. Checks stay on the nominal calendar.
- Generator identity: `replay.json mu.identity` holds the generator-side shift identity. Every user's words must equal user 0's
  words shifted, bit for bit. The only allowed exception is the ctx-splice bits.
- `mucheck --replay MU --run RUN [--su-replay SU --su-run SURUN]` requires all of the following:
  - the strict trace check passes;
  - the identity passes;
  - the user-0 window `[0, W)` equals the single-user run (outputs on every port, and stimulus `in.txt` byte-equal);
  - every other user's window `[shift, shift+W)` equals user 0's window on every output port.

  W is the smallest start gap.

## Single-user output is byte-identical
`logs/su_byte_identity.txt`: `gen` without `--mu` on cut_7 L0/L2/L14/L20 gives the same `in.txt`, `out.txt` and
`replay.json` sha256 for the old and new tool, 12/12 (also equal to TOK's `R_cut_7_<L>_su/in.txt`).

## cut_7 replays (MU GEN mu1 die.v sha 81498f42, TOK programmes, TOK's cuts/kit)
| replay | users (bench shift) | identity |
|---|---|---|
| R_cut_7_L0_mu012 | L0 S000 copy A: 0@0, 1@21312, 2@42624, W 21312 | PASS (3,516 words each, no ctx row: TOK's prog_L0_mu was compiled WITHOUT --mu-ctx, HLOAD arg 117 ctx 0) |
| R_cut_7_L2_muA02 | L2 S002 copy A: 0@0, 2@42624 | PASS (u2: 7 ctx-only words = HLOAD template 124 at 7S/7N) |
| R_cut_7_L2_muB13 | L2 S002 copy B: 1@0, 3@42628 (calendar 21312 / 63940) | PASS |
| R_cut_7_L0_mu012_drop2 / _off1, R_cut_7_L2_muA02_drop2 | mutants (user 2 dropped / user 1 +1 edge) | must FAIL mucheck |

- User 0's stimulus equals the SU stimulus: `gen --mu --users 0` gives an `in.txt` byte-equal to the SU `in.txt` for both L0 and L2.
- Fleet runs: `chain_mu.sh` (Verilator 5.050, ot-run). It reuses the obj of TOK's cut_7 idle build (same netlist and kit) for
  8 runs: SU L0/L2 to the window end plus the 6 MU runs above. Then it runs check + mucheck. Results land in
  `/home/ubuntu/scratch/mu-die-s81/mureplay/runs/out_<replay>/{check,mucheck}.json` and the log is
  `logs/chain_mu.log` in that scratch dir. See `pending_results` for the verdicts.
- cut_0S / cut_3S / cut_3S_ctl are still blocked by the S-line CTL collision (LINECOL). On LINECOL's branch the same
  `gen --mu` applies, and the seq_host cut gets the per-user `f_ks` starts.
