// KV-ING-5 vF cut 19 netlist splice: st_wa_r next state in carry-select form (exact, 0 cycles, no new state).
// Inputs are the QN outputs of the existing flops (Q = ~QN).
module wa_mut (
  input  wire [31:0] kq_n,     // ap_kcode QN (bit 0 = ap_kscal[0] QN, merged flop)
  input  wire [31:0] sq_n,     // ap_kscal QN
  input  wire [31:0] rq_n,     // ap_raddr QN
  input  wire [4:0]  secq_n,   // st_sec QN
  input  wire [2:0]  phq_n,    // st_ph QN
  input  wire [3:0]  mdq_n,    // st_mode[2:0] QN, st_mode[3] = st_d[3] QN (merged flop)
  input  wire        actq_n,   // st_act QN
  input  wire        padq_n,   // st_pad QN
  input  wire [31:0] waq_n,    // st_wa_r QN
  output wire [31:0] d         // st_wa_r D
);
  wire [31:0] kq = ~kq_n, sq = ~sq_n, rq = ~rq_n, wq = ~waq_n;
  wire [4:0]  sec = ~secq_n;
  wire [2:0]  ph = ~phq_n;
  wire [3:0]  md = ~mdq_n;
  wire is_raw = md == 4'd0, is_rows = md == 4'd2;
  wire en = ~actq_n & padq_n & ~is_raw;          // st_run && !is_raw
  wire ik_sc = ph >= 3'd3;
  wire [3:0]  kc_lo  = {1'b0, kq[2:0]} + {1'b0, ph};
  wire [28:0] kc_hi1 = kq[31:3] + 29'd1;
  wire [31:0] kc_sum = {kc_lo[2] ? kc_hi1 : kq[31:3], kc_lo[2:0]};
  wire [3:0]  ks_lo  = {1'b0, sq[2:0]} + {3'd0, ph == 3'd4};
  wire [28:0] ks_hi1 = sq[31:3] + 29'd1;
  wire [31:0] ks_sum = {ks_lo[3] ? ks_hi1 : sq[31:3], ks_lo[2:0]};
  wire [5:0]  rs_lo  = {1'b0, rq[4:0]} + {1'b0, sec};
  wire [26:0] rs_hi1 = rq[31:5] + 27'd1;
  wire [31:0] rs_sum = {rs_lo[5] ? rs_hi1 : rq[31:5], rs_lo[4:0]};
  wire [31:0] nv = is_rows ? rs_sum : ik_sc ? ks_sum : kc_sum;
  assign d = en ? nv : wq;
endmodule
