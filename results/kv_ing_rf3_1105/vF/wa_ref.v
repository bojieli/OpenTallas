// reference: the r3 st_wa_r next state as written in qkd_host_native_engine_ing3 (before cut 19)
module wa_ref (input wire [31:0] kq_n, sq_n, rq_n, input wire [4:0] secq_n, input wire [2:0] phq_n, input wire [3:0] mdq_n,
  input wire actq_n, padq_n, input wire [31:0] waq_n, output wire [31:0] d);
  wire [31:0] ap_kcode = ~kq_n, ap_kscal = ~sq_n, ap_raddr = ~rq_n, st_wa_r = ~waq_n;
  wire [4:0] st_sec = ~secq_n; wire [2:0] st_ph = ~phq_n; wire [3:0] st_mode = ~mdq_n;
  wire st_act = ~actq_n, st_pad = ~padq_n;
  wire is_raw = st_mode == 4'd0, is_rows = st_mode == 4'd2;
  wire st_run = st_act && !st_pad;
  wire ik_sc = st_ph >= 3'd3;
  assign d = (st_run && !is_raw) ? (is_rows ? (ap_raddr + {27'd0, st_sec}) : ik_sc ? (ap_kscal + (st_ph == 3'd4 ? 32'd1 : 32'd0)) : (ap_kcode + {29'd0, st_ph})) : st_wa_r;
endmodule
