`timescale 1ns/1ps
// Literal allowed-cell ports, source preparation only. No wire/timing credit.
// CELL_MAP is default off; original functional packet helper stays byte-identical.
module ot_topk_allowed_cut_packet_prepare #(
    parameter integer WIDTH=1, EDGES=1,
    parameter [WIDTH-1:0] MASK={WIDTH{1'b0}},
    parameter integer CELL_MAP=0
)(
    input wire clk,rst_n,
    input wire [WIDTH-1:0] in_packet,
    output wire [WIDTH-1:0] out_packet
);
    initial if(CELL_MAP!=0 && !((WIDTH==2122 && EDGES==99) || (WIDTH==2088 && EDGES==99) || (WIDTH==2113 && EDGES==28)))
        $fatal(1,"ALLOWED_CUT_FULL_INTERFACE_REQUIRED");
    generate if(CELL_MAP==0) begin:g_original
        ot_topk_fixed_packet_delay_prepare #(.WIDTH(WIDTH),.EDGES(EDGES),.MASK(MASK)) u_packet (
            .clk(clk),.rst_n(rst_n),.in_packet(in_packet),.out_packet(out_packet));
    end else begin:g_allowed
        // WIDTH payload bits plus one present flag per segment; no extra edge.
        wire [WIDTH:0] source_bus[0:EDGES];
        wire [WIDTH:0] final_bus;
        wire root_present;
        TIEHIx1_ASAP7_75t_R u_root_present(.H(root_present));
        assign source_bus[0]={root_present,in_packet};
        for(genvar edge_=0;edge_<=EDGES;edge_=edge_+1) begin:g_segment
            wire [WIDTH:0] repeat0,repeat1;
            for(genvar bit_=0;bit_<=WIDTH;bit_=bit_+1) begin:g_bit
                BUFx4_ASAP7_75t_R u_repeat0(.A(source_bus[edge_][bit_]),.Y(repeat0[bit_]));
                BUFx4_ASAP7_75t_R u_repeat1(.A(repeat0[bit_]),.Y(repeat1[bit_]));
                if(edge_<EDGES) begin:g_capture
                    wire d,qn;
                    BUFx4_ASAP7_75t_R u_terminal(.A(repeat1[bit_]),.Y(d));
                    if(bit_<WIDTH) begin:g_payload
                        DFFHQNx1_ASAP7_75t_R u_ff(.D(d),.CLK(clk),.QN(qn));
                    end else begin:g_present
                        wire setn;
                        TIEHIx1_ASAP7_75t_R u_setn_tie(.H(setn));
                        // Actual Liberty clear=!SETN, preset=!RESETN, QN=IQN.
                        // rst_n=0 therefore QN=1; restoringINV makes present0.
                        DFFASRHQNx1_ASAP7_75t_R u_ff(.D(d),.CLK(clk),.RESETN(rst_n),.SETN(setn),.QN(qn));
                    end
                    INVx1_ASAP7_75t_R u_restore(.A(qn),.Y(source_bus[edge_+1][bit_]));
                end else begin:g_sink_boundary
                    // Original receiver/guard cone remains a separate context
                    // obligation, never a transferred intermediateFF hold PASS.
                    assign final_bus[bit_]=repeat1[bit_];
                end
            end
        end
        wire permitted;
        AND2x2_ASAP7_75t_R u_reset_permitted(.A(rst_n),.B(final_bus[WIDTH]),.Y(permitted));
        for(genvar bit_=0;bit_<WIDTH;bit_=bit_+1) begin:g_fence
            if(MASK[bit_]) AND2x2_ASAP7_75t_R u_control(.A(final_bus[bit_]),.B(permitted),.Y(out_packet[bit_]));
            else assign out_packet[bit_]=final_bus[bit_];
        end
    end endgenerate
endmodule
