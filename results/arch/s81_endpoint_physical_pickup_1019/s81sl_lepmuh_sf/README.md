s81sl_lepmuh_sf -- MU endpoint (ot_s81sl_lep_mu_h, RX_SRAM=1) gate kit, Claude S81-MUEP 10-19. Source
codex/mu-lep-rxsram-1019 @d37b5dae1 (= txscopev12: lepmuh seed5 exact PASS, HSTAMP/TAGDROP/LANDCUT/KSOFF
mutants detected, SRAM_QUAL_PASS). Successor of prospective s81sl_lepmuh_rx; geometry unchanged
(475.2x561.6, 20 SRAM macros on the 43.2 lattice, min channel 22.41), std band widened to y259.2..291.6
(both A and H). Std area: see spec fill_reason (H measured 8544.5 um2 = 56%; A estimated, re-measured by gate).

SAFE-DESIGN checklist (pre-gate; gate packet re-checks 3/6/7 on actual placement):
 1 Pins: PASS -- pin regs default / source-registered landing flops; reset_landing 2 stages.
 2 Reach: PASS by geometry -- every macro <= ~260 um from the band; re-checked on the gate PNG.
 3 Fanout: WAIVED-with-reason for two INPUT PORTS: ro[0] (160 loads) and t_kd[53] (139) feed
   reset-distinct KEPT per-slice landing copies (rov_r/ring_r/kevent_r): the replication is done,
   the source is the parent's lane pin (no tile register drives >32). Fix owed at die level: the
   parent should drive ro[0]/t_kd[53] as 4-8 replicated lane bits. Comb nets 66/54 loads at depth
   350 ps (guidance). Census: /home/ubuntu/scratch/s81-muep-1019/lep_v12_fanout_host.log.
 4 Depth: PASS -- mapped depth 350.1 ps (H).
 5 Storage: PASS -- RX in true SRAM (RX_SRAM=1, show-ahead w/ forwarding), TX in SRAM; no runtime-indexed flop tables.
 6 Floorplan: PASS -- 43.2 lattice, channels >=20, std 40-60% in one full-width band, aspect 1.18.
 7 Clock: gate-checked -- clk/rst_n W pins at band centre; 18.3k sinks one root (guidance only, owner
   0dq); pin-flop spread <=80 TT+FF required; io_hold 0.03.
 8 Schedule: PASS -- static, no added edges vs the priced lep MU reference (Codex v6-v12 proofs).
