`timescale 1ns/1ps
// Initialization-only consumer of the ACTUAL target-aware authenticated HOST
// loader replay. Configurations are installed once after reset, targets1..9,
// then the ISA target0. No input from received data controls normal token issue.
// All HBM-facing cfg outputs here are CORE-domain source pins: they MUST pass
// actual boot CDC queues before reaching their independent HBM clock entries.
// sink_applied is the actual terminal application acknowledgement from those
// queues (including seal acceptance age), never a compiler prediction.
module qkd_static_kv_boot_dispatch #(parameter integer MUT=0)(
 input wire ck,rst_n,input wire[142:0]boot_pr,input wire[3:0]boot_image_target,
 input wire boot_image_ready,boot_image_fault,input wire[15:0]boot_image_epoch,
 input wire[63:0]boot_image_digest,input wire execution_active,
 input wire[159:0]sink_applied,input wire[2:0]local_configured,input wire sink_fault,
 output reg layer_we,output reg[8:0]layer_addr,output reg[63:0]layer_data,
 output reg writer_we,output reg[7:0]writer_addr,output reg[63:0]writer_data,
 output reg ownership_we,output reg[1:0]ownership_addr,output reg[31:0]ownership_data,
 output reg[31:0]landing_we,front_we,output reg[7:0]group_addr,output reg[63:0]group_data,
 output reg[127:0]controller_we,output reg[4:0]controller_addr,output reg[63:0]controller_data,
 output reg[127:0]controller_last,
 output wire setup_ready,output reg fault,output reg[7:0]fault_code,
 output reg[15:0]installed_epoch,output reg[63:0]installed_isa_digest
);
 reg[3:0]expected_target;reg[10:0]next_word;reg ready_q;reg isa_seen;
 reg[8:0]installed;reg have_epoch;
 wire[9:0]addr=boot_pr[73:64];wire[63:0]data=boot_pr[63:0];
 function automatic[10:0]word_count(input[3:0]t);
 case(t)1:word_count=327;2:word_count=181;3:word_count=4;4,5:word_count=192;
 6,7,8,9:word_count=1024;default:word_count=0;endcase
 endfunction
 // Registered HOST output is consumed one edge later by the real cfg inputs.
 // Final ISA readiness remains tied to the actual loader, so a new BEGIN drops
 // setup_ready immediately even after the first successful setup.
 assign setup_ready=(&installed)&&((MUT==3)||(&sink_applied))&&(&local_configured)&&isa_seen&&boot_image_ready&&boot_image_target==0&&!boot_image_fault&&!sink_fault&&!fault;
 integer group_index,pc_index;
 always @(posedge ck or negedge rst_n)begin
 if(!rst_n)begin
  expected_target<=1;next_word<=0;ready_q<=0;isa_seen<=0;installed<=0;have_epoch<=0;
  installed_epoch<=0;installed_isa_digest<=0;fault<=0;fault_code<=0;
  layer_we<=0;writer_we<=0;ownership_we<=0;landing_we<=0;front_we<=0;controller_we<=0;controller_last<=0;
  layer_addr<=0;layer_data<=0;writer_addr<=0;writer_data<=0;ownership_addr<=0;ownership_data<=0;
  group_addr<=0;group_data<=0;controller_addr<=0;controller_data<=0;
 end else begin
  ready_q<=boot_image_ready;
  layer_we<=0;writer_we<=0;ownership_we<=0;landing_we<=0;front_we<=0;controller_we<=0;controller_last<=0;
  if(boot_image_fault||sink_fault)begin fault<=1;fault_code[0]<=1;end
  if((boot_pr[74]||boot_pr[142])&&execution_active)begin fault<=1;fault_code[1]<=1;end
  if(boot_pr[142]&&boot_image_target!=0)begin fault<=1;fault_code[2]<=1;end
  if(boot_pr[74]&&boot_image_target!=0&&!fault&&!execution_active)begin
   if((MUT!=1&&boot_image_target!=expected_target)||boot_image_target>9||{1'b0,addr}!=next_word||next_word>=word_count(boot_image_target))begin
    fault<=1;fault_code[3]<=1;
   end else if(have_epoch&&boot_image_epoch!=installed_epoch)begin fault<=1;fault_code[4]<=1;end
   else begin
    if(!have_epoch)begin have_epoch<=1;installed_epoch<=boot_image_epoch;end
    next_word<=next_word+1'b1;
    case(boot_image_target)
    1:begin layer_we<=1;layer_addr<=addr[8:0];layer_data<=data;end
    2:begin writer_we<=1;writer_addr<=addr[7:0];writer_data<=data;end
    3:begin
      if(data[63:32]!=0)begin fault<=1;fault_code[5]<=1;end
      else begin ownership_we<=1;ownership_addr<=addr[1:0];ownership_data<=data[31:0];end
    end
    4,5:begin
      group_index=int'(addr)/6;
      if(boot_image_target==4)landing_we<=32'b1<<group_index;
      else front_we<=32'b1<<group_index;
      group_addr<=8'(int'(addr)%6);group_data<=data;
    end
    6,7,8,9:begin
      pc_index=32*(int'(boot_image_target)-6)+int'(addr[9:5]);
      if(MUT==2)pc_index=pc_index^1;
      controller_we<=128'b1<<pc_index;controller_addr<=addr[4:0];controller_data<=data;
      if(addr[4:0]==31)controller_last<=128'b1<<pc_index;
    end
    default:begin fault<=1;fault_code[3]<=1;end
    endcase
   end
  end
  if(boot_image_ready&&!ready_q&&!fault)begin
   if(boot_image_target==0)begin
    if(expected_target!=0||!have_epoch||boot_image_epoch!=installed_epoch)begin fault<=1;fault_code[6]<=1;end
    else begin isa_seen<=1;installed_isa_digest<=boot_image_digest;end
   end else if(boot_image_target!=expected_target||next_word!=word_count(boot_image_target))begin fault<=1;fault_code[7]<=1;end
   else begin installed[boot_image_target-1'b1]<=1;expected_target<=(boot_image_target==9)?4'd0:expected_target+1'b1;next_word<=0;end
  end
 end
 end
endmodule
