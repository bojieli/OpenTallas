module step(input [31:0] count,input inc,output bad);
wire ot_creq_c8=&count[7:0],ot_creq_c16=&count[15:0],ot_creq_c24=&count[23:0];
wire[31:0] chunk={ (count [31:24] + ot_creq_c24),
                    (count [23:16] + ot_creq_c16),
                    (count [15:8] + ot_creq_c8),
                    (count [7:0] + 8'd1) };
wire[31:0] next=inc?chunk:count;
wire next_c8=inc ? (count [7:0] == 8'hfe) : ot_creq_c8;
wire next_c16=inc ? (count [15:0] == 16'hfffe) : ot_creq_c16;
wire next_c24=inc ? (count [23:0] == 24'hfffffe) : ot_creq_c24;
assign bad=(next != count+inc) | (next_c8 != (&next[7:0])) | (next_c16 != (&next[15:0])) | (next_c24 != (&next[23:0]));
endmodule
