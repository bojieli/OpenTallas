// xp unit bench: ot_hgi_xp_sched + ot_hgi_xp_rd against an 8-lane VM slice model (in-order lanes, LAT + jitter) and an
// SM model that runs every record AT ITS PRICE (serial weight stream).  Checks: every wave bit-exact vs the VM image,
// wave order / count, slot content at issue (golden x identity), no load over a slot in use, in-order retire after done.
// Throughput: retire-to-retire interval per record class vs the price sheet => cycles the x plane ADDS over price.
module tb_hgi_xp;
  parameter integer NREC = 27; parameter integer LAT = 11; parameter integer PACK = 4;
  parameter integer MUT_DROP = 0; parameter integer MUT_RET = 0; parameter integer MUT_XRS = 0;
  logic clk = 0, rst = 1; always #1 clk = ~clk;
  logic [63:0] rm [NREC]; string dir; integer jit = 0, errors = 0, cyc = 0;
  logic rec_v, rec_rdy, cmd_v, cmd_rdy, done_v, iss_v, cdone_v, ret_v, f_s, f_r, wave_v, wave_last;
  logic [6:0] iss_xb; logic [2:0] iss_seq, ret_seq; logic [14:0] cmd_sec; logic [10:0] cmd_nsec; logic [3:0] cmd_id, done_id, wave_id, wave_n;
  logic [7:0] rq_v, rs_v, wave_idx; logic [7:0][14:0] rq_sec; logic [7:0][255:0] rs_d; logic [2047:0] wave_d;
  integer fi = 0;
  wire [63:0] r = rm[fi < NREC ? fi : 0];
  assign rec_v = !rst && fi < NREC;
  ot_hgi_xp_sched #(.MUT_RET(MUT_RET), .MUT_XRS(MUT_XRS)) u_s (.clk, .rst, .rec_v, .rec_rdy, .rec_xr(r[61]), .rec_xb(r[60:54]), .rec_nxe(r[53:46]),
    .rec_sec(r[45:31]), .rec_nsec(r[30:20]), .cmd_v, .cmd_rdy, .cmd_sec, .cmd_nsec, .cmd_id, .done_v, .done_id,
    .iss_v, .iss_xb, .iss_seq, .cdone_v, .ret_v, .ret_seq, .fault(f_s));
  ot_hgi_xp_rd #(.MUT_DROP(MUT_DROP)) u_r (.clk, .rst, .cmd_v, .cmd_rdy, .cmd_sec, .cmd_nsec, .cmd_id, .rq_v, .rq_sec, .rs_v, .rs_d,
    .wave_v, .wave_d, .wave_n, .wave_last, .wave_id, .wave_idx, .fault(f_r), .rq_cr(8'd0), .wave_rdy(1'b1), .wave_pop());
  function automatic logic [31:0] xw(input logic [14:0] s, input integer j); return ({14'd0, s, 3'(j)} * 32'h9E3779B1) ^ 32'hA5A51013; endfunction
  // VM lanes
  logic [14:0] lq [8][$]; integer lt [8][$];
  // loads by slot id
  integer l_sec [16], l_nsec [16], l_xb [16], l_nxe [16], l_cnt [16];
  integer tag [128]; logic [15:0] dp_v; logic [3:0] dp_id [16];
  // records
  integer iq = 0, cq_ = 0, rq_ = 0, rt_prev = 0, t0 = -1; longint sm_free = 0; longint c_end [$]; integer busy_xb [$], busy_n [$];
  longint cls_meas [16], cls_price [16]; integer cls_n [16]; longint tot_price = 0;
  always @(posedge clk) begin
    cyc <= cyc + 1; rs_v <= '0; cdone_v <= 1'b0; done_v <= 1'b0;
    if (!rst) begin
      if (rec_v && rec_rdy) begin if (t0 < 0) t0 = cyc; fi <= fi + 1; end
      for (int l = 0; l < 8; l++) begin
        if (rq_v[l]) begin lq[l].push_back(rq_sec[l]); lt[l].push_back(cyc + LAT - 2 + (jit > 0 ? $urandom_range(0, jit) : 0));
          if (rq_sec[l][2:0] != 3'(l)) begin errors++; $display("ERR lane %0d sector %0d", l, rq_sec[l]); end end
        if (lq[l].size() != 0 && lt[l][0] <= cyc) begin
          rs_v[l] <= 1'b1; for (int j = 0; j < 8; j++) rs_d[l][32*j +: 32] <= xw(lq[l][0], j);
          void'(lq[l].pop_front()); void'(lt[l].pop_front());
        end
      end
      if (cmd_v && cmd_rdy) begin
        l_sec[cmd_id] = cmd_sec; l_nsec[cmd_id] = cmd_nsec; l_cnt[cmd_id] = 0;
        for (int w = 0; w < u_s.W; w++) if (u_s.w_v[w] && u_s.w_disp[w] && u_s.win[w].sl == cmd_id) ;
        l_xb[cmd_id] = u_s.s_xb[cmd_id]; l_nxe[cmd_id] = u_s.s_nxe[cmd_id];
        for (int a = l_xb[cmd_id]; a < l_xb[cmd_id] + l_nxe[cmd_id]; a++) tag[a] = -1;
        foreach (busy_xb[b]) if (busy_xb[b] < l_xb[cmd_id] + l_nxe[cmd_id] && l_xb[cmd_id] < busy_xb[b] + busy_n[b]) begin
          errors++; $display("ERR cyc %0d load over a slot in use (xb %0d)", cyc, l_xb[cmd_id]); end
      end
      if (wave_v) begin
        automatic integer id = wave_id, ex_n;
        ex_n = (l_nsec[id] - 8 * l_cnt[id] > 8) ? 8 : l_nsec[id] - 8 * l_cnt[id];
        if (wave_idx != 8'(l_cnt[id]) || wave_n != 4'(ex_n) || wave_last != (l_nsec[id] - 8 * l_cnt[id] <= 8)) begin
          errors++; $display("ERR cyc %0d wave id %0d idx %0d exp %0d n %0d", cyc, id, wave_idx, l_cnt[id], wave_n); end
        for (int i = 0; i < ex_n; i++) for (int j = 0; j < 8; j++)
          if (wave_d[256*i + 32*j +: 32] !== xw(15'(l_sec[id] + 8 * wave_idx + i), j)) begin errors++; if (errors < 8) $display("ERR cyc %0d wave data id %0d", cyc, id); end
        l_cnt[id]++;
        if (wave_last) begin dp_v[0] <= 1'b1; dp_id[0] <= wave_id; end
      end
      if (!(wave_v && wave_last)) dp_v[0] <= 1'b0;
      for (int k = 1; k < PACK; k++) begin dp_v[k] <= dp_v[k-1]; dp_id[k] <= dp_id[k-1]; end
      if (dp_v[PACK-1]) begin
        automatic integer id = dp_id[PACK-1];
        done_v <= 1'b1; done_id <= dp_id[PACK-1];
        for (int a = l_xb[id]; a < l_xb[id] + l_nxe[id]; a++) tag[a] = (l_cnt[id] * 8 >= l_nsec[id]) ? l_sec[id] : -2;
      end
      if (iss_v) begin
        automatic logic [63:0] q = rm[iq]; automatic longint st;
        if (iss_xb != q[60:54]) begin errors++; $display("ERR cyc %0d rec %0d issued with xb %0d exp %0d", cyc, iq, iss_xb, q[60:54]); end
        for (int a = q[60:54]; a < q[60:54] + q[53:46]; a++) if (tag[a] != q[45:31]) begin errors++; if (errors < 8) $display("ERR cyc %0d rec %0d x slot addr %0d holds %0d exp %0d", cyc, iq, a, tag[a], q[45:31]); end
        st = (longint'(cyc) * 8 > sm_free) ? longint'(cyc) * 8 : sm_free; sm_free = st + q[19:4];
        c_end.push_back(sm_free); busy_xb.push_back(q[60:54]); busy_n.push_back(q[53:46]); iq++;
      end
      if (c_end.size() != 0 && c_end[0] <= longint'(cyc) * 8) begin
        cdone_v <= 1'b1; void'(c_end.pop_front()); void'(busy_xb.pop_front()); void'(busy_n.pop_front()); cq_++; end
      if (ret_v) begin
        automatic logic [63:0] q = rm[rq_];
        if (cq_ <= rq_) begin errors++; $display("ERR cyc %0d rec %0d retired before complete", cyc, rq_); end
        if (ret_seq != 3'(rq_)) begin errors++; $display("ERR retire order"); end
        cls_meas[q[3:0]] += (cyc - (rq_ == 0 ? t0 : rt_prev)); cls_price[q[3:0]] += q[19:4]; cls_n[q[3:0]]++; tot_price += q[19:4];
        rt_prev = cyc; rq_++;
        if (rq_ == NREC) begin
          for (int c = 0; c < 16; c++) if (cls_n[c] != 0) $display("CLASS %0d n %0d measured %0d price %0.1f ratio %0.3f", c, cls_n[c], cls_meas[c], cls_price[c] / 8.0, cls_meas[c] * 8.0 / cls_price[c]);
          $display("%s service %0d price %0.1f ratio %0.3f errors=%0d faults=%0d%0d", (errors == 0 && !f_s && !f_r) ? "PASS" : "FAIL", cyc - t0, tot_price / 8.0, (cyc - t0) * 8.0 / tot_price, errors, f_s, f_r);
          $finish;
        end
      end
      if (cyc > 200000 || errors > 50) begin $display("FAIL watchdog/errs cyc %0d retired %0d errors=%0d faults=%0d%0d", cyc, rq_, errors, f_s, f_r); $finish; end
    end
  end
  initial begin
    void'($value$plusargs("VEC=%s", dir)); void'($value$plusargs("JIT=%d", jit)); $readmemh(dir, rm);
    for (int a = 0; a < 128; a++) tag[a] = -3; dp_v = '0;
    repeat (4) @(posedge clk); rst <= 0;
  end
endmodule
