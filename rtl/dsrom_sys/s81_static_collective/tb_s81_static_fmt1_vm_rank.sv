`timescale 1ns/1ps
module tb_s81_static_fmt1_vm_rank;
 reg tx_beat_slot,rx_beat_slot,tx_frame_slot,rx_frame_slot;reg[1:0]tx_phase,rx_phase;integer group_index,start_cycle,legacy_checks=0;
 reg clk=0;always #5 clk=~clk;
 reg rst_n=0;integer cyc=-1,nrec=28,mut=0,checks=0;reg issue,commit;
 reg[7:0]beat_plan[0:1023];reg[2047:0]beatfile;reg [127:0] plan[0:43];reg [2047:0] planfile;reg [15:0] seq,cseq;reg last,clast;reg [59:0] rows;
 reg prev_commit=0;reg[15:0] prev_seq;reg[59:0] prev_rows;
 wire[15:0] sv;wire[3:0] sf;wire[223:0] sr;wire[8191:0] sd;wire[255:0] sm;
 wire[3:0] fault;wire[15:0] we;wire[11:0]ptv,prv;wire[6143:0]ptd,prd;
 wire[4*2048-1:0] wd;wire[239:0] wa;
 function automatic [511:0] value(input integer rank,input integer item);
  reg[511:0] v;begin for(integer l=0;l<16;l=l+1)v[l*32+:32]=32'h3f000000+rank*65536+item*16+l;value=v;end
 endfunction
 function automatic [14:0] row(input integer rank,input integer item);
  begin
   if(item<20)row=4096+20*rank+item;
   else if(item<28)row=4224+8*rank+item-20;
   else if(item<36)row=4816+8*rank+item-28;
   else row=4848+8*rank+item-36;
  end
 endfunction
 wire legacy_v,legacy_lock,legacy_fault;wire[594:0]legacy_frame;
 ot_s81ph_link_gbx #(.FMT(1)) legacy_rx(.clk(clk),.rst_n(rst_n),.f_tx_v(1'b0),.f_tx(595'b0),
  .r_tx_v(1'b0),.r_tx(53'b0),.beat_tx(),.beat_rx_v(ptv[3]),.beat_rx(ptd[1536+:512]),
  .f_rx_v(legacy_v),.f_rx(legacy_frame),.r_rx_v(),.r_rx(),.locked(legacy_lock),.fault(legacy_fault));
 always @(posedge clk)begin
  #2;
  if(rst_n && legacy_v && mut==0)begin
   if(legacy_frame[543:32]!==value(1,int'(legacy_frame[594:585])))$fatal(1,"legacy FMT1 interoperability data");
   legacy_checks=legacy_checks+1;
  end
 end
 genvar r,s;
 generate for(r=0;r<4;r=r+1)begin:E
  wire valid_src=issue && !(mut==1 && r==2 && seq==3);
  wire[15:0] source_seq=(mut==3 && r==1 && seq==4)?16'd5:seq;
  wire[3:0] mask=(mut==4 && r==3 && seq==2)?4'h7:4'hf;
  wire[2203:0] vmp;wire[14:0] crq;
  s81_static_fmt1_vm_rank #(.RANK(r)) e(.clk(clk),.rst_n(rst_n),.issue_slot(issue),.f_crs({value(r,seq),valid_src}),.read_slot(issue),.read_row(14'(seq)),.t_crq(crq),
   .tag(32'h12345600|32'(seq)),.seq(source_seq),.last(last),.rankmask(mask),
   .tx_beat_slot(tx_beat_slot),.tx_phase(tx_phase),.tx_frame_slot(tx_frame_slot),
   .rx_beat_slot(rx_beat_slot),.rx_phase(rx_phase),.rx_frame_slot(rx_frame_slot),.phy_tx_valid(ptv[r*3+:3]),.phy_tx_data(ptd[r*1536+:1536]),
   .phy_rx_valid(prv[r*3+:3]),.phy_rx_data(prd[r*1536+:1536]),.commit_slot(commit),.commit_tag(32'h12345600|32'(cseq)),
   .commit_seq(cseq),.commit_last(clast),.commit_rankmask(4'hf),.commit_rows(rows),
   .t_vm(vmp),.fault(fault[r]));
  for(genvar k=0;k<4;k=k+1)begin:VM
   assign sv[r*4+k]=vmp[k*551];
   assign sr[r*56+k*14+:14]=vmp[k*551+1+:14];
   assign sm[r*64+k*16+:16]=vmp[k*551+15+:16];
   assign sd[r*2048+k*512+:512]=vmp[k*551+31+:512];
   always @(posedge clk)begin
    #2;if(rst_n && vmp[k*551] && vmp[k*551+543+:8]!==vmp[k*551+35+:8])$fatal(1,"VM identity packing");
   end
  end
  always @(posedge clk)begin
   #2;if(rst_n && crq!=={14'(seq),issue})$fatal(1,"VM request registration");
  end
  for(s=0;s<3;s=s+1)begin:L
   localparam integer PEER=s<r ? s:s+1;
   localparam integer BACK=r<PEER ? r:r-1;
   wire pv=ptv[PEER*3+BACK];wire[511:0]pd=ptd[(PEER*3+BACK)*512+:512];
   reg dv=0;reg[511:0]dd=0;
   always @(posedge clk)begin dv<=pv;dd<=pd;end
   wire delayed=mut==2 && r==0 && PEER==1;
   // Declared off-chip PHY connection; digital transmit/receive are DUT rank RTL.
   assign prv[r*3+s]=delayed ? dv:pv;
   assign prd[(r*3+s)*512+:512]=(delayed ? dd:pd)^((mut==5 && r==2 && PEER==0 && cyc==start_cycle+8)?(512'b1<<100):512'b0);
  end
 end endgenerate
 initial begin
  if($value$plusargs("N=%d",nrec))begin end
  if($value$plusargs("MUT=%d",mut))begin end
  if(!$value$plusargs("PLAN=%s",planfile))$fatal(1,"compiler PLAN required");
  $readmemh(planfile,plan,0,nrec-1);
  if(!$value$plusargs("BEATS=%s",beatfile))$fatal(1,"compiler BEATS required");
  $readmemh(beatfile,beat_plan,0,int'(plan[0][127:96])+((nrec+2)/3)*16+23);
  start_cycle=int'(plan[0][127:96]);
  issue=0;commit=0;seq=0;cseq=0;last=0;clast=0;rows=0;
  repeat(3)@(negedge clk);rst_n=1;
  for(cyc=0;cyc<start_cycle+((nrec+2)/3)*16+24;cyc=cyc+1)begin
   {tx_beat_slot,tx_phase,tx_frame_slot,rx_beat_slot,rx_phase,rx_frame_slot}=beat_plan[cyc];
   issue=0;commit=0;
   for(integer j=0;j<nrec;j=j+1)begin
    if(cyc==plan[j][127:96])begin issue=1;seq=16'(j);last=plan[j][3];end
    if(cyc==plan[j][95:64])begin commit=1;cseq=16'(j);clast=plan[j][3];rows=plan[j][63:4];end
   end
   if(mut==6 && commit && cseq==2)rows[14]=1;
   @(posedge clk);#1;
   if(mut==0)begin
    if(|fault)$fatal(1,"fault cycle=%0d ep=%h commit=%b",cyc,fault,commit);
    
    if(sv!={16{prev_commit}})$fatal(1,"source pin timing");
    if(prev_commit)for(integer d=0;d<4;d=d+1)for(integer k=0;k<4;k=k+1)begin
     if(sd[d*2048+k*512+:512]!==value(k,prev_seq))$fatal(1,"source pin data");
     if(sr[d*56+k*14+:14]!==prev_rows[k*15+:14])$fatal(1,"source pin row");
     if(sm[d*64+k*16+:16]!==16'hffff)$fatal(1,"source pin mask");
    end

   end
   prev_commit=commit;prev_seq=cseq;prev_rows=rows;
   @(negedge clk);
  end
  if(mut==0 && legacy_checks!=nrec)$fatal(1,"legacy FMT1 frame count %0d != %0d",legacy_checks,nrec);
  if(mut==5 && !E[2].e.transport.L[0].lane.cf)$fatal(1,"CRC payload corruption escaped codec");
  if(mut!=0 && !(|fault))$fatal(1,"MUTANT ESCAPED %0d",mut);
  $display("PASS VM-pin-component-only N=%0d MUT=%0d checked_fp32=%0d fault=%h cycles=%0d",nrec,mut,checks,fault,cyc);$finish;
 end
endmodule
