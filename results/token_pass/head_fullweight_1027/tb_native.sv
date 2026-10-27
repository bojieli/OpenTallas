`timescale 1ns/1ps
// Current generated most-replicated partition vs independent boundary-delay
// model and released checkpoint head-row golden. This is a partition token
// vehicle, never a full-head or full-model token claim.
module tb_head_partition_token;
reg ck=0;always #0.4165 ck=~ck;
reg rn=0,start=0;reg[565:0]di=0;wire[565:0]dout;
integer mut_ft=0;reg[19:0]ft_pattern=20'h591c7;wire[19:0]ft_out;wire[19:0]ft_drive=ft_pattern^(mut_ft?20'd1:20'd0);integer ft_checks=0;
always@(negedge ck)begin if(cyc>2)begin if(ft_out!==ft_pattern)$fatal(1,"HEAD_NATIVE_FT mismatch");ft_checks+=20;end ft_pattern<={ft_pattern[18:0],ft_pattern[19]^ft_pattern[16]};end
integer mutant=0;integer row0_i=21888,exp_row_i=21946;reg[31:0]exp_bits=32'h4173a558;wire[16:0]ref_row0=row0_i[16:0];wire[16:0]tile_row=ref_row0+(mutant?17'd128:17'd0);
ot_s81hd_tile_p #(.INSTANCE("h")) dut(.hci0_ck0_i(ft_drive[0]),.hci0_ck0_o(ft_out[0]),.hci0_ck1_i(ft_drive[1]),.hci0_ck1_o(ft_out[1]),.hci0_mesh_i(ft_drive[2]),.hci0_mesh_o(ft_out[2]),.hci0_rst_i(ft_drive[3]),.hci0_rst_o(ft_out[3]),.hci1_ck0_i(ft_drive[4]),.hci1_ck0_o(ft_out[4]),.hci1_ck1_i(ft_drive[5]),.hci1_ck1_o(ft_out[5]),.hci1_mesh_i(ft_drive[6]),.hci1_mesh_o(ft_out[6]),.hci1_rst_i(ft_drive[7]),.hci1_rst_o(ft_out[7]),.hci2_ck0_i(ft_drive[8]),.hci2_ck0_o(ft_out[8]),.hci2_ck1_i(ft_drive[9]),.hci2_ck1_o(ft_out[9]),.hci2_mesh_i(ft_drive[10]),.hci2_mesh_o(ft_out[10]),.hci2_rst_i(ft_drive[11]),.hci2_rst_o(ft_out[11]),.hci3_ck0_i(ft_drive[12]),.hci3_ck0_o(ft_out[12]),.hci3_ck1_i(ft_drive[13]),.hci3_ck1_o(ft_out[13]),.hci3_mesh_i(ft_drive[14]),.hci3_mesh_o(ft_out[14]),.hci3_rst_i(ft_drive[15]),.hci3_rst_o(ft_out[15]),.hci4_ck0_i(ft_drive[16]),.hci4_ck0_o(ft_out[16]),.hci4_ck1_i(ft_drive[17]),.hci4_ck1_o(ft_out[17]),.hci4_mesh_i(ft_drive[18]),.hci4_mesh_o(ft_out[18]),.hci4_rst_i(ft_drive[19]),.hci4_rst_o(ft_out[19]),.clk(ck),.clk_t1(ck),.clk_t2(ck),.clk_t3(ck),.clk_t4(ck),.clk_t5(ck),
 .arst_n(rn),.start_i(start),.rst_o_0(),.rst_o_1(),.rst_o_2(),.rst_o_3(),
 .start_o_0(),.start_o_1(),.start_o_2(),.start_o_3(),.i(di),.o(dout),.strap_row0(tile_row),.strap_ten(1'b1));
reg[4:0]rp=0,sp=0;reg[564:0]ri=0,ro_q=0;wire[564:0]ro;
always@(posedge ck)begin rp<={rp[3:0],rn};sp<={sp[3:0],start};ri<=di[564:0];ro_q<=ro;end
wire ref_rst=rp[4]&sp[4];
ot_s81hd_tile_reference #(.INSTANCE("h"),.CV(1),.A_INPUT_STAGES(1),.MERGE_HOP(1),.CMP_STAGES(3)) ref_tile(
 .ck(ck),.rst_n(ref_rst),.i(ri),.o(ro),.row0(ref_row0),.ten(1'b1));
reg[255:0]xa[0:255],xb[0:63];string dir;integer cyc=0,g0=0,m,checks=0,nres=0;
always@(posedge ck)cyc<=cyc+1;
always@(negedge ck)if(cyc>20&&dout[565])begin
 checks++;
 if(dout[564:0]!==ro_q)$fatal(1,"HEAD_PARTITION lockstep mismatch at%0d result_v%b ref_v%b mutant%0d",cyc,dout[514],ro_q[514],mutant);
 if(dout[514])begin
  if(dout[531:515]!==exp_row_i[16:0]||dout[563:532]!==exp_bits||dout[564])$fatal(1,"HEAD_PARTITION released-checkpoint golden mismatch");
  nres++;$display("HEAD_PARTITION_RESULT row%0d bits%h go_to_result%0d",dout[531:515],dout[563:532],cyc-g0);
 end
end
initial begin
 if($value$plusargs("MUT_FT=%d",mut_ft))begin end
 if($value$plusargs("ROW0=%d",row0_i))begin end
 if($value$plusargs("EXP_ROW=%d",exp_row_i))begin end
 if($value$plusargs("EXP_BITS=%h",exp_bits))begin end
 if(!$value$plusargs("DIR=%s",dir))$fatal(1,"DIR required");
 if($value$plusargs("MUT_ROW=%d",mutant))begin end
 $readmemh({dir,"/xa.hex"},xa);$readmemh({dir,"/xb.hex"},xb);
 repeat(4)@(negedge ck);rn=1;start=1;repeat(20)@(negedge ck);
 g0=cyc;di=0;di[565]=1;di[512]=1;di[513]=1;di[514]=1;di[531:515]=17'h1ffff;di[563:532]=32'hff800000;
 @(negedge ck);di[514]=0;di[512]=0;
 for(m=0;m<8192+7*11+8;m++)begin
  while(cyc-g0!=5+m)@(negedge ck);
  di[255:0]=xa[m%256];di[511:256]=xb[m%64];
 end
 di[513]=0;
 while(cyc-g0<9000)@(negedge ck);
 if(nres!=1||checks<8500)$fatal(1,"HEAD_PARTITION no complete result nres%0d checks%0d",nres,checks);
 $display("HEAD_NATIVE_FT PASS checks%0d",ft_checks);
 $display("HEAD_PARTITION_TOKEN PASS row0 %0d rows128 dims5120 positions1 checks%0d added_boundary_cycles2",row0_i,checks);$finish;
end
endmodule
