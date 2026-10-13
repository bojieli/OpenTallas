`timescale 1ns/1ps
`default_nettype none
// Four-word mutable-SRAM SECDED checker. CAPTURE computes syndrome;
// CHECK repairs locally and registers one verdict. LOAD may reduce bank flags.
// Data registers have no reset. Scalar mode captures every cycle with pipeline
// validity; regional mode uses kept local enables. CHECK consumes the preceding CAPTURE.
module vm_ck4 #(parameter integer LOCAL_REGIONS=0)(input wire ck, input wire rst_n,
 input wire capture_i, check_i, write_i,
 input wire [7:0] capture_regions_i,check_regions_i,
 input wire [287:0] sample_i, expected_i,
 input wire [255:0] owner_mask_i, padding_mask_i,
 output reg error_o, output reg valid_o,
 output reg [287:0] repaired_o);
 function [7:0] syndrome(input [71:0] code);
  reg [6:0] s; integer p,j;
  begin
   s=0;
   for(p=0;p<7;p=p+1)for(j=1;j<=71;j=j+1)
    if((j&(1<<p))!=0)s[p]=s[p]^code[j-1];
   syndrome={^code,s};
  end
 endfunction
 function [71:0] repair(input [71:0] code,input [7:0] syn);
  begin
   repair=code;
   if(syn[7]&&syn[6:0]!=0&&syn[6:0]<=71)
    repair=code^(72'd1<<(syn[6:0]-1));
   else if(syn[7]&&syn[6:0]==0)repair[71]=~code[71];
  end
 endfunction
 function ue(input [7:0] syn);
  begin ue=(syn[6:0]!=0)&&(!syn[7]||syn[6:0]>71);end
 endfunction
 function [63:0] payload(input [71:0] code);
  integer j,k;
  begin
   payload=0;k=0;
   for(j=1;j<=71;j=j+1)
    if(j!=1&&j!=2&&j!=4&&j!=8&&j!=16&&j!=32&&j!=64)begin
     payload[k]=code[j-1];k=k+1;
    end
  end
 endfunction
 reg [287:0] sample_q,expected_q;
 reg [31:0] sample_syn_q,expected_syn_q;
 reg [255:0] owner_mask_q,padding_mask_q;
 reg write_q,cap_valid;
 wire [287:0] repaired;
 wire [255:0] sample_data,expected_data;
 wire [3:0] sample_ue,expected_ue;
 for(genvar k=0;k<4;k=k+1)begin:words
  assign repaired[k*72+:72]=repair(sample_q[k*72+:72],sample_syn_q[k*8+:8]);
  assign sample_data[k*64+:64]=payload(repaired[k*72+:72]);
  assign expected_data[k*64+:64]=payload(repair(expected_q[k*72+:72],expected_syn_q[k*8+:8]));
  assign sample_ue[k]=ue(sample_syn_q[k*8+:8]);
  assign expected_ue[k]=ue(expected_syn_q[k*8+:8]);
 end
 always @(posedge ck)begin
  owner_mask_q<=owner_mask_i;padding_mask_q<=padding_mask_i;write_q<=write_i;
  for(integer h=0;h<8;h=h+1)begin
   if(!LOCAL_REGIONS||capture_regions_i[h])begin
    sample_q[h*36+:36]<=sample_i[h*36+:36];expected_q[h*36+:36]<=expected_i[h*36+:36];
   end
   if(!LOCAL_REGIONS||(check_regions_i[h]&&cap_valid))repaired_o[h*36+:36]<=repaired[h*36+:36];
  end
  for(integer k=0;k<4;k=k+1)begin
   if(!LOCAL_REGIONS||capture_regions_i[k*2])begin
    sample_syn_q[k*8+:8]<=syndrome(sample_i[k*72+:72]);
    expected_syn_q[k*8+:8]<=syndrome(expected_i[k*72+:72]);
   end
  end
 end
 always @(posedge ck or negedge rst_n)begin
  if(!rst_n)begin cap_valid<=0;error_o<=0;valid_o<=0;end
  else begin
   cap_valid<=capture_i;valid_o<=check_i&&cap_valid;
   if(check_i)begin
    valid_o<=cap_valid;
`ifdef MUT_CK_IGNORE
    error_o<=0;
`else
    error_o<=!cap_valid || (|sample_ue) || (|expected_ue) || (|(sample_data&padding_mask_q))
      || (|((sample_data^expected_data)&(write_q?256'hffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff:owner_mask_q)));
`endif
   end
  end
 end
endmodule
`default_nettype wire
