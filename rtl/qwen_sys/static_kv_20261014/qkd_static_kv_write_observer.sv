`timescale 1ns/1fs
// Physical write observation, never an admission/ready/ACK gate. Context and
// payload originate in the actual producer descriptor and stay in the SAME
// CDC/SROW entry. Full masks are checked at core intake; raw PHY has no mask
// pins and writes a complete 288-bit ECC word. A write observation occurs at
// physical CMD+5; any fault propagates before actual completion at CMD+17.
module qkd_static_kv_write_observer #(parameter integer STRICT=1, WL=5)(
 input wire hclk,rst_n,input wire [327:0] po,input wire static_column,
 input wire expected_static_column,input wire [346:0] context_word,
 output reg commit_valid,output reg [60:0] commit_identity,
 output reg [28:0] commit_address,output reg fault
);
 reg [18:0] open_row[0:31];
 reg [31:0] opened;
 wire command=po[28]&&static_column;
 wire native_write=command&&context_word[346]&&po[29];
 wire [28:0] actual_address={open_row[po[34:30]],po[34:30],po[39:35]};
 initial if(WL<2)$fatal(1,"write observer requires WL>=2");
 reg [WL-1:0] valid;
 reg [346:0] payload[0:WL-1];
 reg [287:0] encoded;
 function automatic [71:0] encode64(input [63:0] d);
  reg [71:0] c;integer j;begin
   c=0;j=0;for(integer p=1;p<=71;p=p+1)if((p&(p-1))!=0)begin c[p-1]=d[j];j=j+1;end
   for(integer k=0;k<7;k=k+1)for(integer p=1;p<=71;p=p+1)if((p&(1<<k))!=0)c[(1<<k)-1]=c[(1<<k)-1]^c[p-1];
   c[71]=^c[70:0];encode64=c;
  end
 endfunction
 function automatic [287:0] encode256(input [255:0] d);
  for(integer w=0;w<4;w=w+1)encode256[w*72+:72]=encode64(d[w*64+:64]);
 endfunction
 always @(posedge hclk)begin
  if(po[0]&&po[3:1]==3'd1)open_row[po[8:4]]<=po[27:9];
  payload[0]<=context_word;
  for(integer i=1;i<WL;i=i+1)payload[i]<=payload[i-1];
  encoded<=encode256(payload[WL-2][255:0]);
  commit_identity<=payload[WL-1][345:285];commit_address<=payload[WL-1][284:256];
 end
 always @(posedge hclk or negedge rst_n)
  if(!rst_n)begin opened<=0;valid<=0;commit_valid<=0;fault<=0;end
  else begin
   valid<={valid[WL-2:0],native_write};commit_valid<=valid[WL-1];
   if(po[0])case(po[3:1])
    3'd1:opened[po[8:4]]<=1;
    3'd0:opened[po[8:4]]<=0;
    3'd5:opened<=0;
    default:;
   endcase
   if(STRICT!=0&&command!=expected_static_column)fault<=1;
   if(command&&context_word[346]&&(!po[29]||!opened[po[34:30]]||actual_address!=context_word[284:256]))fault<=1;
   if(valid[WL-1]&&po[327:40]!=encoded)fault<=1;
  end
endmodule
