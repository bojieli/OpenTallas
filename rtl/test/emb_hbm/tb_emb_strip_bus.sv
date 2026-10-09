`timescale 1ps/1fs
module tb_emb_strip_bus;
 parameter integer NEG=0;
 reg clk=0,rst_n=0; always #416.666667 clk=~clk;
 reg [524:0] link_i=0;
 wire [524:0] link_o,g_link,off_link;
 reg [259:0] ret[0:31]; wire [287:0] cmd[0:31],off_cmd[0:31];
 wire [31:0] gm,gw,sc,ev; wire gwe; wire [4:0] gb,gc; wire [18:0] gr; wire [255:0] gd; wire [8255:0] ed;
 wire f,gf,of; wire [7:0] fc,gfc,ofc; wire [31:0] ce,gce,oce,ue,gue,oue;
 assign {sc[0],ev[0],ed[0*258+:258]}=ret[0];
 assign {sc[1],ev[1],ed[1*258+:258]}=ret[1];
 assign {sc[2],ev[2],ed[2*258+:258]}=ret[2];
 assign {sc[3],ev[3],ed[3*258+:258]}=ret[3];
 assign {sc[4],ev[4],ed[4*258+:258]}=ret[4];
 assign {sc[5],ev[5],ed[5*258+:258]}=ret[5];
 assign {sc[6],ev[6],ed[6*258+:258]}=ret[6];
 assign {sc[7],ev[7],ed[7*258+:258]}=ret[7];
 assign {sc[8],ev[8],ed[8*258+:258]}=ret[8];
 assign {sc[9],ev[9],ed[9*258+:258]}=ret[9];
 assign {sc[10],ev[10],ed[10*258+:258]}=ret[10];
 assign {sc[11],ev[11],ed[11*258+:258]}=ret[11];
 assign {sc[12],ev[12],ed[12*258+:258]}=ret[12];
 assign {sc[13],ev[13],ed[13*258+:258]}=ret[13];
 assign {sc[14],ev[14],ed[14*258+:258]}=ret[14];
 assign {sc[15],ev[15],ed[15*258+:258]}=ret[15];
 assign {sc[16],ev[16],ed[16*258+:258]}=ret[16];
 assign {sc[17],ev[17],ed[17*258+:258]}=ret[17];
 assign {sc[18],ev[18],ed[18*258+:258]}=ret[18];
 assign {sc[19],ev[19],ed[19*258+:258]}=ret[19];
 assign {sc[20],ev[20],ed[20*258+:258]}=ret[20];
 assign {sc[21],ev[21],ed[21*258+:258]}=ret[21];
 assign {sc[22],ev[22],ed[22*258+:258]}=ret[22];
 assign {sc[23],ev[23],ed[23*258+:258]}=ret[23];
 assign {sc[24],ev[24],ed[24*258+:258]}=ret[24];
 assign {sc[25],ev[25],ed[25*258+:258]}=ret[25];
 assign {sc[26],ev[26],ed[26*258+:258]}=ret[26];
 assign {sc[27],ev[27],ed[27*258+:258]}=ret[27];
 assign {sc[28],ev[28],ed[28*258+:258]}=ret[28];
 assign {sc[29],ev[29],ed[29*258+:258]}=ret[29];
 assign {sc[30],ev[30],ed[30*258+:258]}=ret[30];
 assign {sc[31],ev[31],ed[31*258+:258]}=ret[31];
 ot_qfd_emb_strip_bus #(.ENABLE(1)) dut(.clk(clk),.rst_n(rst_n),.link_i(link_i),.link_o(link_o),.fault(f),.fault_code(fc),.ce_cnt(ce),.ue_info(ue),.cmd0(cmd[0]),.ret0(ret[0] ^ ((NEG && 0==17) ? 260'b1 : 260'b0)),.cmd1(cmd[1]),.ret1(ret[1] ^ ((NEG && 1==17) ? 260'b1 : 260'b0)),.cmd2(cmd[2]),.ret2(ret[2] ^ ((NEG && 2==17) ? 260'b1 : 260'b0)),.cmd3(cmd[3]),.ret3(ret[3] ^ ((NEG && 3==17) ? 260'b1 : 260'b0)),.cmd4(cmd[4]),.ret4(ret[4] ^ ((NEG && 4==17) ? 260'b1 : 260'b0)),.cmd5(cmd[5]),.ret5(ret[5] ^ ((NEG && 5==17) ? 260'b1 : 260'b0)),.cmd6(cmd[6]),.ret6(ret[6] ^ ((NEG && 6==17) ? 260'b1 : 260'b0)),.cmd7(cmd[7]),.ret7(ret[7] ^ ((NEG && 7==17) ? 260'b1 : 260'b0)),.cmd8(cmd[8]),.ret8(ret[8] ^ ((NEG && 8==17) ? 260'b1 : 260'b0)),.cmd9(cmd[9]),.ret9(ret[9] ^ ((NEG && 9==17) ? 260'b1 : 260'b0)),.cmd10(cmd[10]),.ret10(ret[10] ^ ((NEG && 10==17) ? 260'b1 : 260'b0)),.cmd11(cmd[11]),.ret11(ret[11] ^ ((NEG && 11==17) ? 260'b1 : 260'b0)),.cmd12(cmd[12]),.ret12(ret[12] ^ ((NEG && 12==17) ? 260'b1 : 260'b0)),.cmd13(cmd[13]),.ret13(ret[13] ^ ((NEG && 13==17) ? 260'b1 : 260'b0)),.cmd14(cmd[14]),.ret14(ret[14] ^ ((NEG && 14==17) ? 260'b1 : 260'b0)),.cmd15(cmd[15]),.ret15(ret[15] ^ ((NEG && 15==17) ? 260'b1 : 260'b0)),.cmd16(cmd[16]),.ret16(ret[16] ^ ((NEG && 16==17) ? 260'b1 : 260'b0)),.cmd17(cmd[17]),.ret17(ret[17] ^ ((NEG && 17==17) ? 260'b1 : 260'b0)),.cmd18(cmd[18]),.ret18(ret[18] ^ ((NEG && 18==17) ? 260'b1 : 260'b0)),.cmd19(cmd[19]),.ret19(ret[19] ^ ((NEG && 19==17) ? 260'b1 : 260'b0)),.cmd20(cmd[20]),.ret20(ret[20] ^ ((NEG && 20==17) ? 260'b1 : 260'b0)),.cmd21(cmd[21]),.ret21(ret[21] ^ ((NEG && 21==17) ? 260'b1 : 260'b0)),.cmd22(cmd[22]),.ret22(ret[22] ^ ((NEG && 22==17) ? 260'b1 : 260'b0)),.cmd23(cmd[23]),.ret23(ret[23] ^ ((NEG && 23==17) ? 260'b1 : 260'b0)),.cmd24(cmd[24]),.ret24(ret[24] ^ ((NEG && 24==17) ? 260'b1 : 260'b0)),.cmd25(cmd[25]),.ret25(ret[25] ^ ((NEG && 25==17) ? 260'b1 : 260'b0)),.cmd26(cmd[26]),.ret26(ret[26] ^ ((NEG && 26==17) ? 260'b1 : 260'b0)),.cmd27(cmd[27]),.ret27(ret[27] ^ ((NEG && 27==17) ? 260'b1 : 260'b0)),.cmd28(cmd[28]),.ret28(ret[28] ^ ((NEG && 28==17) ? 260'b1 : 260'b0)),.cmd29(cmd[29]),.ret29(ret[29] ^ ((NEG && 29==17) ? 260'b1 : 260'b0)),.cmd30(cmd[30]),.ret30(ret[30] ^ ((NEG && 30==17) ? 260'b1 : 260'b0)),.cmd31(cmd[31]),.ret31(ret[31] ^ ((NEG && 31==17) ? 260'b1 : 260'b0)));
 ot_qfd_emb_strip_bus disabled(.clk(clk),.rst_n(rst_n),.link_i(link_i),.link_o(off_link),.fault(of),.fault_code(ofc),.ce_cnt(oce),.ue_info(oue),.cmd0(off_cmd[0]),.ret0(ret[0]),.cmd1(off_cmd[1]),.ret1(ret[1]),.cmd2(off_cmd[2]),.ret2(ret[2]),.cmd3(off_cmd[3]),.ret3(ret[3]),.cmd4(off_cmd[4]),.ret4(ret[4]),.cmd5(off_cmd[5]),.ret5(ret[5]),.cmd6(off_cmd[6]),.ret6(ret[6]),.cmd7(off_cmd[7]),.ret7(ret[7]),.cmd8(off_cmd[8]),.ret8(ret[8]),.cmd9(off_cmd[9]),.ret9(ret[9]),.cmd10(off_cmd[10]),.ret10(ret[10]),.cmd11(off_cmd[11]),.ret11(ret[11]),.cmd12(off_cmd[12]),.ret12(ret[12]),.cmd13(off_cmd[13]),.ret13(ret[13]),.cmd14(off_cmd[14]),.ret14(ret[14]),.cmd15(off_cmd[15]),.ret15(ret[15]),.cmd16(off_cmd[16]),.ret16(ret[16]),.cmd17(off_cmd[17]),.ret17(ret[17]),.cmd18(off_cmd[18]),.ret18(ret[18]),.cmd19(off_cmd[19]),.ret19(ret[19]),.cmd20(off_cmd[20]),.ret20(ret[20]),.cmd21(off_cmd[21]),.ret21(ret[21]),.cmd22(off_cmd[22]),.ret22(ret[22]),.cmd23(off_cmd[23]),.ret23(ret[23]),.cmd24(off_cmd[24]),.ret24(ret[24]),.cmd25(off_cmd[25]),.ret25(ret[25]),.cmd26(off_cmd[26]),.ret26(ret[26]),.cmd27(off_cmd[27]),.ret27(ret[27]),.cmd28(off_cmd[28]),.ret28(ret[28]),.cmd29(off_cmd[29]),.ret29(ret[29]),.cmd30(off_cmd[30]),.ret30(ret[30]),.cmd31(off_cmd[31]),.ret31(ret[31]));
 ot_qfd_emb_strip golden(.clk(clk),.rst_n(rst_n),.i_v(link_i[524]),.i_d(link_i[523:1]),.o_cr(link_i[0]),.o_v(g_link[524]),.o_d(g_link[523:1]),.i_cr(g_link[0]),.s_m(gm),.w_m(gw),.s_we(gwe),.s_bank(gb),.s_col(gc),.s_row(gr),.w_d(gd),.s_cr(sc),.e_v(ev),.e_d(ed),.fault(gf),.fault_code(gfc),.ce_cnt(gce),.ue_info(gue));
 integer i,j,k;
 reg [522:0] packet;
 always @(negedge clk) if(rst_n) begin
  if({link_o,f,fc,ce,ue} !== {g_link,gf,gfc,gce,gue}) $fatal(1,"FAIL strip functional equivalence");
  if({off_link,of,ofc,oce,oue} !== 0) $fatal(1,"FAIL strip default-off status");
  for(k=0;k<32;k=k+1) begin
   if(cmd[k] !== {gm[k],gw[k],gwe,gb,gc,gr,gd}) $fatal(1,"FAIL strip command mapping lane=%0d",k);
   if({dut.enabled.s_cr[k],dut.enabled.e_v[k],dut.enabled.e_d[k*258+:258]} !== ret[k]) $fatal(1,"FAIL strip return mapping lane=%0d",k);
   if(off_cmd[k] !== 0) $fatal(1,"FAIL strip default-off cmd lane=%0d",k);
  end
 end
 initial begin
  for(i=0;i<32;i=i+1) ret[i]=0;
  repeat(4) @(posedge clk); rst_n=1;
  for(j=0;j<1024;j=j+1) begin
   @(posedge clk); #1;
   for(i=0;i<32;i=i+1) begin
    ret[i][259]=((j+i)%7==0); ret[i][258]=((j+i)%13==0);
    ret[i][257:0]={8{32'(j*89+i*113)}}; ret[i][257:256]=0;
   end
   packet=0; packet[522]=1; packet[3:0]=j%16;
   packet[280:25]={8{32'(j*379)}}; packet[24:0]=j;
   packet[521:520]=(j%64==0) ? 2'b00 : 2'b01;
   link_i={1'(j%32==0),packet,1'b1};
  end
  @(posedge clk); #1; link_i=0;
  repeat(20) @(posedge clk);
  $display("PASS strip_bus full32PC 1024-cycle functional and all-pin mapping default-off"); $finish;
 end
endmodule
