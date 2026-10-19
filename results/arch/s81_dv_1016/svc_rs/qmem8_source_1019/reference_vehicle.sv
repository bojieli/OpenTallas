module reference_vehicle (input wire clk,q_word,input wire [511:0] f_hdr,q_d,input wire [11:0] f_idx,input wire [9:0] rc,output wire [511:0] eq_w);
 localparam integer D=32,H=16;
    reg [D*16-1:0] qmem [0:H-1];
 reg [511:0] cap;
 always @(posedge clk) begin
        if (q_word) qmem[{f_hdr[448], f_idx[6:4]}] <= q_d;
        cap <= qmem[4'(rc - 10'd1)];
 end
 assign eq_w=cap;
endmodule
