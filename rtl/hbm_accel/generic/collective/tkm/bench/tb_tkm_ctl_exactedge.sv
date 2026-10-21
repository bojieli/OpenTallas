`timescale 1ns/1ps
// Minimum actual controller comparison, production params TP192/KMAX2048/NSEG8/HOP3.
// Uses the existing seg bench clock/reset/start/flit calendar and known vector files.
// up0 is an external test stream; the actual SRAM buffer RTL closes the buffer path.
// This proves replica changes against recovered ctl source, not the old full parent.
module tb_tkm_ctl_exactedge;
 parameter integer MUT=0;
 reg clk=0,rst_n=0,start=0,arg_mode=0;always #0.4167 clk=~clk;
 reg[11:0]cfg_n;reg[12:0]cfg_k,cfg_nout;reg[7:0]cfg_g,cfg_gbase;
 reg[15:0]cfg_pf;reg[39:0]cfg_obase,cfg_rbase;reg cfg_has_r;
 reg[3:0]del_slot_i=0,del_valid_i=0;reg[2179:0]del_flit=0;
 reg[343:0]up0=0;wire buf_valid;wire[343:0]buf_data;
 reg[31:0]cfg[0:15],a[0:192*2048-1],b[0:192*2048-1],ns[0:191];
 integer G,N,K,PF,NOUT,HASR,OB,RB,GB,override_nout=0,cyc=0,errors=0,entry_edges=0,write_edges=0,read_edges=0,buffer_edges=0;
 integer seed=32'h1921016;string dir;
 wire r_w_v;
 wire [39:0]r_w_addr;
 wire [15:0]r_w_mask;
 wire [511:0]r_w_data;
 wire r_busy;
 wire r_done;
 wire r_fault;
 wire [31:0]r_stat_cycles;
 wire r_entry_v;
 wire [343:0]r_entry;
 wire r_clr;
 wire [7:0]r_conv_s;
 wire r_buf_wv;
 wire [9:0]r_buf_wa;
 wire [343:0]r_buf_wdata;
 wire r_read_v;
 wire [9:0]r_read_addr;
 wire d_w_v;
 wire [39:0]d_w_addr;
 wire [15:0]d_w_mask;
 wire [511:0]d_w_data;
 wire d_busy;
 wire d_done;
 wire d_fault;
 wire [31:0]d_stat_cycles;
 wire d_entry_v;
 wire [343:0]d_entry;
 wire d_clr;
 wire [7:0]d_conv_s;
 wire d_buf_wv;
 wire [9:0]d_buf_wa;
 wire [343:0]d_buf_wdata;
 wire d_read_v;
 wire [9:0]d_read_addr;
 ot_hgi_coll_tkm_ctl_reference #(.TP(192),.KMAX(2048),.NSEG(8),.HOP(3),.MUT(0)) r(.clk(clk),.rst_n(rst_n),.start(start),.arg_mode(arg_mode),.cfg_n(cfg_n),.cfg_k(cfg_k),.cfg_nout(cfg_nout),.cfg_g(cfg_g),.cfg_gbase(cfg_gbase),.cfg_pf(cfg_pf),.cfg_obase(cfg_obase),.cfg_rbase(cfg_rbase),.cfg_has_r(cfg_has_r),.del_slot_i(del_slot_i),.del_valid_i(del_valid_i),.del_flit(del_flit),.up0(up0),.buf_valid(buf_valid),.buf_data(buf_data),.w_v(r_w_v),.w_addr(r_w_addr),.w_mask(r_w_mask),.w_data(r_w_data),.busy(r_busy),.done(r_done),.fault(r_fault),.stat_cycles(r_stat_cycles),.entry_v(r_entry_v),.entry(r_entry),.clr(r_clr),.conv_s(r_conv_s),.buf_wv(r_buf_wv),.buf_wa(r_buf_wa),.buf_wdata(r_buf_wdata),.read_v(r_read_v),.read_addr(r_read_addr));
 ot_hgi_coll_tkm_ctl #(.TP(192),.KMAX(2048),.NSEG(8),.HOP(3),.MUT(MUT)) d(.clk(clk),.rst_n(rst_n),.start(start),.arg_mode(arg_mode),.cfg_n(cfg_n),.cfg_k(cfg_k),.cfg_nout(cfg_nout),.cfg_g(cfg_g),.cfg_gbase(cfg_gbase),.cfg_pf(cfg_pf),.cfg_obase(cfg_obase),.cfg_rbase(cfg_rbase),.cfg_has_r(cfg_has_r),.del_slot_i(del_slot_i),.del_valid_i(del_valid_i),.del_flit(del_flit),.up0(up0),.buf_valid(buf_valid),.buf_data(buf_data),.w_v(d_w_v),.w_addr(d_w_addr),.w_mask(d_w_mask),.w_data(d_w_data),.busy(d_busy),.done(d_done),.fault(d_fault),.stat_cycles(d_stat_cycles),.entry_v(d_entry_v),.entry(d_entry),.clr(d_clr),.conv_s(d_conv_s),.buf_wv(d_buf_wv),.buf_wa(d_buf_wa),.buf_wdata(d_buf_wdata),.read_v(d_read_v),.read_addr(d_read_addr));
 ot_hgi_coll_tkm_buffer #(.DW(344)) actual_buffer(.clk(clk),.rst_n(rst_n),.w_v(r_buf_wv),.w_addr(r_buf_wa),.w_data(r_buf_wdata),.r_v(r_read_v),.r_addr(r_read_addr),.rd_v(buf_valid),.rd_data(buf_data));
 function automatic[544:0]make_flit(input integer rank_,f);
  reg[544:0]v;v=0;v[544]=1;v[535:528]=8'(GB+rank_);v[527:512]=16'(rank_*PF+f);
  for(integer j=0;j<8;j=j+1)begin
   v[32*j+:32]=(8*f+j<int'(ns[rank_]))?a[rank_*2048+8*f+j]:32'hffffffff;
   v[256+32*j+:32]=(8*f+j<int'(ns[rank_]))?b[rank_*2048+8*f+j]:32'hffffffff;
  end return v;
 endfunction
 task mismatch(input string port_);begin
  errors=errors+1;if(errors<9)$display("TKM_CTL_EXACTEDGE_MISMATCH cycle=%0d port=%s tick=%0d",cyc,port_,r.tick);
 end endtask
 always @(negedge clk)begin
  cyc=cyc+1;
  if(rst_n)begin
   if(r_w_v!==d_w_v)mismatch("w_v");
   if(r_busy!==d_busy)mismatch("busy");
   if(r_done!==d_done)mismatch("done");
   if(r_fault!==d_fault)mismatch("fault");
   if(r_entry_v!==d_entry_v)mismatch("entry_v");
   if(r_clr!==d_clr)mismatch("clr");
   if(r_conv_s!==d_conv_s)mismatch("conv_s");
   if(r_buf_wv!==d_buf_wv)mismatch("buf_wv");
   if(r_read_v!==d_read_v)mismatch("read_v");
   if((r_busy||r_done)&&r_stat_cycles!==d_stat_cycles)mismatch("stat_cycles");
   if((r_w_v)&&r_w_addr!==d_w_addr)mismatch("w_addr");
   if((r_w_v)&&r_w_mask!==d_w_mask)mismatch("w_mask");
   if((r_w_v)&&r_w_data!==d_w_data)mismatch("w_data");
   if((r_entry_v)&&r_entry!==d_entry)mismatch("entry");
   if((r_buf_wv)&&r_buf_wa!==d_buf_wa)mismatch("buf_wa");
   if((r_buf_wv)&&r_buf_wdata!==d_buf_wdata)mismatch("buf_wdata");
   if((r_read_v)&&r_read_addr!==d_read_addr)mismatch("read_addr");
   if(r_entry_v)entry_edges=entry_edges+1;if(r_w_v)write_edges=write_edges+1;
   if(r_read_v)read_edges=read_edges+1;if(r_buf_wv)buffer_edges=buffer_edges+1;
  end
  del_slot_i=0;del_valid_i=0;del_flit=0;
  if(r.busy_c&&(r.tick+1)>=8&&(r.tick+1)<r.ingress_end&&((r.tick+1-8)%8==0))begin
   for(integer l=0;l<4;l=l+1)begin:drive
    integer ix;ix=((int'(r.tick)+1-8)/8)*4+l;
    if(ix<G*PF)begin del_slot_i[l]=1;del_valid_i[l]=1;del_flit[545*l+:545]=make_flit((ix/PF+128)%G,ix%PF);end
   end
  end
  for(integer j=0;j<10;j=j+1)begin seed=(seed<<13)^seed;seed=(seed>>17)^seed;seed=(seed<<5)^seed;up0[32*j+:32]=32'(seed);end
  for(integer j=0;j<4;j=j+1)begin up0[86*j+85]=1'b1;up0[86*j+84]=1'(cyc/4);end
 end
 initial begin
  integer expected,elapsed;
  if(!$value$plusargs("DIR=%s",dir))$fatal(1,"missing DIR");
  if($value$plusargs("NOUT=%d",override_nout))begin end
  $readmemh({dir,"/cfg.hex"},cfg);$readmemh({dir,"/a.hex"},a);$readmemh({dir,"/b.hex"},b);$readmemh({dir,"/n.hex"},ns);
  G=cfg[0];N=cfg[1];K=cfg[2];HASR=cfg[4];NOUT=override_nout?override_nout:cfg[5];OB=cfg[9];RB=cfg[10];GB=G>=96?0:(int'(cfg[3])/G)*G;PF=(N+7)/8;
  cfg_n=12'(N);cfg_k=13'(K);cfg_nout=13'(NOUT);cfg_g=8'(G);cfg_gbase=8'(GB);cfg_pf=16'(PF);cfg_obase=40'(OB);cfg_rbase=40'(RB);cfg_has_r=1'(HASR);
  expected=8+((G*PF+3)/4)*8+2*(3*32+8+42+4)+3*((NOUT+3)/4)+24+1;
  repeat(10)@(negedge clk);rst_n=1;repeat(10)@(negedge clk);start=1;@(negedge clk);start=0;
  elapsed=0;while(!(r_done&&d_done)&&elapsed<expected+20)begin @(posedge clk);elapsed=elapsed+1;end
  if(!(r_done&&d_done))mismatch("timeout");
  repeat(3)@(negedge clk);
  if(!entry_edges||!write_edges||!read_edges||!buffer_edges)mismatch("coverage");
  if(!(r_done===d_done))mismatch("done");
  if(errors)$fatal(1,"TKM_CTL_EXACTEDGE FAIL mismatches=%0d entries=%0d writes=%0d reads=%0d buffer=%0d",errors,entry_edges,write_edges,read_edges,buffer_edges);
  $display("TKM_CTL_EXACTEDGE PASS MUT=%0d cycles=%0d entries=%0d writes=%0d reads=%0d buffer=%0d",MUT,cyc,entry_edges,write_edges,read_edges,buffer_edges);$finish;
 end
endmodule
