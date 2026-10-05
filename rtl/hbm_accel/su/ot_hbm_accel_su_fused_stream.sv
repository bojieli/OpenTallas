`timescale 1ns/1ps
// Additive, default-off endpoint for the existing exact fused SU engines.
// KIND: 0 HC norm, 1 Q norm, 2 KV norm+RoPE, 3 SwiGLU, 4 HC post.
// The parent reserves ALL output events in its real landing before cmd_ready.
// This is not an elastic engine: sink_ready must remain true during the lease.
// A missed landing or arithmetic fault holds busy; no fabricated completion.
module ot_hbm_accel_su_fused_stream #(
    parameter integer ENABLE = 0, KIND = 0, N = 1024, D = 5120, RD = 0,
    parameter integer BCAST = 7, RET = 8, LM = 6, LA = 5,
    parameter integer RW = 9, BW = 9, PUBLISH_QUANT = 1, ROUTED = 1
)(
    input wire clk, rst_n,
    input wire cmd_valid, input wire [31:0] cmd_id,
    input wire reserve_grant, output wire [15:0] reserve_events,
    output wire cmd_ready, output reg busy, output reg done,
    output reg [31:0] completion_id,
    input wire [511:0] comb, input wire [127:0] post_pre,
    input wire [31:0] n_f, eps, lim,
    input wire [(RD ? RD/2 : 1)*32-1:0] cos_t, sin_t,
    input wire gain_valid, input wire [7:0] gain_index,
    input wire [N*32-1:0] gain_data, output wire gain_ready,
    input wire in_valid, output wire in_ready,
    // norm: x copy-major; SwiGLU: g/u/w in planes 0/1/2;
    // HC post: [group][r0..r3] in plane0, y in first N/4 words of plane1.
    input wire [4*N*32-1:0] operands,
    input wire sink_ready,
    output wire y_valid, ro_valid, q_valid,
    output wire [7:0] y_index, q_index,
    output wire [N*32-1:0] y_data, ro_data,
    output wire [N*8-1:0] q_codes,
    output wire [(N/32)*10-1:0] q_exp,
    output wire [N*16-1:0] q_bf16,
    output reg fault
);
    localparam integer NV = (D+N-1)/N;
    localparam integer NB = KIND==4 ? (4*D+N-1)/N : NV;
    localparam integer NE = KIND<3 ? NV*(1+PUBLISH_QUANT+(RD!=0)) : (KIND==3 ? NB*(1+PUBLISH_QUANT) : NB);
    wire fire = cmd_valid && cmd_ready;
    reg start, streaming;
    reg [15:0] loaded, issued, landed;
    reg [31:0] held_id;
    reg [511:0] hc;
    reg [127:0] pp;
    reg [31:0] nf, ep, li;
    reg [(RD ? RD/2 : 1)*32-1:0] ct, st;
    wire accepted = in_valid && in_ready;
    wire engine_fault;
    wire [2:0] events = {2'b0,y_valid}+{2'b0,ro_valid}+{2'b0,q_valid};
    assign reserve_events = ENABLE ? NE : 0;
    assign gain_ready = ENABLE && KIND<3 && !busy && !fault && loaded<NV;
    assign cmd_ready = ENABLE && !busy && !fault && reserve_grant &&
                       (KIND>=3 || loaded==NV);
    assign in_ready = ENABLE && busy && streaming && !fault && issued<NB;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            busy<=0; done<=0; start<=0; streaming<=0; loaded<=0;
            issued<=0; landed<=0; fault<=0; completion_id<=0; held_id<=0;
            hc<=0; pp<=0; nf<=0; ep<=0; li<=0; ct<=0; st<=0;
        end else begin
            done<=0; start<=fire;
            if (gain_valid && gain_ready) begin
                if (gain_index==loaded) loaded<=loaded+1;
                else fault<=1;
            end
            if (fire) begin
                busy<=1; streaming<=0; issued<=0; landed<=0; held_id<=cmd_id;
                hc<=comb; pp<=post_pre; nf<=n_f; ep<=eps; li<=lim; ct<=cos_t; st<=sin_t;
            end
            if (start) streaming<=1;
            if (accepted) issued<=issued+1;
            if (engine_fault) fault<=1;
            if (events!=0) begin
                if (!busy || !sink_ready || landed+events>NE) fault<=1;
                else begin
                    landed<=landed+events;
                    if (landed+events==NE && issued==NB && !fault && !engine_fault) begin
                        busy<=0; streaming<=0; done<=1;
                        completion_id<=held_id; loaded<=0;
                    end
                end
            end
        end
    end
    generate if (!ENABLE) begin : g_off
        assign y_valid=0; assign ro_valid=0; assign q_valid=0;
        assign y_index=0; assign q_index=0; assign y_data=0; assign ro_data=0;
        assign q_codes=0; assign q_exp=0; assign q_bf16=0; assign engine_fault=0;
    end else if (KIND<3) begin : g_norm
        wire iv; wire [4*N*32-1:0] xd;
        ot_dsrom_su_hcpost_wire #(.W(4*N*32),.D(BCAST)) u_in
            (.clk(clk),.rst_n(rst_n),.v(accepted),.d(operands),.vq(iv),.q(xd));
        wire yv, qv, rv, rov;
        wire [7:0] yi, qi;
        wire [N*32-1:0] yy, rr;
        wire [(PUBLISH_QUANT ? N/32 : 1)*256-1:0] qc;
        wire [(PUBLISH_QUANT ? N/32 : 1)*10-1:0] qe;
        wire [(PUBLISH_QUANT ? N/32 : 1)*512-1:0] qy; wire [31:0] scalar;
        ot_dsrom_su_norm #(.N(N),.D(D),.HC(KIND==0),.RD(RD),.QUANT(PUBLISH_QUANT),
            .RW(RW),.BW(BW),.LM(LM),.LA(LA)) u_engine
            (.clk(clk),.rst_n(rst_n),.go(start),.in_v(iv),
             .in_x(xd[(KIND==0 ? 4 : 1)*N*32-1:0]),.pre(pp),.n_f(nf),.eps(ep),
             .wl_v(gain_valid && gain_ready && gain_index==loaded),
             .wl_i(gain_index),.wl_d(gain_data),.cos_t(ct),.sin_t(st),
             .y_v(yv),.y_i(yi),.y(yy),.r_v(rv),.r(scalar),
             .q_v(qv),.q_i(qi),.q_codes(qc),.q_e(qe),.q_y(qy),
             .ro_v(rov),.ro(rr),.fault(engine_fault));
        wire [N*32+8-1:0] yo;
        wire [N*8+(N/32)*10+N*16+8-1:0] qo;
        ot_dsrom_su_hcpost_wire #(.W(N*32+8),.D(RET)) u_y
            (.clk(clk),.rst_n(rst_n),.v(yv),.d({yi,yy}),.vq(y_valid),.q(yo));
        assign {y_index,y_data}=yo;
        ot_dsrom_su_hcpost_wire #(.W(N*32),.D(RET)) u_ro
            (.clk(clk),.rst_n(rst_n),.v(rov),.d(rr),.vq(ro_valid),.q(ro_data));
        ot_dsrom_su_hcpost_wire #(.W(N*8+(N/32)*10+N*16+8),.D(RET)) u_q
            (.clk(clk),.rst_n(rst_n),.v(qv),.d({qi,qc,qe,qy}),.vq(q_valid),.q(qo));
        assign {q_index,q_codes,q_exp,q_bf16}=qo;
    end else if (KIND==3) begin : g_swiglu
        wire iv; wire [3*N*32-1:0] ix;
        ot_dsrom_su_hcpost_wire #(.W(3*N*32),.D(BCAST)) u_in
            (.clk(clk),.rst_n(rst_n),.v(accepted),.d(operands[0+:3*N*32]),.vq(iv),.q(ix));
        wire [N*32-1:0] a, bf;
        wire [N-1:0] av, af;
        genvar l,b;
        for(l=0;l<N;l=l+1) begin : g_l
            ot_dsrom_su_swiglu_lane #(.LM(LM),.LA(LA),.ROUTED(ROUTED)) u
                (.clk(clk),.rst_n(rst_n),.v(iv),.g(ix[l*32+:32]),
                 .u(ix[N*32+l*32+:32]),.w(ix[2*N*32+l*32+:32]),.lim(li),
                 .a(a[l*32+:32]),.vo(av[l]),.fault(af[l]));
            ot_dsrom_su_bf16rnd r (.x(a[l*32+:32]),.y(bf[l*32+:32]));
        end
        // Preserve the original VM-visible BF16 before downstream quantisation.
        ot_dsrom_su_hcpost_wire #(.W(N*32),.D(RET)) u_y
            (.clk(clk),.rst_n(rst_n),.v(av[0]),.d(bf),.vq(y_valid),.q(y_data));
        assign y_index=landed[7:0];
        if(PUBLISH_QUANT) begin : g_quant
            wire [N/32-1:0] qv,qf;
            wire [N*8-1:0] qc; wire [(N/32)*10-1:0] qe; wire [N*16-1:0] qy;
            for(b=0;b<N/32;b=b+1) begin : g_b
                ot_hdc_actquant u (.clk(clk),.rst_n(rst_n),.v(av[0]),.fp4(1'b0),
                    .x(bf[1024*b+:1024]),.vo(qv[b]),.q(qc[256*b+:256]),
                    .e(qe[10*b+:10]),.y(qy[512*b+:512]),.fault(qf[b]));
            end
            wire [N*8+(N/32)*10+N*16-1:0] oq;
            ot_dsrom_su_hcpost_wire #(.W(N*8+(N/32)*10+N*16),.D(RET)) u_q
                (.clk(clk),.rst_n(rst_n),.v(qv[0]),.d({qc,qe,qy}),.vq(q_valid),.q(oq));
            assign {q_codes,q_exp,q_bf16}=oq;
            assign engine_fault=(|af)|(qv[0] && (|qf));
        end else begin : g_no_quant
            assign q_valid=0; assign q_codes=0; assign q_exp=0; assign q_bf16=0;
            assign engine_fault=|af;
        end
        assign ro_valid=0; assign ro_data=0; assign q_index=0;
    end else if (KIND==4) begin : g_hc_post
        // ML5/AL4 until the owner's ML6 integration fix is available and qualified.
        ot_dsrom_su_hcpost #(.NG(N/4),.WIN(BCAST),.WOUT(RET),.ML(5),.AL(4)) u_engine
            (.clk(clk),.rst_n(rst_n),.go(start),.comb(hc),.post(pp),
             .in_v(accepted),.in_r(operands[0+:N*32]),
             .in_y(operands[N*32+:(N/4)*32]),.out_v(y_valid),.out_d(y_data),.fault(engine_fault));
        assign y_index=landed[7:0]; assign q_index=0;
        assign ro_valid=0; assign q_valid=0; assign ro_data=0;
        assign q_codes=0; assign q_exp=0; assign q_bf16=0;
    end else begin : g_invalid
        assign y_valid=0; assign ro_valid=0; assign q_valid=0;
        assign y_index=0; assign q_index=0; assign y_data=0; assign ro_data=0;
        assign q_codes=0; assign q_exp=0; assign q_bf16=0; assign engine_fault=1;
    end endgenerate
endmodule
