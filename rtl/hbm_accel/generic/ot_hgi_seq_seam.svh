// ot_hgi_seq_seam.svh -- FROZEN seam contract of the R25GQ sequencer split (el1013-hbm-seq-split, 2026-10-13).
// Parent ot_hgi_seq_split (wires only; same ports / params as ot_hgi_seq) = ot_hgi_seq_fe + ot_hgi_seq_au + ot_hgi_seq_be.
// Include inside each child module body (localparams only). Do not change a name, width or timing rule here without
// the coordinator: three agents build against it.
//
// RULES (every seam signal)
//  R1 TX: the sender drives the port straight from a dedicated flop (no logic after it). RX: the receiver registers the
//     port once (suffix _r) before any use. A sender decision in cycle t is in the TX flop in t+1 and in the RX flop in t+2.
//     Exception X1: S1 and S4 land directly in the AU A0 flops (a0_* IS the RX flop; one 2:1 select by s4_v allowed).
//  R2 No ready crosses a seam: pulses / valid-only, flow control by credit (S5 q_pop) or hold (S5 inj_hold).
//  R3 Every valid / pulse / level TX and RX flop resets to 0 on the child's OWN reset synchroniser (2 flops from rst_n,
//     async assert, sync release, as rs_* in the flat file); data flops carry no reset.
//  R4 clk and rst_n go to all three children; no other shared net. Pin inputs keep their ot_hgi_seq_hdly + pin flop in the
//     child that owns the pin.
//
// PIN OWNERSHIP (top-level ports)
//  FE: md_d, md_k, f_req_v/rdy/addr, f_rsp_v/data.
//  AU: rank (its own rank_r copy), cfg: none.
//  BE: cfg_vocab, cfg_ctx_max, hold, busy, db_*, vr_*, u_v, u_rdy, d_*, u_done, u_fault, wr_quiet, cpl_*.
//
// STATE OWNERSHIP (flat names)
//  FE: ring + macros, wp/wv/inflight/drop/fetching/faddr*/rqf/room_q (moved out of the rn_m block), reader, fqv FIFO,
//      parser (fs, h, hq_*, pi, rcl, rskip, ctag, settle), loops, lim, run_f, FE's own qt (alloc tag) and the credit
//      counter q_cred; kern_off / img_l / img_ha / img_hb / img_q (image address, from md_d_r / md_k_r).
//  AU: pos / pos1 / token copies, tbc, DYN builder, trow, hrow_q, A0..A5 + av, a6_* flags.
//  BE: record queue g_q, head mux + qh copies, q_cnt/qh/qt, resolver + injector, main FSM st, run_q, doorbell,
//      completion, cc, outst, d_*, token/pos/pos1_q, tk_*.  e_ps1 is computed locally: pos1_q + hdr[H_SLOT +: 3]
//      (== the flat h_row p1 field; no table read crosses a seam).
//
// ---------------------------------------------------------------- S5a  BE -> FE and AU: job load (pulse)
//  be_jl_v            1   BE decision: S_IDLE with db_pend (the cycle the flat loads token/pos and clears tbc)
//  be_jl_entry        2   dbq_entry          (FE)
//  be_jl_kernel       4   dbq_kernel         (FE)
//  be_jl_loff        32   dbq_loff           (FE)
//  be_jl_pos         20   dbq_pos            (AU; FE uses only pos == 0 for the predicate: it registers be_jl_pos == 0)
//  be_jl_token       18   dbq_token          (AU)
//  FE on jl RX: kern_off, then img_l/img_ha/img_hb, then img_q (3 edges); fe_kz (level, TX) = (kern_off == 0).
//  AU on jl RX: pos/pos1/token copies load, tbc <= 0 (au_tbl_ok drops the next cycle).
//  BE: stays in S_DB for JL_WAIT cycles after the be_jl_v decision cycle, then db_bad uses fe_kz_r; S_DB2, S_DB3 as flat.
// ---------------------------------------------------------------- S5b  BE -> FE, AU: job control
//  be_js              1   pulse, decision = flat job_start (S_DB3 && !db_bad).  FE: everything the flat does on job_start
//                         (FE reset of fs/rp/.., fetch start faddr <= img_q.., drop <= fl_after, run_f <= 1, qt <= 0,
//                         q_cred <= QD).  AU: av <= 0.  job_start reaches FE/AU 2 cycles after the BE decision.
//  be_stop            1   pulse (FE only), decision = every flat site that clears run_f (fault3, unit-fault abort, S_ENDRD
//                         done).  FE: run_f <= 0, fetching <= 0.  BE drops alloc / item / result RX while !run_q.
//  be_qpop            1   pulse (FE only), decision = flat q_pop.  FE: q_cred + 1.
//  be_lv_v            1   pulse (FE only) + be_lv_cnt 16 = flat lv_rsp / lv_rcnt.
//  be_inj_hold        1   level (FE only).  BE raises the TX flop when the injector takes an entry (J_IDLE -> J_INJ), issues
//                         its first be_inj no earlier than INJ_WAIT full cycles after the first cycle the TX flop is 1,
//                         and clears it in the cycle after the last be_inj.  FE: fe_pop2 gets
//                         && !(rcl == RC_DSP && be_inj_hold_r) in place of the flat be_inj term.
// ---------------------------------------------------------------- AU -> FE
//  au_tbl_ok          1   level = tbc[6] (TX flop).  FE uses au_tbl_ok_r in fe_hcap.
// ---------------------------------------------------------------- S1  FE -> AU item (valid-only; TX loaded on fe_item)
//  fe_s1_v 1, fe_s1_base 40, fe_s1_lstr 32, fe_s1_l1str 32, fe_s1_str 32, fe_s1_dmul 27, fe_s1_dsel 6, fe_s1_nsel 6,
//  fe_s1_n 20, fe_s1_idx 1, fe_s1_sp 2, fe_s1_L 16, fe_s1_L1 16, fe_s1_slot 3, fe_s1_j 3, fe_s1_tag QB, fe_s1_last 1,
//  fe_s1_isI 1, fe_s1_hi 1, fe_s1_et 1     = the FE branch of the flat a0_* load, same expressions.
//  fe_hslot           3   level: hw[H_SLOT +: 3] loaded at fe_hcap (a copy of h's slot). AU: hslot_r, then
//                         hrow_q <= trow_of(trow, hslot_r)  (valid with the record's first item at A0).
// ---------------------------------------------------------------- S4  BE -> AU re-injection (valid-only; TX on be_inj)
//  be_s4_v 1, be_s4_ph 24, be_s4_base 40, be_s4_dmul 27, be_s4_sp 2, be_s4_x 32, be_s4_j 3, be_s4_tag QB
//  AU A0 load: s4_v ? the flat be branch : fe_s1_v ? the FE branch; av[0] <= s4_v | s1_v.  s4_v & s1_v in one cycle is a
//  protocol violation: AU raises the sticky sim-only flag seam_err (`ifndef SYNTHESIS $error) and takes S4.
// ---------------------------------------------------------------- S3  AU -> BE result (valid-only; TX after A5)
//  au_s3_v 1 (= av[5]), au_s3_be 1, au_s3_tag QB, au_s3_j 3, au_s3_last 1, au_s3_isI 1, au_s3_acc 64, au_s3_n 21,
//  au_s3_px 1, au_s3_pn 1, au_s3_flt 1 (a6_flt), au_s3_badd 1 (a6_bad_d), au_s3_iax 18 (a6_iax[17:0]), au_s3_ixb 1,
//  au_s3_ian 18, au_s3_inb 1, au_s3_ihbm 1 (a6_ihbm).   BE RX then applies the flat fw / bw writes and nres count.
// ---------------------------------------------------------------- S2  FE -> BE
//  alloc (one channel; TX loaded on fe_halloc from hw / q_akind / rdy0 / Lc / L1c / qt, or on fe_aalloc from h, K_FENCE /
//  K_LVM, rdy0 = 1):  fe_s2a_v 1, fe_s2a_tag QB, fe_s2a_hdr 128, fe_s2a_kind 3, fe_s2a_rdy0 1, fe_s2a_L 16, fe_s2a_L1 16
//  item (= the flat it_d staging; TX loaded on fe_item | fe_sut):  fe_s2i_v 1, fe_s2i_d 256, fe_s2i_tag QB,
//  fe_s2i_slot 3 (fe_sl), fe_s2i_sut 1, fe_s2i_np0 1 (hq_np == 0)
//  BE RX decodes per-entry enables from the RX flops (al, it_we, su_we) one cycle later; BE keeps its own qt check:
//  fe_s2a_tag must equal BE qt (sim-only seam_err otherwise).
//  fe_kz              1   level, see S5a.
// ---------------------------------------------------------------- latency vs flat (derived; MEASURE in the lockstep bench)
//  alloc +1 (header) / +2 (FENCE, LOOP-from-VM); raw item +1; AU result +3 (S1 +1, S3 +2); re-injection +4 + INJ_WAIT;
//  job start +JL_WAIT; q_cnt < QD seen by FE 2 cycles late (credit).
localparam integer SEAM_INJ_WAIT = 2;   // min safe: last FE item reaches A0 2 cycles after hold TX rises; S4 takes 2
localparam integer SEAM_JL_WAIT  = 6;   // jl TX 1 + RX 1 + kern_off 1 + kz TX 1 + kz RX 1 + 1 margin
// mutants (each must FAIL the lockstep bench):
//  OT_HGI_SEQ_MUT_SEAM_CRED  FE: q_cred initialised to QD + 1            (dropped-credit class: queue overrun)
//  OT_HGI_SEQ_MUT_SEAM_QPOP  FE: every 2nd be_qpop_r ignored              (dropped credit: decode stalls)
//  OT_HGI_SEQ_MUT_SEAM_HOLD  BE: first be_inj SEAM_INJ_WAIT - 1 early     (off-by-one hold: S1 / S4 collide)
//  OT_HGI_SEQ_MUT_SEAM_RST   AU: av / tbc on the raw rst_n instead of its synchroniser AND no av flush on be_js
//                            (stale reset copy: a result of the previous job lands in the new queue)
//  the flat mutants OT_HGI_SEQ_MUT_WAIT / _LOOP / _IDXL / _TOKX stay, in the child that holds the logic.
