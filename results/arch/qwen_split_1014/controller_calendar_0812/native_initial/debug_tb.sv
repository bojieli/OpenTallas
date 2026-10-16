`timescale 1ns/1ps
// Actual PROFILE0 ELASTIC controller driven only by independent compiled runs.
// Only external PHY/HBM is modeled. No PROFILE1/trace discovery is instantiated.
module tb_controller_calendar_native;
 parameter integer MUT=0;
 reg ck=0;always #0.512 ck=~ck;
 reg rn=0,we=0,seal=0,go=0;reg[4:0]addr=0;reg[63:0]data=0;
 wire owner,rd,sr,wr,raw,calfault,idle;wire[42:0]cmd;wire[15:0]epoch;
 qkd_controller_hbm_calendar #(.MUT(MUT))cal(ck,rn,we,addr,data,seal,go,16'd7,6'd3,owner,cmd,rd,sr,wr,epoch,raw,calfault,idle);
 wire [327:0]po;wire[293:0]co;wire[260:0]er;wire fault,cf;wire[15:0]oe;
 reg[288:0]pi=0;
 qkd_ctrl_pc_host_static #(.PROFILE(0),.ELASTIC(1),.RAW_WD(256),.TQD(64))dut(
 .pll_hbm(ck),.hrst(rn),.ck(ck),.rsi(rn),.pc(5'd13),.ci(319'b0),.co(co),.es(288'b0),.er(er),.po(po),.pi(pi),.ki(33'b0),.ko(),.fi(1'b0),.fo(fault),
 .static_cmd_owner(owner),.static_cmd(cmd),.reserved_rd(rd),.reserved_static_col(sr),.reserved_write_col(wr),.static_epoch(epoch),.expected_raw_valid(raw),
 .cfg_stack(2'b0),.es_context(318'b0),.es_expected_valid(1'b0),.es_expected_identity(61'b0),.es_expected_address(29'b0),.es_expected_pc(5'b0),.es_expected_stack(2'b0),
 .native_commit_valid(),.native_commit_identity(),.native_commit_address(),.corrected_epoch(oe),.completion_v(),.completion_we(),.completion_fault(cf),.idle_core(),.idle_hbm(),.drain_fault_core(),.drain_fault_hbm());
 function automatic[255:0]payload(input integer sector);
 for(integer j=0;j<8;j++)payload[j*32+:32]=32'hac100000^32'(sector*311+j*31);
 endfunction
 function automatic[71:0]ecc(input[63:0]d);
 reg[71:0]c;integer j;begin c=0;j=0;for(integer p=1;p<=71;p++)if((p&(p-1))!=0)begin c[p-1]=d[j];j++;end
 for(integer k=0;k<7;k++)for(integer p=1;p<=71;p++)if((p&(1<<k))!=0)c[(1<<k)-1]^=c[p-1];c[71]=^c[70:0];ecc=c;end
 endfunction
 function automatic[287:0]encode(input[255:0]d);for(integer j=0;j<4;j++)encode[j*72+:72]=ecc(d[j*64+:64]);endfunction
 reg[127:0]image[0:15];reg[288:0]due[0:9000];integer openrow[0:31];
 integer edge_num=0,reads=0,landed=0,last_arrival=0,jitter=0;
 string image_path;
 initial begin
 void'($value$plusargs("JITTER=%d",jitter));
 if(!$value$plusargs("IMAGE=%s",image_path))$fatal(1,"missing compiled image");
 $readmemh(image_path,image);for(integer j=0;j<9001;j++)due[j]=0;for(integer j=0;j<32;j++)openrow[j]=-1;
 repeat(6)@(negedge ck);rn=1;repeat(150)@(negedge ck);
 for(integer i=0;i<32;i++)begin we=1;addr=5'(i);data=i<16?image[i][63:0]:image[i-16][127:64];@(negedge ck);end
 we=0;repeat(3)@(negedge ck);seal=1;@(negedge ck);seal=0;repeat(3)@(negedge ck);
 go=1;@(negedge ck);go=0;
 repeat(2500)@(negedge ck);
 if(reads!=512||landed!=512)$fatal(1,"FAIL native calendar count reads%0d landed%0d",reads,landed);
 $display("PASS native controller calendar PROFILE0 reads=%0d landed=%0d jitter=%0d",reads,landed,jitter);$finish;
 end
 always @(posedge ck)begin
 edge_num++;
 if(rn)begin
 if(po[0]&&po[3:1]==1)openrow[po[8:4]]=po[27:9];
 if(po[28])begin
 automatic integer bank=po[34:30],col=po[39:35],sec=((bank>>2)<<7)|(col<<2)|(bank&3),arrival=edge_num+23+jitter;
 if(po[29]||openrow[bank]!=67)$fatal(1,"FAIL native calendar PHY row/direction bank%0d row%0d",bank,openrow[bank]);
 if(arrival<=last_arrival)arrival=last_arrival+1;last_arrival=arrival;
 due[arrival]={encode(payload(sec)),1'b1};reads++;
 end
 if(co[0])begin
 automatic integer o=landed-256,sec=landed<256?landed:512+((o&8)<<4)+((o>>4)<<3)+(o&7);
 if(oe!=7||{co[11:9],co[7:1]}!=10'(sec)||co[281:26]!==payload(sec))$fatal(1,"FAIL native calendar actual data index%0d",landed);
 landed++;
 end
 if(fault||cf||calfault)begin $display("DETAIL schedule%0b cmd%0b early%0b raw%0b legalrd%0b j%0d go%0b open%h done%h",dut.u_ctl.core.on.fault_schedule,dut.f_cmd,dut.f_early,dut.f_raw,dut.u_ctl.core.on.legal_rd,dut.u_ctl.core.on.j,dut.u_ctl.core.go,dut.u_ctl.core.on.open,dut.u_ctl.core.on.done);$fatal(1,"FAIL native calendar fault edge%0d fo%0b cf%0b cal%0b",edge_num,fault,cf,calfault);end
 end
 end
 always @(negedge ck)pi=due[edge_num+1];
endmodule
