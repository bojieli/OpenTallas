# svgr_top vL7 RRMIR: reserve_ready mirrors (DIE-HBM-88, 2026-11-07)

Third vL6 cone: producer.stream_fault (seam_s_fault flop) -> fault -> producer reserve_ready -> feed reserve_ready ->
issuer reserve_v = st_v && reserve_ready -> push_s -> sq[sq_w] (4 x 117 bits) / sq_w / sq_n / st_v, and back through the
feed reserve_fire into the producer bank enables (allocated / bank_epoch / bank_total / completed_q / ready_q).

RRMIR=1 (ot_svgr_top_cachecut parameter, default 0 = unchanged; yosys equiv of the 0 form vs f69e0b0bbb proven):
* producer: kept copies of stream_fault (same D = next_sf, same srst reset): sf_p[b] gate bank b's reserve enables,
  sf_d the start check and drain; seam_res_v = |bank_go.  Exports srst, descriptor_ok, the producer half of the
  allocation next state (alloc_keep = allocated & ~drain_end_b, clr = drain_end_b) and nsf_p = stream_fault | start fault.
* feed: kept per-landing-bank mirrors av_i[b], av_f[b] == !allocated[b] && !stream_fault, D = the same expression on
  the next state (reserve side local: a fire with a bad descriptor faults, a good fire allocates its bank).  Reset by
  srst to 1.  reserve_ready (to the issuer) = srst && av_i[bank] && !seam_h_fault && !|seam_bfault && legal;
  feed fire / descriptor fault use av_f.  seam_h_fault / seam_bfault stay direct (face flops at the pins).
* Cycle-exact, 0 PIN CYCLES, ports unchanged, +13 kept flops (LBANKS 4).

Bench (tb_rr.sv, run_rr.sh, mk_mut.py; dirs ref/ = f69e0b0bbb cachecut + cache, dut/ = new cachecut, rtl/ = vL6 kit
issuer / calendar / static feed / reset sync): lock-step of the whole cachecut, every output every edge, protocol-steered
random stimulus with bad descriptors, h/b fault pulses, stream / hbm / both resets (also mid-run).  See RESULTS.txt.
