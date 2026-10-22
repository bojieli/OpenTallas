`timescale 1ns/1ps
// PL-SEQ option B bench wrapper: dsdv_seq_host_c (hardened core) + the die lane stand-in (two registered 276-b rung
// stages = the dvrlyh relays the die places toward s_4N) == dsdv_seq_host, port for port.  MUT 3 = one lane stage
// missing (latency 5), as dsdv_seq_host's MUT 3.  The S81U-SEQ golden bench runs on this wrapper
// (run_seq_host_c_bench.sh), so every seq_host mutant (1..6) is exercised on the core.
module dsdv_seq_host_bw #(parameter integer V = 276, parameter integer STAGE = 0, parameter integer MUT = 0, parameter integer RL = 1) (
    input  wire          ck,
    input  wire          rst_n,
    input  wire [7:0]    tap_k, sink_k,
    input  wire [V-1:0]  vi_s, output wire [V-1:0] vo_s,
    input  wire [V-1:0]  vi_n, output wire [V-1:0] vo_n,
    input  wire [514:0]  f_host, output wire [76:0] t_host, input wire [3:0] f_lf,
    input  wire [52:0]   f_ks,   output wire [53:0] t_kd,
    output wire [32:0]   s_j,    input  wire [1:0]  s_jd_w, s_jd_e,
    output wire [291:0]  s_hw_w, s_hw_e, input wire [8:0] s_hc_w, s_hc_e,
    input  wire [1:0]    st_rg_w, st_rg_e,
    output wire          cw_v, output wire [9:0] cw_a, output wire [255:0] cw_d
);
    wire [V-1:0] cn, cs, n1, s1;
    dsdv_seq_host_c #(.V(V), .STAGE(STAGE), .MUT(MUT), .RL(RL)) u_c (.ck(ck), .rst_n(rst_n), .tap_k(tap_k), .sink_k(sink_k),
        .vi_s(vi_s), .vo_s(vo_s), .vi_n(cs), .vo_n(cn), .f_host(f_host), .t_host(t_host), .f_lf(f_lf), .f_ks(f_ks), .t_kd(t_kd),
        .s_j(s_j), .s_jd_w(s_jd_w), .s_jd_e(s_jd_e), .s_hw_w(s_hw_w), .s_hw_e(s_hw_e), .s_hc_w(s_hc_w), .s_hc_e(s_hc_e),
        .st_rg_w(st_rg_w), .st_rg_e(st_rg_e), .cw_v(cw_v), .cw_a(cw_a), .cw_d(cw_d));
    dsdv_sh_ft #(.V(V)) u_d0 (.ck(ck), .ni(cn), .no(n1), .si(s1), .so(cs));       // die lane relay 1 (stand-in)
    generate if (MUT == 3) begin : g_mut3
        assign vo_n = n1; assign s1 = vi_n;                                        // negative control: one lane stage missing
    end else begin : g_d1
        dsdv_sh_ft #(.V(V)) u_d1 (.ck(ck), .ni(n1), .no(vo_n), .si(vi_n), .so(s1)); // die lane relay 2 (stand-in)
    end endgenerate
endmodule
