// Genuine arithmetic leaves; both outputs are useful. No identity delay cells.
(* keep_hierarchy *) module hidx_csa_fa #(parameter ID=0,MUT=0)(input a,b,c,output s,carry);
 assign s=a^b^c;
 assign carry=((a&b)|(a&c)|(b&c)) ^ ((MUT==6 && ID==0)?1'b1:1'b0);
endmodule
(* keep_hierarchy *) module hidx_csa_ha #(parameter ID=0)(input a,b,output s,carry);
 assign s=a^b;
 assign carry=a&b;
endmodule
(* keep_hierarchy *) module hidx_csa #(parameter ID=0,N=8,W=4,MUT=0)(input[N-1:0]x,output[W-1:0]y);
 generate
 if(N==8)begin:n8
 wire f0s,f0c; hidx_csa_fa #(.ID(ID*100+0),.MUT(MUT)) f0(.a(x[0]),.b(x[1]),.c(x[2]),.s(f0s),.carry(f0c));
 wire f1s,f1c; hidx_csa_fa #(.ID(ID*100+1),.MUT(MUT)) f1(.a(x[3]),.b(x[4]),.c(x[5]),.s(f1s),.carry(f1c));
 wire f2s,f2c; hidx_csa_fa #(.ID(ID*100+2),.MUT(MUT)) f2(.a(f0s),.b(f1s),.c(x[6]),.s(f2s),.carry(f2c));
 wire f3s,f3c; hidx_csa_fa #(.ID(ID*100+3),.MUT(MUT)) f3(.a(f2c),.b(f0c),.c(f1c),.s(f3s),.carry(f3c));
 wire h0s,h0c; hidx_csa_ha #(.ID(ID*100+0)) h0(.a(f2s),.b(x[7]),.s(h0s),.carry(h0c));
 assign y[0]=h0s;
 wire h1s,h1c; hidx_csa_ha #(.ID(ID*100+1)) h1(.a(f3s),.b(h0c),.s(h1s),.carry(h1c));
 assign y[1]=h1s;
 wire h2s,h2c; hidx_csa_ha #(.ID(ID*100+2)) h2(.a(f3c),.b(h1c),.s(h2s),.carry(h2c));
 assign y[2]=h2s;
 assign y[3]=h2c;
 end
 if(N==16)begin:n16
 wire f0s,f0c; hidx_csa_fa #(.ID(ID*100+0),.MUT(MUT)) f0(.a(x[0]),.b(x[1]),.c(x[2]),.s(f0s),.carry(f0c));
 wire f1s,f1c; hidx_csa_fa #(.ID(ID*100+1),.MUT(MUT)) f1(.a(x[3]),.b(x[4]),.c(x[5]),.s(f1s),.carry(f1c));
 wire f2s,f2c; hidx_csa_fa #(.ID(ID*100+2),.MUT(MUT)) f2(.a(x[6]),.b(x[7]),.c(x[8]),.s(f2s),.carry(f2c));
 wire f3s,f3c; hidx_csa_fa #(.ID(ID*100+3),.MUT(MUT)) f3(.a(x[9]),.b(x[10]),.c(x[11]),.s(f3s),.carry(f3c));
 wire f4s,f4c; hidx_csa_fa #(.ID(ID*100+4),.MUT(MUT)) f4(.a(x[12]),.b(x[13]),.c(x[14]),.s(f4s),.carry(f4c));
 wire f5s,f5c; hidx_csa_fa #(.ID(ID*100+5),.MUT(MUT)) f5(.a(f0s),.b(f1s),.c(f2s),.s(f5s),.carry(f5c));
 wire f6s,f6c; hidx_csa_fa #(.ID(ID*100+6),.MUT(MUT)) f6(.a(f3s),.b(f4s),.c(x[15]),.s(f6s),.carry(f6c));
 wire f7s,f7c; hidx_csa_fa #(.ID(ID*100+7),.MUT(MUT)) f7(.a(f0c),.b(f1c),.c(f2c),.s(f7s),.carry(f7c));
 wire f8s,f8c; hidx_csa_fa #(.ID(ID*100+8),.MUT(MUT)) f8(.a(f5c),.b(f6c),.c(f7s),.s(f8s),.carry(f8c));
 wire f9s,f9c; hidx_csa_fa #(.ID(ID*100+9),.MUT(MUT)) f9(.a(f8s),.b(f3c),.c(f4c),.s(f9s),.carry(f9c));
 wire f10s,f10c; hidx_csa_fa #(.ID(ID*100+10),.MUT(MUT)) f10(.a(f9c),.b(f8c),.c(f7c),.s(f10s),.carry(f10c));
 wire h0s,h0c; hidx_csa_ha #(.ID(ID*100+0)) h0(.a(f5s),.b(f6s),.s(h0s),.carry(h0c));
 assign y[0]=h0s;
 wire h1s,h1c; hidx_csa_ha #(.ID(ID*100+1)) h1(.a(f9s),.b(h0c),.s(h1s),.carry(h1c));
 assign y[1]=h1s;
 wire h2s,h2c; hidx_csa_ha #(.ID(ID*100+2)) h2(.a(f10s),.b(h1c),.s(h2s),.carry(h2c));
 assign y[2]=h2s;
 wire h3s,h3c; hidx_csa_ha #(.ID(ID*100+3)) h3(.a(f10c),.b(h2c),.s(h3s),.carry(h3c));
 assign y[3]=h3s;
 assign y[4]=h3c;
 end
 endgenerate
endmodule

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
 wire[W-1:0]count0,count1;
 hidx_csa #(.ID(ID*2),.N(N),.W(W),.MUT(MUT)) tree0(.x(mask),.y(count0));
 hidx_csa #(.ID(ID*2+1),.N(N),.W(W),.MUT(MUT)) tree1(.x(mask),.y(count1));
 integer c;
 always @(posedge clk)for(c=0;c<24;c=c+1)sel[c*W+:W]<=(c<12 ? count0 : count1) ^ ((MUT==5 && ID==0 && c==23)?1:0);
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
