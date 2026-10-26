`timescale 1ns/1ps
module tb_context_controller;
 parameter integer MUT=0,PC=13;
 reg ck=0;always #0.512 ck=~ck;
 reg rn=0,we=0,seal=0,go=0;reg[5:0]layer=0;reg[15:0]epoch=0;reg[4:0]addr=0;reg[63:0]data=0;
 reg[13:0]T=1;reg[1:0]stack=0;reg[2:0]group=0;
 wire owner,rd,sr,wr,raw,cf,idle;wire[42:0]cmd;wire[15:0]ep;
 qkd_controller_context_calendar #(.MUT(MUT))cal(ck,rn,we,addr,data,seal,go,epoch,layer,owner,cmd,rd,sr,wr,ep,raw,cf,idle,T,stack,group);
 wire rv,cv,cwe,busy,fault,phaseidle;wire[2:0]rop;wire[4:0]rb,cb,cc;wire[18:0]row;
 ot_qkd_static_ctrl_pc_emb #(.CONTEXT_DESC(1),.ENABLE(1),.PC(PC),.PHASE(0),.PROFILE(0))dut(
 .clk(ck),.rst_n(rn),.cmd_v(cmd[0]),.cmd(cmd[32:1]),.cmd_first(cmd[42:33]),.reserved_rd(rd),.reserved_static_col(sr),.reserved_write_col(wr),.boot_window(1'b0),.col_boot(),.cmd_credit(),
 .row_v(rv),.row_op(rop),.row_bank(rb),.row_row(row),.col_v(cv),.col_bank(cb),.col_col(cc),.col_we(cwe),.busy(busy),.fault(fault),.phase_idle(phaseidle),
 .s_context(347'b0),.col_context(),.s_v(1'b0),.s_we(1'b0),.s_bank(5'b0),.s_col(5'b0),.s_row(19'b0),.s_cr(),.col_sr());
 reg[127:0]image[0:15];integer expectsec[0:511];integer expected_rd[0:2499];integer count=0,reads=0,total=0,edge_num=0,origin=-99999,relative_edge,openrow[0:31];
 integer f,rc,ti,si,gi,ni,x;string imagepath,casespath;
 initial begin
 if(MUT==4)force dut.core.on.context_count=9'd256;
 if(MUT==5)force dut.core.on.bank[16].ahead=1'b0;
 if(!$value$plusargs("IMAGE=%s",imagepath)||!$value$plusargs("CASES=%s",casespath))$fatal(1,"missing files");
 $readmemh(imagepath,image);f=$fopen(casespath,"r");if(!f)$fatal(1,"missing expected vectors");
 repeat(6)@(negedge ck);rn=1;repeat(160)@(negedge ck);
 for(integer i=0;i<32;i++)begin we=1;addr=5'(i);data=i<16?image[i][63:0]:image[i-16][127:64];@(negedge ck);end
 we=0;repeat(3)@(negedge ck);seal=1;@(negedge ck);seal=0;repeat(3)@(negedge ck);
 for(integer l=0;l<36;l++)begin
 rc=$fscanf(f,"%d %d %d %d\n",ti,si,gi,ni);if(rc!=4)$fatal(1,"missing layer case");
 for(integer i=0;i<ni;i++)begin rc=$fscanf(f,"%d ",x);expectsec[i]=x;end
 for(integer i=0;i<2500;i++)begin rc=$fscanf(f,"%d ",x);expected_rd[i]=x;end
 T=14'(ti);stack=2'(si);group=3'(gi);layer=6'(l);epoch=16'(100+l);count=ni;reads=0;
 go=1;@(negedge ck);go=0;repeat(2500)@(negedge ck);
 if(reads!=count)$fatal(1,"FAIL context controller layer%0d reads%0d/%0d",l,reads,count);
 end
 $display("PASS context controller PROFILE0 persistent36layers total%0d exact address and slots",total);$finish;
 end
 always @(posedge ck)begin
 edge_num++;if(go)origin=edge_num;relative_edge=edge_num-origin;#0.001;
 if(rn)begin
 if(relative_edge>=2 && relative_edge<2499 && rd!==1'(expected_rd[relative_edge]))$fatal(1,"FAIL context controller calendar timeline edge%0d",relative_edge);
 if(rv&&rop==1)openrow[rb]=row;
 if(cv)begin
 if(reads>=count || (((cb>>2)<<7)|(cc<<2)|(cb&3))!=expectsec[reads] || cwe || openrow[cb]!=64+integer'(layer))
 $fatal(1,"FAIL context controller layer%0d address[%0d] bank%0d col%0d expected%0d row%0d",layer,reads,cb,cc,expectsec[reads],openrow[cb]);
 reads++;total++;
 end
 if(dut.core.on.streaming&&dut.core.on.context_active&&dut.core.on.context_v && (!dut.core.on.bank[16].ahead || !dut.core.on.bank[20].ahead))$fatal(1,"FAIL context controller V banksets4/5 protection");
 if(fault||cf)begin $display("DETAIL sf%0b ref%0b legal%0b open%h stale%h blk%h rcd%h ccd%h running%0b k%0d last%0d",dut.core.on.fault_schedule,dut.core.on.fault_r,dut.core.on.legal_rd,dut.core.on.open,dut.core.on.stale,dut.core.on.blk,dut.core.on.rcd_z,dut.core.on.ccdl_z,dut.core.on.running,dut.core.on.k,dut.core.on.last);$fatal(1,"FAIL context controller fault layer%0d edge%0d j%0d ordinal%0d",layer,relative_edge,dut.core.on.j,dut.core.on.ordinal);end
 end
 end
endmodule
