module old_am(input clk,raw_v,input [543:0] pma_rx,output [543:0] face_data,output reg am_ok,pv);
wire [543:0] raw_word;
ot_s81_pma_rxm prx(.pma_rck(clk),.pma_rx(pma_rx),.q(raw_word));
ot_pl_pad #(.W(544),.N(1)) u_face_p_d(.ck(clk),.d(raw_word),.q(face_data));
wire p_v;ot_pl_pad #(.W(1),.N(1)) u_face_p_v(.ck(clk),.d(raw_v),.q(p_v));
wire [543:0] p_d=face_data;
wire [11:0] amx=p_d[543:532]^12'hA5C;
function automatic [3:0] pop12(input [11:0] x); integer b; begin pop12 = 0; for (b = 0; b < 12; b = b + 1) pop12 = pop12 + x[b]; end endfunction
always @(posedge clk) begin am_ok <= p_v && (pop12(amx) <= 2); pv <= p_v; end
endmodule
module new_am(input clk,raw_v,input [543:0] pma_rx,output [543:0] face_data,output reg am_ok,pv);
wire [543:0] raw_word;
ot_s81_pma_rxm prx(.pma_rck(clk),.pma_rx(pma_rx),.q(raw_word));
ot_pl_pad #(.W(544),.N(1)) u_face_p_d(.ck(clk),.d(raw_word),.q(face_data));
wire p_v;ot_pl_pad #(.W(1),.N(1)) u_face_p_v(.ck(clk),.d(raw_v),.q(p_v));
wire [543:0] p_d=face_data;
wire [8:0] am_face3;ot_s81_kp4_am_face3 u_face_am3(.clk(clk),.p_d(raw_word),.parts(am_face3));
    wire [3:0] am_distance = {1'b0, am_face3[2:0]} + {1'b0, am_face3[5:3]} + {1'b0, am_face3[8:6]};
    always @(posedge clk) begin am_ok <= p_v && (am_distance <= 4'd2); pv <= p_v; end
endmodule
module ot_s81_kp4_am_face3 (
    input wire clk,
    input wire [543:0] p_d,
    output reg [8:0] parts
);
    wire [11:0] amx = p_d[543:532] ^ 12'hA5C;
    function automatic [2:0] pop4(input [3:0] x);
        begin pop4 = {2'b0,x[0]} + {2'b0,x[1]} + {2'b0,x[2]} + {2'b0,x[3]}; end
    endfunction
    always @(posedge clk) begin
        parts[2:0] <= pop4(amx[3:0]);
        parts[5:3] <= pop4(amx[7:4]);
        parts[8:6] <= pop4(amx[11:8]);
    end
endmodule
module ot_pl_pad #(
    parameter integer W = 1,
    parameter integer N = 1
) (
    input  wire         ck,
    input  wire [W-1:0] d,
    output wire [W-1:0] q
);
    generate if (N == 0) begin : g_wire
        assign q = d;
    end else begin : g_reg
        reg [W-1:0] r [0:N-1];
        integer j;
        always @(posedge ck) begin
            r[0] <= d;
            for (j = 1; j < N; j = j + 1) r[j] <= r[j - 1];
        end
        assign q = r[N-1];
    end endgenerate
endmodule

