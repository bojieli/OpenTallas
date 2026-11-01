`timescale 1ps/1ps
module tb_pages;
 reg clk=0,rst_n=0;always begin #416 clk=1;#417 clk=0;end
 reg cfg_v=0,desc_v=0,launch_v=0;reg[11:0]cfg_addr=0;reg[255:0]cfg_data=0;
 reg[12:0]limit=128;wire cmd_v,configured,fault,active;wire[307:0]cmd;wire[31:0]cycle;
 ot_hgi_dma_back_cp_collar dut(.clk(clk),.rst_n(rst_n),.tgt(8'd106),.cfg_v(cfg_v),.cfg_target(8'd106),.cfg_addr(cfg_addr),.cfg_data(cfg_data),.desc_v(desc_v),.desc_base(12'd0),.desc_limit(limit),.desc_loops(16'd1),.launch_v(launch_v),.tgt_active(1'b0),.tgt_fault(1'b0),.cmd_v(cmd_v),.cmd(cmd),.cycle(cycle),.configured(configured),.fault(fault),.active(active));
 reg[255:0]words[0:255];reg[307:0]gold[0:127];reg[31:0]at[0:127];
 integer pg=0,seen=0,total=0,base=-1,mut_active=0,last_at,n;
 always @(negedge clk)if(rst_n)begin
 if(fault)$fatal(1,"NATIVE_CP_PAGE_FAULT page=%0d seen=%0d",pg,seen);
 if(cmd_v)begin
 if(seen>=limit)$fatal(1,"EXTRA_PAGE_COMMAND");
 if(base<0)base=integer'(cycle)-integer'(at[seen]);
 if(integer'(cycle)!=base+integer'(at[seen])||cmd[307:64]!==gold[seen][307:64]||cmd[31:0]!==gold[seen][31:0]+32'(base)||cmd[63:32]!==gold[seen][63:32]+32'(base))$fatal(1,"PAGE_BYTE_DATE_MISMATCH page=%0d command=%0d",pg,seen);
 seen=seen+1;total=total+1;
 end
 end
 task tick;begin @(posedge clk);#1;end endtask
 initial begin
 if($value$plusargs("MUT_ACTIVE=%d",mut_active))begin end
 repeat(32)tick();rst_n=1;repeat(16)tick();
 for(pg=0;pg<2;pg=pg+1)begin
 seen=0;base=-1;
 if(pg==0)begin limit=128;last_at=@@LAST_AT0@@;$readmemh("page0.hex",words,0,255);$readmemh("page0_cmd.hex",gold,0,127);$readmemh("page0_at.hex",at,0,127);end
 else begin limit=12;last_at=@@LAST_AT1@@;$readmemh("page1.hex",words,0,23);$readmemh("page1_cmd.hex",gold,0,11);$readmemh("page1_at.hex",at,0,11);end
 for(n=0;n<2*limit;n=n+1)begin cfg_addr=12'h800+12'(n);cfg_data=words[n];cfg_v=1;tick();cfg_v=0;tick();end
 repeat(16)tick();desc_v=1;tick();desc_v=0;repeat(16)tick();
 if(!configured)$fatal(1,"PAGE_NOT_ARMED");
 launch_v=1;tick();launch_v=0;
 if(mut_active!=0)begin repeat(64)tick();cfg_addr=12'h800;cfg_v=1;tick();cfg_v=0;end
 repeat(last_at+64)tick();
 if(seen!=limit||active||configured)$fatal(1,"PAGE_DRAIN seen=%0d limit=%0d active=%b configured=%b",seen,limit,active,configured);
 $display("NATIVE_CP_PAGE_PASS page=%0d commands=%0d base=%0d",pg,seen,base);
 end
 if(total!=140)$fatal(1,"PAGE_CONSERVATION");
 $display("PASS NATIVE_CW308_PAGING140 commands pages=2 capacity=128 exact833ps");$finish;
 end
endmodule
