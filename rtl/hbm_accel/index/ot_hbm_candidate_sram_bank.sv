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
 reg[3:0] st,st_n;reg failed,writing;reg[6:0] address;
 reg[511:0] wd,answer;reg[575:0] encoded,captured;
 reg[63:0] syndromes;reg ce,poison;reg[127:0] valid,valid_n;
reg[0:0] failed_n;
reg[0:0] writing_n;
reg[6:0] address_n;
reg[511:0] wd_n;
reg[511:0] answer_n;
reg[575:0] captured_n;
reg[63:0] syndromes_n;
reg[0:0] ce_n;
reg[0:0] poison_n;
 wire codes_ok=failed_n==~failed&&writing_n==~writing&&address_n==~address&&wd_n==~wd&&answer_n==~answer&&captured_n==~captured&&syndromes_n==~syndromes&&ce_n==~ce&&poison_n==~poison&&st_n==~st&&valid_n==~valid;
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
 if(!por_n)begin st<=0;st_n<=15;failed<=0;failed_n<=~(0);writing<=0;writing_n<=~(0);address<=0;address_n<=~(0);wd<=0;wd_n<=~(0);answer<=0;answer_n<=~(0);
 encoded<=0;captured<=0;captured_n<=~(0);syndromes<=0;syndromes_n<=~(0);ce<=0;ce_n<=~(0);poison<=0;poison_n<=~(0);valid<=0;valid_n<=~128'b0;end
 else if(ENABLE)begin
 if(!codes_ok)failed<=1;failed_n<=~(1);
 else case(st)
 0:if(req_v&&req_r)begin writing<=req_write;writing_n<=~(req_write);address<=req_address;address_n<=~(req_address);wd<=req_data;wd_n<=~(req_data);ce<=0;ce_n<=~(0);poison<=0;poison_n<=~(0);st<=1;st_n<=~4'd1;end
 1:begin
 if(writing)for(integer k=0;k<8;k=k+1)encoded[72*k+:72]<=encode64(wd[64*k+:64]);
 st<=2;st_n<=~4'd2;
 end
 2:begin
 if(writing)begin valid[address]<=1;valid_n[address]<=0;answer<=wd;answer_n<=~(wd);st<=5;st_n<=~4'd5;end
 else begin captured<=rd[575:0];captured_n<=~(rd[575:0]);poison<=!valid[address];poison_n<=~(!valid[address]);st<=3;st_n<=~4'd3;end
 end
 3:begin for(integer k=0;k<8;k=k+1)syndromes[8*k+:8]<=syndrome64(captured[72*k+:72]);syndromes_n[8*k+:8]<=~(syndrome64(captured[72*k+:72]));st<=4;st_n<=~4'd4;end
 4:begin ce<=any_ce;ce_n<=~(any_ce);poison<=poison||any_ue;poison_n<=~(poison||any_ue);answer<=(poison||any_ue)?512'd0:corrected;answer_n<=~((poison||any_ue)?512'd0:corrected);
 if(poison||any_ue)failed<=1;failed_n<=~(1);st<=5;st_n<=~4'd5;end
 5:if(rsp_r)begin st<=0;st_n<=15;end
 default:failed<=1;failed_n<=~(1);
 endcase
 end
 end
endmodule
`default_nettype wire
