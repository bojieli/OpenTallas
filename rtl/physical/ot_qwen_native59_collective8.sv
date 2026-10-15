`timescale 1ns/1ps
// Persistent functional eight-die native59 model. Public vectors are TP8 rank=4*DIE+PKG.
// Source-exact LATU14/LATS40/BPC3600 transport, no stimulus or expected-result arrays.
// Hierarchical state probes are functional model instrumentation, not qualified physical interfaces.
module ot_qwen_native59_collective8 #(
    parameter integer LANES=16, LATU=14, LATS=40, BPC=3600, ICR=32
)(
    input wire clk, rst_n,
    input wire [7:0] in_valid, in_mode, in_last,
    input wire [8*32*LANES-1:0] in_data,
    input wire [8*59-1:0] in_tag,
    output wire [7:0] in_cr,
    output wire [8*6-1:0] in_credits,
    output wire [7:0] out_valid, out_last, out_err,
    output wire [8*32*LANES-1:0] out_data,
    output wire [8*59-1:0] out_tag,
    output wire [23:0] out_rank,
    output wire [7:0] fault, online, drained,
    output wire [39:0] fault_code
);
    localparam integer ND=8, FW=32*LANES, TAGW=59, PW=FW+2+TAGW, RW=FW+2+TAGW;
    wire [ND-1:0] flt; wire [ND*5-1:0] fc;
    wire [ND-1:0] upv,uprdy,upcr,dpv,dpcr,urv,urrdy,urcr,drv,drcr;
    wire [ND*PW-1:0] uprec,dprec; wire [ND*RW-1:0] urrec,drrec;
    wire [ND*3-1:0] sxv,sxrdy,sxcr,srv,srcr;
    wire [ND*3*PW-1:0] sxrec,srrec;
    initial if(LATU!=14 || LATS!=40 || BPC!=3600 || ICR!=32 || LANES!=16)
        $error("persistent native59 source contract requires LATU14 LATS40 BPC3600 ICR32 LANES16");
    genvar g, j;
    generate
        for (g = 0; g < ND; g = g + 1) begin : g_die
            localparam integer P = g / 2, D = g % 2, R = 4*D+P;
            ot_coll_tp8_die_native59 #(.PKG(P), .DIE(D), .LANES(LANES), .WT(0), .ICR(ICR)) u_die (
                .clk(clk), .rst_n(rst_n),
                .in_valid(in_valid[R]), .in_cr(in_cr[R]), .in_data(in_data[R*FW +: FW]), .in_last(in_last[R]), .in_mode(in_mode[R]),
                .in_tag(in_tag[R*TAGW +: TAGW]),
                .up_valid(upv[g]), .up_rec(uprec[g*PW +: PW]), .up_ready(uprdy[g]), .up_cr_in(upcr[g]),
                .dp_valid(dpv[g]), .dp_rec(dprec[g*PW +: PW]), .dp_cr_out(dpcr[g]),
                .ur_valid(urv[g]), .ur_rec(urrec[g*RW +: RW]), .ur_ready(urrdy[g]), .ur_cr_in(urcr[g]),
                .dr_valid(drv[g]), .dr_rec(drrec[g*RW +: RW]), .dr_cr_out(drcr[g]),
                .sx_valid(sxv[g*3 +: 3]), .sx_rec(sxrec[g*3*PW +: 3*PW]), .sx_ready(sxrdy[g*3 +: 3]),
                .sx_cr_in(sxcr[g*3 +: 3]), .sr_valid(srv[g*3 +: 3]), .sr_rec(srrec[g*3*PW +: 3*PW]),
                .sr_cr_out(srcr[g*3 +: 3]),
                .out_valid(out_valid[R]), .out_data(out_data[R*FW +: FW]), .out_last(out_last[R]), .out_rank(out_rank[R*3 +: 3]),
                .out_err(out_err[R]), .out_tag(out_tag[R*TAGW +: TAGW]), .fault(flt[g]), .fault_code(fc[g*5 +: 5]));
            reg [6:0] local_credits;
            reg local_credit_fault;
            wire core_online = u_die.rs_a && u_die.rs && u_die.rs_m && u_die.u_eng.rst_i;
            assign online[R] = rst_n && core_online;
            assign in_credits[R*6 +: 6] = local_credits[5:0];
            always @(posedge clk or negedge rst_n) begin
                if(!rst_n) begin local_credits<=ICR; local_credit_fault<=0; end
                else begin
                    if(in_valid[R] && !core_online) local_credit_fault<=1;
                    if(core_online) begin
                        local_credits<=local_credits + in_cr[R] - in_valid[R];
                        if((in_valid[R] && local_credits==0) ||
                           (in_cr[R] && !in_valid[R] && local_credits==ICR)) local_credit_fault<=1;
                    end
                end
            end
            assign fault[R] = flt[g] || local_credit_fault;
            assign fault_code[R*5 +: 5] = fc[g*5 +: 5] | (local_credit_fault ? 5'b10000 : 5'b00000);
            wire engine_sources_empty;
            wire [3:0] source_empty;
            for(genvar e=0;e<4;e=e+1) begin:g_source_empty
                assign source_empty[e] = u_die.u_eng.mcnt[e]==0 && !u_die.u_eng.hv[e] && u_die.u_eng.cr[e]==32;
            end
            assign engine_sources_empty=&source_empty;
            wire engine_empty = engine_sources_empty && u_die.u_eng.ib_empty &&
                !u_die.u_eng.iv_q && !u_die.u_eng.lpv && !(|u_die.u_eng.rxv_q) &&
                !u_die.u_eng.txv_q && !u_die.u_eng.txv_d && !(|u_die.u_eng.cri_q) &&
                !u_die.u_eng.cro_q && !u_die.e_icr && !u_die.u_eng.s0_v && !u_die.u_eng.s0_vl &&
                !u_die.u_eng.s0_vcd && !u_die.u_eng.g_busy && !u_die.u_eng.gc_v &&
                !u_die.u_eng.go_v && !u_die.u_eng.gov_m && !(|u_die.u_eng.sv) &&
                u_die.u_eng.inflight==0 && u_die.u_eng.identity_count==0 && !u_die.u_eng.ov_q;
            wire collector_empty = !u_die.iv_q && !u_die.rl_v && !u_die.upv_q && !u_die.upc_q &&
                !u_die.icr_q && !u_die.dpv_q && !u_die.dpc_q && !u_die.lb_hv && !u_die.pq_hv &&
                !u_die.eq_hv && !u_die.lq_hv && !u_die.tq_hv && !u_die.rq_hv && !u_die.mf_hv &&
                u_die.eq_res==0 && u_die.infl==0 && !u_die.gh_v && !(|u_die.ml_v) &&
                u_die.ecred==4 && u_die.lq_res==0 && u_die.tq_res==0 && u_die.mf_n==0 &&
                !u_die.e_ov && !u_die.urv_q && !u_die.urc_q && !u_die.drv_q && !u_die.drc_q &&
                u_die.rcred==32 && u_die.mc==0 && !u_die.ov_q && u_die.cr_a==0 && u_die.cr_b==0 &&
                !(|u_die.sxv_q) && !(|u_die.srv_q) && !(|u_die.sxc_q) && !(|u_die.src_q);
            wire [2:0] sx_empty;
            assign drained[R] = online[R] && !fault[R] && !in_valid[R] && local_credits==ICR &&
                engine_empty && collector_empty && !(|u_up.v_line) && !(|u_up.c_line) &&
                !(|u_ur.v_line) && !(|u_ur.c_line) && (&sx_empty);
            // in-package UCIe: this die -> its peer (g ^ 1)
            ot_rom_ucie_link #(.PW(PW), .LAT(LATU), .FLIT_BYTES(FW / 8), .BPC_NUM(BPC)) u_up (
                .clk(clk), .rst_n(rst_n), .in_valid(upv[g]), .in_rec(uprec[g*PW +: PW]), .in_ready(uprdy[g]),
                .out_valid(dpv[g ^ 1]), .out_rec(dprec[(g ^ 1)*PW +: PW]), .cr_in(dpcr[g ^ 1]), .cr_out(upcr[g]));
            ot_rom_ucie_link #(.PW(RW), .LAT(LATU), .FLIT_BYTES(FW / 8), .BPC_NUM(BPC)) u_ur (
                .clk(clk), .rst_n(rst_n), .in_valid(urv[g]), .in_rec(urrec[g*RW +: RW]), .in_ready(urrdy[g]),
                .out_valid(drv[g ^ 1]), .out_rec(drrec[(g ^ 1)*RW +: RW]), .cr_in(drcr[g ^ 1]), .cr_out(urcr[g]));
            // SerDes: port j -> die D of package Q = (P + 1 + j) mod 4, arriving on its port (P - Q + 3) mod 4
            for (j = 0; j < 3; j = j + 1) begin : g_sx
                localparam integer Q = (P + 1 + j) % 4, R2 = 2 * Q + D, J2 = (P - Q + 7) % 4;
                assign sx_empty[j] = !(|u_sx.v_line) && !(|u_sx.c_line);
                ot_rom_ucie_link #(.PW(PW), .LAT(LATS), .FLIT_BYTES(FW / 8), .BPC_NUM(BPC)) u_sx (
                    .clk(clk), .rst_n(rst_n), .in_valid(sxv[g*3 + j]), .in_rec(sxrec[(g*3 + j)*PW +: PW]),
                    .in_ready(sxrdy[g*3 + j]), .out_valid(srv[R2*3 + J2]), .out_rec(srrec[(R2*3 + J2)*PW +: PW]),
                    .cr_in(srcr[R2*3 + J2]), .cr_out(sxcr[g*3 + j]));
            end
        end
    endgenerate
endmodule
