`timescale 1ns/1ps
`default_nettype none
// Exact interface of selected50a9 HWINmux→f873MU47→8afseqhost.
// All realMU/status pins preserved. Source-only, no physical/wholeprogrammeclaim.
//
// S81/PORTFIX-FLT 10-25 (S81 DECISION 4: each unit has ONE 1-bit sticky fault; detail status codes are dropped; the
// faults are reported to the host).  Port changes: t_mf[3:0], hostb_fault[2:0] and hb_job_active (= t_host[65], still
// in t_host) are no longer outputs; + the two 1-bit DIE FAULT RINGS (ot_s81_frs stops in the ring partitions):
//   sid_ro -> 16 C slice stops -> sid_ri        vid_ro -> 16 svc stops -> vid_ri
// The ring heads sid_ro / vid_ro launch this unit's own sticky fault (flop outputs).
// Own sticky fault own_f = OR of the former t_mf (MU hslot slot collision / off-calendar / RL return / config + hwin RX
// tag / late event / window config + static KS6 starter faults) and hostb_fault (HOSTB landing select / KS-HBE source
// faults); ring returns land in pin flops and latch sticky (sid_f, vid_f).
// DIE FAULT WORD -> HOST, in band on the existing host return t_host (-> s_7N lep THOST frames; also sampled whole into
// the s_0N HBC return record), 0 new lanes, 0 new frame kinds:
//   t_host = {alive [76], st 11 = {fault [75], wf 4 [74:71], sseq 6 [70:65]}, t_v [64], t_d 64 [63:0]}
//   [75] fault = core fault (sh_lk: ingest / host-sd / lane / issuer / wf) | sid_f | vid_f | own_f
//   [74] sid_f = sid ring (any C slice stop, or own_f via the ring head)
//   [73] vid_f = vid ring (any svc stop: irg / svc entries / pvso / etap / iqf / eng / phy_hbm feeders, or own_f)
//   [72] own_f = this unit's own fault (MU slot / window / KS starter / HOSTB source)
//   [71] core wf = OR of the former wf {rg_f, rg_drop, svc_f, vf} (the detail bits are dropped)
//   alive, sseq, t_v, t_d unchanged.  The lep sends a THOST frame on every change of t_host[76:65] (status-only
//   change merges into a pending t_v frame), so every newly set fault bit reaches the host as a frame; the bits are
//   sticky until the die reset (OWNER DECISION 13 wavefront: fault = control state, cleared by reset).
// Timing: [75:71] leave this wrapper's register one edge after the core's t_host register (fault / status bits only;
// t_v / t_d / sseq / alive keep their edges): 0 cycles on every data / host-return path.
module dsdv_hostb_seqhost_mux #(parameter integer HOSTB_ENABLE=0, STATIC_KS6=0,
 parameter integer STATIC_KS_SPAN=0, parameter [31:0] STATIC_KS_GRAPH_TAG=0,
 parameter integer FMUT=0) (   // FMUT (bench negative controls only): 1 ring heads not driven, 2 own bit dropped, 3 sid/vid swapped
    input  wire          ck,
    input  wire          rst_n,
    input  wire [7:0]    tap_k, sink_k,
    input  wire [275:0]  vi_s, output wire [275:0] vo_s,
    input  wire [275:0]  vi_n, output wire [275:0] vo_n,
    input wire select_hbe,input wire [514:0] hbe_f_host,input wire [52:0] starter_f_ks,
    input wire [2:0] hbe_ks_slot,
    output wire [52:0] engram_f_ks,
    output wire hb_starter_armed,
    input  wire [514:0]  f_host, output wire [76:0] t_host, input wire [3:0] f_lf,
    input  wire [52:0]   f_ks,   output wire [53:0] t_kd,
    input  wire          sid_ri, vid_ri,   // fault ring ends (last C slice stop / last svc stop)
    output wire          sid_ro, vid_ro,   // fault ring heads (own sticky fault, registered)
    output wire [32:0]   s_j,    input  wire [1:0]  s_jd_w, s_jd_e,
    output wire [291:0]  s_hw_w, s_hw_e, input wire [8:0] s_hc_w, s_hc_e,
    input  wire [1:0]    st_rg_w, st_rg_e,
    output wire          cw_v, output wire [9:0] cw_a, output wire [255:0] cw_d,
    output wire [33:0]   mu_c_7n, mu_c_7s, mu_c_0n, mu_c_0s,
    output wire [10:0]   mu_rc_7n, mu_rc_7s, mu_rc_0n, mu_rc_0s,
    input  wire [31:0]   mu_rt_7n, mu_rt_0n
);
 wire [514:0] issue_host;wire [52:0] issue_ks;
 wire [76:0] t_core;wire [3:0] t_mf;wire [2:0] hostb_fault;   // former outputs, internal (bench taps)
 dsdv_hostb_source #(.HOSTB_ENABLE(HOSTB_ENABLE),.STATIC_KS6(STATIC_KS6),
 .STATIC_KS_SPAN(STATIC_KS_SPAN),.STATIC_KS_GRAPH_TAG(STATIC_KS_GRAPH_TAG)) u_source(
 .ck(ck),.rst_n(rst_n),.select_hbe(select_hbe),.upstream_fault(|t_mf),
 .f_host(f_host),.hbe_f_host(hbe_f_host),.f_ks(f_ks),.starter_f_ks(starter_f_ks),
 .hbe_ks_slot(hbe_ks_slot),.issue_host(issue_host),.issue_ks(issue_ks),
 .engram_f_ks(engram_f_ks),.hostb_fault(hostb_fault),.hb_starter_armed(hb_starter_armed));
 dsdv_seq_host_mux u_seqhost(.ck(ck),.rst_n(rst_n),.tap_k(tap_k),.sink_k(sink_k),.vi_s(vi_s),.vo_s(vo_s),.vi_n(vi_n),.vo_n(vo_n),
 .f_host(issue_host),.t_host(t_core),.f_lf(f_lf),.f_ks(issue_ks),.t_kd(t_kd),.t_mf(t_mf),.s_j(s_j),
 .s_jd_w(s_jd_w),.s_jd_e(s_jd_e),.s_hw_w(s_hw_w),.s_hw_e(s_hw_e),.s_hc_w(s_hc_w),.s_hc_e(s_hc_e),
 .st_rg_w(st_rg_w),.st_rg_e(st_rg_e),.cw_v(cw_v),.cw_a(cw_a),.cw_d(cw_d),
 .mu_c_7n(mu_c_7n),.mu_c_7s(mu_c_7s),.mu_c_0n(mu_c_0n),.mu_c_0s(mu_c_0s),
 .mu_rc_7n(mu_rc_7n),.mu_rc_7s(mu_rc_7s),.mu_rc_0n(mu_rc_0n),.mu_rc_0s(mu_rc_0s),.mu_rt_7n(mu_rt_7n),.mu_rt_0n(mu_rt_0n));
 // ---- die fault word (control state: one relayed reset leaf, cleared by the die reset wavefront)
 wire [0:0] frn;ot_rst_relay #(.REGIONS(1)) u_frr(.clk(ck),.rst_n_in(rst_n),.rst_n(frn));
 reg sid_q,vid_q,own_f,sid_f,vid_f,sid_h,vid_h;reg [4:0] st_q;
 always @(posedge ck or negedge frn[0])
  if(!frn[0])begin sid_q<=0;vid_q<=0;own_f<=0;sid_f<=0;vid_f<=0;sid_h<=0;vid_h<=0;st_q<=0;end
  else begin
   sid_q<=sid_ri;vid_q<=vid_ri;                                          // ring-end pin flops
   own_f<=own_f|(|t_mf)|(|hostb_fault);
   sid_f<=sid_f|sid_q;vid_f<=vid_f|vid_q;
   sid_h<=(FMUT==1)?1'b0:own_f;vid_h<=(FMUT==1)?1'b0:own_f;             // ring heads
   st_q<=(FMUT==3)?{t_core[75]|own_f|sid_f|vid_f,vid_f,sid_f,own_f,|t_core[74:71]}
                  :{t_core[75]|own_f|sid_f|vid_f,sid_f,vid_f,(FMUT==2)?1'b0:own_f,|t_core[74:71]};
  end
 assign sid_ro=sid_h;assign vid_ro=vid_h;
 assign t_host={t_core[76],st_q,t_core[70:0]};
endmodule
`default_nettype wire
