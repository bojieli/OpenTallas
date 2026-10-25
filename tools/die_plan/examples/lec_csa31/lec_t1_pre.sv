// LEC test fixture (tools/die_plan/test_lec.py): the 2026-10-24 csa31 shape (a[31:24] of a 31-b operand at k = 3)
module lec_sub #(parameter W = 4) (input logic clk, input logic rst_n, input logic en, input logic [W-1:0] d,
                                   output logic [W-1:0] q);
  always_ff @(posedge clk or negedge rst_n) if (!rst_n) q <= '0; else if (en) q <= d;
endmodule
module lec_t1(input wire clk, input wire rst_n, input wire en, input wire [30:0] a, input wire [30:0] b,
              output reg [30:0] y, output wire [3:0] bo, output reg [3:0] st, output wire [3:0] sq, output wire [3:0] mo);
    function automatic [30:0] csa31(input [30:0] a, input [30:0] b);
        reg [8:0] z, o; reg c; integer k;
        begin
            c = 1'b0;
            for (k = 0; k < 4; k = k + 1) begin
                z = {1'b0, a[8*k +: 8]} + {1'b0, b[8*k +: 8]};
                o = {1'b0, a[8*k +: 8]} + {1'b0, b[8*k +: 8]} + 9'd1;
                if (k < 3) csa31[8*k +: 8] = c ? o[7:0] : z[7:0]; else csa31[30:24] = c ? o[6:0] : z[6:0];
                c = c ? o[8] : z[8];
            end
        end
    endfunction
  reg [3:0] mem [0:3];
  reg [1:0] wa;
  always @(posedge clk) begin
    if (en) mem[wa] <= a[3:0];
    wa <= wa + 2'd1;
    y <= csa31(a, b);
  end
  assign mo = mem[b[1:0]];
  always @(posedge clk) if (!rst_n) st <= 4'd0; else case (st) 4'd0: st <= en ? 4'd1 : 4'd0; 4'd1: st <= 4'd2;
                                                                  4'd2: st <= a[0] ? 4'd3 : 4'd0; default: st <= 4'd0; endcase
  lec_bbx u_bb(.clk(clk), .a(mem[a[5:4]] ^ y[3:0]), .y(bo));
  lec_sub #(.W(4)) u_sub(.clk(clk), .rst_n(rst_n), .en(en), .d(bo), .q(sq));
endmodule
