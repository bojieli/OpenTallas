`timescale 1ns/1ps
// HBM-NEXT-UNITS IDXQ 2026-10-19: ot_hnx_idxn_calendar CW=1 (compact stream windows: one shared head row + a 2-row ring
// per stream) against CW=0 (the verified IDXN structure: 4-row head copy + 4-row prefetch window per stream), lockstep on
// EVERY edge and EVERY output (row_start, OPR / QEM / KEY / PRE / SEL / LIN / LOUT classes, done, fault), same programme,
// same start / length / n_rows / pitch. Programmes: the compiled IDXN frame (chain 14) and random 2,048-word frames (every
// word of all 256 frame rows; collisions fault in both copies and must fault on the same edge).
// Mutants (forced on the CW=1 copy): +MUT=1 ring bypass off (a row fetched on the last edge of the previous row is read
// from the stale ring), +MUT=2 ring slot pinned to 0 (odd rows overwrite even rows), +MUT=3 head row 0 not shared (row 0
// read from the ring).
module tb_hnx_idxn_cw;
 reg clk=0;always #5 clk=~clk;
 reg rst_n=0,we=0,start=0;reg[7:0]addr=0;reg[255:0]data=0;reg[11:0]len=0,pitch=232;reg[4:0]nrows=1;
 integer mutation=0,cyc=0,errors=0,edges=0,starts=0,dones=0,faults0=0,faults1=0,busy=0;
 localparam integer OW=1+1+1+7+1+5+1+8+5+1+8+16+8+32+1+1+5+1+4+5+1+1;
 wire[OW-1:0]o0,o1;
 for(genvar c=0;c<2;c=c+1)begin:g
  wire rs,ow,oq,qe,kv,pv,lc,lf,le,dn,ft;wire[6:0]oi;wire[4:0]qh,kr,lr,er;wire[7:0]ki,pi;wire[3:0]eg;
  wire[15:0]sop;wire[7:0]sps;wire[31:0]sad;
  ot_hnx_idxn_calendar #(.K(8),.S(4),.CW(c)) cal(.clk(clk),.clk_mem(clk),.rst_n(rst_n),.program_we(we),.program_addr(addr),
   .program_data(data),.start(start),.length(len),.n_rows(nrows),.pitch(pitch),.row_start(rs),.opr_weight(ow),.opr_query(oq),
   .opr_index(oi),.qem_v(qe),.qem_head(qh),.key_v(kv),.key_index(ki),.key_row(kr),.pre_v(pv),.pre_index(pi),.sel_op(sop),
   .sel_pass(sps),.sel_addr(sad),.lin_clear(lc),.lin_flush(lf),.lin_row(lr),.lout_emit(le),.lout_group(eg),.lout_row(er),
   .done(dn),.fault(ft));
  wire[OW-1:0]o={rs,ow,oq,oi,qe,qh,kv,ki,kr,pv,pi,sop,sps,sad,lc,lf,lr,le,eg,er,dn,ft};
 end
 assign o0=g[0].o;assign o1=g[1].o;
 for(genvar k=0;k<8;k=k+1)begin:gm
  initial begin
   #1;
   if(mutation==1)force g[1].cal.gs[k].gring.byp=1'b0;
   if(mutation==2)force g[1].cal.gs[k].fslot=2'd0;
  end
 end
 initial begin #1; if(mutation==3)force g[1].cal.head=1024'd0; end
 always @(negedge clk)if(rst_n)begin
  cyc++;
  if(o0!==o1)begin errors++;if(errors<10)$display("CWBAD cyc%0d xor %h",cyc,o0^o1);end
  if(|o0)edges++; if(g[0].rs)starts++; if(g[0].dn)dones++; if(g[0].ft)faults0=1; if(g[1].ft)faults1=1;
 end
 reg[31:0]prog[0:2047];integer rows=1,plen=0,rnd=0,seed=1;
 initial begin
  if($value$plusargs("MUT=%d",mutation))begin end
  if($value$plusargs("ROWS=%d",rows))begin end
  if($value$plusargs("PITCH=%d",pitch))begin end
  if(!$value$plusargs("LEN=%d",plen))$fatal(1,"+LEN");
  for(integer i=0;i<2048;i=i+1)prog[i]=0;
  $readmemh("cal.hex",prog);
  repeat(4)@(negedge clk);rst_n=1;repeat(4)@(negedge clk);
  for(integer r=0;r<256;r=r+1)begin
   we=1;addr=8'(r);for(integer j=0;j<8;j=j+1)data[j*32+:32]=prog[r*8+j];@(negedge clk);
  end
  we=0;repeat(8)@(negedge clk);
  len=12'(plen);nrows=5'(rows);start=1;@(negedge clk);start=0;
  repeat(plen+(rows-1)*pitch+40)@(negedge clk);
  $display("IDXN_CW rows%0d pitch%0d len%0d mut%0d errors%0d active_edges%0d row_starts%0d dones%0d fault_cw0 %0d fault_cw1 %0d",
   rows,pitch,plen,mutation,errors,edges,starts,dones,faults0,faults1);
  if(errors||starts!=rows||edges==0)$fatal(1,"IDXN_CW FAIL");
  $display("IDXN_CW PASS");$finish;
 end
endmodule
