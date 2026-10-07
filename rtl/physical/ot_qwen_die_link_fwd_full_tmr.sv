`timescale 1ns/1ps
// Default-off full-cycle successor. No old station source is modified.
// Each direction owns its clock. Opaque control is not a new protection code.
// Physical qualification MUST prove data min delay against the two-inverter
// forwarded clock insertion; zero-delay RTL does not prove inter-stage hold.
module ot_qwen_die_link_fwd_full_tmr #(
    parameter integer NL = 1,
    parameter integer LW = 528,
    parameter integer CW = 16,
    parameter integer ENABLE = 0
)(
    input wire rst_n,
    input wire [NL-1:0] fclk_ab_i, fclk_ba_i,
    output wire [NL-1:0] fclk_ab_o, fclk_ba_o,
    input wire [NL*LW-1:0] a_i, b_i,
    output wire [NL*LW-1:0] a_o, b_o
);
    generate if (ENABLE) begin: active
        genvar k;
        for (k=0;k<NL;k=k+1) begin: link
            ot_qwen_link_fwd_direction_tmr #(.LW(LW),.CW(CW)) ab(
                .rst_n(rst_n),.fclk_i(fclk_ab_i[k]),.fclk_o(fclk_ab_o[k]),
                .d_i(a_i[k*LW+:LW]),.d_o(b_o[k*LW+:LW]));
            ot_qwen_link_fwd_direction_tmr #(.LW(LW),.CW(CW)) ba(
                .rst_n(rst_n),.fclk_i(fclk_ba_i[k]),.fclk_o(fclk_ba_o[k]),
                .d_i(b_i[k*LW+:LW]),.d_o(a_o[k*LW+:LW]));
        end
    end else begin: disabled
        assign fclk_ab_o=0; assign fclk_ba_o=0;
        assign a_o=0; assign b_o=0;
    end endgenerate
endmodule

(* keep_hierarchy = 1 *)
module ot_qwen_link_fwd_direction_tmr #(parameter integer LW=528, CW=16)(
    input wire rst_n, fclk_i, input wire [LW-1:0] d_i,
    output wire fclk_o, output wire [LW-1:0] d_o
);
    // Cold POR only. Warm reset requires endpoint drain and coordinated epoch.
    // Control CLR deasserts from the local majority release; its physical
    // recovery/removal path remains timed. Raw POR reaches all six rail FFs.
    // Only release-chain storage is triplicated. No whole-link integrity claim.
    (* async_reg = "true", keep = 1, dont_touch = 1 *) reg [2:0] release0, release1;
    genvar rail;
    generate for(rail=0;rail<3;rail=rail+1) begin: release_rail
        // Process attributes prevent identical cold-POR rails merging in synth.
        (* keep = 1, dont_touch = 1 *) always @(posedge fclk_i or negedge rst_n)
            if (!rst_n) begin release0[rail]<=0; release1[rail]<=0; end
            else begin release0[rail]<=1; release1[rail]<=release0[rail]; end
    end endgenerate
    (* keep = 1 *) wire release_run;
    assign release_run=(release1[0]&release1[1]) |
                       (release1[0]&release1[2]) | (release1[1]&release1[2]);
    (* keep = 1, dont_touch = 1 *) reg [LW-CW-1:0] data_q;
    (* keep = 1, dont_touch = 1 *) reg [CW-1:0] control_q;
    always @(posedge fclk_i) data_q <= d_i[LW-1:CW];
    always @(posedge fclk_i or negedge release_run)
        if (!release_run) control_q<=0;
        else control_q<=d_i[CW-1:0];
    assign d_o={data_q,control_q};
    (* keep = 1 *) wire clock_mid;
    (* keep = 1, dont_touch = 1 *) ot_qwen_link_fwd_inv_tmr inv0(.a(fclk_i),.y(clock_mid));
    (* keep = 1, dont_touch = 1 *) ot_qwen_link_fwd_inv_tmr inv1(.a(clock_mid),.y(fclk_o));
endmodule

(* keep_hierarchy = 1 *)
module ot_qwen_link_fwd_inv_tmr(input wire a, output wire y);
    assign y=~a;
endmodule
