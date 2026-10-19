`timescale 1ns/1ps
// Lockstep: folded host receive tile ot_hbm_host_cp_rx (landing + packet in one tile, no 512-b bus, packet RXREG=0,
// regional reset relays) against the SEPARATE pair it replaces (ot_hbm_host_landing256 PINREG=1 -> 512-b bus ->
// ot_hbm_host_packet_static RXREG=1, both reset by one relayed rst_n with the same 2+1 stages). Each side drives its
// own REAL ot_hbm_host_static_ingress; the endpoint-face credit model reacts to the reference. Every output of the
// fold (pop, f_send, f_flit, AXI master, land_fault, protocol_fault) and of its ingress is compared on every edge
// (4-state !==). Traffic: two legal configuration programmes (F20/8xF24 -> cfg_v, F28, F2c, F30 status reads) around a
// mid-run reset, then random F20..F30 writes/reads, malformed / unknown-op packets and a nonzero flit header (sticky
// faults), irq/fault toggles, landing back-pressure through the pop credit. MUT 1/2 must FAIL.
module tb_hbm_host_cp_rx_lockstep;
parameter integer MUT=0;
parameter integer NPKT=900;
reg clk=0,rst_n=0; always #1 clk=~clk;
reg in_v=0; reg [544:0] in_data=0; reg t_cr=0; reg irq=0,fault=0;
// ---------------- DUT: fold
wire d_pop,d_send,d_lf,d_pf; wire [544:0] d_flit;
wire d_awv,d_wv,d_br,d_arv,d_rr; wire [11:0] d_awa,d_ara; wire [31:0] d_wd,d_rd; wire [3:0] d_ws;
wire d_awr,d_wr,d_bv,d_arr,d_rv; wire [1:0] d_bresp;
ot_hbm_host_cp_rx #(.MUT(MUT)) dut(.clk(clk),.rst_n(rst_n),.in_v(in_v),.in_data(in_data),.pop(d_pop),
 .f_send(d_send),.f_flit(d_flit),.t_cr(t_cr),
 .s_awvalid(d_awv),.s_awready(d_awr),.s_awaddr(d_awa),.s_wvalid(d_wv),.s_wready(d_wr),.s_wdata(d_wd),.s_wstrb(d_ws),
 .s_bvalid(d_bv),.s_bresp(d_bresp),.s_bready(d_br),.s_arvalid(d_arv),.s_arready(d_arr),.s_araddr(d_ara),
 .s_rvalid(d_rv),.s_rready(d_rr),.s_rdata(d_rd),.irq(irq),.fault(fault),.land_fault(d_lf),.protocol_fault(d_pf));
wire d_cfgv,d_descv,d_lv,d_if; wire [7:0] d_ct; wire [11:0] d_ca,d_db; wire [255:0] d_cd; wire [12:0] d_dl; wire [15:0] d_dlp;
ot_hbm_host_static_ingress #(.TARGET_MASK(256'd1<<112)) d_ing(.clk(clk),.rst_n(rst_n),
 .s_awvalid(d_awv),.s_awready(d_awr),.s_awaddr(d_awa),.s_wvalid(d_wv),.s_wready(d_wr),.s_wdata(d_wd),.s_wstrb(d_ws),
 .s_bvalid(d_bv),.s_bready(d_br),.s_bresp(d_bresp),.s_arvalid(d_arv),.s_arready(d_arr),.s_araddr(d_ara),
 .s_rvalid(d_rv),.s_rready(d_rr),.s_rdata(d_rd),.block_ready(1'b0),.program_active(1'b0),.program_fault(1'b0),
 .cfg_v(d_cfgv),.cfg_target(d_ct),.cfg_addr(d_ca),.cfg_data(d_cd),.desc_v(d_descv),.desc_base(d_db),.desc_limit(d_dl),
 .desc_loops(d_dlp),.launch_v(d_lv),.fault(d_if));
// ---------------- reference: the separate pair, one relayed reset
wire [0:0] r_rst;
ot_rst_relay #(.REGIONS(1),.SYNC_STAGES(2),.TREE_STAGES(1)) r_rr(.clk(clk),.rst_n_in(rst_n),.rst_n(r_rst));
wire r_ov,r_ordy,r_pop,r_lf; wire [511:0] r_od;
ot_hbm_host_landing256 #(.PINREG(1)) r_land(.clk(clk),.rst_n(r_rst[0]),.in_v(in_v),.in_data(in_data),
 .out_v(r_ov),.out_data(r_od),.out_ready(r_ordy),.pop(r_pop),.fault(r_lf));
wire r_send,r_pf; wire [544:0] r_flit;
wire r_awv,r_wv,r_br,r_arv,r_rr2; wire [11:0] r_awa,r_ara; wire [31:0] r_wd,r_rd; wire [3:0] r_ws;
wire r_awr,r_wr,r_bv,r_arr,r_rv; wire [1:0] r_bresp;
ot_hbm_host_packet_static r_pkt(.clk(clk),.rst_n(r_rst[0]),.rx_valid(r_ov),.rx_packet(r_od),.rx_ready(r_ordy),
 .f_send(r_send),.f_flit(r_flit),.t_cr(t_cr),
 .s_awvalid(r_awv),.s_awready(r_awr),.s_awaddr(r_awa),.s_wvalid(r_wv),.s_wready(r_wr),.s_wdata(r_wd),.s_wstrb(r_ws),
 .s_bvalid(r_bv),.s_bresp(r_bresp),.s_bready(r_br),.s_arvalid(r_arv),.s_arready(r_arr),.s_araddr(r_ara),
 .s_rvalid(r_rv),.s_rready(r_rr2),.s_rdata(r_rd),.irq(irq),.fault(fault),.protocol_fault(r_pf));
wire r_cfgv,r_descv,r_lv,r_if; wire [7:0] r_ct; wire [11:0] r_ca,r_db; wire [255:0] r_cd; wire [12:0] r_dl; wire [15:0] r_dlp;
ot_hbm_host_static_ingress #(.TARGET_MASK(256'd1<<112)) r_ing(.clk(clk),.rst_n(rst_n),
 .s_awvalid(r_awv),.s_awready(r_awr),.s_awaddr(r_awa),.s_wvalid(r_wv),.s_wready(r_wr),.s_wdata(r_wd),.s_wstrb(r_ws),
 .s_bvalid(r_bv),.s_bready(r_br),.s_bresp(r_bresp),.s_arvalid(r_arv),.s_arready(r_arr),.s_araddr(r_ara),
 .s_rvalid(r_rv),.s_rready(r_rr2),.s_rdata(r_rd),.block_ready(1'b0),.program_active(1'b0),.program_fault(1'b0),
 .cfg_v(r_cfgv),.cfg_target(r_ct),.cfg_addr(r_ca),.cfg_data(r_cd),.desc_v(r_descv),.desc_base(r_db),.desc_limit(r_dl),
 .desc_loops(r_dlp),.launch_v(r_lv),.fault(r_if));
// ---------------- compare every edge
wire [544:0] dvec={d_pop,d_send,d_lf,d_pf,d_awv,d_wv,d_br,d_arv,d_rr,d_awa,d_ara,d_wd,d_ws,d_cfgv,d_descv,d_lv,d_if,d_ct,d_ca,d_cd[63:0]};
wire [544:0] rvec={r_pop,r_send,r_lf,r_pf,r_awv,r_wv,r_br,r_arv,r_rr2,r_awa,r_ara,r_wd,r_ws,r_cfgv,r_descv,r_lv,r_if,r_ct,r_ca,r_cd[63:0]};
integer edges=0,mism=0,flits=0,cfgs=0,rds=0,pfs=0,lfs=0,started=0;
always @(posedge clk) if(started) begin
 edges=edges+1;
 if(dvec!==rvec || d_flit!==r_flit || d_cd!==r_cd || d_db!==r_db || d_dl!==r_dl || d_dlp!==r_dlp) begin
  mism=mism+1; if(mism<=5) $display("MISMATCH t=%0t pop %b/%b send %b/%b aw %b/%b w %b/%b ar %b/%b pf %b/%b lf %b/%b flit_eq %0d",$time,
   d_pop,r_pop,d_send,r_send,d_awv,r_awv,d_wv,r_wv,d_arv,r_arv,d_pf,r_pf,d_lf,r_lf,d_flit===r_flit);
 end
 if(r_send) flits=flits+1; if(r_cfgv) cfgs=cfgs+1; if(r_rv && r_rr2) rds=rds+1;
end
// ---------------- endpoint face model (reacts to the reference): landing credit 256, tx credit after a delay
integer lcred=256, cyc=0, crq[0:65535], crh=0, crt=0, seed=17;
always @(posedge clk) begin
 cyc<=cyc+1; t_cr<=0;
 if(!rst_n) begin crh=0; crt=0; end
 else begin
  if(r_send) begin crq[crt]=cyc+3+($unsigned($random(seed))%11); crt=crt+1; end
  if(crh!=crt && crq[crh]<=cyc) begin t_cr<=1; crh=crh+1; end
 end
end
function [511:0] pk(input [7:0] op,input [7:0] ver,input [15:0] id,input [11:0] a,input [31:0] d,input [3:0] st,input junk);
 pk={340'd0,junk,1'b0,2'd0,4'd0,st,32'd0,d,52'd0,a,id,ver,op}; endfunction
task send(input [544:0] w); begin
 @(negedge clk); while(lcred==0) @(negedge clk);
 in_v=1; in_data=w; lcred=lcred-1; @(negedge clk); in_v=0; in_data=$random(seed);
 // landing credit returns on the reference pop (sampled at negedge: pop is a flop Q)
end endtask
always @(negedge clk) if(started && r_pop) lcred=lcred+1;
integer i,j,k,r,gap,pid=0; reg [11:0] a; reg [7:0] op; reg [544:0] w;
task legal(input [7:0] op_i,input [11:0] a_i,input [31:0] d_i); begin
 send({33'd0,pk(op_i,8'd1,pid[15:0],a_i,d_i,4'hf,1'b0)}); pid=pid+1;
 gap=$unsigned($random(seed))%4; repeat(gap) @(negedge clk);
 if(($unsigned($random(seed))%37)==0) irq=~irq;
 if(($unsigned($random(seed))%91)==0) fault=~fault;
end endtask
// legal configuration programme: F20 select (target 112), 8 x F24 pieces -> one cfg_v, F28 range, F2c loops; F30 reads
task prog_rows(input integer rows); begin
 for(j=0;j<rows;j=j+1) begin
  legal(8'h01,12'hf20,{12'd0,j[11:0],8'd112});
  for(k=0;k<8;k=k+1) begin legal(8'h01,12'hf24,$random(seed)); if(k==3) legal(8'h02,12'hf30,0); end
  legal(8'h01,12'hf28,{7'd0,13'd200+j[12:0],12'd10});
  legal(8'h01,12'hf2c,{16'd0,16'd1+j[15:0]});
  if(j%3==0) legal(8'h02,$random(seed),0);
 end
end endtask
initial begin
 repeat(3) @(posedge clk); started=1; repeat(4) @(posedge clk); rst_n=1; repeat(8) @(posedge clk);
 prog_rows(40); repeat(4000) @(negedge clk);   // ~490 legal packets, 40 cfg_v; drain before the reset
 // mid-run reset with traffic in flight
 legal(8'h01,12'hf20,{12'd0,12'd7,8'd112}); legal(8'h01,12'hf24,32'h1234);
 repeat(1) @(negedge clk); rst_n=0; repeat(6) @(negedge clk); rst_n=1; lcred=256; repeat(10) @(negedge clk);
 prog_rows(40); repeat(4000) @(negedge clk);   // drain: the landing FIFO runs ahead of the AXI pace
 // random / malformed / unknown-op traffic (faults the ingress and the packet: sticky)
 for(i=0;i<NPKT;i=i+1) begin
  r=$unsigned($random(seed))%100;
  a=(r<35)?12'hf24:(r<45)?12'hf20:(r<52)?12'hf28:(r<58)?12'hf2c:(r<62)?12'hf30:$random(seed);
  op=(r<70)?8'h01:(r<90)?8'h02:(r<94)?8'h03:8'h01;
  w={33'd0,pk(op,(r>=97)?8'd2:8'd1,i[15:0],a,$random(seed),4'hf,(r==96))};
  if(i==NPKT/2) w[530]=1'b1;                       // nonzero reserved flit header -> landing fault (sticky)
  send(w);
  gap=$unsigned($random(seed))%4; repeat(gap) @(negedge clk);
  if(($unsigned($random(seed))%37)==0) irq=~irq;
  if(($unsigned($random(seed))%91)==0) fault=~fault;
 end
 repeat(2000) @(posedge clk);
 pfs=r_pf; lfs=r_lf;
 if(mism==0 && edges>10000 && flits>1000 && cfgs>=80 && rds>100 && pfs==1 && lfs==1)
  $display("HOST_CP_RX_LOCKSTEP_PASS edges=%0d packets=%0d flits=%0d cfg=%0d reads=%0d mism=0",edges,pid+NPKT,flits,cfgs,rds);
 else $display("HOST_CP_RX_LOCKSTEP_FAIL mism=%0d edges=%0d flits=%0d cfg=%0d reads=%0d pf=%0d lf=%0d",mism,edges,flits,cfgs,rds,pfs,lfs);
 $finish;
end
initial begin #20000000; $display("HOST_CP_RX_LOCKSTEP_FAIL timeout"); $finish; end
endmodule
