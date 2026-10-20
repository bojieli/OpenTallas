`timescale 1ns/1ps
// Existing-edge control distribution. SAFE_DIST=0 is the qualified legacy.
// SAFE_DIST=1 is a candidate only: native all-driver census is required before
// physical adoption. LAT7 DRST0 uses independently kept 4-bit consumers at
// every original pipeline cut; other configurations retain legacy behavior.
module ot_hdc_fp32_add_lat_fan32 #(
 parameter integer LAT=3,CUTS=-1,DRST=1,SAFE_DIST=0,SLICE_W=4
)(input wire clk,rst_n,valid_in,input wire[31:0]a,b,
 output wire[31:0]y,output wire[1:0]err,output wire valid_out);
 generate if(SAFE_DIST!=0 && LAT==7 && DRST==0 && (CUTS==-1 || CUTS==15)) begin:g_dist
  wire[119:0] a1;
  wire[97:0] a2;
  wire[101:0] b1;
  wire[107:0] b2a;
  wire[72:0] b2b;
  wire[70:0] c1;
  wire[34:0] c2,out;
  ot_hdc_fan32_decode u_decode(.a(a),.b(b),.v(valid_in),.q(a1));
  ot_hdc_fan32_stage #(.STAGE(1),.WI(120),.WO(98),.VB(118),.SW(SLICE_W)) u_a2(.clk(clk),.rst_n(rst_n),.d(a1),.q(a2));
  ot_hdc_fan32_stage #(.STAGE(2),.WI(98),.WO(102),.VB(97),.SW(SLICE_W)) u_b1(.clk(clk),.rst_n(rst_n),.d(a2),.q(b1));
  ot_hdc_fan32_stage #(.STAGE(3),.WI(102),.WO(108),.VB(101),.SW(SLICE_W)) u_b2a(.clk(clk),.rst_n(rst_n),.d(b1),.q(b2a));
  ot_hdc_fan32_stage #(.STAGE(4),.WI(108),.WO(73),.VB(107),.SW(SLICE_W)) u_b2b(.clk(clk),.rst_n(rst_n),.d(b2a),.q(b2b));
  ot_hdc_fan32_stage #(.STAGE(5),.WI(73),.WO(71),.VB(72),.SW(SLICE_W)) u_c1(.clk(clk),.rst_n(rst_n),.d(b2b),.q(c1));
  ot_hdc_fan32_stage #(.STAGE(6),.WI(71),.WO(35),.VB(70),.SW(SLICE_W)) u_c2(.clk(clk),.rst_n(rst_n),.d(c1),.q(c2));
  ot_hdc_fan32_stage #(.STAGE(7),.WI(35),.WO(35),.VB(0),.SW(SLICE_W)) u_out(.clk(clk),.rst_n(rst_n),.d(c2),.q(out));
  assign {y,err,valid_out}=out;
 end else begin:g_legacy
  ot_hdc_fp32_add_lat #(.LAT(LAT),.CUTS(CUTS),.DRST(DRST)) u(.*);
 end endgenerate
endmodule

module ot_hdc_fan32_decode(input wire[31:0]a,b,input wire v,output wire[119:0]q);
 wire[7:0] af=a[30:23],bf=b[30:23];
 wire[7:0] ae=(af==0)?8'd1:af,be=(bf==0)?8'd1:bf;
 wire[23:0] am={(af!=0),a[22:0]},bm={(bf!=0),b[22:0]};
 wire nf=(af==255)||(bf==255),az=(a[30:0]==0),bz=(b[30:0]==0);
 wire[31:0] code=nf?32'd0:(az?(bz?32'd0:b):a);
 assign q={(a[30:0]<b[30:0]),v,(nf||az||bz),(nf?2'd1:2'd0),code,(a[31]^b[31]),a[31],b[31],ae,be,am,bm,(ae-be),(be-ae)};
endmodule

module ot_hdc_fan32_stage #(parameter integer STAGE=1,WI=120,WO=98,VB=118,SW=4)
(input wire clk,rst_n,input wire[WI-1:0]d,output wire[WO-1:0]q);
 genvar i;
 generate for(i=0;i<(WO+SW-1)/SW;i=i+1) begin:g_part
  localparam integer N=(WO-i*SW<SW)?WO-i*SW:SW;
  (* keep_hierarchy=1 *) ot_hdc_fan32_part #(.STAGE(STAGE),.WI(WI),.WO(WO),.VB(VB),.BASE(i*SW),.W(N)) u(.clk(clk),.rst_n(rst_n),.d(d),.q(q[i*SW+:N]));
 end endgenerate
endmodule

(* keep_hierarchy=1 *) module ot_hdc_fan32_part #(
 parameter integer STAGE=1,WI=120,WO=98,VB=118,BASE=0,W=4
)(input wire clk,rst_n,input wire[WI-1:0]d,output wire[W-1:0]q);
 reg[WI-1:0] rd;
 reg rv;
 wire[WI-1:0] x;
 always @(posedge clk) rd<=d;
 always @(posedge clk or negedge rst_n) if(!rst_n)rv<=0;else rv<=d[VB];
 genvar k;
 generate for(k=0;k<WI;k=k+1)begin:g_bit
  assign x[k]=(k==VB)?rv:rd[k];
 end endgenerate
 function automatic[27:0] jam28(input[23:0]m,input[7:0]n);
  reg[27:0]z,lost;
  begin z={1'b0,m,3'b000};if(n>=28)jam28={27'd0,|z};else begin lost=z&~({28{1'b1}}<<n[4:0]);jam28=(z>>n[4:0])|{27'd0,|lost};end end
 endfunction
 function automatic[5:0] lzc(input[31:0]z);
  integer j;reg found;
  begin lzc=32;found=0;for(j=31;j>=0;j=j-1)if(z[j]&&!found)begin lzc=31-j;found=1;end end
 endfunction
 function automatic[97:0] fa2(input[119:0]z);
  reg sw,v,byp,sub,as_,bs_;reg[1:0]e;reg[31:0]code;
  reg[7:0]ae,be,da,db;reg[23:0]am,bm;reg[27:0]sa,sb;
  begin {sw,v,byp,e,code,sub,as_,bs_,ae,be,am,bm,da,db}=z;
   sa=jam28(am,db);sb=jam28(bm,da);
   fa2={v,byp,sub,(sw?bs_:as_),e,code,(sw?be:ae),(sw?bm:am),(sw?sa:sb)};
  end
 endfunction
 function automatic[101:0] fb1(input[97:0]z);
  reg v,byp,sub,sign_;reg[1:0]e;reg[31:0]code;reg[7:0]exp_;reg[23:0]big_;reg[27:0]small_,b,s,dif_;
  begin {v,byp,sub,sign_,e,code,exp_,big_,small_}=z;b={1'b0,big_,3'b000};s=b+small_;dif_=b-small_;
   fb1={v,byp,sub,sign_,e,code,exp_,s,dif_};
  end
 endfunction
 function automatic[107:0] fb2a(input[101:0]z);
  reg v,byp,sub,sign_,carry_;reg[1:0]e;reg[31:0]code;reg[7:0]exp_,room;reg[27:0]s,dif_;reg[26:0]av,sent;reg[5:0]lz_;
  begin {v,byp,sub,sign_,e,code,exp_,s,dif_}=z;carry_=s[27];av=carry_?{s[27:2],s[1]|s[0]}:s[26:0];room=exp_-8'd1;
   sent=(room<=26)?(27'd1<<(5'd26-room[4:0])):27'd0;lz_=lzc({dif_[26:0]|sent,5'b11111});
   fb2a={v,byp,sub,sign_,e,code,exp_,av,dif_,lz_,carry_};
  end
 endfunction
 function automatic[72:0] fb2b(input[107:0]z);
  reg v,byp,sub,sign_,carry_;reg[1:0]e;reg[31:0]code;reg[7:0]exp_,es,ea;reg[26:0]av,sv;reg[27:0]dif_;reg[5:0]lz_;
  begin {v,byp,sub,sign_,e,code,exp_,av,dif_,lz_,carry_}=z;sv=dif_[26:0]<<lz_[4:0];es=exp_-{3'd0,lz_[4:0]};ea=exp_+carry_;
   fb2b={v,byp,sign_,(sub&&(dif_==0)),e,code,(sub?es:ea),(sub?sv:av)};
  end
 endfunction
 function automatic[70:0] fc1(input[72:0]z);
  reg v,byp,sign_,zero_;reg[1:0]e;reg[31:0]code;reg[7:0]exp_;reg[26:0]val;reg inc;reg[24:0]r;
  begin {v,byp,sign_,zero_,e,code,exp_,val}=z;inc=val[2]&&((|val[1:0])||val[3]);r={1'b0,val[26:3]}+inc;
   fc1={v,byp,zero_,sign_,e,code,exp_,r[23:0],r[24]};
  end
 endfunction
 function automatic[34:0] fc2(input[70:0]z);
  reg v,byp,zero_,sign_,rc,subn,over_;reg[1:0]err_;reg[31:0]bcode,code,y_;reg[7:0]exp_;reg[23:0]rnd,man;reg[8:0]e;
  begin {v,byp,zero_,sign_,err_,bcode,exp_,rnd,rc}=z;man=rc?{1'b1,rnd[23:1]}:rnd;e={1'b0,exp_}+rc;subn=(e==1)&&!man[23];code={sign_,(subn?8'd0:e[7:0]),man[22:0]};over_=(exp_==255)||(e>=255);
   if(byp) y_=bcode;
   else if(zero_)begin y_=0;err_=0;end
   else if(over_)begin y_=0;err_=2;end
   else begin y_=(code[30:0]==0)?32'd0:code;err_=0;end
   fc2={y_,err_,v};
  end
 endfunction
 wire[WO-1:0] result;
 generate
  if(STAGE==1)assign result=fa2(x);
  else if(STAGE==2)assign result=fb1(x);
  else if(STAGE==3)assign result=fb2a(x);
  else if(STAGE==4)assign result=fb2b(x);
  else if(STAGE==5)assign result=fc1(x);
  else if(STAGE==6)assign result=fc2(x);
  else assign result=x;
 endgenerate
 assign q=result[BASE+:W];
endmodule
