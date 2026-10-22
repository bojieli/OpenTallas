# s81dv_idxrg2 -- idxrd2 row-abutting regional index reader (dsdv_idx_rg x16 a die), LEAD2-S81/L20 10-19

Supersedes kit s81dv_idxrg (1058.4 x 1101.6 guess, 6 x 256x256 macros at 10.0 contacts/um, scale/item-queue flop arrays;
its gate3 never wrote a result). RTL 04e86d694 (claude/s81-l20sub-1019).

SAFE-DESIGN CHECKLIST (owner 10-19)
1 Pins: PASS -- source-registered (every input lands in a pin flop, every output leaves one); reset_landing 2 stages (rst).
2 Reach: PASS -- 518.4 x 777.6 outline: no single-cycle wire > 405 um inside a std-cell cone except the clock;
  die side: rq/rd abutted 40 um to dsfd_ctrl_rg2, chains 13 um neighbour hops; long lanes (qf 17 st, score tail 33 st) are
  die relays <= 405 um (plan_idxrd2), not in this tile.
3 Fanout: to verify at the gate (keep_module audit); no new wide broadcast (scale row cache 256 b -> one 32-b lane mux).
4 Depth: PASS by construction -- scale row read is its own registered stage (issue -> read -> load); item-queue head is a
  registered 3-entry show-ahead buffer; no new combinational in->out path.
5 Storage: FIXED -- scale RF (8 kb) and item queue (7.4 kb) moved to SRAM; landing / list already SRAM.  WAIVED: score FIFO
  sq 64 x 38 = 2.4 kb and metadata mq 64 x 21 = 1.3 kb stay flops (at the ~2 kb threshold; written and read every cycle on the
  engine's fixed-latency path).
6 Floorplan: macros 7 x ot_sram_1r1w_1024x256_m2_r2c2 (faces 415 / 70.47 um = 5.89 contacts/um <= 6), halo 5.4, outline =
  the idxrd2 die-plan reader slot (any taller reader puts die lanes over block bodies: dv_plan --idxrd 2 refuses), aspect 1.5,
  std util to be read from the gate synthesis (est. 187k / (403.1k - 86.2k macros) ~ 59%; > 60% -> structural re-plan, not squeeze).
7 Clock: single root ck, CTS centre; owner rule = pin-flop spread <= 80 ps TT+FF (gate); io_hold_margin 0.03.
8 Schedule: static; the reader's emission window is unchanged (T0 + 10 + P w); scale row reads add 0 slot cycles (consumer
  runs >= 8/11 key/cycle vs the P = 3 slot rate 1/3); item visibility +2 cycles inside the HBM lead (no priced edge).
