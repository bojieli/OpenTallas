module count2(input clk,input [2:0] q,input s_v,s_r,s_go,output reg[2:0] sq_n); parameter SQ_COUNT_PARALLEL=1; always @* begin sq_n=q;
          if (SQ_COUNT_PARALLEL != 0) begin
            // Keep the late JEDEC pop decision out of a serial add/subtract chain.
            // Count, ready, pop and every calendar edge retain their original cycle.
            case ({(s_v && s_r), s_go})
              2'b10: sq_n = q + 1'b1;
              2'b01: sq_n = q + 1'b1;
              2'b00, 2'b11: sq_n = q;
              default: sq_n = q + ((s_v && s_r) ? 1'b1 : 1'b0) - (s_go ? 1'b1 : 1'b0);
            endcase
          end else begin
            sq_n = q + ((s_v && s_r) ? 1'b1 : 1'b0) - (s_go ? 1'b1 : 1'b0);
          end
end endmodule
