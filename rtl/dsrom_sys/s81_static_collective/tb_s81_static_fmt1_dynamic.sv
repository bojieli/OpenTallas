`timescale 1ns/1ps
module tb_s81_static_fmt1_dynamic;
 integer rotation=0;reg[1:0]strap[0:3];
 wire[127:0]gtag;wire[63:0]gseq;wire[3:0]glast;
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
 genvar r,s;
 generate for(r=0;r<4;r=r+1)begin:E
  wire valid_src=issue && !(mut==1 && r==2 && seq==3);
  wire[15:0] source_seq=(mut==3 && r==1 && seq==4)?16'd5:seq;
  wire[3:0] mask=(mut==4 && r==3 && seq==2)?4'h7:4'hf;
  s81_static_fmt1_rank_dynamic e(.rank(strap[r]),.gather_tag(gtag[r*32+:32]),.gather_seq(gseq[r*16+:16]),.gather_last(glast[r]),.clk(clk),.rst_n(rst_n),.issue_slot(issue),.src_valid(valid_src),.src_data(value(strap[r],seq)),
   .tag(32'h12345678),.seq(source_seq),.last(last),.rankmask(mask),
   .tx_beat_slot(tx_beat_slot),.tx_phase(tx_phase),.tx_frame_slot(tx_frame_slot),
   .rx_beat_slot(rx_beat_slot),.rx_phase(rx_phase),.rx_frame_slot(rx_frame_slot),.phy_tx_valid(ptv[r*3+:3]),.phy_tx_data(ptd[r*1536+:1536]),
   .phy_rx_valid(prv[r*3+:3]),.phy_rx_data(prd[r*1536+:1536]),.commit_slot(commit),.commit_tag(32'h12345678),
   .commit_seq(cseq),.commit_last(clast),.commit_rankmask(4'hf),.commit_rows(rows),
   .vm_we(we[r*4+:4]),.vm_rows(wa[r*60+:60]),.vm_data(wd[r*2048+:2048]),.fault(fault[r]));
  s81_static_tp4_vm_producer producer(.clk(clk),.rst_n(rst_n),.gather_we(we[r*4+:4]),
   .gather_rows(wa[r*60+:60]),.gather_data(wd[r*2048+:2048]),.identity(8'h78),
   .capture_lane(8'b0),.storage_slot(8'b0),.source_v(sv[r*4+:4]),.source_row(sr[r*56+:56]),
   .source_mask(sm[r*64+:64]),.source_data(sd[r*2048+:2048]),.source_tag(),
   .source_capture_lane(),.source_storage_slot(),.fault(sf[r]));
  for(s=0;s<3;s=s+1)begin:L
   wire[1:0]PEER=(strap[r] ^2'(s+1))-rotation[1:0];
   localparam integer BACK=s;
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
  if($value$plusargs("ROT=%d",rotation))begin end
  for(integer d=0;d<4;d=d+1)strap[d]=2'(d+rotation);
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
   if(mut==7 && cyc==start_cycle+9)strap[0]=strap[0]^2'b01;
   if(mut==6 && commit && cseq==2)rows[14]=1;
   if(mut==8 && cyc==0)begin
    issue=1;#1;if(fault!==4'hf)$fatal(1,"uninitialized boot issue not refused on source edge");
   end
   @(posedge clk);#1;
   if(mut==0)begin
    if(|fault || |sf)$fatal(1,"fault cycle=%0d ep=%h commit=%b",cyc,fault,commit);
    if(we!={16{commit}})$fatal(1,"write timing cycle=%0d we=%h",cyc,we);
    if(sv!={16{prev_commit}})$fatal(1,"source pin timing");
    if(prev_commit)for(integer d=0;d<4;d=d+1)for(integer k=0;k<4;k=k+1)begin
     if(sd[d*2048+k*512+:512]!==value(k,prev_seq))$fatal(1,"source pin data");
     if(sr[d*56+k*14+:14]!==prev_rows[k*15+:14])$fatal(1,"source pin row");
     if(sm[d*64+k*16+:16]!==16'hffff)$fatal(1,"source pin mask");
    end
    if(commit)for(integer d=0;d<4;d=d+1)begin
     if(gtag[d*32+:32]!==32'h12345678 || gseq[d*16+:16]!==cseq || glast[d]!==clast)$fatal(1,"gather metadata alignment");
    end
    if(commit)for(integer d=0;d<4;d=d+1)for(integer k=0;k<4;k=k+1)begin
     if(wd[d*2048+k*512+:512]!==value(k,cseq))$fatal(1,"data d=%0d k=%0d got=%h want=%h",d,k,wd[d*2048+k*512+:32],value(k,cseq));
     if(wa[d*60+k*15+:15]!==rows[k*15+:15])$fatal(1,"row");checks=checks+16;
    end
   end
   prev_commit=commit;prev_seq=cseq;prev_rows=rows;
   @(negedge clk);
  end

  if(mut==5 && !E[2].e.impl.L[1].lane.cf)$fatal(1,"CRC payload corruption escaped codec");
  if(mut!=0 && !(|fault || |sf))$fatal(1,"MUTANT ESCAPED %0d",mut);
  $display("PASS dynamic-rank-XOR-component-only ROT=%0d N=%0d MUT=%0d checked_fp32=%0d fault=%h cycles=%0d",rotation,nrec,mut,checks,fault,cyc);$finish;
 end
endmodule
