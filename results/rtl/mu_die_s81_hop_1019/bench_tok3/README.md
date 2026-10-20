# TOK.DS.BENCH.3 rerun with the post-XR2 lower_vpx fix (LEAD2-S81/TOK3, 10-19)

**Cause (TOK2, bench_vpx on current RTL).** The 78 missing non-hop RD beats came from the compiler. Each send config
landed one edge early, on the previous beat's 4th lo pair. Codex 73879e4d2 (cherry-picked here) sets CFG_AT 4,
LO_AFTER_CTL 16, RX_WR_AFTER_PIN 6 and P 6. With these, bench_vpx base gives 14 sends, 56 writes and 28 readbacks per
side, all PASS.

**What this directory holds.**
- `compiler/prog_L0_mu_A`: L0 MU copy A, recompiled with the fix. Same tree_mu, calendar_ar_q4 and layerbench
  fixtures as MU-DIE-S81/HOP. The summary is unchanged: rows 139, line collisions 0, mu_win nw 46, RL 10,589, PASS.
- `replays/`: `R_cut_7_L0_hop012` (base), `_tagdrop` (mu-win-drop:0) and `_wrongcopy` (mu-win-ab:1), regenerated from
  that programme. The flags are the HOP ones: `--mu --users 0,1,2 --copy A --mu-win auto --mu-win-kinds tx`.
- `gold/`: epx gold from the compiled schedule. All scope = 564 beats, of which 480 are hop beats.

**Control.** Run on the OLD programme, the same tool reproduces the committed HOP `ep_expect.txt`, the HOP `in.txt` and
the TOK-B3 `_all.epx` byte-identically. So every difference in the new replay comes from the compiler fix.

**Schedule change.**
- User 0 RD bursts: u_s_7N 1303..1381 (was 1301..1366) and u_s_7S 1312..1390 (was 1311..1376). That is 14 beats at
  P 6, so each burst ends 15 or 14 edges later. Users 1 and 2 follow at +21,312 and +42,624.
- Hop beats move +2 (the first is now 8226, was 8224).
- Lane words are unchanged at 1,986. In-events rise from 693 to 741.

**Run.** `fleet_tok3.sh` is ONE ot-run job on ot-epyc7, with 4 runs in parallel. It reuses the existing probed cut_7
objs in `/srv/opentallas-scratch/claude/mu-die-s81-hop/out_{base,rtl_tagdrop}/obj` (Verilator 5.050) and changes only
the runtime inputs; nothing is rebuilt. The s81-tokb3 epcheck-TB builds have no `sim`: their C++ compile was killed at
18:2x (exit 143). The Python epcheck on the probe `ep.txt` is the consumer check.

`chain_tok3.sh` waits for the client, copies the run dirs back and runs epcheck. The verdicts it expects:

| run | check | expect |
|---|---|---|
| out_base | epcheck --scope all | PASS 564/564: all 84 non-hop RD beats, MU faults 0 |
| out_base | epcheck --scope hop | PASS 480/480 |
| out_base_tagdrop | --scope hop --expect-fail | caught (untagged u_s_7N hop beats) |
| out_base_wrongcopy | --scope hop --expect-fail | caught (te fault) |
| out_rtl_tagdrop | --scope hop --expect-fail | caught (0/480 tagged) |

Results go to `witness/` once the runs land (see pending_results, LEAD2-S81/TOK3).

**Added cycles** (compiler only, no RTL change): each 14-beat send leg gets +15 edges (P 5 -> 6), and the HOP gets +2.
These are already priced in Codex 07ff2cc83 `edge_price.json`.
