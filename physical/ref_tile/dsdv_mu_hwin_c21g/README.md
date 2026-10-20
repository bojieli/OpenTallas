dsdv_mu_hwin_c21g -- HWIN21g gate kit (Claude S81-HWIN21g 10-19) = c21d geometry + RTL config relay (CFG_RELAY=1). Parallel to c21d/c21e/c21f.
Why: the c21d gate (CTS, ot-epyc9 dsdv_mu_hwin_c21d-20261019-182825) fixed SRAM Q -> capture D, but the worst setup became INPUT PORT f_mw/f_mc (E face)
-> the 16 per-event config landing flops g_event_broadcast[*].cfg_{w1,addr,w0,rl,attr}_r spread along the 561.6 um band (-251 -> -206 ps after repair, 950 endpoints).
Fix (RTL, opt-in parameter, default 0 = HWIN21cb logic): f_mw/f_mc land in a relay register stage before ANY consumer. Two kept, reset-distinct copies form a
balanced 2-way landed tree: copy 0 -> west events 0-7 + the central pin flops mw_q/mc_q + west boot-data groups + RL limit payload; copy 1 -> east events 8-15 +
east boot groups. Port -> relay is one load per copy (east copy near the E face, west copy at the band centre, <= ~300 um); relay -> event copies is a full
cycle over <= ~280 um, fanout <= 25 per relay bit. Cost: +1 edge on the config path ONLY (f_mw / f_mc words land one edge later); f_ks start, mu_rt RX and all
outputs unchanged (INBOX lanes/LEAD2-S81.md: the MU calendar issues HWIN/HSLOT boot words one edge earlier, or keeps >= 1 idle edge before the first start).
Exact: DUT(CFG_RELAY=1)(x) == HWIN21cb 072dd6141 (z^-1 x) on all outputs/faults/internal control every cycle: run_c21g_bench.sh mitres the rtl/ DUT against the
sha256-pinned frozen 072dd6141 source (renamed dsdv_mu_hwin_cbref_1019, CBREF_MITER) and the 1e057 anchor (EARLY_MITER), both on z^-1 config (Verilator 5.050).
Mutants: norelay (CFG_RELAY=0 on raw ports), eastcopy (relay copy 1 forced 0), mut2 (EC_MUT=2) -> CBREF_MITER/EARLY_MITER (witnesses results/rtl/s81_mu_hwin21g_1019/).
wd_in hold (-28.5 ps in c21d chunk-1 hold repair): hold-aware buffer budget = the flow's chunked OT_HOLD_GUARD (c21b gate: chunk 1 -36.8 -> chunk 2 +30.0 ps,
margin met, same macro/wdata structure); the write-data launch flops are already per-SRAM-instance (mem_early_capture wdata), so they sit at each macro's band edge
(<= 145 um to wd_in). Lattice fill exception: COORD 19:05 RATIFIED for the HWIN c21d family (HANDOFF), c21g = c21d geometry.

SAFE-DESIGN checklist (pre-gate; the gate packet re-checks 2/3/6/7 on the actual placement):
 1 Pins: PASS -- source-registered pins; config ports now land in the relay (2 kept copies) before the mw_q/mc_q pin flops; reset_landing 2 stages (unchanged).
 2 Reach: fixed -- SRAM pin -> band <= 145.2 um; config broadcast split port -> relay (<= ~300 um, 1 load) + relay -> copies (<= ~280 um); gate reach census confirms.
 3 Fanout: PASS -- relay bit <= 25 loads (copy 0, f_mw[25]); copies kept and reset-distinct (4 new reset regions, 26 sinks each) so Yosys cannot merge them.
 4 Depth: PASS -- unchanged c21b cones; cfg decode (valid && 2-bit type) now starts at a relay flop with a full cycle.
 5 Storage: PASS -- 86,016 bits in 84 SRAM macros; relay +104 flops.
 6 Floorplan: PASS (c21d) -- 43.2 lattice, 10.8 halo, one full-width band ~44%, aspect 1.44, outline 218350 um2; lattice fill exception ratified (COORD 19:05).
 7 Clock: gate-checked -- ck/rst_n W pins inside the band; pin-flop spread <= 80 TT+FF; io_hold 0.03.
 8 Schedule: PASS -- static; +1 edge on f_mw/f_mc config words only (priced: boot-time words, 0 token-latency edges), INBOX lanes/LEAD2-S81.md.

(c21d text follows)
dsdv_mu_hwin_c21d -- HWIN21d MAIN gate kit (Claude S81-HWIN21d 10-19). Re-pack of dsdv_mu_hwin_c21b, RTL BYTE-IDENTICAL
(rtl/dsrom_sys/s81_dv/unit/dsdv_mu_hwin_capture*_1019.sv at 072dd6141). Second structural response to the HWIN macro<->band wires:
the c21b gate (dsdv_mu_hwin_c21b-20261019-175703, post-CTS) shows setup -162.5 ps at g_event_mem[*].g_early.u_payload.g_select[*].capture D
(SRAM Q -> forward/load mux -> capture, macros up to ~370 um from the band) and FF hold -43 ps / 515 at SRAM wd_in (band wdata -> ~370 um -> macro).
Coordinator options (restart brief 10-19): macro-local capture/launch registers, or a re-pack to <=150 um reach. Chosen: RE-PACK, because
 - the c21b geometry has no std-cell rows beside the macros (row pitch 43.2 - macro 20.79 - 2 x 10.8 halo = 0.8 um; column 3.2 um), so macro-local
   registers need new channels anyway (a wider outline plus off-band power islands, against checklist 6), and they add a read and a write edge
   (+2 edges to price, new miters); the re-pack keeps cycles_added 0 and the c21b benches/witnesses stand unchanged;
 - macro area within 150 um of one band of length L is ~2 x 145 x L, so 84 lattice slots need L ~ 560-650 um: 12 columns x 7 rows (3 below / 4 above the band), outline 561.6 x 388.8.
Geometry: macros on the 43.2 lattice, all R0 (MX/R180 put 63 signal pins off the asap7 tracks on the lattice; R0 pins sit on the bottom 3.8 um), 10.8 halo,
channels 24.84 (x) / 22.41 (y); one full-width std band y169.02..204.12 (130 rows), std 8600 um2 = 44.0%;
max SRAM pin -> band 145.2 um (c21b ~370). Each event's 5 SRAMs (attr + 4 payload) are 5 consecutive column slots (<=2 adjacent columns);
retire/gap SRAMs in the centre columns. ck/rst_n W pins inside the band. No clock_span warning (561.6 < 600).
Benches: unchanged DUT -> the c21b kit bench (physical/ref_tile/dsdv_mu_hwin_c21b/run_c21b_bench.sh, Verilator 5.050) ns47 / ns2 PASS and mutants EC_MUT=2 /
NEXT_WRAP_MUTANT FAIL EARLY_MITER (witnesses results/rtl/s81_mu_hwin21cb_1019/), lint; the job re-runs them.
Schedule/pricing: +0 public edges (RTL unchanged; cycle-exact miter vs anchor 1e057). INBOX lanes/LEAD2-S81.md.

SAFE-DESIGN checklist (pre-gate; the gate packet re-checks 2/3/6/7 on the actual placement):
 1 Pins: PASS -- source-registered pins (ks_q/mc_q/mw_q/rt_q in, c_q/rc_q/t_wf out), keep_pin_regs, reset_landing 2 stages (unchanged).
 2 Reach: fixed -- SRAM pin -> band <= 145.2 um (was ~370); band length 561.6 um, pins on the W/E band ends; gate reach census confirms.
 3 Fanout: PASS -- unchanged c21b RTL (ra_r <=4 banks + 1 compare; load/hit select per <=8 bits, kept); textbook census on the gate.
 4 Depth: PASS -- unchanged c21b cones (r_addr_in / hit flop-only; advance compare ends in a 2:1 mux); capture D cone now SRAM clk->Q + <=150 um.
 5 Storage: PASS -- 86,016 bits in 84 SRAM macros.
 6 Floorplan: fixed -- 43.2 lattice, 10.8 halo, one full-width band at 44%, aspect 1.44, outline 218350 um2 (c21b 235146).
 7 Clock: gate-checked -- ck/rst_n W pins inside the band; pin-flop spread <= 80 TT+FF; io_hold 0.03.
 8 Schedule: PASS -- static, cycles_added 0.
