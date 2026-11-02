// DISABLED TT_C source-event candidate. External clock/reset/START sampling and latency are unchanged.
// Enable only together with the paired regional receiver map, homes, clock/reset model and reviewed source event.
module ot_dp_landing_origin_s_regional #(
    parameter integer PADW=1,
    parameter integer REGIONS=4,
    parameter integer ENABLE=0
)(
    input wire clk, rst_raw_n, p_start, strap_efall,
    input wire [PADW-1:0] strap_pad,
    input wire [REGIONS-1:0] rst_region_raw_n,
    output wire [REGIONS-1:0] start_r, start_d_r
);
    localparam integer PADMAX=(1<<PADW)-1;
    generate if (ENABLE==0) begin : g_off
        wire start, start_d;
        ot_dp_landing_origin_s #(.PADW(PADW),.FWD_COPY(0)) u_original (
            .clk(clk),.rst_raw_n(rst_raw_n),.p_start(p_start),
            .strap_efall(strap_efall),.strap_pad(strap_pad),.start(start),.start_d(start_d));
        assign start_r={REGIONS{start}};
        assign start_d_r={REGIONS{start_d}};
    end else begin : g_on
        // Keep the original SF/S0 sampling point and fanout of p_start.
        (* async_reg="true" *) reg sf, s0;
        wire s_in=strap_efall ? sf : p_start;
        always @(negedge clk) sf<=p_start;
        always @(posedge clk) if (!rst_raw_n) s0<=0; else s0<=s_in;
`ifdef OT_TT_REGION_MUT_LATE
        reg delayed_s0;
        always @(posedge clk) if (!rst_raw_n) delayed_s0<=0; else delayed_s0<=s0;
`endif
        for (genvar r=0;r<REGIONS;r=r+1) begin : g_region
            (* keep="true", async_reg="true" *) reg s1;
            (* keep="true" *) reg s2;
            (* keep="true" *) reg [PADMAX-1:0] pd;
            always @(posedge clk) begin
                if (!rst_region_raw_n[r]) begin s1<=0;
`ifdef OT_TT_REGION_MUT_RESET
                    if (r!=2) s2<=0;
`else
                    s2<=0;
`endif
                    pd<=0;
                end else begin
`ifdef OT_TT_REGION_MUT_LATE
                    if (r==1) s1<=delayed_s0; else s1<=s0;
`else
                    s1<=s0;
`endif
                    s2<=s1;
                    pd<=PADMAX'({pd,s2});
                end
            end
            wire [PADMAX:0] taps={pd,s2};
            wire [PADMAX:0] taps_e={taps[PADMAX-1:0],s1};
            assign start_r[r]=taps[strap_pad];
            assign start_d_r[r]=taps_e[strap_pad];
        end
    end endgenerate
endmodule
