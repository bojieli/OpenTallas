module gold(input has,input [31:0] q,input [31:0] cnt,output y);
 function automatic f_take(input has,input [31:0] qv,input [31:0] cnt);
  reg [31:0] b,c,sv,kv;reg [32:0] t;
  begin
   b=~cnt;
`ifdef OT_COLL_ISS8_MUT_RELOAD
   c=32'd1;
`else
   c=32'd2;
`endif
   sv=qv ^ b ^ c;kv=(qv & b) | (qv & c) | (b & c);
   t={1'b0,sv}+{1'b0,kv[30:0],1'b0};
   f_take=has && !(kv[31] || t[32]);
  end
 endfunction
 assign y=f_take(has,q,cnt);
endmodule
module gate(input has,input [31:0] q,input [31:0] cnt,output y);
 function automatic [64:0] f_cs(input has,input [31:0] qv,input [31:0] cnt);
  reg [31:0] b,c,sv,kv;
  begin
   b=~cnt;
`ifdef OT_COLL_ISS8_MUT_RELOAD
   c=32'd1;
`else
   c=32'd2;
`endif
   sv=qv ^ b ^ c;kv=(qv & b) | (qv & c) | (b & c);
   f_cs={has && !kv[31],sv,kv[30:0],1'b0};
  end
 endfunction
 function automatic f_fin(input [64:0] w);
  reg [32:0] t;
  begin
   t={1'b0,w[63:32]}+{1'b0,w[31:0]};
   f_fin=w[64] && !t[32];
  end
 endfunction
 wire [64:0] w=f_cs(has,q,cnt);
 reg [64:0] w_q; // the split registers w; combinational equality of the two halves is what is checked here
 assign y=f_fin(w);
endmodule
