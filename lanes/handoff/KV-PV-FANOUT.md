# KV-PV-FANOUT handoff (Opus 5.5, started 11-24 12:3x PST). ONE job: class (c) structural fix for KV pv (bin -> scattered readers).
## Result
- Cause: class (c) readers are landing-pad stages (u_pd<T> trunks, kit_dly_ram leads u_pd<L>_ram_pdram, plain pads), 1998/2037;
  519/520 bad pad cases already have T >= ceil(um/405) stages. DLY-SPREAD (tools/die_plan/dly_spread.tcl) left them clumped:
  route end (load centroid / SRAM pin) inside a hard macro -> every route hits it -> NOROUTE -> GPL sites kept.
- Fix pushed main 39d2f6c76a2: ROUTE-END-OUT (ds_out: in-macro end -> nearest halo-box point; OT_DLY_SPREAD_END_OUT=0 = old).
  test_dly_spread.py 14/14. No plan row; A5t6 needs rt >= 39d2f6c76a2.
- Replays (epyc11 /srv/opentallas-scratch2/claude/kv-pv-fanout/dbg, rep.sh TYPE orig|fix, read-only kit mounts of A5t3 probes):
  bin->pad >672 um: v6 96->0, pv 25->0, v8e 62->0, v4e 59->59. pve/v2e odb unreadable.
## Residuals (not done)
- v4e: 59 chains, ends outside macros, ds_route finds no street-line path (pocket). Needs a maze fallback in ds_route.
- seg-8 trunks (budgets.r_dly_lockup.kv3_pv.seg=8): after spread v8e sg-hops >672 um 3->67 (max 793, via lockup latch). Lower seg = plan row.
- 39 core-reader cases (u_pv_u_T*Q* regs, 17 >833 ps) and 1 short pad: need BIN-COPY / +1 cycle; not touched.
- Lane clone: epyc10 /srv/opentallas-scratch2/claude/kv-pv-fanout/wt
## Round 2 (COORD follow-up, 11-24 evening) -- DONE
- MAZE fallback in ds_route pushed main 247bec6f231 (test 15/15); v4e replay >672 um 59 -> 0.
- ROW-REBASED c8dbec67218c on A5t5 669cbe6e39bd (epyc10 /srv/opentallas-scratch2/claude/kv-pv-fanout):
  row 2 SEGST = budgets.r_dly_lockup.kv3_pv.pad_min_stations 8; row 3 RELSITE = relay_sites minimax for pv relay-leaf regs
  (relay_rows.json e95d1393fe77, from epyc11 dbg/relsite.py on the A5t3 probes; probe-measured >672 um 8,000+ -> 47, kv3_pv max 691).
  Gate gateF/: PRE 25 RSTREACH = A5t5 set (0 new), G0 PASS, scoped strict bind 23 types 0 errors. 0 cycles.
- The short pad (kv3_pv pd2_ram_pdram_4_108) was cleared by the tool fix (2 stages = 3 hops of about 272 um).
- Residual: kv3_pv 47 relay regs 672-691 um after re-site (fixed endpoints too far apart; needs a relay_depth +1 cycle if they fail).
