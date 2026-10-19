`timescale 1ns/1ps
// Isolated selected contract, default off; no production wrapper instantiates it.
// Publication/profile/epoch/final-read predicates require actual source binding.
// Faults diagnose defects; no producer ready/permission or stall path exists.
module qfd_dv_held_user_xbase #(parameter integer ENABLE=0)(
 input wire ck,rst_n,publish,input wire[1:0]publish_user,legacy_user,
 input wire[15:0]publish_epoch,use_epoch,
 input wire profile_matches,all_copies_authenticated,
 input wire me_apply,xpf_apply,input wire[1:0]epoch_class,
 input wire[23:0]me_base,xpf_base,
 input wire retire_me,retire_xpf,me_final_read,xpf_final_use,
 output wire[23:0]me_address,xpf_address,
 output wire[1:0]me_user,xpf_user,output wire[15:0]held_epoch,
 output wire me_active,xpf_active,output reg fault
);
 reg[1:0]mu,xu;reg[15:0]epoch_r;reg ml,xl;
 reg[23:0]canonical;
 always@*case(epoch_class)
  2'd0,2'd2:canonical=24'd4096;
  2'd1:canonical=24'd16384;
  default:canonical=24'd32768;
 endcase
 assign me_user=ENABLE!=0?mu:legacy_user;
 assign xpf_user=ENABLE!=0?xu:legacy_user;
 assign held_epoch=ENABLE!=0?epoch_r:publish_epoch;
 assign me_active=ENABLE!=0?ml:1'b0;
 assign xpf_active=ENABLE!=0?xl:1'b0;
 wire me_ok=me_base==canonical,xpf_ok=xpf_base==canonical;
 assign me_address=ENABLE!=0&&me_apply&&me_ok?{me_base[23:18],mu,me_base[15:0]}:me_base;
 assign xpf_address=ENABLE!=0&&xpf_apply&&xpf_ok?{xpf_base[23:18],xu,xpf_base[15:0]}:xpf_base;
 always@(posedge ck or negedge rst_n)begin
  if(!rst_n)begin mu<=0;xu<=0;epoch_r<=0;ml<=0;xl<=0;fault<=0;end
  else if(ENABLE!=0)begin
   if((ml||xl)&&(!profile_matches||!all_copies_authenticated))fault<=1;
   if(publish)begin
    if(ml||xl||!profile_matches||!all_copies_authenticated)fault<=1;
    mu<=publish_user;xu<=publish_user;epoch_r<=publish_epoch;ml<=1;xl<=1;
   end
   if(me_apply&&(!ml||!me_ok||use_epoch!=epoch_r||!profile_matches||!all_copies_authenticated))fault<=1;
   if(xpf_apply&&(!xl||!xpf_ok||use_epoch!=epoch_r||!profile_matches||!all_copies_authenticated))fault<=1;
   if(retire_me)begin if(!ml||!me_final_read)fault<=1;ml<=0;end
   if(retire_xpf)begin if(!xl||!xpf_final_use)fault<=1;xl<=0;end
  end
 end
endmodule
