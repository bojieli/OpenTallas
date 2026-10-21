`timescale 1ps/1ps
module tb_fdn_kept_selectors;
parameter integer D=4,K=2,PHASE=0,MUT=0;
reg wc=0,rc=0,rst=0;always #500 wc=~wc;
initial begin #(500+PHASE);forever begin rc=~rc;#500;end end
reg [1094:0] tx=0,own=0;reg [31:0]rng=32'h5a24db78;
always @(negedge wc)begin
 rng={rng[30:0],rng[31]^rng[21]^rng[1]^rng[0]};
 for(integer b=0;b<1095;b=b+1)begin tx[b]=rng[b%32]^(b%7==0);own[b]=rng[(b+5)%32]^(b%5==0);end
 tx[1094]=rng[0];tx[547]=rng[1];
end
initial begin #10000;rst=1;#270000;rst=0;#14000;rst=1;end
wire [D*1095-1:0]bank;wire [D*((D<=2?1:$clog2(D))+1)-1:0]epo;wire [D*46-1:0]vld;wire [1094:0]land;
ot_pl_land_n32_split_w #(.W(1095),.D(D)) w(wc,{2{rst}},tx,bank,epo,vld);
ot_pl_land_split_r #(.W(1095),.D(D),.K(K)) r(rc,{2{rst}},bank,epo,vld,land);
wire [45:0]sa,sd;
wire[D-1:0]ba,bd;
for(genvar i=0;i<D;i=i+1)begin assign ba[i]=bank[i*1095+1094];assign bd[i]=bank[i*1095+547];end
ot_pl_land_field_copies #(.COPIES(46),.D(D),.K(K+(MUT==1))) ca(.ck(rc),.rsi(rst),.bank(ba),.epo(epo),.vld(vld[45*D+:D]),.o(sa));
ot_pl_land_field_copies #(.COPIES(46),.D(D),.K(K+(MUT==1))) cd(.ck(rc),.rsi(rst),.bank((MUT==2)?ba:bd),.epo(epo),.vld(vld[22*D+:D]),.o(sd));
wire[1094:0]q0,q1;wire p0,p1;
qfd_dv_s8_fdn_arf1 a(.ck(rc),.rst_n(rst),.cmd_i(116'd0),.chu_q(land),.own_ch(own),.ch_dn_o(q0),.pc_bad(p0),.agu_q(10'd0),.ag_own(10'd0));
qfd_dv_s8_fdn_arf1 #(.USE_SEL_COPIES(1)) b(.ck(rc),.rst_n(rst),.cmd_i(116'd0),.chu_q(land),.own_ch(own),.chu_ar_sel(sa),.chu_dd_sel(sd),.ch_dn_o(q1),.pc_bad(p1),.agu_q(10'd0),.ag_own(10'd0));
integer checks=0;
always @(posedge rc)begin #1;if(rst && $time>40000 && ($time<270000 || $time>330000))begin
 if(sa!=={46{land[1094]}} || sd!=={46{land[547]}} || q0!==q1 || p0!==p1)$fatal(1,"FDN_SELECTOR_MISMATCH D%0d PHASE%0d MUT%0d time%0t",D,PHASE,MUT,$time);
 checks=checks+1;
end
if($time>600000)begin if(checks<300)$fatal(1,"coverage");$display("PASS FDN kept selectors D%0d phase%0d checks%0d same read edge two resets",D,PHASE,checks);$finish;end end
endmodule
