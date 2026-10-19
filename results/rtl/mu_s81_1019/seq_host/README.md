# MU.TOK.DS4: S81 host plane on the real seq_host parent (MU-S81-2/SEQ, 2026-10-19)

The earlier gate, MU_HOST_GATE (results/rtl/mu_s81_1018/host), drove `dsdv_mu_hslot` against a fixed-latency stand-in
unit. This bench drives the MU die master `dsdv_seq_host_mux` from MU-S81-2/DIE (claude/mu-s81-2-die-1019 ac336f805,
`bind_table_p4l3_mu`) instead. That master is `dsdv_seq_host_mu` NSLOT 47, wrapping the real `dsdv_seq_host` (L0 link,
L1 `ot_dsdv_fixed_issue`, L2 V packer, L3/L4 hops) and `dsdv_mu_hslot`, plus `dsdv_mu_hwin` (8 window events, 4 end
slices). The bench boots it with the compiled L0 programme (`results/rtl/s81_mu_1018/prog_L0_mu`, HLOAD context row)
through its host lane. It then sends the boot config as host CSR 0x15 (f_mc: slot gaps, RL) and CSR 0x16 (f_mw: window
events and per-slot attributes {land, ab} = {s % 3 != 2, s % 2}), as the die does. Users start on `f_ks` at the record
calendar shifts (`results/arch/mu_s81_1018/calendar_{ar,mtp}.json`, phase-q 4). Verilator 5.050 ran on ot-epyc6
through ot-run. Bench: `rtl/dsrom_sys/s81_dv/unit/test/run_seq_host_mu_bench.sh` (`tb_dsdv_seq_host_mu.sv`,
`check_seq_host_mu.py`, `seq_host_mu_cases.py`). Stdout is in `gate_stdout.log`, and the gate printed
**SEQHOST_MU_GATE PASS**.

| run | result |
|---|---|
| ar: 46 AR users x 2 periods (92 starts, gaps 21,312 / 21,316) | **PASS**: user 0 identical to its single run. The single run equals the plain `dsdv_seq_host` with the same KD edge and payload; only t_kd[31:0] = {user, pos, 0} differs (zero added latency). 92/92 KIT dones carry their own start's {user, pos} on the KIT done edge. TX windows and replays are exact with each calendar slot's attributes in both periods. 1,444 events, 0 missing, 0 extra, no fault |
| mtp: MTP 10 users + filler x 2 periods (22 starts, gaps 124,524 x 10 + 58,160) | **PASS** (same checks, 350 events) |
| f_uniform: the former single-period config (S 21,312) on the record calendar | t_mf[1] at user 3 (edge 66177), as required |
| f_offcal: one start 4 edges off its slot | t_mf[1], as required |
| f_dup: the same user in two slots while it is outstanding | t_mf[1], as required |
| f_collide: slot 0 reused while its start is outstanding | t_mf[0], as required |
| f_rl: RL one edge long | t_mf[2] (return mismatch), as required |
| MU_MUT 1 (user field dropped) / 2 (collision check dropped) / 5 (gap index stuck) | all FAIL as required. Regexes are in `mutants.json`; witnesses are `mut*_fail_witness.log` |
| regressions: MU_HOST_GATE (stand-in leaf bench), MU_HWIN_GATE (hwin bench + LEP_MU_DIE lint), lint -Wall of hslot, hwin and the master | PASS / PASS / clean |

In the fault runs the hslot raises the expected bit first. t_mf[2] follows about 65 edges later, when the unit returns
the start that was not recorded. The checker requires the expected bit on the first fault edge.

## RTL fix (integration gap found by this bench)
1. `dsdv_mu_hslot` and `dsdv_mu_hwin` each had a slot timer with a single uniform period S. The record calendar is not
   uniform. For AR, shift_k = 4 floor(k (P/4) / 46), so the gaps are 21,312 or 21,316. For MTP, the 10 slots of
   124,524 are followed by a 58,160 filler slot. On the real unit, user 3 landed 4 edges off the grid and the hslot
   raised t_mf[1] (run `f_uniform`).
2. The slot entries wrapped at NSLOT 47, but an AR period has 46 slots. `dsdv_mu_hwin` looks up its per-slot
   attributes by entry (`eat[event][entry]`), so from the second period on every user would have taken the
   neighbouring slot's {land, ab}: the wrong A/B copy and the wrong replay enable.

The fix, applied identically in both leaves, is a slot gap table. Each sel-0 `f_mc` word appends one gap g[k], and
the timer walks g[0..n-1] cyclically, with a registered prefetch of the next gap. The entries and all pointers wrap at
nw = n, so the entry index is the calendar slot in every period. The checks use nw in place of NSLOT: every gap >= nw,
RL > nw, window D in [nw + 2, RL - 2], and more than NSLOT gaps is a fault. One sel-0 word (n = 1) is the former
uniform period with nw = NSLOT, so the old behaviour is unchanged. Both leaf regressions pass unchanged. The pins
(f_mc 26 b, f_mw), the CSRs 0x15 / 0x16 and the die wiring are unchanged. Area grows by 47 x 24 b of gap table plus
about 40 control flops per leaf. No stub, no tie-off. A new bench mutant, MUT 5, freezes the gap index.

**Re-close needed.** `dsdv_mu_hslot.sv` is no longer byte-identical to the CLOSED view
`physical/ref_tile/dsdv_mu_hslot` (28a8118d5). MU-S81-2/DIE had kept it identical on purpose, but the closed RTL cannot
run the record calendar. Owner (MU-S81 kits): re-close dsdv_mu_hslot NSLOT 47 on this RTL. `dsdv_mu_hwin` has no kit
yet, so its kit is built from this RTL. A cheaper alternative exists, if the lead prefers it: a uniform AR calendar with
S = 21,316 and P + 108 (-0.011 % tok/s) keeps the closed hslot. It cannot hold the MTP filler slot, and hwin still
needs the nw wrap fix.

## Scope note: what "46 outstanding" means on the real unit
On the real seq_host, start -> KIT done is 64 edges (L0 programme: KIT age 57 + 7). The slot is at least 21,312 edges,
and `ot_dsdv_fixed_issue` holds at most 2 job contexts. At most one start is therefore outstanding in the hslot at any
time (`max_outstanding = 1`). The 46 AR users are all in flight across the die chain, not at once inside one seq_host.
The 47-outstanding case (RL close to one round) exists only on the stand-in bench (MU_HOST_GATE). The real issuer
cannot reach it, because a third live job faults with code 5 (MU-S81/TOK m_ctx3).
