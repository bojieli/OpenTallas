// Generated from52ce3 stream PC SHA256 7489b12bf6962c952c647d863fa4ea0cc1de39a2337cf9069ac67741298120e2
// SECDED shadow bits per PC: 13968; live+shadow mismatch fails closed.
`timescale 1ps/1fs





























module ot_hbm_accel_stream_pc #(
  parameter integer ENABLE   = 0,
  parameter integer REF_MODE = 1,
  parameter integer PC       = 0,
  parameter integer T_RCD = 19, T_RP = 16, T_RAS = 28, T_RTP = 6, T_CCDL = 3,
  parameter integer T_RRDS = 3, T_RRDL = 4, T_FAW = 15, T_RFC = 342, T_RFCPB = 196,
  parameter integer T_REFI = 3808, T_REFIPB = 118, T_RREFD = 8,
  parameter integer CRED = 32,
  parameter integer REF_PHASE = 0,
  parameter integer IDLE0 = 3, IDLE1 = 4, IDLE2 = 2, IDLE3 = 5,
  parameter integer IDLE4 = 1, IDLE5 = 6, IDLE6 = 0, IDLE7 = 7
)(
  input  wire        clk, rst_n,
  input  wire        desc_v, output wire desc_r,
  input  wire [18:0] desc_row, input wire [10:0] desc_n, input wire [10:0] desc_first,
  input  wire        go, input wire next_posted, input wire col_gnt,
  output wire window_end, output wire window_next,
  output wire        row_v, output wire row_prio, input wire row_gnt,
  output wire [2:0]  row_op, output wire [4:0] row_bank, output wire [18:0] row_row,
  output wire        col_v, output wire [4:0] col_bank, output wire [4:0] col_col,
  input  wire [2:0]  cred_ret,
  output wire        busy, output wire ref_fault
);
  localparam [2:0] PRE=0, ACT=1, RD=2, REFAB=4, PREALL=5, REFPB=6;
  generate if (!ENABLE) begin : off
    assign desc_r=0; assign row_v=0; assign row_prio=0; assign row_op=0; assign row_bank=0;
    assign row_row=0; assign col_v=0; assign col_bank=0; assign col_col=0; assign busy=0;
    assign ref_fault=0; assign window_end=0; assign window_next=0;
  end else begin : on
    import ot_gpu_w6_secded_pkg::*;
    function automatic [287:0] seal256(input [255:0] raw);
      for(integer k=0;k<4;k=k+1) seal256[k*72+:72]=encode64(raw[k*64+:64]);
    endfunction
    wire [31:0] bank_protect;
    wire [3:0] bg_protect;
    reg next_valid;
      reg [71:0] next_valid_seal ; reg [18:0] next_row;
      reg [71:0] next_row_seal ; reg [10:0] next_first,next_n;
      reg [71:0] next_first_seal ;
      reg [71:0] next_n_seal ;
    localparam integer PERIOD = REF_MODE ? T_REFIPB : T_REFI;
    localparam integer LEAD   = T_RAS + T_RP + 4;
    localparam integer RW     = $clog2(2 * PERIOD + 4);

    localparam integer RPH    = REF_PHASE + ((REF_PHASE + PERIOD + PC) % 2);
    function automatic [2:0] idle_rank(input [2:0] s);
      idle_rank = (s==3'(IDLE0))?0:(s==3'(IDLE1))?1:(s==3'(IDLE2))?2:(s==3'(IDLE3))?3:
                  (s==3'(IDLE4))?4:(s==3'(IDLE5))?5:(s==3'(IDLE6))?6:7;
    endfunction
    reg [10:0] j, n;
      reg [71:0] j_seal ;
      reg [71:0] n_seal ; reg [18:0] row;
      reg [71:0] row_seal ;
    reg [31:0] open, done, stale, refreshed;
      reg [71:0] open_seal ;
      reg [71:0] done_seal ;
      reg [71:0] stale_seal ;
      reg [71:0] refreshed_seal ;
    reg [1:0] rrds_c;
      reg [71:0] rrds_c_seal ; reg [3:0] noact_c;
      reg [71:0] noact_c_seal ; reg [RW-1:0] ref_c;
      reg [71:0] ref_c_seal ; reg ref_pend;
      reg [71:0] ref_pend_seal ; reg [4:0] rb;
      reg [71:0] rb_seal ; reg fault_r;
      reg [71:0] fault_r_seal ;
    reg [6:0] credit;
      reg [71:0] credit_seal ; reg running;
      reg [71:0] running_seal ; reg [31:0] blk;
      reg [71:0] blk_seal ;
    reg streaming;
      reg [71:0] streaming_seal ; reg [2:0] last;
      reg [71:0] last_seal ; reg [10:0] nm1;
      reg [71:0] nm1_seal ;
    wire [2:0] k = j[9:7];
    wire [4:0] rd_bank = {j[9:7], j[1:0]};
    wire [1:0] rd_bg = j[1:0];

    wire ref_due = (ref_c == 0);
    reg  phase;
      reg [71:0] phase_seal ;
    wire slot_next = (phase != 1'(PC % 2));
    wire [RW-1:0] ref_n = ref_due ? RW'(PERIOD - 1) : ref_c - 1'b1;
    wire ref_due_n = (ref_n == 0);
    wire act_block = REF_MODE ? (ref_n != 0 && ref_n < RW'(T_RREFD))
                              : (ref_n <= RW'(T_RP + T_RAS + 2));
    wire rd_block  = REF_MODE ? 1'b0 : (ref_c <= RW'(T_RP + T_RTP + 2));
    wire preall_ok = !REF_MODE && ref_n <= RW'(T_RP + 2) && ref_n >= RW'(T_RP) && (|open);

    reg r_v, r_prio;
       reg [2:0] r_op;
       reg [4:0] r_bank;

    reg c_v, c_prio;
      reg [71:0] c_v_seal ;
      reg [71:0] c_prio_seal ; reg [2:0] c_op;
      reg [71:0] c_op_seal ; reg [4:0] c_bank;
      reg [71:0] c_bank_seal ; reg [31:0] c_oh;
      reg [71:0] c_oh_seal ;
    wire row_fire = c_v && row_gnt;
    wire [31:0] open_nx = !row_fire ? open : (c_op == ACT) ? (open | c_oh) : (c_op == PRE) ? (open & ~c_oh) :
                          (c_op == PREALL) ? 32'b0 : open;
    wire rd_ok;
    wire [6:0] cr_inc = credit + 7'(cred_ret), cr_dec = credit + 7'(cred_ret) - 7'd1;

    wire [31:0] rcd_z, ras_z, rtp_z, aok_z, aok_busy;
    wire [223:0] keys;
    for (genvar b = 0; b < 32; b = b + 1) begin : bank
      reg [4:0] rcd, ras;
      reg [71:0] rcd_seal ;
      reg [71:0] ras_seal ; reg [8:0] aok;
      reg [71:0] aok_seal ; reg [2:0] rtp;
      reg [71:0] rtp_seal ;
      wire act_e = row_fire && c_op == ACT && c_oh[b];
      wire pre_e = row_fire && ((c_op == PRE && c_oh[b]) || c_op == PREALL);
      wire rfa_e = row_fire && c_op == REFAB;
      wire rfp_e = row_fire && c_op == REFPB && c_oh[b];
      wire rd_e  = rd_ok && rd_bank == 5'(b);
      always @(posedge clk or negedge rst_n)
        if (!rst_n) begin begin rcd <= 0; rcd_seal <= seal256(256'(5'(0))); end  begin ras <= 0; ras_seal <= seal256(256'(5'(0))); end  begin aok <= 0; aok_seal <= seal256(256'(9'(0))); end  begin rtp <= 0; rtp_seal <= seal256(256'(3'(0))); end  end
        else begin
          if (act_e) begin begin rcd <= 5'(T_RCD - 1); rcd_seal <= seal256(256'(5'(5'(T_RCD - 1)))); end  begin ras <= 5'(T_RAS - 1); ras_seal <= seal256(256'(5'(5'(T_RAS - 1)))); end  end
          else begin if (rcd != 0) begin rcd <= rcd - 1'b1; rcd_seal <= seal256(256'(5'(rcd - 1'b1))); end  if (ras != 0) begin ras <= ras - 1'b1; ras_seal <= seal256(256'(5'(ras - 1'b1))); end  end
          if (rd_e) begin rtp <= 3'(T_RTP - 1); rtp_seal <= seal256(256'(3'(3'(T_RTP - 1)))); end  else if (rtp != 0) begin rtp <= rtp - 1'b1; rtp_seal <= seal256(256'(3'(rtp - 1'b1))); end
          if (act_e) begin aok <= 9'(T_RAS + T_RP - 1); aok_seal <= seal256(256'(9'(9'(T_RAS + T_RP - 1)))); end
          else if (rfa_e) begin aok <= 9'(T_RFC - 1); aok_seal <= seal256(256'(9'(9'(T_RFC - 1)))); end
          else if (rfp_e) begin aok <= 9'(T_RFCPB - 1); aok_seal <= seal256(256'(9'(9'(T_RFCPB - 1)))); end
          else if (pre_e && aok < 9'(T_RP)) begin aok <= 9'(T_RP - 1); aok_seal <= seal256(256'(9'(9'(T_RP - 1)))); end
          else if (aok != 0) begin aok <= aok - 1'b1; aok_seal <= seal256(256'(9'(aok - 1'b1))); end
        end
      assign bank_protect[b]=(rcd_seal != 72'(seal256(256'(rcd)))) || (ras_seal != 72'(seal256(256'(ras)))) || (aok_seal != 72'(seal256(256'(aok)))) || (rtp_seal != 72'(seal256(256'(rtp))));
      assign rcd_z[b] = (rcd == 0); assign ras_z[b] = (ras == 0); assign rtp_z[b] = (rtp == 0);
      assign aok_z[b] = (aok == 0); assign aok_busy[b] = (aok > 9'(LEAD));



      localparam [2:0] S = 3'(b >> 2);
      wire [2:0] d = S - k;
      wire ahead = (S >= k && S <= last) || next_posted;
      wire [6:0] base = !streaming ? 7'(idle_rank(S)) + (open[b] ? 7'd32 : 7'd0) :
                        open[b] ? ((done[b] || stale[b]) ? 7'd24 : 7'd32) :
                        (ahead && d <= 3'd2) ? 7'd16 + 7'(3'd2 - d) :
                        ahead ? 7'(d) : 7'd8 + 7'(S);
      assign keys[b*7 +: 7] = refreshed[b] ? 7'd127 : base + ((!open[b] && aok_busy[b]) ? 7'd64 : 7'd0);
    end

    wire [3:0] rrdl_z, ccdl_z, faw_z;
    for (genvar g = 0; g < 4; g = g + 1) begin : bgs
      reg [2:0] rrdl;
      reg [71:0] rrdl_seal ; reg [1:0] ccdl;
      reg [71:0] ccdl_seal ; reg [3:0] faw;
      reg [71:0] faw_seal ;
      wire act_g = row_fire && c_op == ACT && c_bank[1:0] == 2'(g);

      wire faw_take = row_fire && c_op == ACT && faw == 0 && (g == 0 || !(|faw_z[g == 0 ? 0 : g-1:0]));
      always @(posedge clk or negedge rst_n)
        if (!rst_n) begin begin rrdl <= 0; rrdl_seal <= seal256(256'(3'(0))); end  begin ccdl <= 0; ccdl_seal <= seal256(256'(2'(0))); end  begin faw <= 0; faw_seal <= seal256(256'(4'(0))); end  end
        else begin
          if (act_g) begin rrdl <= 3'(T_RRDL - 1); rrdl_seal <= seal256(256'(3'(3'(T_RRDL - 1)))); end  else if (rrdl != 0) begin rrdl <= rrdl - 1'b1; rrdl_seal <= seal256(256'(3'(rrdl - 1'b1))); end
          if (rd_ok && rd_bg == 2'(g)) begin ccdl <= 2'(T_CCDL - 1); ccdl_seal <= seal256(256'(2'(2'(T_CCDL - 1)))); end  else if (ccdl != 0) begin ccdl <= ccdl - 1'b1; ccdl_seal <= seal256(256'(2'(ccdl - 1'b1))); end
          if (faw_take) begin faw <= 4'(T_FAW - 1); faw_seal <= seal256(256'(4'(4'(T_FAW - 1)))); end  else if (faw != 0) begin faw <= faw - 1'b1; faw_seal <= seal256(256'(4'(faw - 1'b1))); end
        end
      assign bg_protect[g]=(rrdl_seal != 72'(seal256(256'(rrdl)))) || (ccdl_seal != 72'(seal256(256'(ccdl)))) || (faw_seal != 72'(seal256(256'(faw))));
      assign rrdl_z[g] = (rrdl == 0); assign ccdl_z[g] = (ccdl == 0); assign faw_z[g] = (faw == 0);
    end
    wire protection_bad=(|bank_protect) || (|bg_protect) || (next_valid_seal != 72'(seal256(256'(next_valid)))) || (next_row_seal != 72'(seal256(256'(next_row)))) || (next_first_seal != 72'(seal256(256'(next_first)))) || (next_n_seal != 72'(seal256(256'(next_n)))) || (j_seal != 72'(seal256(256'(j)))) || (n_seal != 72'(seal256(256'(n)))) || (row_seal != 72'(seal256(256'(row)))) || (open_seal != 72'(seal256(256'(open)))) || (done_seal != 72'(seal256(256'(done)))) || (stale_seal != 72'(seal256(256'(stale)))) || (refreshed_seal != 72'(seal256(256'(refreshed)))) || (rrds_c_seal != 72'(seal256(256'(rrds_c)))) || (noact_c_seal != 72'(seal256(256'(noact_c)))) || (ref_c_seal != 72'(seal256(256'(ref_c)))) || (ref_pend_seal != 72'(seal256(256'(ref_pend)))) || (rb_seal != 72'(seal256(256'(rb)))) || (fault_r_seal != 72'(seal256(256'(fault_r)))) || (credit_seal != 72'(seal256(256'(credit)))) || (running_seal != 72'(seal256(256'(running)))) || (blk_seal != 72'(seal256(256'(blk)))) || (streaming_seal != 72'(seal256(256'(streaming)))) || (last_seal != 72'(seal256(256'(last)))) || (nm1_seal != 72'(seal256(256'(nm1)))) || (phase_seal != 72'(seal256(256'(phase)))) || (c_v_seal != 72'(seal256(256'(c_v)))) || (c_prio_seal != 72'(seal256(256'(c_prio)))) || (c_op_seal != 72'(seal256(256'(c_op)))) || (c_bank_seal != 72'(seal256(256'(c_bank)))) || (c_oh_seal != 72'(seal256(256'(c_oh)))) || (s1k_seal[0] != 72'(seal256(256'(s1k[0])))) || (s1k_seal[1] != 72'(seal256(256'(s1k[1])))) || (s1k_seal[2] != 72'(seal256(256'(s1k[2])))) || (s1k_seal[3] != 72'(seal256(256'(s1k[3])))) || (s1k_seal[4] != 72'(seal256(256'(s1k[4])))) || (s1k_seal[5] != 72'(seal256(256'(s1k[5])))) || (s1k_seal[6] != 72'(seal256(256'(s1k[6])))) || (s1k_seal[7] != 72'(seal256(256'(s1k[7])))) || (s1i_seal[0] != 72'(seal256(256'(s1i[0])))) || (s1i_seal[1] != 72'(seal256(256'(s1i[1])))) || (s1i_seal[2] != 72'(seal256(256'(s1i[2])))) || (s1i_seal[3] != 72'(seal256(256'(s1i[3])))) || (s1i_seal[4] != 72'(seal256(256'(s1i[4])))) || (s1i_seal[5] != 72'(seal256(256'(s1i[5])))) || (s1i_seal[6] != 72'(seal256(256'(s1i[6])))) || (s1i_seal[7] != 72'(seal256(256'(s1i[7])))) || (s2k_seal[0] != 72'(seal256(256'(s2k[0])))) || (s2k_seal[1] != 72'(seal256(256'(s2k[1])))) || (s2i_seal[0] != 72'(seal256(256'(s2i[0])))) || (s2i_seal[1] != 72'(seal256(256'(s2i[1])))) || (bsel_seal != 72'(seal256(256'(bsel)))) || (keys_r_seal != 288'(seal256(256'(keys_r))));
    wire faw_ok = |faw_z;



    function automatic [8:0] min4(input [27:0] k4, input [1:0] dummy);
      reg [6:0] ka, kb;
       reg ia, ib;

      begin
        ka = (k4[13:7] < k4[6:0]) ? k4[13:7] : k4[6:0];   ia = (k4[13:7] < k4[6:0]);
        kb = (k4[27:21] < k4[20:14]) ? k4[27:21] : k4[20:14]; ib = (k4[27:21] < k4[20:14]);
        min4 = (kb < ka) ? {kb, 1'b1, ib} : {ka, 1'b0, ia};
      end
    endfunction
    reg [6:0] s1k [0:7];
      reg [71:0] s1k_seal [0:7]; reg [4:0] s1i [0:7];
      reg [71:0] s1i_seal [0:7]; reg [6:0] s2k [0:1];
      reg [71:0] s2k_seal [0:1]; reg [4:0] s2i [0:1];
      reg [71:0] s2i_seal [0:1]; reg [4:0] bsel;
      reg [71:0] bsel_seal ;
    wire [71:0] m1; wire [17:0] m2; reg [223:0] keys_r;
      reg [287:0] keys_r_seal ;
    for (genvar q = 0; q < 8; q = q + 1) begin : st1
      assign m1[q*9 +: 9] = min4(keys_r[q*28 +: 28], 2'd0);
    end
    for (genvar q = 0; q < 2; q = q + 1) begin : st2
      assign m2[q*9 +: 9] = min4({s1k[4*q+3], s1k[4*q+2], s1k[4*q+1], s1k[4*q]}, 2'd0);
    end
    always @(posedge clk or negedge rst_n)
      if (!rst_n) begin
        for (integer q = 0; q < 8; q = q + 1) begin begin s1k[q] <= 7'd127; s1k_seal[q] <= seal256(256'(7'(7'd127))); end  begin s1i[q] <= 0; s1i_seal[q] <= seal256(256'(5'(0))); end  end
        for (integer q = 0; q < 2; q = q + 1) begin begin s2k[q] <= 7'd127; s2k_seal[q] <= seal256(256'(7'(7'd127))); end  begin s2i[q] <= 0; s2i_seal[q] <= seal256(256'(5'(0))); end  end
        begin bsel <= 0; bsel_seal <= seal256(256'(5'(0))); end  begin keys_r <= {32{7'd127}}; keys_r_seal <= seal256(256'(224'({32{7'd127}}))); end
      end else begin
        begin keys_r <= keys; keys_r_seal <= seal256(256'(224'(keys))); end
        for (integer q = 0; q < 8; q = q + 1) begin
          begin s1k[q] <= m1[q*9 + 2 +: 7]; s1k_seal[q] <= seal256(256'(7'(m1[q*9 + 2 +: 7]))); end  begin s1i[q] <= {3'(q), m1[q*9 +: 2]}; s1i_seal[q] <= seal256(256'(5'({3'(q), m1[q*9 +: 2]}))); end
        end
        for (integer q = 0; q < 2; q = q + 1) begin
          begin s2k[q] <= m2[q*9 + 2 +: 7]; s2k_seal[q] <= seal256(256'(7'(m2[q*9 + 2 +: 7]))); end  begin s2i[q] <= s1i[4*q + m2[q*9 +: 2]]; s2i_seal[q] <= seal256(256'(5'(s1i[4*q + m2[q*9 +: 2]]))); end
        end
        begin bsel <= (s2k[1] < s2k[0]) ? s2i[1] : s2i[0]; bsel_seal <= seal256(256'(5'((s2k[1] < s2k[0]) ? s2i[1] : s2i[0]))); end
      end

    wire rd_offer; assign rd_ok=rd_offer&&col_gnt;
    assign rd_offer = !protection_bad && running && streaming && !rd_block && open[rd_bank] && !stale[rd_bank] &&
                   rcd_z[rd_bank] && ccdl_z[rd_bg] && credit != 0 && !blk[rd_bank];

    function automatic [4:0] act_bank(input integer c, input [2:0] kk);
      act_bank = {(c >= 4) ? kk + 3'd1 : kk, 2'(c & 3)};
    endfunction


    wire [31:0] act_okb = ~open & ~done & ~blk & aok_z & {8{rrdl_z}};
    wire [3:0] grp_k  = act_okb[{k, 2'b00} +: 4];
    wire [3:0] grp_k1 = (k != 3'd7 && k + 3'd1 <= last) ? act_okb[{k + 3'd1, 2'b00} +: 4] : 4'b0;
    wire [7:0] act_cand = {grp_k1, grp_k};
    wire [7:0] act_oh8 = act_cand & (~act_cand + 8'd1);
    wire [31:0] pre_cand = open & (done | stale) & ~blk & ras_z & rtp_z;
    wire [31:0] pre_oh, act_oh;
    for (genvar b = 0; b < 32; b = b + 1) begin : oh
      if (b == 0) begin : z assign pre_oh[b] = pre_cand[b]; end
      else begin : nz assign pre_oh[b] = pre_cand[b] & ~(|pre_cand[b-1:0]); end
      assign act_oh[b] = (3'(b >> 2) == k) ? act_oh8[b & 3] :
                         (3'(b >> 2) == k + 3'd1 && k != 3'd7) ? act_oh8[4 + (b & 3)] : 1'b0;
    end
    function automatic [4:0] ffs32(input [31:0] v);
      reg [15:0] v16;
       reg [7:0] v8;
       reg [3:0] v4;
       reg [1:0] v2;

      begin
        ffs32[4] = ~|v[15:0];  v16 = ffs32[4] ? v[31:16] : v[15:0];
        ffs32[3] = ~|v16[7:0]; v8 = ffs32[3] ? v16[15:8] : v16[7:0];
        ffs32[2] = ~|v8[3:0];  v4 = ffs32[2] ? v8[7:4] : v8[3:0];
        ffs32[1] = ~|v4[1:0];  v2 = ffs32[1] ? v4[3:2] : v4[1:0];
        ffs32[0] = ~v2[0];
      end
    endfunction
    wire act_ok_any = streaming && !act_block && noact_c == 0 && rrds_c == 0 && faw_ok && (|act_cand);
    wire [2:0] act_sel = 3'(ffs32({24'b0, act_cand}));
    wire [4:0] pre_sel = ffs32(pre_cand);
    wire forced_pre = REF_MODE && ref_pend && |(blk & open & ras_z & rtp_z);
    reg [31:0] r_oh;

    always @* begin
      r_v = 0; r_prio = 0; r_op = PRE; r_bank = 0; r_oh = 0;
      if (REF_MODE && ref_due_n && ref_pend) begin r_v = 1; r_prio = 1; r_op = REFPB; r_bank = rb; r_oh = blk; end
      else if (!REF_MODE && ref_due_n) begin r_v = 1; r_prio = 1; r_op = REFAB; end
      else if (preall_ok) begin r_v = 1; r_prio = 1; r_op = PREALL; end
      else if (forced_pre) begin r_v = 1; r_prio = 1; r_op = PRE; r_bank = rb; r_oh = blk; end
      else if (act_ok_any) begin r_v = 1; r_op = ACT; r_bank = act_bank(act_sel, k); r_oh = act_oh; end
      else if (|pre_cand) begin r_v = 1; r_op = PRE; r_bank = pre_sel; r_oh = pre_oh; end
    end
    assign row_v = c_v && !protection_bad; assign row_prio = c_prio; assign row_op = c_op; assign row_bank = c_bank;
    assign row_row = row;
    assign col_v = rd_offer; assign col_bank = rd_bank; assign col_col = j[6:2];
    assign desc_r = !next_valid && !fault_r && !protection_bad;
    assign busy = streaming || next_valid; assign ref_fault = fault_r || protection_bad;
    assign window_end=rd_ok && j==nm1; assign window_next=next_valid||(streaming&&desc_v&&desc_r);
    always @(posedge clk or negedge rst_n) begin
      if (!rst_n) begin
        begin next_valid <= 0; next_valid_seal <= seal256(256'(1'(0))); end  begin next_row <= 0; next_row_seal <= seal256(256'(19'(0))); end  begin next_first <= 0; next_first_seal <= seal256(256'(11'(0))); end  begin next_n <= 0; next_n_seal <= seal256(256'(11'(0))); end
        begin streaming <= 0; streaming_seal <= seal256(256'(1'(0))); end  begin last <= 0; last_seal <= seal256(256'(3'(0))); end  begin nm1 <= 0; nm1_seal <= seal256(256'(11'(0))); end
        begin j <= 0; j_seal <= seal256(256'(11'(0))); end  begin n <= 0; n_seal <= seal256(256'(11'(0))); end  begin row <= 0; row_seal <= seal256(256'(19'(0))); end  begin open <= 0; open_seal <= seal256(256'(32'(0))); end  begin done <= 0; done_seal <= seal256(256'(32'(0))); end  begin stale <= 0; stale_seal <= seal256(256'(32'(0))); end  begin refreshed <= 0; refreshed_seal <= seal256(256'(32'(0))); end
        begin rrds_c <= 0; rrds_c_seal <= seal256(256'(2'(0))); end  begin noact_c <= 0; noact_c_seal <= seal256(256'(4'(0))); end  begin ref_pend <= 0; ref_pend_seal <= seal256(256'(1'(0))); end  begin blk <= 0; blk_seal <= seal256(256'(32'(0))); end  begin rb <= 0; rb_seal <= seal256(256'(5'(0))); end  begin fault_r <= 0; fault_r_seal <= seal256(256'(1'(0))); end  begin credit <= 7'(CRED); credit_seal <= seal256(256'(7'(7'(CRED)))); end
        begin ref_c <= RW'(RPH + PERIOD); ref_c_seal <= seal256(256'(RW'(RW'(RPH + PERIOD)))); end  begin running <= 0; running_seal <= seal256(256'(1'(0))); end  begin phase <= 0; phase_seal <= seal256(256'(1'(0))); end
        begin c_v <= 0; c_v_seal <= seal256(256'(1'(0))); end  begin c_prio <= 0; c_prio_seal <= seal256(256'(1'(0))); end  begin c_op <= PRE; c_op_seal <= seal256(256'(3'(PRE))); end  begin c_bank <= 0; c_bank_seal <= seal256(256'(5'(0))); end  begin c_oh <= 0; c_oh_seal <= seal256(256'(32'(0))); end
      end else begin
        if (rrds_c != 0) begin rrds_c <= rrds_c - 1'b1; rrds_c_seal <= seal256(256'(2'(rrds_c - 1'b1))); end
        if (noact_c != 0) begin noact_c <= noact_c - 1'b1; noact_c_seal <= seal256(256'(4'(noact_c - 1'b1))); end
        begin credit <= rd_ok ? cr_dec : cr_inc; credit_seal <= seal256(256'(7'(rd_ok ? cr_dec : cr_inc))); end

        begin ref_c <= ref_n; ref_c_seal <= seal256(256'(RW'(ref_n))); end  begin phase <= ~phase; phase_seal <= seal256(256'(1'(~phase))); end

        begin c_v <= slot_next && r_v; c_v_seal <= seal256(256'(1'(slot_next && r_v))); end  begin c_prio <= r_prio; c_prio_seal <= seal256(256'(1'(r_prio))); end  begin c_op <= r_op; c_op_seal <= seal256(256'(3'(r_op))); end  begin c_bank <= r_bank; c_bank_seal <= seal256(256'(5'(r_bank))); end  begin c_oh <= r_oh; c_oh_seal <= seal256(256'(32'(r_oh))); end
        if (REF_MODE && ref_c == RW'(LEAD)) begin begin ref_pend <= 1; ref_pend_seal <= seal256(256'(1'(1))); end  begin rb <= bsel; rb_seal <= seal256(256'(5'(bsel))); end  begin blk <= 32'b1 << bsel; blk_seal <= seal256(256'(32'(32'b1 << bsel))); end  end

        if (ref_due && (!row_fire || !(c_op == REFPB || c_op == REFAB) ||
                        (REF_MODE && (|(blk & open) || |(blk & ~aok_z))) || (!REF_MODE && |open))) begin fault_r <= 1; fault_r_seal <= seal256(256'(1'(1))); end
        if (streaming && go) begin running <= 1; running_seal <= seal256(256'(1'(1))); end

        if (rd_ok) begin
          begin j <= j + 1'b1; j_seal <= seal256(256'(11'(j + 1'b1))); end
          if (j == nm1) begin
            if(next_valid) begin
              begin j <= next_first; j_seal <= seal256(256'(11'(next_first))); end  begin n <= next_n; n_seal <= seal256(256'(11'(next_n))); end  begin row <= next_row; row_seal <= seal256(256'(19'(next_row))); end  begin done <= 0; done_seal <= seal256(256'(32'(0))); end
              begin nm1 <= next_first+next_n-1'b1; nm1_seal <= seal256(256'(11'(next_first+next_n-1'b1))); end  begin last <= 3'((next_first+next_n-1'b1)>>7); last_seal <= seal256(256'(3'(3'((next_first+next_n-1'b1)>>7)))); end
              begin stale <= (row==next_row) ? stale : open_nx; stale_seal <= seal256(256'(32'((row==next_row) ? stale : open_nx))); end
              begin next_valid <= 0; next_valid_seal <= seal256(256'(1'(0))); end
            end else if(desc_v&&desc_r)begin
              begin j <= desc_first; j_seal <= seal256(256'(11'(desc_first))); end begin n <= desc_n; n_seal <= seal256(256'(11'(desc_n))); end begin row <= desc_row; row_seal <= seal256(256'(19'(desc_row))); end begin done <= 0; done_seal <= seal256(256'(32'(0))); end
              begin nm1 <= desc_first+desc_n-1'b1; nm1_seal <= seal256(256'(11'(desc_first+desc_n-1'b1))); end begin last <= 3'((desc_first+desc_n-1'b1)>>7); last_seal <= seal256(256'(3'(3'((desc_first+desc_n-1'b1)>>7)))); end
              begin stale <= (row==desc_row)?stale:open_nx; stale_seal <= seal256(256'(32'((row==desc_row)?stale:open_nx))); end
            end else begin begin streaming <= 0; streaming_seal <= seal256(256'(1'(0))); end  begin running <= 0; running_seal <= seal256(256'(1'(0))); end  end
          end
          if (j[6:2] == 5'd31 && !window_next) begin done[rd_bank] <= 1'b1; done_seal <= seal256(256'(32'(((done & ~(32'(1)<<(rd_bank))) | (32'(1'(1'b1))<<(rd_bank)))))); end
        end

        if (row_fire) case (c_op)
          ACT: begin begin open <= open | c_oh; open_seal <= seal256(256'(32'(open | c_oh))); end  begin rrds_c <= 2'(T_RRDS - 1); rrds_c_seal <= seal256(256'(2'(2'(T_RRDS - 1)))); end  end
          PRE: begin begin open <= open & ~c_oh; open_seal <= seal256(256'(32'(open & ~c_oh))); end  begin stale <= stale & ~c_oh; stale_seal <= seal256(256'(32'(stale & ~c_oh))); end  end
          PREALL: begin begin open <= 0; open_seal <= seal256(256'(32'(0))); end  begin stale <= 0; stale_seal <= seal256(256'(32'(0))); end  end
          REFPB: begin
            begin noact_c <= 4'(T_RREFD - 1); noact_c_seal <= seal256(256'(4'(4'(T_RREFD - 1)))); end  begin ref_pend <= 0; ref_pend_seal <= seal256(256'(1'(0))); end  begin blk <= 0; blk_seal <= seal256(256'(32'(0))); end
            begin refreshed <= (&(refreshed | (32'b1 << rb))) ? 32'b0 : (refreshed | (32'b1 << rb)); refreshed_seal <= seal256(256'(32'((&(refreshed | (32'b1 << rb))) ? 32'b0 : (refreshed | (32'b1 << rb))))); end
          end
          default: ;
        endcase

        if(desc_v && desc_r && streaming && !window_end) begin
          begin next_valid <= 1; next_valid_seal <= seal256(256'(1'(1))); end  begin next_row <= desc_row; next_row_seal <= seal256(256'(19'(desc_row))); end  begin next_first <= desc_first; next_first_seal <= seal256(256'(11'(desc_first))); end  begin next_n <= desc_n; next_n_seal <= seal256(256'(11'(desc_n))); end
        end
        if (desc_v && desc_r && !streaming && !fault_r) begin
          begin j <= desc_first; j_seal <= seal256(256'(11'(desc_first))); end  begin n <= desc_n; n_seal <= seal256(256'(11'(desc_n))); end  begin row <= desc_row; row_seal <= seal256(256'(19'(desc_row))); end  begin done <= 0; done_seal <= seal256(256'(32'(0))); end  begin running <= 0; running_seal <= seal256(256'(1'(0))); end
          begin streaming <= (desc_n != 0); streaming_seal <= seal256(256'(1'((desc_n != 0)))); end  begin nm1 <= desc_first+desc_n-11'd1; nm1_seal <= seal256(256'(11'(desc_first+desc_n-11'd1))); end  begin last <= 3'((desc_first+desc_n-11'd1)>>7); last_seal <= seal256(256'(3'(3'((desc_first+desc_n-11'd1)>>7)))); end
          begin stale <= (row==desc_row) ? stale : open_nx; stale_seal <= seal256(256'(32'((row==desc_row) ? stale : open_nx))); end
        end
      end
    end
  end endgenerate
endmodule
