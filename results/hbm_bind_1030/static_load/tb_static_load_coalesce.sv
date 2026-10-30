`timescale 1ns/1ps
module tb_static_load_coalesce;
 parameter MUT=0;
 reg clk=0;always #5 clk=~clk;
 reg rst=0,dv=0,step=0;reg[226:0]desc=0;
 wire active,fault,av,last;wire[39:0]sa,da;wire[2:0]fmt;wire[3:0]count;
 ot_hbm_static_load_addr_counter #(.MUT_ZERO_STRIDE(MUT==1),.MUT_STRIPE(MUT==2),.MUT_BATCH(MUT==3),.MUT_UE_SIZE(MUT==4))u(clk,rst,dv,desc,step,active,fault,av,last,sa,da,fmt,count);
 reg[39:0]ea,ed;reg[2:0]ef,eleaf;reg[3:0]ec;reg el;reg[61:0]cmdexp;reg[1:0]eq;
 reg[14:0]wr;reg[3:0]wc;reg bufid;reg[15:0]epoch;
 wire lv,mfault;wire[61:0]cmd;wire[2:0]leaf;wire[1:0]quad;
 ot_hbm_static_load_addr_map map(av,sa,da,fmt,count,bufid,epoch,wr,wc,lv,mfault,cmd,leaf,quad);
 reg[226:0]ds[0:431];reg[190:0]ex[0:22367];reg[63:0]sp[0:431];
 integer di,j,first,ns,checks=0,words=0,multi_count=0,reachable=0;
 task tick;begin @(posedge clk);#1;end endtask
 initial begin
 $readmemh("coalesce_desc.mem",ds);$readmemh("coalesce_expect.mem",ex);$readmemh("coalesce_span.mem",sp);
 for(di=0;di<432;di=di+1)begin
 @(negedge clk);rst=0;dv=0;step=0;repeat(2)tick();@(negedge clk);rst=1;desc=ds[di];dv=1;tick();@(negedge clk);dv=0;
 first=sp[di][63:32];ns=sp[di][31:0];
 for(j=0;j<ns;j=j+1)begin
 {ea,ed,ef,ec,el,cmdexp,eleaf,eq,wr,wc,bufid,epoch}=ex[first+j];step=1;tick();
 if(!av||fault||{sa,da,fmt,count,last}!=={ea,ed,ef,ec,el})$fatal(1,"COALESCE_COUNTER_MISMATCH descriptor=%0d uop=%0d count=%0d expected=%0d",di,j,count,ec);
 if(sa[36:35]==2)begin
 if(!lv||mfault||{cmd,leaf,quad}!=={cmdexp,eleaf,eq})$fatal(1,"COALESCE_62BIT_MISMATCH descriptor=%0d uop=%0d",di,j);
 reachable=reachable+1;
 end else if(lv||!mfault)$fatal(1,"COALESCE_UNBOUND_STACK_ESCAPED");
 checks=checks+1;words=words+count;if(count>1)multi_count=multi_count+1;@(negedge clk);
 end
 step=0;tick();if(active||fault||av)$fatal(1,"COALESCE_DRAIN");
 end
 $display("PASS COALESCE_NATIVE_TOK_EXPANSION descriptors=432 uops=%0d words=%0d multielement_uops=%0d currentstack2commands=%0d formats=6 linear/stripe4 src/dststrides0/1/3 row_and_sector_edges",checks,words,multi_count,reachable);$finish;
 end
endmodule
