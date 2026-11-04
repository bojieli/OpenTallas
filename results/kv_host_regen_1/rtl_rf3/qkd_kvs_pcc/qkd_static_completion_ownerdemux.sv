`timescale 1ns/1ps
// Observation-only ordered ledger: never gates or reschedules a command.
// launch_* names the command on the actual controller es output in this domain.
// completion_* must be the real controller's JEDEC retirement observer, not er259.
module qkd_static_completion_ownerdemux #(parameter integer MUT=0)(
 input wire ck,rst_n,launch_v,launch_boot,launch_we,
 input wire completion_v,completion_we,
 output reg normal_completion_v,boot_completion_v,
 output reg normal_completion_we,boot_completion_we,
 output reg fault,output wire empty);
 reg[63:0]owner,wr;reg[5:0]wp,rp;reg[6:0]count;
 assign empty=count==0;
 wire retire=completion_v&&count!=0&&completion_we==wr[rp]&&!fault;
 always @(posedge ck or negedge rst_n)begin
  if(!rst_n)begin wp<=0;rp<=0;count<=0;owner<=0;wr<=0;normal_completion_v<=0;boot_completion_v<=0;normal_completion_we<=0;boot_completion_we<=0;fault<=0;end
  else begin
   normal_completion_v<=0;boot_completion_v<=0;
   if(launch_v)begin
    if(count==64&&!retire)fault<=1;
    else begin owner[wp]<=launch_boot;wr[wp]<=launch_we;wp<=wp+1'b1;end
   end
   if(completion_v)begin
    if(!retire)fault<=1;
    else begin
     rp<=rp+1'b1;
     normal_completion_v<=MUT==1?owner[rp]:!owner[rp];
     boot_completion_v<=owner[rp];
     normal_completion_we<=completion_we;boot_completion_we<=completion_we;
    end
   end
   case({launch_v&&(count<64||retire),retire})
    2'b10:count<=count+1'b1;2'b01:count<=count-1'b1;default:;
   endcase
  end
 end
endmodule
