module tb;
reg clk=0,rst_n=0;reg[15:0]rq;reg[383:0]ra;reg[7:0]sr_v,sw_v,old_sv;reg[119:0]sr_addr,sw_addr,old_sa;reg[63:0]sw_mask,old_sm;reg[2047:0]sw_d,old_sd;
wire[511:0]od_rd;wire[2047:0]od_sr;wire[7:0]od_rv;wire od_flt;
wire[511:0]oraw_rd;wire[2047:0]oraw_sr;wire[7:0]oraw_rv;wire oraw_flt;
wire[511:0]nd_rd;wire[2047:0]nd_sr;wire[7:0]nd_rv;wire nd_flt;
wire[511:0]nr_rd;wire[2047:0]nr_sr;wire[7:0]nr_rv;wire nr_flt;
ot_hgi_su_lgroup2_lf #(.N(16),.M(16),.LWB(15),.AW(24),.NS(8),.NLW(0),.MACRO(0),.BREG(1),.FREG(1)) u_od ( .clk(clk),.rst_n(rst_n),.rq(rq),.rr(rq),.ra(ra),.rd(od_rd),.sr_v(sr_v),.sr_addr(sr_addr),.sr_d(od_sr),.sr_rv(od_rv),.sw_v(old_sv),.sw_addr(old_sa),.sw_mask(old_sm),.sw_d(old_sd),.lw(1'b0),.lwa(24'd0),.lwd(32'd0),.s1_v(1'b0),.s1_a(15'd0),.s1_d(32'd0),.flt(od_flt));
ot_hgi_su_lgroup2_lf #(.N(16),.M(16),.LWB(15),.AW(24),.NS(8),.NLW(0),.MACRO(0),.BREG(1),.FREG(1)) u_oraw ( .clk(clk),.rst_n(rst_n),.rq(rq),.rr(rq),.ra(ra),.rd(oraw_rd),.sr_v(sr_v),.sr_addr(sr_addr),.sr_d(oraw_sr),.sr_rv(oraw_rv),.sw_v(sw_v),.sw_addr(sw_addr),.sw_mask(sw_mask),.sw_d(sw_d),.lw(1'b0),.lwa(24'd0),.lwd(32'd0),.s1_v(1'b0),.s1_a(15'd0),.s1_d(32'd0),.flt(oraw_flt));
ot_hgi_su_lgroup2_local_1106 #(.N(16),.M(16),.LWB(15),.AW(24),.NS(8),.NLW(0),.MACRO(0),.BREG(1),.FREG(1),.DREG(1)) u_nd ( .clk(clk),.rst_n(rst_n),.rq(rq),.rr(rq),.ra(ra),.rd(nd_rd),.sr_v(sr_v),.sr_addr(sr_addr),.sr_d(nd_sr),.sr_rv(nd_rv),.sw_v(sw_v),.sw_addr(sw_addr),.sw_mask(sw_mask),.sw_d(sw_d),.lw(1'b0),.lwa(24'd0),.lwd(32'd0),.s1_v(1'b0),.s1_a(15'd0),.s1_d(32'd0),.flt(nd_flt));
ot_hgi_su_lgroup2_local_1106 #(.N(16),.M(16),.LWB(15),.AW(24),.NS(8),.NLW(0),.MACRO(0),.BREG(1),.FREG(1),.RREG(1)) u_nr ( .clk(clk),.rst_n(rst_n),.rq(rq),.rr(rq),.ra(ra),.rd(nr_rd),.sr_v(sr_v),.sr_addr(sr_addr),.sr_d(nr_sr),.sr_rv(nr_rv),.sw_v(sw_v),.sw_addr(sw_addr),.sw_mask(sw_mask),.sw_d(sw_d),.lw(1'b0),.lwa(24'd0),.lwd(32'd0),.s1_v(1'b0),.s1_a(15'd0),.s1_d(32'd0),.flt(nr_flt));
always @(posedge clk)begin old_sv<=sw_v;old_sa<=sw_addr;old_sm<=sw_mask;old_sd<=sw_d;end
reg[511:0]prev_rd;reg[2047:0]prev_sr;reg[7:0]prev_rv;integer checked=0,dmut=0,rmut=0,fltchecks=0;
integer r;integer row;integer warm=0;
initial begin
rq=16'hffff;sr_v=8'hff;sw_v=0;sw_addr=0;sw_mask=0;sw_d=0;sr_addr=0;ra=0;
for(integer n=0;n<1600;n=n+1)begin
rst_n=(n>=5 && !(n>=700&&n<707) && !(n>=1200&&n<1207));
if(!rst_n)warm=0;else warm=warm+1;
for(integer l=0;l<16;l=l+1)begin
 r=$random;row=(n<80)?(n%64):((r&32'h7fffffff)%64);ra[l*24+:24]=row*16+l;
end
for(integer j=0;j<8;j=j+1)begin
 r=$random;row=(r&32'h7fffffff)%64;sr_addr[j*15+:15]=row*16;
 r=$random;row=(r&32'h7fffffff)%64;sw_addr[j*15+:15]=(n<80)?((n%64)*16+8*(j%2)):(row*16+8*(j%2));
 for(integer k=0;k<8;k=k+1)sw_d[j*256+k*32+:32]=$random;
end
sw_v=(n<80)?8'h03:$random;sw_mask=(n<80)?64'hffffffffffffffff:{$random,$random};
#5;clk=1;#1;
if(n>90)begin
if(nd_rd!==od_rd || nd_sr!==od_sr || nd_rv!==od_rv || nd_flt!==od_flt)$fatal(1,"DREG mismatch cycle%0d",n);
if(nr_rd!==prev_rd || nr_sr!==prev_sr)$fatal(1,"RREG data mismatch cycle%0d",n);
if(warm>4 && nr_rv!==prev_rv)$fatal(1,"RREG valid mismatch cycle%0d",n);
if(nr_flt!==oraw_flt)$fatal(1,"RREG fault mismatch cycle%0d",n);
checked=checked+1;fltchecks=fltchecks+2;
if(oraw_rd!==od_rd ||oraw_sr!==od_sr)dmut=dmut+1;
if(oraw_rd!==prev_rd ||oraw_sr!==prev_sr)rmut=rmut+1;
end
prev_rd=oraw_rd;prev_sr=oraw_sr;prev_rv=oraw_rv;
#4;clk=0;
end
if(dmut==0||rmut==0)$fatal(1,"vacuous mutant");
$display("PASS checks=%0d datawords=%0d faultchecks=%0d write_stage_mutant=%0d read_stage_mutant=%0d",checked,checked*144,fltchecks,dmut,rmut);$finish;
end
endmodule
