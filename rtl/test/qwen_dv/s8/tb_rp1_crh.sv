`timescale 1ns/1ps
module tb_rp1_crh;
 reg ck=0;always #5 ck=~ck;
 reg rst_n=0;reg[115:0]cmd=0;reg[1037:0]chd=0;
 wire[115:0]ctl_cmd;wire[1037:0]ctl_chd;wire we,fault;wire[1:0]kind;wire[23:0]addr;wire[1023:0]data;
 qfd_dv_s8_rp1 rp(.ck(ck),.rst_n(rst_n),.cmd_q(cmd),.chd_q(chd),.tw_we(1'b0),.tw_kind(2'd0),.tw_addr(24'd0),.tw_data(1024'd0),
 .ctl_cmd(ctl_cmd),.ctl_chd(ctl_chd),.vtw_we(we),.vtw_kind(kind),.vtw_addr(addr),.vtw_data(data),.fault(fault));
 wire[511:0]lo,hi;genvar g;
 generate for(g=0;g<16;g=g+1)begin
 assign lo[32*g+:32]=data[64*g+:32];assign hi[32*g+:32]=data[64*g+32+:32];end endgenerate
 wire[255:0]ql,qh;wire fl,fh;
 qfd_dv_s8_crh_rp1 cl(.ck(ck),.rst_n(rst_n),.cr_re(8'd0),.cr_addr(192'd0),.q(ql),.tw_we(we),.tw_kind(kind),.tw_addr(addr),.tw_d(lo),.fault(fl));
 qfd_dv_s8_crh_rp1 ch(.ck(ck),.rst_n(rst_n),.cr_re(8'd0),.cr_addr(192'd0),.q(qh),.tw_we(we),.tw_kind(kind),.tw_addr(addr),.tw_d(hi),.fault(fh));
 integer k,l,a;reg[511:0]payload;reg[255:0]el,eh;
 task tick;begin @(posedge ck);#1;@(negedge ck);end endtask
 initial begin
 repeat(2)tick();rst_n=1;repeat(5)tick();
 cmd=0;cmd[0]=1;cmd[3:1]=7;cmd[7:4]=3;tick();cmd=0;tick();
 cmd[0]=1;cmd[115:112]=15;cmd[3:1]=0;cmd[5:4]=1;cmd[15:6]=16;#1;
 if(ctl_cmd[0]!==0)$fatal(1,"ARM not consumed");tick();cmd=0;tick();
 for(k=0;k<8;k=k+1)begin
  payload=0;for(l=0;l<8;l=l+1)payload[64*l+:64]={32'habc00000+32'(k*16+l),32'h12300000+32'(k*16+l)};
  chd={518'd0,1'b1,1'b1,3'd0,3'(k),payload};#1;
  if(!we || kind!=1 || addr!={12'd0,1'b1,1'(k%2),10'(16+k/2)} || data!={payload,payload} || ctl_chd[519] || fault)$fatal(1,"RP1 beat mismatch k=%0d addr=%h fault=%b",k,addr,fault);
  tick();chd=0;tick();
 end
 repeat(5)tick();
 for(a=0;a<4;a=a+1)begin
  el=0;eh=0;for(l=0;l<8;l=l+1)begin el[32*l+:32]=32'h12300000+32'(2*a*16+l);eh[32*l+:32]=32'habc00000+32'(2*a*16+l);end
  if(cl.g_crb[0].u_m.mem[16+a]!==el || ch.g_crb[0].u_m.mem[16+a]!==eh)$fatal(1,"CROM bank0 word%0d",a);
  for(l=0;l<8;l=l+1)begin el[32*l+:32]=32'h12300000+32'((2*a+1)*16+l);eh[32*l+:32]=32'habc00000+32'((2*a+1)*16+l);end
  if(cl.g_crb[1].u_m.mem[16+a]!==el || ch.g_crb[1].u_m.mem[16+a]!==eh)$fatal(1,"CROM bank1 word%0d",a);
 end
 if(fl || fh || fault)$fatal(1,"unexpected fault");
 // The ninth return is not consumed after the eight-beat epoch closes.
 chd[519:518]=3;#1;if(we || !ctl_chd[519])$fatal(1,"closed epoch swallowed ninth return");
 $display("PASS RP1 eight payloads -> four words x two banks, exact lo/hi512 and legacyctl masks; ninth return forwarded");$finish;
 end
endmodule
