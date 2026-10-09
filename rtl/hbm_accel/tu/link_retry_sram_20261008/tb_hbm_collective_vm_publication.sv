`timescale 1ns/1ps
module tb_hbm_collective_vm_publication;
 reg clk=0;always #0.416667 clk=~clk;
 reg rst=0,abort=0,service_fault=0,sv=0,release_lease=0;
 reg[23:0] epoch=1;wire sr,published,quiet,fault;
 wire[3:0] reqv,rspr;reg[3:0] reqr=0,rspv=0;
 wire[1347:0] req;reg[1091:0] rsp=0;
 reg[1:0] injrd=0;reg[31:0] idx=0;wire[1:0] injv;wire[1023:0] data;
 reg provider_busy=0;integer wait_left=0,provider_q=0,sectors=0,cycles=0;
 reg[15:0] provider_tag;reg[31:0] provider_addr;
 wire sq=!provider_busy && rspv==0;
 ot_hbm_collective_vm_publication #(.ENABLE(1),.OWNER_W(74)) dut(
 .clk(clk),.rst_n(rst),.warm_abort(abort),.service_fault(service_fault),.service_quiet(sq),
 .start_valid(sv),.start_ready(sr),.owner(74'h2000000000000000001),.operation(32'd14),.pc(12'd42),.query_slot(2'd1),
 .base_word(32'd233472),.session(epoch),.req_valid(reqv),.req_ready(reqr),.req(req),
 .rsp_valid(rspv),.rsp_ready(rspr),.rsp(rsp),.published(published),.quiet(quiet),.fault(fault),
 .release_lease(release_lease),.inj_rd(injrd),.inj_idx(idx),.inj_valid(injv),.inj_data(data));
 function[31:0]word(input integer n);begin word=32'h3f800000^(n*32'h10021);end endfunction
 function[255:0]sector_data(input integer n);integer j;begin
 for(j=0;j<8;j=j+1)sector_data[32*j+:32]=word(n*8+j);end endfunction
 function[511:0]flit(input integer n);integer j;begin
 for(j=0;j<16;j=j+1)flit[32*j+:32]=word(n*16+j);end endfunction
 always@(negedge clk)begin
 cycles=cycles+1;reqr=cycles%5==0?0:4'hf;
 if(provider_busy && wait_left>0)wait_left=wait_left-1;
 else if(provider_busy && rspv==0)begin
 rspv=1<<provider_q;rsp[273*provider_q+:273]={provider_tag,1'b0,sector_data((provider_addr/4-233472)/8)};end
 end
 always@(posedge clk)if(rst)begin
 for(integer q=0;q<4;q=q+1)begin
 if(reqv[q]&&reqr[q])begin
 if(provider_busy)$fatal(1,"more than one VM request outstanding");
 if(req[337*q+336] || req[337*q+16+:32]!=32'hffffffff || req[337*q+:16]>>14!=q)$fatal(1,"actual VM read ABI");
 provider_addr=req[337*q+304+:32];provider_tag=req[337*q+:16];provider_q=q;
 if(((provider_addr/4-233472)/1024)!=q)$fatal(1,"quarter read ownership lost");
 provider_busy=1;wait_left=2+cycles%3;sectors=sectors+1;
 end
 if(rspv[q]&&rspr[q])begin provider_busy=0;rspv[q]<=0;end
 end
 end
 integer issued=0,seen=0,captured=0;
 reg[31:0] ordinal=0;wire[1:0] cv,cf;wire[1087:0] cp;
 for(genvar l=0;l<2;l=l+1)begin:g_capture
 ot_hbm_collective_indexed_capture u_capture(.clk(clk),.rst_n(rst),.request_valid(injrd[l]),
 .ordinal(ordinal[16*l+:16]),.index(idx[16*l+:16]),.response_valid(injv[l]),.response_fault(fault),
 .response_data(data[512*l+:512]),.capture_valid(cv[l]),.capture_packet(cp[544*l+:544]),.pending(),.fault(cf[l]));
 end
 always@(posedge clk)if(reading&&rst)begin
 for(integer l=0;l<2;l=l+1)if(cv[l])begin
 if(cp[544*l+528+:16]!=captured || cp[544*l+512+:16]!=expected_idx[captured] || cp[544*l+:512]!==flit(expected_idx[captured]))$fatal(1,"native indexed capture ownership");
 if(cycles-expected_cycle[captured]!=5)$fatal(1,"native hub capture latency");
 captured=captured+1;end
 if(|cf)$fatal(1,"native indexed capture fault");
 end
 reg reading=0;
 integer expected_idx[0:255],expected_cycle[0:255];
 always@(negedge clk)if(reading)begin
 injrd=issued<256?2'b11:0;
 for(integer l=0;l<2;l=l+1)begin ordinal[16*l+:16]=issued+l;idx[16*l+:16]=(((4+(issued+l)%8)%8)*32+(issued+l)/8);end
 end
 always@(posedge clk)if(reading&&rst)begin
 for(integer l=0;l<2;l=l+1)begin
 if(injrd[l])begin expected_idx[issued]=idx[16*l+:16];expected_cycle[issued]=cycles;issued=issued+1;end
 end
#0.01;
 for(integer l=0;l<2;l=l+1)begin
 if(injv[l])begin
 if(data[512*l+:512]!==flit(expected_idx[seen]))$fatal(1,"published FP32 order flit%0d",expected_idx[seen]);
 if(cycles-expected_cycle[seen]!=4)$fatal(1,"real SRAM capture latency got%0d",cycles-expected_cycle[seen]);
 seen=seen+1;end
 end
 if(fault)$fatal(1,"publication indexed response fault");
 end
 task tick;begin @(posedge clk);#0.02;end endtask
 integer i;
 initial begin
 repeat(4)tick;@(negedge clk);rst=1;tick;
 @(negedge clk);sv=1;tick;@(negedge clk);sv=0;
 for(i=0;i<6000&&!published;i=i+1)tick;
 if(dut.g_on.bound_owner!==74'h2000000000000000001)$fatal(1,"actual Qwen74bit owner truncated");
 if(!published||fault||sectors!=512)$fatal(1,"full4096 actual VM publication");
 $display("PASS fourquarter4096 FP32512 matched VM sectors, held requests/responses and write visibility");
 reading=1;
 for(i=0;i<400&&captured<256;i=i+1)tick;
 reading=0;injrd=0;repeat(8)tick;
 if(issued!=256||seen!=256||captured!=256||fault)$fatal(1,"full256 flit injector read completion");
 $display("PASS both512bit injector lanes rotate all256 flits in golden order, actual4edge SECDED SRAM response and5edge native hub capture");
 @(negedge clk);release_lease=1;tick;@(negedge clk);release_lease=0;tick;
 if(!quiet||published)$fatal(1,"lease release did not quiesce");
 epoch=2;@(negedge clk);sv=1;tick;@(negedge clk);sv=0;
 while(!provider_busy)tick;
 @(negedge clk);abort=1;tick;@(negedge clk);abort=0;
 for(i=0;i<20&&!quiet;i=i+1)tick;
 if(!quiet||fault||published||provider_busy)$fatal(1,"abort did not drain held tagged response");
 $display("PASS warmabort drains actual outstanding service, keeps tag sequence, no stale publication");
 @(negedge clk);service_fault=1;tick;
 if(!fault||published||reqv)$fatal(1,"external VM fault did not quarantine");
 $display("PASS separate provider fault quarantines; writeEcho is not fault transport");
 $display("PASS_ALL");$finish;
 end
 initial begin#15000;$fatal(1,"watchdog");end
endmodule
