// Exact verbatim module extracted from current native static LOAD converter.
module ot_hbm_dma_convert_part #(parameter COPY_ID=0,PART=0,MUT=0)(input wire clk,input wire[2:0]fmt_i,input wire[31:0]raw,output reg[7:0]q);
 (* keep="true" *)reg[2:0]fmt,f0,f1;
    function automatic [31:0] i8_f(input [7:0] c);
        reg [7:0] a; reg [2:0] p; integer k;
        begin
            a = c[7] ? (~c + 8'd1) : c; p = 3'd0;
            for (k = 0; k < 8; k = k + 1) if (a[k]) p = k[2:0];
            i8_f = (a == 8'd0) ? 32'd0 : {c[7], 8'd127 + {5'd0, p}, ({15'd0, a} << (5'd23 - {2'd0, p})) & 23'h7FFFFF};
        end
    endfunction
    function automatic [31:0] e4m3_f(input [7:0] c);
        reg [3:0] e; reg [2:0] m; reg [1:0] p;
        begin
            e = c[6:3]; m = c[2:0];
            if (e == 4'hF && m == 3'h7) e4m3_f = 32'h7FC00000;
            else if (e == 4'd0) begin
                if (m == 3'd0) e4m3_f = {c[7], 31'd0};
                else begin
                    p = m[2] ? 2'd2 : m[1] ? 2'd1 : 2'd0;
                    e4m3_f = {c[7], 8'd127 - 8'd9 + {6'd0, p}, ({20'd0, m} << (5'd23 - {3'd0, p})) & 23'h7FFFFF};
                end
            end else e4m3_f = {c[7], 8'd120 + {4'd0, e}, m, 20'd0};
        end
    endfunction

 function automatic [31:0] decode_word(input [31:0] raw,input [2:0] fmt);
 begin
 case(fmt)
  1:decode_word={raw[15:0],16'd0};
  2:decode_word=e4m3_f(raw[7:0]);
  4:decode_word=i8_f(raw[7:0]);
  6:decode_word=raw[7:0]==255?32'h7fc00000:raw[7:0]==0?32'h00400000:{1'b0,raw[7:0],23'd0};
  default:decode_word=raw;
 endcase
 end
 endfunction

 wire[31:0]result=decode_word(raw,fmt);
 always @(posedge clk)begin
 f0<=fmt_i;f1<=f0;fmt<=f1;
 q<=result[PART*8+:8]^((MUT==1&&fmt==1&&PART==2)?8'h01:8'h00);
 end
endmodule
