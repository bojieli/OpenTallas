`timescale 1ns/1ps
// Transport unit boundary test. The slaves below are declared AXI test
// endpoints, not native programme or arithmetic qualification.
module tb_host_cfg_transport;
 parameter integer MUT=0;
 reg clk=0;always #3 clk=~clk;
 reg slow=0;always #4 slow=~slow;
 reg shifted=0;initial begin #1.5;forever #3 shifted=~shifted;end
 wire[2:0]dc={shifted,slow,clk};reg rst_n=0;
 reg[11:0]aa=0,ra=0;reg av=0,wv=0,br=0,arv=0,rr=0;reg[31:0]wd=0;reg[3:0]ws=15;
 wire awr,wr,bv,arr,rv,fault;wire[1:0]bres,rres;wire[31:0]rd;
 wire[2:0][11:0]ma,mra,da,dra;wire[2:0][31:0]mwd,mrd,dwd,drd;
 wire[2:0][3:0]mws,dws;wire[2:0][1:0]mbres,mrres,dbres,drres;
 wire[2:0]mav,mar,mwv,mwr,mbv,mbr,mrav,mrar,mrv,mrr;
 wire[2:0]dav,dar,dwv,dwr,dbv,dbr,drav,drar,drv,drr;
 integer expected_dest=0;reg[11:0]expected_addr=0;reg[31:0]expected_data=0;reg[3:0]expected_strb=15;
 wire[2:0][31:0]write_count,read_count;
 ot_hbm_host_cfg_demux #(.MUT(MUT==3?1:0)) demux(.clk(clk),.rst_n(rst_n),
 .s_awaddr(aa),.s_awvalid(av),.s_awready(awr),.s_wdata(wd),.s_wstrb(ws),.s_wvalid(wv),.s_wready(wr),
 .s_bresp(bres),.s_bvalid(bv),.s_bready(br),.s_araddr(ra),.s_arvalid(arv),.s_arready(arr),
 .s_rdata(rd),.s_rresp(rres),.s_rvalid(rv),.s_rready(rr),
 .m_awaddr(ma),.m_awvalid(mav),.m_awready(mar),.m_wdata(mwd),.m_wstrb(mws),.m_wvalid(mwv),.m_wready(mwr),
 .m_bresp(mbres),.m_bvalid(mbv),.m_bready(mbr),.m_araddr(mra),.m_arvalid(mrav),.m_arready(mrar),
 .m_rdata(mrd),.m_rresp(mrres),.m_rvalid(mrv),.m_rready(mrr),.fault(fault));
 for(genvar g=0;g<3;g=g+1)begin:ports
  ot_hbm_host_cfg_cdc #(.MUT(MUT==1?1:(MUT==2?2:0))) cdc(.s_clk(clk),.m_clk(dc[g]),.rst_n(rst_n),
  .s_awaddr(ma[g]),.s_awvalid(mav[g]),.s_awready(mar[g]),.s_wdata(mwd[g]),.s_wstrb(mws[g]),.s_wvalid(mwv[g]),.s_wready(mwr[g]),
  .s_bresp(mbres[g]),.s_bvalid(mbv[g]),.s_bready(mbr[g]),.s_araddr(mra[g]),.s_arvalid(mrav[g]),.s_arready(mrar[g]),
  .s_rdata(mrd[g]),.s_rresp(mrres[g]),.s_rvalid(mrv[g]),.s_rready(mrr[g]),
  .m_awaddr(da[g]),.m_awvalid(dav[g]),.m_awready(dar[g]),.m_wdata(dwd[g]),.m_wstrb(dws[g]),.m_wvalid(dwv[g]),.m_wready(dwr[g]),
  .m_bresp(dbres[g]),.m_bvalid(dbv[g]),.m_bready(dbr[g]),.m_araddr(dra[g]),.m_arvalid(drav[g]),.m_arready(drar[g]),
  .m_rdata(drd[g]),.m_rresp(drres[g]),.m_rvalid(drv[g]),.m_rready(drr[g]));
  host_cfg_boundary_slave #(.ID(g)) slave(.clk(dc[g]),.rst_n(rst_n),
  .awaddr(da[g]),.awvalid(dav[g]),.awready(dar[g]),.wdata(dwd[g]),.wstrb(dws[g]),.wvalid(dwv[g]),.wready(dwr[g]),
  .bresp(dbres[g]),.bvalid(dbv[g]),.bready(dbr[g]),.araddr(dra[g]),.arvalid(drav[g]),.arready(drar[g]),
  .rdata(drd[g]),.rresp(drres[g]),.rvalid(drv[g]),.rready(drr[g]),
  .expected_dest(expected_dest),.expected_addr(expected_addr),.expected_data(expected_data),.expected_strb(expected_strb),
  .writes(write_count[g]),.reads(read_count[g]));
 end
 task tick;@(posedge clk);#0.5;endtask
 function automatic[11:0]address(input integer d,input integer slot);
 begin
  if(d==0)case(slot)0:address='hf20;1:address='hf24;2:address='hf28;3:address='hf2c;default:address='hf30;endcase
  else begin case(slot)0:address='hf34;1:address='hf38;2:address='hf3c;3:address='hf40;default:address='hf44;endcase
   if(d==2)address[11:8]=4'he;
  end
 end endfunction
 task write32(input[11:0]a,input[31:0]d,input integer order,input integer stalls);
 begin
  @(negedge clk);aa=a;wd=d;
  fork
   begin if(order==2)repeat(3)tick();@(negedge clk);av=1;do @(posedge clk);while(!awr);@(negedge clk);av=0;end
   begin if(order==1)repeat(2)tick();@(negedge clk);wv=1;do @(posedge clk);while(!wr);@(negedge clk);wv=0;end
  join
  while(!bv)tick();if(bres!==a[3:2])$fatal(1,"HOST_CFG_TRANSPORT BRESP got%h expected%h",bres,a[3:2]);
  repeat(stalls)begin tick();if(!bv||bres!==a[3:2])$fatal(1,"HOST_CFG_TRANSPORT heldB");end
  @(negedge clk);br=1;tick();@(negedge clk);br=0;
 end endtask
 task read32(input[11:0]a,input integer stalls);
 reg[31:0]want;
 begin
  want={16'h4a11,2'(expected_dest),2'b0,4'hf,a[7:0]};
  @(negedge clk);ra=a;arv=1;do @(posedge clk);while(!arr);@(negedge clk);arv=0;
  while(!rv)tick();if(rres!==a[3:2]||rd!==want)$fatal(1,"HOST_CFG_TRANSPORT RRESP/data got%h/%h expected%h",rres,rd,want);
  repeat(stalls)begin tick();if(!rv||rres!==a[3:2]||rd!==want)$fatal(1,"HOST_CFG_TRANSPORT heldR");end
  @(negedge clk);rr=1;tick();@(negedge clk);rr=0;
 end endtask
 reg[11:0]a;integer before_w,before_r;
 initial begin
  repeat(8)tick();rst_n=1;repeat(8)tick();
  for(integer n=0;n<16;n=n+1)for(integer d=0;d<3;d=d+1)for(integer slot=0;slot<5;slot=slot+1)begin
   a=address(d,slot);expected_dest=d;expected_addr={4'hf,a[7:0]};expected_data=32'hfe300000^32'(n*15+d*5+slot);expected_strb=4'(n);ws=expected_strb;
   write32(a,expected_data,n%3,n%7);read32(a,n%5);
  end
  for(integer d=0;d<3;d=d+1)if(write_count[d]!=80||read_count[d]!=80)$fatal(1,"HOST_CFG_TRANSPORT count port%0d",d);
  before_w=write_count[0]+write_count[1]+write_count[2];before_r=read_count[0]+read_count[1]+read_count[2];
  @(negedge clk);aa='hd00;wd=1;av=1;wv=1;do @(posedge clk);while(!awr||!wr);@(negedge clk);av=0;wv=0;
  while(!bv)tick();if(bres!=2)$fatal(1,"HOST_CFG_TRANSPORT invalid route accepted");br=1;tick();br=0;
  repeat(20)tick();if(before_w!=write_count[0]+write_count[1]+write_count[2]||before_r!=read_count[0]+read_count[1]+read_count[2])$fatal(1,"HOST_CFG_TRANSPORT invalid route escaped");
  $display("HOST_CFG_TRANSPORT_PASS targets3 writes240 reads240 AW_W_orders3 all_BRESP_RRESP heldresponses invalid_no_dispatch clocks1200_900_shifted");$finish;
 end
 initial begin #1000000;$fatal(1,"HOST_CFG_TRANSPORT watchdog");end
endmodule

module host_cfg_boundary_slave #(parameter integer ID=0)(
 input wire clk,rst_n,input wire[11:0]awaddr,input wire awvalid,output wire awready,
 input wire[31:0]wdata,input wire[3:0]wstrb,input wire wvalid,output wire wready,
 output reg[1:0]bresp,output reg bvalid,input wire bready,
 input wire[11:0]araddr,input wire arvalid,output wire arready,
 output reg[31:0]rdata,output reg[1:0]rresp,output reg rvalid,input wire rready,
 input wire[31:0] expected_dest,input wire[11:0]expected_addr,input wire[31:0]expected_data,input wire[3:0]expected_strb,
 output reg[31:0]writes,reads);
 reg ah,wh;reg[11:0]aa;reg[31:0]wd;reg[3:0]ws;integer cy=0;
 assign awready=rst_n&&!ah&&!bvalid&&(cy%3!=0);
 assign wready=rst_n&&!wh&&!bvalid&&(cy%5!=0);
 assign arready=rst_n&&!rvalid&&(cy%4!=0);
 always @(posedge clk or negedge rst_n)begin
 if(!rst_n)begin ah<=0;wh<=0;bvalid<=0;rvalid<=0;writes<=0;reads<=0;cy<=0;end
 else begin
  cy<=cy+1;
  if(awvalid&&awready)begin ah<=1;aa<=awaddr;end
  if(wvalid&&wready)begin wh<=1;wd<=wdata;ws<=wstrb;end
  if(bvalid&&bready)bvalid<=0;
  if(rvalid&&rready)rvalid<=0;
  if(ah&&wh&&!bvalid)begin
   if(expected_dest!=ID||aa!==expected_addr||wd!==expected_data||ws!==expected_strb)$fatal(1,"HOST_CFG_TRANSPORT target/payload mismatch id%0d expected%0d",ID,expected_dest);
   ah<=0;wh<=0;bvalid<=1;bresp<=aa[3:2];writes<=writes+1;
  end
  if(arvalid&&arready)begin
   if(expected_dest!=ID||araddr!==expected_addr)$fatal(1,"HOST_CFG_TRANSPORT read target/address");
   rvalid<=1;rresp<=araddr[3:2];rdata<={16'h4a11,2'(ID),2'b0,araddr};reads<=reads+1;
  end
 end end
endmodule
