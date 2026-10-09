`timescale 1ps/1fs
`default_nettype none
// One real depth128 bank, eight SECDED72 words in THREE actual256-bit seats.
// Held input -> encoded register -> macro; macro -> capture -> syndrome -> correction.
module ot_hbm_candidate_sram_bank #(parameter integer ENABLE=0)(
 input wire clk,por_n,req_v,output wire req_r,input wire req_write,
 input wire[6:0] req_address,input wire[511:0] req_data,
 output wire rsp_v,input wire rsp_r,output wire[511:0] rsp_data,
 output wire rsp_write,rsp_ce,rsp_poison,output wire fault
);
 import ot_gpu_w6_secded_pkg::*;
 import ot_hbm_accel_r5a_ecc_pkg::*;
 reg[3:0] st;reg failed,writing;reg[6:0] address;
 reg[511:0] wd,answer;reg[575:0] encoded,captured;
 reg[63:0] syndromes;reg ce,poison;reg[127:0] valid;
 wire codes_ok=st<=5;
 wire[767:0] rd;
 wire[767:0] packed_word={192'b0,encoded};
 for(genvar m=0;m<3;m=m+1)begin:g_macro
 ot_sram_1r1w_128x256_m1_r2c2 u_sram(.clk(clk),
 .r_ce_in(ENABLE&&st==1&&!writing&&codes_ok),.r_addr_in(address),.rd_out(rd[256*m+:256]),
 .w_ce_in(ENABLE&&st==2&&writing&&codes_ok),.w_addr_in(address),.wd_in(packed_word[256*m+:256]),
 .w_mask_in({256{1'b1}}),.rr_en(2'b0),.rr_addr(14'b0),.cr_en(2'b0),.cr_sel(16'b0));
 end
 assign req_r=ENABLE&&st==0&&codes_ok&&!failed;
 assign rsp_v=ENABLE&&st==5&&codes_ok;
 assign rsp_data=answer;assign rsp_write=writing;assign rsp_ce=ce;assign rsp_poison=poison;
 assign fault=ENABLE&&(!codes_ok||failed);
 reg[511:0] corrected;reg any_ce,any_ue;reg[65:0] dec;
 always @*begin
 corrected=0;any_ce=0;any_ue=0;dec=0;
 for(integer k=0;k<8;k=k+1)begin
 dec=finish64(captured[72*k+:72],syndromes[8*k+:8]);
 corrected[64*k+:64]=dec[63:0];any_ce=any_ce|dec[64];any_ue=any_ue|dec[65];
 end
 end
 always @(posedge clk or negedge por_n)begin
 if(!por_n)begin st<=0;failed<=0;writing<=0;address<=0;wd<=0;answer<=0;
 encoded<=0;captured<=0;syndromes<=0;ce<=0;poison<=0;valid<=0;end
 else if(ENABLE)begin
 if(!codes_ok)failed<=1;
 else case(st)
 0:if(req_v&&req_r)begin writing<=req_write;address<=req_address;wd<=req_data;ce<=0;poison<=0;st<=1;end
 1:begin
 if(writing)for(integer k=0;k<8;k=k+1)encoded[72*k+:72]<=encode64(wd[64*k+:64]);
 st<=2;
 end
 2:begin
 if(writing)begin valid[address]<=1;answer<=wd;st<=5;end
 else begin captured<=rd[575:0];poison<=!valid[address];st<=3;end
 end
 3:begin for(integer k=0;k<8;k=k+1)syndromes[8*k+:8]<=syndrome64(captured[72*k+:72]);st<=4;end
 4:begin ce<=any_ce;poison<=poison||any_ue;answer<=(poison||any_ue)?512'd0:corrected;
 if(poison||any_ue)failed<=1;st<=5;end
 5:if(rsp_r)begin st<=0;end
 default:failed<=1;
 endcase
 end
 end
endmodule
`default_nettype wire
