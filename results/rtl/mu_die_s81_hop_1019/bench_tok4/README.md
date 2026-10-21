# TOK.DS.BENCH.3: SEND-frame fix (S81-TOK4, 10-19)

**TOK3 result** (`../bench_tok3/witness/`, cut_7 L0, ep7 objs reused, Verilator 5.050). All 564 endpoint beats now
arrive: the 78 RD beats that were lost before are present, so Codex's P 6 fix works. MU faults are 0 and all three
mutants are caught. But the base run FAILS. Every beat (564 of 564, at u_s_7N and u_s_7S) lands on the compiled gold
edge minus 2. With the gold moved by -2, the same run passes: scope all 564/564 and hop 480/480, all tagged.

**Cause: the compiler mixes two cycle frames.**
- `leg_program` and `hop_leg` give slice-PIN cycles. That is the bench_vpx frame: pin 8136 -> tg 8140 -> lov1 8156
  -> SEND 8163.
- `ctl_path()['edges']` and the CTL `in` events use compiler EVENT edges, which are the landed pin + RSTOP_HOP (2).
  dv_cut_replay lands event e on the pin at e - 2.
- The send events used `t0 + s - first + lat`, so each send came out RSTOP_HOP late.
- Before Codex's change, the constants (CFG_AT 3, LO_AFTER_CTL 15) were 2 too low. That error cancelled the frame
  error, which is why the old HOP run got 480/480. Codex's correct post-XR2 constants (4 / 16) exposed it.

**Fix.** `lower_vpx`: send `ce -= RSTOP_HOP` in `lower_hop` and in the allgather legs. The CTL schedule and the
calendar are unchanged: `calendar.json` and `ctl_templates.json` are byte-identical. The compile summary is unchanged
too (rows 139, collisions 0, mu_win PASS nw 46, RL 10,589).

What changes:
- The mu_win TX D values move -2, to 8061 / 8091 / 8100 / 8102. These are the values of the original HOP compile.
- `ep_expect` and the gold are the TOK3 ones minus 2.
- `in.txt` changes only in the window command words.

The fix adds no cycles. It removes the 2 edges that TOK3 priced on every send ("first send +2", "HOP +2") in Codex's
07ff2cc83 `edge_price.json`. In the die frame the sends are not later than the old programme's, apart from the P 6
spacing.

**Run.** `fleet_tok4.sh` on ep7 `/srv/opentallas-scratch/claude/s81-tok4` reuses the same objs and changes only the
inputs. `chain_tok4.sh` copies the runs back and runs epcheck. Expected: base all 564/564 and hop 480/480 PASS, and
tagdrop, wrongcopy and rtl_tagdrop all CAUGHT. Results go in `witness/`.
