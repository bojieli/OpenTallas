`timescale 1ns/1ps
`default_nettype none
// lock-step: old core vs new core, every output compared every cycle after reset + flush.
// Stimulus: legal query/weight reads in random order, then illegal ones (both slots, misaligned sectors, wrong sid,
// bank valid without request, missing valid). Bank model answers D edges after the core saw the request.
`ifndef RTX
 `define RTX 4
`endif
`ifndef CYC
 `define CYC 40000
`endif
module tb;
 localparam integer DD=8+`RTX;
 reg clk=0,rst_n=0;
 reg [1:0] sid=1; reg ws=0,qs=0; reg [6:0] qi=0; reg [15:0] wsec=0,qsec=0;
 reg [2055:0] rr=0;
 wire [135:0] rq_g,rq_n; wire bv_g,bv_n,f_g,f_n; wire [4:0] bh_g,bh_n; wire [1:0] bn_g,bn_n; wire [1023:0] bd_g,bd_n; wire [15:0] hw_g,hw_n;
 ot_hbm_idx_vm_query_static_core #(.VM_RT_EXTRA(`RTX)) g(.clk(clk),.rst_n(rst_n),.sid(sid),.weight_slot(ws),.query_slot(qs),.query_index(qi),.weight_sector(wsec),.query_sector(qsec),.vm_rq(rq_g),.vm_rr(rr),.block_v(bv_g),.block_head(bh_g),.block_number(bn_g),.block_data(bd_g),.head_weight(hw_g),.fault(f_g));
 ot_hbm_idx_vm_query_n12s_core #(.VM_RT_EXTRA(`RTX)) n(.clk(clk),.rst_n(rst_n),.sid(sid),.weight_slot(ws),.query_slot(qs),.query_index(qi),.weight_sector(wsec),.query_sector(qsec),.vm_rq(rq_n),.vm_rr(rr),.block_v(bv_n),.block_head(bh_n),.block_number(bn_n),.block_data(bd_n),.head_weight(hw_n),.fault(f_n));
 // bank model: request seen in rq_g at edge e -> valid at vm_rr so that expected lines up (due[D-1] face): D-1 edges after rq_v
 reg [7:0] v_dl [0:DD]; integer i,c,bad_cnt=0,nbv=0,nw=0,nf=0,nchk=0,mode=0,rstn_ok=0,seed=`SEED,nvq=0,nbad_bd=0;
 integer sect=0,nff=0,nmm=0,ndiffdata=0,wn=0,seen_f=0,nint=0; reg [7:0] lastv; reg [31:0] r; integer first_bad=-1;
 always #1 clk=~clk;
 task rnd_inputs; begin
   ws=0;qs=0;
   r=$random(seed);
   case (mode)
    0,1,5: begin // legal (5: with rare single bank valid flips, so `bad` from parts/weight_seen fires first): two weight reads first, then mix; mode 0 own sid, mode 1 mirror
     if(wn<4) begin ws=(wn%2==0); wn=wn+1; wsec={mode!=0,(mode!=0)?2'b0:sid,13'd0}+(wn*8)%1024*8; wsec[2:0]=0; end
     else if(r[3:0]<7) begin qs=1; qi=$random(seed); qsec={mode!=0,(mode!=0)?2'b0:sid,13'd0}; qsec[9:2]=$random(seed); end
     else if(r[3:0]<10) begin ws=1; wsec={mode!=0,(mode!=0)?2'b0:sid,13'd0}; wsec[9:3]=$random(seed); end
    end
    6: begin // aligned, high bits vary: bit 15 bypass, carry through the adder into the sid bits, rare wrong sid
     if(wn<4) begin ws=(wn%2==0); wn=wn+1; wsec={1'b0,sid,13'd0}+(wn*8)%1024*8; wsec[2:0]=0; end
     else if(r[3:0]<7) begin qs=1; qi=$random(seed); qsec={1'b0,sid,13'd0}; qsec[11:2]=$random(seed);
      if(r[6:4]==0) begin qsec[15:13]=$random(seed); qsec[15]=1; qsec[12:2]=$random(seed); end
      if(r[10:7]==0) qsec[12:2]=11'h7ff-r[14:11];
      if(r[15:11]==0) begin qsec[15:13]=$random(seed); qsec[12:2]=$random(seed); end end
     else if(r[3:0]<10) begin ws=1; wsec={1'b0,sid,13'd0}; wsec[12:3]=$random(seed);
      if(r[6:4]==0) begin wsec[15:13]=$random(seed); wsec[15]=1; end
      if(r[15:11]==0) wsec[15:13]=$random(seed); end
    end
    default: begin // illegal: anything
     ws=r[0]; qs=r[1]; qi=$random(seed); wsec=$random(seed); qsec=$random(seed);
    end
   endcase
   if(mode==3) sid=$random(seed);
 end endtask
 task apply_rr; reg[7:0] v; integer b; begin
   v=v_dl[`RTX+7];
   for(b=0;b<8;b=b+1) begin
     rr[257*b+:256]={8{$random(seed)}};
     rr[257*b+256]=v[b];
     if(mode>=2 && mode!=5 && ($random(seed)&255)==0) rr[257*b+256]=~v[b];
     if(mode==5 && v[b] && ($random(seed)&63)==0) rr[257*b+256]=~v[b];
     if(mode==4 && ($random(seed)&7)==0) rr[257*b+256]=$random(seed);
   end
 end endtask
 initial begin
  qi=1;#0.25 qi=0; // wake the old core @* decode (X until first input change)
  for(i=0;i<=DD;i=i+1)v_dl[i]=0;
  repeat(12)@(negedge clk); rst_n=1;
  for(i=0;i<DD+6;i=i+1)@(negedge clk);
  rstn_ok=1;
  for(c=0;c<`CYC;c=c+1)begin
   @(negedge clk);
   // sections: quiesce, then reset so sticky faults clear (a block in flight at the reset edge may still land in
   // the reset-free data flops of the new core only; those flops are consumed only under reset valid bits)
   if(c==`CYC*3/10||(c>=`CYC*5/10&&c%400==0))begin
    ws=0;qs=0;
    repeat(DD+8)begin @(negedge clk);for(i=DD;i>0;i=i-1)v_dl[i]=v_dl[i-1];for(i=0;i<8;i=i+1)v_dl[0][i]=rq_g[17*i+16];apply_rr;end
    mode=(c==`CYC*3/10)?1:(sect%5==0)?2:(sect%5==1)?3:(sect%5==2)?4:(sect%5==3)?6:5; if(c!=`CYC*3/10)sect=sect+1; wn=0;
    rst_n=0;rstn_ok=0;seen_f=0;repeat(12)begin @(negedge clk);for(i=DD;i>0;i=i-1)v_dl[i]=v_dl[i-1];for(i=0;i<8;i=i+1)v_dl[0][i]=rq_g[17*i+16];apply_rr;end
    rst_n=1;repeat(DD+6)@(negedge clk);rstn_ok=1;
   end
   rnd_inputs;
   for(i=DD;i>0;i=i-1)v_dl[i]=v_dl[i-1];
   for(i=0;i<8;i=i+1)v_dl[0][i]=rq_g[17*i+16];
   apply_rr;
  end
  $display("RESULT rtx=%0d seed=%0d chk=%0d diff=%0d first=%0d block_v=%0d fault_cycles=%0d legal_blocks_nofault=%0d legal_fault_cycles=%0d internal_diff=%0d first_faults=%0d mode6_req_nofault=%0d", `RTX, `SEED, nchk, bad_cnt, first_bad, nbv, nf,nvq,nw,nint,nff,nmm);
  $finish;
 end
 always @(posedge clk) if(rstn_ok) begin #0.5;
  nchk=nchk+1;
  if(bv_g===1)nbv=nbv+1;
  if(!seen_f&&f_g!==1&&(g.bad!==n.bad||g.weight_seen!==n.weight_seen))nint=nint+1;
  if(f_g===1)nf=nf+1; if(mode<2&&bv_g===1&&f_g!==1)nvq=nvq+1; if(mode<2&&f_g===1)nw=nw+1;
  if(f_g===1&&!seen_f)nff=nff+1;
  if(f_g===1) seen_f=1;
  if(!seen_f&&mode==6&&|rq_g)nmm=nmm+1;
  if(f_g!==f_n||(!seen_f&&(rq_g!==rq_n||bv_g!==bv_n||(bv_g===1&&(bh_g!==bh_n||bn_g!==bn_n||bd_g!==bd_n||hw_g!==hw_n)))))begin
   bad_cnt=bad_cnt+1;
   if(first_bad<0)begin first_bad=nchk;
    $display("DIFF at %0d rq %0d bv %b/%b f %b/%b bh %b/%b bn %b/%b bd %0d hw %h/%h",nchk,rq_g!==rq_n,bv_g,bv_n,f_g,f_n,bh_g,bh_n,bn_g,bn_n,bd_g!==bd_n,hw_g,hw_n);
   end
  end
 end
endmodule
`default_nettype wire
