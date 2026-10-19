// Standalone opt-in source experiment. No production top or defaults changed.
// ID changes elaboration identity, not arithmetic. keep_hierarchy is the existing
// canonical source contract; no transparent distribution modules are used.
(* keep_hierarchy *) module hidx_c1_compact #(parameter integer ID=0,MUT=0)(
 input wire clk,input wire[7:0] lane_v,input wire[31:0]payload,
 output reg[31:0] y);
 (* keep *) reg[7:0]mask;
 (* keep *) reg[31:0]pay;
 always @(posedge clk) begin mask<=lane_v;pay<=payload;end
 // Balanced population counts, including each lane's exclusive prefix.
 function automatic[3:0] pc8(input[7:0]x);
 reg[1:0]a,b,c,d;reg[2:0]ab,cd;
 begin a={1'b0,x[0]}+x[1];b={1'b0,x[2]}+x[3];
 c={1'b0,x[4]}+x[5];d={1'b0,x[6]}+x[7];ab={1'b0,a}+b;cd={1'b0,c}+d;pc8={1'b0,ab}+cd;end
 endfunction
 integer k,s,j;reg[3:0]pref;reg[3:0]v;
 always @* begin
  y=0;
  for(s=0;s<8;s=s+1) begin
   v=0;
   for(k=0;k<8;k=k+1) begin
    pref=pc8(mask & ((8'd1<<k)-1));
    if(MUT==1)pref=pc8(mask & ((8'd1<<(k+1))-1));
    if(mask[k] && pref==s) begin
     if(MUT==2)v=v|pay[(7-k)*4+:4];
     else if(MUT==3)v=v|pay[k*4+:4]|pay[((k+1)%8)*4+:4];
     else if(!(MUT==4 && ID==8))v=v|pay[k*4+:4];
    end
   end
   y[s*4+:4]=v;
  end
 end
endmodule

(* keep_hierarchy *) module hidx_c1_count #(parameter integer ID=0,N=8,W=4,MUT=0)(
 input wire clk,input wire[N-1:0]lane_v,
 output wire[24*W-1:0]selects);
 (* keep *) reg[N-1:0]mask;
 (* keep *) reg[24*W-1:0]sel;
 always @(posedge clk)mask<=lane_v;
 function automatic[3:0]pc8(input[7:0]x);
 reg[1:0]a,b,c,d;reg[2:0]ab,cd;
 begin a={1'b0,x[0]}+x[1];b={1'b0,x[2]}+x[3];c={1'b0,x[4]}+x[5];d={1'b0,x[6]}+x[7];ab={1'b0,a}+b;cd={1'b0,c}+d;pc8={1'b0,ab}+cd;end
 endfunction
 wire[W-1:0]count;
 generate if(N==8)assign count=pc8(mask);else assign count={1'b0,pc8(mask[7:0])}+{1'b0,pc8(mask[15:8])};endgenerate
 integer c;
 always @(posedge clk)for(c=0;c<24;c=c+1)sel[c*W+:W]<=count ^ ((MUT==5 && ID==0 && c==23)?1:0);
 assign selects=sel;
endmodule

module hidx_coupon1 #(parameter integer ENABLE=0,MUT=0)(
 input wire clk,input wire[15:0]lane_v,input wire[287:0]payload,
 output wire[287:0]compacted,
 output wire[6*24*4-1:0]pair_select,
 output wire[12*24*5-1:0]quad_select);
 generate if(ENABLE)begin:on
  for(genvar z=0;z<9;z=z+1)begin:slice
   wire[31:0]p;wire[31:0]y;
   for(genvar k=0;k<8;k=k+1)begin:lane
    assign p[k*4+:4]=payload[k*36+z*4+:4];
    assign compacted[k*36+z*4+:4]=y[k*4+:4];
   end
   hidx_c1_compact #(.ID(z),.MUT(MUT)) own(.clk(clk),.lane_v(lane_v[7:0]),.payload(p),.y(y));
  end
  for(genvar z=0;z<6;z=z+1)begin:pair
   hidx_c1_count #(.ID(z),.N(8),.W(4),.MUT(MUT)) own(.clk(clk),.lane_v(lane_v[7:0]),.selects(pair_select[z*96+:96]));
  end
  for(genvar z=0;z<12;z=z+1)begin:quad
   hidx_c1_count #(.ID(6+z),.N(16),.W(5),.MUT(MUT)) own(.clk(clk),.lane_v(lane_v),.selects(quad_select[z*120+:120]));
  end
 end else begin:off
  assign compacted=0;assign pair_select=0;assign quad_select=0;
 end endgenerate
endmodule
