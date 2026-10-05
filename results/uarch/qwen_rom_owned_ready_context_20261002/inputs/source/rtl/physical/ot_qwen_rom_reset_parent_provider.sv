`timescale 1ns/1ps
// Additive source provider for the already-running SMIN6 full map.
// Pin contract: external reset deassert100..780ps after stream positive edge,
// low pulse>=330ps; stream input slew5..80ps, reset slew5..80ps.
// Parent retains ib_go/ib/x until launch_enable; parent_domains_ready is a
// registered stream-domain all-domain/drain acknowledgment, never tied high
// as a substitute for service/serial readiness. No queue or numerical change.
// Four reset pad buffers: each32um signal route reserved, separately priced.
module ot_qwen_rom_reset_parent_provider #(
    parameter integer RESET_CONTEXT = 0
) (
    input wire clk_stream,
    input wire external_reset_n,
    input wire parent_domains_ready,
    input wire ib_go,
    output wire released_reset_n,
    output wire launch_enable
);
    generate if (RESET_CONTEXT != 0) begin : g_context
        wire s1_qn,s1_d,s2_qn,reset_unpadded,launch_unbuffered;
        wire [4:0] pad;
        DFFASRHQNx1_ASAP7_75t_R s1 (.CLK(clk_stream),.RESETN(external_reset_n),.SETN(1'b1),.D(1'b1),.QN(s1_qn));
        INVx1_ASAP7_75t_R i1 (.A(s1_qn),.Y(s1_d));
        DFFASRHQNx1_ASAP7_75t_R s2 (.CLK(clk_stream),.RESETN(external_reset_n),.SETN(1'b1),.D(s1_d),.QN(s2_qn));
        INVx1_ASAP7_75t_R i2 (.A(s2_qn),.Y(reset_unpadded));
        assign pad[0]=reset_unpadded;
        genvar p;
        for(p=0;p<4;p=p+1) begin : g_pad
            BUFx4_ASAP7_75t_R delay_pad (.A(pad[p]),.Y(pad[p+1]));
        end
        assign released_reset_n=pad[4];
        AND3x1_ASAP7_75t_R launch_join (.A(ib_go),.B(parent_domains_ready),.C(released_reset_n),.Y(launch_unbuffered));
        BUFx4_ASAP7_75t_R launch_driver (.A(launch_unbuffered),.Y(launch_enable));
    end else begin : g_original
        assign released_reset_n=external_reset_n;
        assign launch_enable=ib_go;
    end endgenerate
endmodule
