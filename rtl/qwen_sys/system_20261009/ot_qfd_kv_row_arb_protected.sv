// Additive mutable-state-protected successor; original arbiter byte-identical.
`timescale 1ns/1ps
// Full32-PC minimum row mechanism. Head FIFO and independent-half ownership
// are upstream. Grants are sampled with the held head on the launch edge.
// Each281b slot: {col5,source5,loc7,isk,tail,sel2,tail_lanes4,data256}.
// Multiple slots for one tile share ONE merged-word credit, with equal-hop
// arrival and the original same-word/disjoint-quarter merge rule.
module ot_qfd_kv_row_arb_protected #(
 parameter integer ENABLE=0,STACK=0,ROW=0,DEPTH=8,MUT_V_ATOMIC=0
)(
 input wire clk,rst_n,input wire [6:0] rr,
 input wire [31:0] h_v,input wire [63:0] h_need,
 input wire [8191:0] h_data,
 input wire [351:0] h_tile0,h_tile1,
 input wire [223:0] h_loc0,h_loc1,
 input wire [63:0] h_sel0,h_sel1,
 input wire [31:0] h_isk,h_tail,input wire [127:0] h_tail_lanes,
 input wire [31:0] tile_credit_return,
 output wire [63:0] h_grant,
 output wire [2:0] row_v,output wire [842:0] row_data,
 output wire fault
);
 // Constant option-M physical binding. Each96block set fills eight column
 // groups x three row bands per quadrant; four-bit tile index is Morton.
 function automatic [11:0] place(input [10:0] tile);
  integer nb,k,q,slot,col,row;
  begin
   nb=tile>>4;k=tile&15;q=0;slot=0;
   if(nb<16)begin q=0;slot=nb;end
   else if(nb<32)begin q=1;slot=nb-16;end
   else if(nb<48)begin q=2;slot=nb-32;end
   else if(nb<64)begin q=3;slot=nb-48;end
   else if(nb<72)begin q=0;slot=16+nb-64;end
   else if(nb<80)begin q=1;slot=16+nb-72;end
   else if(nb<88)begin q=2;slot=16+nb-80;end
   else begin q=3;slot=16+nb-88;end
   col=(slot/3)*4+((k>>2)&1)*2+(k&1);
   row=(slot%3)*4+((k>>3)&1)*2+((k>>1)&1);
   place={1'(nb>=96),2'(q),4'(row),5'(col)};
  end
 endfunction
 (* keep *) reg [3:0] credits[0:31],credits1[0:31],credits2[0:31];
 (* keep *) reg [2:0] rv0,rv1,rv2;
 (* keep *) reg [842:0] rd0,rd1,rd2;
 (* keep *) reg f0,f1,f2;
 reg disagreement;
 always @*begin
  disagreement=(rv0!=rv1)||(rv0!=rv2)||(rd0!=rd1)||(rd0!=rd2)||(f0!=f1)||(f0!=f2);
  for(integer t=0;t<32;t=t+1)
   if(credits[t]!=credits1[t]||credits[t]!=credits2[t]||credits[t]>DEPTH)disagreement=1;
 end
 reg [63:0] grants;reg [31:0] reserved;
 reg [2:0] launch_v;reg [842:0] launch_data;
 reg [31:0] claimed;reg [6:0] word[0:31];reg [3:0] seen[0:31];
 integer i,j,p,half,start,n,col;reg [11:0] dst,other_dst;
 reg [10:0] tile;reg [6:0] loc;reg [1:0] sel;reg [3:0] quarter;
 reg [255:0] data;reg eligible,invalid;
 always @* begin
  grants=0;reserved=0;launch_v=0;launch_data=0;claimed=0;n=0;invalid=0;
  dst=0;other_dst=0;tile=0;loc=0;sel=0;quarter=0;data=0;eligible=0;col=0;p=0;half=0;
  for(j=0;j<32;j=j+1)begin word[j]=0;seen[j]=0;end
  start=(rr-STACK*32)&127;if(start>=32)start=0;
  for(i=0;i<32;i=i+1)begin
   p=(start+i)%32;
   for(half=0;half<2;half=half+1)begin
    tile=half?h_tile1[p*11+:11]:h_tile0[p*11+:11];dst=place(tile);col=dst[4:0];
    loc=half?h_loc1[p*7+:7]:h_loc0[p*7+:7];
    sel=half?h_sel1[p*2+:2]:h_sel0[p*2+:2];
    data=h_isk[p]?h_data[p*256+:256]:{128'd0,h_data[p*256+half*128+:128]};
    quarter=h_isk[p]?((h_tail[p]&&h_tail_lanes[p*4+:4]==0)?4'd0:(4'b0011<<sel)):(4'b0001<<sel);
    eligible=h_v[p]&&h_need[p*2+half]&&!dst[11]&&dst[10:9]==STACK&&dst[8:5]==ROW;
    if(h_v[p]&&h_need[p*2+half]&&(dst[11]||dst[10:9]!=STACK|| (h_isk[p]&&(half!=0||sel[0]))))invalid=1;
    other_dst=place(half?h_tile0[p*11+:11]:h_tile1[p*11+:11]);
    if(MUT_V_ATOMIC!=0&&h_need[p*2+:2]==2'b11&&other_dst[8:5]!=ROW)eligible=0;
    if(eligible)begin
     if(!claimed[col])begin claimed[col]=1;word[col]=loc;seen[col]=0;end
     if(word[col]==loc)begin
      if(n<3&&credits[col]!=0&&(seen[col]&quarter)==0)begin
       grants[p*2+half]=1;reserved[col]=1;launch_v[n]=1;
       launch_data[n*281+:281]={5'(col),5'(p),loc,h_isk[p],h_tail[p],sel,h_tail_lanes[p*4+:4],data};
       n=n+1;
      end
      // Earlier valid overlapping quarter blocks later requests even if that
      // earlier request itself could not join the word (golden merge rule).
      seen[col]=seen[col]|quarter;
     end
    end
   end
  end
 end
 reg credit_bad;integer c;
 always @*begin
  credit_bad=0;
  for(integer t=0;t<32;t=t+1)
   if(tile_credit_return[t]&&credits[t]==DEPTH&&!reserved[t])credit_bad=1;
 end
 wire safe=ENABLE&&!f0&&!disagreement&&!invalid&&!credit_bad;
 assign row_v=safe?rv0:3'd0;assign row_data=rd0;assign fault=f0||disagreement;
 assign h_grant=safe?grants:64'd0;
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin rv0<=0;rv1<=0;rv2<=0;rd0<=0;rd1<=0;rd2<=0;f0<=0;f1<=0;f2<=0;
   for(c=0;c<32;c=c+1)begin credits[c]<=DEPTH;credits1[c]<=DEPTH;credits2[c]<=DEPTH;endend
  else begin
   rv0<=safe?launch_v:3'd0;rv1<=safe?launch_v:3'd0;rv2<=safe?launch_v:3'd0;
   rd0<=launch_data;rd1<=launch_data;rd2<=launch_data;
   f0<=f0||(ENABLE&&(invalid||credit_bad||disagreement));
   f1<=f0||(ENABLE&&(invalid||credit_bad||disagreement));
   f2<=f0||(ENABLE&&(invalid||credit_bad||disagreement));
   for(c=0;c<32;c=c+1)if(safe)begin
    case({tile_credit_return[c],reserved[c]})
     2'b01:begin credits[c]<=credits[c]-1'b1;credits1[c]<=credits[c]-1'b1;credits2[c]<=credits[c]-1'b1;end
     2'b10:begin credits[c]<=credits[c]+1'b1;credits1[c]<=credits[c]+1'b1;credits2[c]<=credits[c]+1'b1;end
     default:begin credits[c]<=credits[c];credits1[c]<=credits[c];credits2[c]<=credits[c];end
    endcase
   end
  end
 end
endmodule
