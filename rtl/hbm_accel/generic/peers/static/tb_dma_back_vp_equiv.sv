`timescale 1ns/1ps
// _vp vs _cursor: the cursor reference gets the SAME command DESC_LAT=2 cycles later (vp's descriptor pipeline);
// every control output, request and write beat must match cycle for cycle.  HBM-V15-HARDEN 10-15
module tb_dma_back_vp_equiv;
 reg clk=0;always #5 clk=~clk;reg rst_n=0;reg [31:0] cycle=0;
 reg mv_v=0;reg [226:0] mv=0;reg [31:0] issue_at=0,drain_at=0;
 reg d1_v=0,d2_v=0;reg [226:0] d1_mv=0,d2_mv=0;reg [31:0] d1_i=0,d2_i=0,d1_d=0,d2_d=0;
 always @(posedge clk) begin d1_v<=mv_v;d1_mv<=mv;d1_i<=issue_at;d1_d<=drain_at;d2_v<=d1_v;d2_mv<=d1_mv;d2_i<=d1_i;d2_d<=d1_d; end
 wire srca,donea,faulta,quieta,busya,reservea,banka,fillbanka,filla;
 wire srcb,doneb,faultb,quietb,busyb,reserveb,bankb,fillbankb,fillb;
 wire [135:0] rqa,rqb;wire [2311:0] wda,wdb;wire [15:0] epocha,epochb,fillepocha,fillepochb;
 wire [11:0] sectorsa,sectorsb;wire [31:0] basea,baseb;wire [2055:0] rr;
 reg [6:0] response_v[0:7];reg [11:0] wa=0;reg [11:0] ack[0:4];
 integer checks=0,count=0,cases=0,bad_cases=0,faults_seen=0; reg allow_fault=0;
 always @(posedge clk)begin
  cycle<=cycle+1;
  for(integer b=0;b<8;b=b+1)response_v[b]<=rst_n?{response_v[b][5:0],rqa[b*17+16]}:7'b0;
  begin:ACK_SUM integer n; n=0;for(integer b=0;b<8;b=b+1)if(wda[b*289+288])n=n+1;ack[0]<=12'(n);end
  for(integer k=1;k<5;k=k+1)ack[k]<=ack[k-1];
 end
 for(genvar b=0;b<8;b=b+1)begin:R
  assign rr[b*257+:257]={response_v[b][6],{8{32'h39c10000+32'(b*271)+cycle}}};
 end
 ot_hgi_dma_back_static_cursor ref_i( .clk(clk),.rst_n(rst_n),.cycle(cycle),.mv_v(d2_v),.mv(d2_mv),.issue_at(d2_i),.drain_at(d2_d),
 .mv_wb_bank(1'b0),.mv_wb_epoch(16'h1234),.mv_src(srca),.mv_done(donea),.mv_fault(faulta),.quiet(quieta),.busy(busya),
 .rq(rqa),.rr(rr),.wb_reserve_v(reservea),.wb_reserve_bank(banka),.wb_fill_bank(fillbanka),
 .wb_reserve_epoch(epocha),.wb_fill_epoch(fillepocha),.wb_reserve_sectors(sectorsa),.wb_reserve_base(basea),
 .wb_fill_start(filla),.wb_ready(1'b1),.wd(wda),.wa(wa));
 ot_hgi_dma_back_static_vp dut( .clk(clk),.rst_n(rst_n),.cycle(cycle),.mv_v(mv_v),.mv(mv),.issue_at(issue_at),.drain_at(drain_at),
 .mv_wb_bank(1'b0),.mv_wb_epoch(16'h1234),.mv_src(srcb),.mv_done(doneb),.mv_fault(faultb),.quiet(quietb),.busy(busyb),
 .rq(rqb),.rr(rr),.wb_reserve_v(reserveb),.wb_reserve_bank(bankb),.wb_fill_bank(fillbankb),
 .wb_reserve_epoch(epochb),.wb_fill_epoch(fillepochb),.wb_reserve_sectors(sectorsb),.wb_reserve_base(baseb),
 .wb_fill_start(fillb),.wb_ready(1'b1),.wd(wdb),.wa(wa));
 always @(negedge clk)if(rst_n)begin
  wa=ack[4];checks=checks+1;
  if({srca,donea,faulta,quieta,busya,reservea,banka,fillbanka,epocha,fillepocha,sectorsa,basea,filla}!==
     {srcb,doneb,faultb,quietb,busyb,reserveb,bankb,fillbankb,epochb,fillepochb,sectorsb,baseb,fillb})$fatal(1,"control mismatch cycle%0d",cycle);
  if(faulta) faults_seen=faults_seen+1;
  if(faulta&&!allow_fault)$fatal(1,"invalid stimulus cycle%0d mv=%h valid=%b cv=%b nsec=%0d row=%0d stride=%0d hstride=%0d ci=%0d cd=%0d",cycle,ref_i.cm,ref_i.CONTROL.valid_move,ref_i.cv,ref_i.cm[226:209],ref_i.cm[205:186],ref_i.cm[76:45],ref_i.cm[169:138],ref_i.ci,ref_i.cd);
  for(integer b=0;b<8;b=b+1)begin
   if(rqa[b*17+16]!==rqb[b*17+16] || (rqa[b*17+16] && rqa[b*17+:17]!==rqb[b*17+:17]))$fatal(1,"rq mismatch");
   if(wda[b*289+288]!==wdb[b*289+288])$fatal(1,"valid mismatch");
   if(wda[b*289+288])begin
    if(wda[b*289+:289]!==wdb[b*289+:289])$fatal(1,"write beat mismatch cycle%0d bank%0d",cycle,b);
    count=count+1;
   end
  end
 end
 function automatic [226:0] descriptor(input integer nsec,input integer rows);
  descriptor={21'(nsec*8),20'(rows),16'd1,32'(nsec*32),40'h100000,3'd0,2'd0,16'd1,32'(((nsec+7)/8)*64),40'd0,3'd0,2'd1};
 endfunction
 task automatic run_case(input integer nsec,input integer rows,input integer delay);
 integer before_count,lim;
 begin
  before_count=count;@(negedge clk);#1;mv=descriptor(nsec,rows);issue_at=cycle+6;drain_at=cycle+16+delay;mv_v=1;
  @(negedge clk);#1;mv_v=0;lim=cycle+((nsec+7)/8)*rows+delay+40;
  while(cycle<lim)@(negedge clk);
  #1;if(count-before_count!=nsec*rows)$fatal(1,"missing beats nsec%0d rows%0d count%0d",nsec,rows,count-before_count);
  cases=cases+1;
 end
 endtask
 // invalid descriptors (each range / alignment term, wrong stack, late issue, early drain): fault timing and every
 // output must match too; the products are formed from range-truncated operands, so these cases guard that shortcut.
 task automatic bad_case(input [226:0] d,input integer lead,input integer lag);
 begin
  @(negedge clk);#1;mv=d;issue_at=cycle+lead;drain_at=cycle+lead+lag;mv_v=1;@(negedge clk);#1;mv_v=0;
  repeat(12)@(negedge clk);
  #1;rst_n=0;@(negedge clk);#1;rst_n=1;bad_cases=bad_cases+1;
 end
 endtask
 initial begin
  for(integer b=0;b<8;b=b+1)response_v[b]=0;
  for(integer k=0;k<5;k=k+1)ack[k]=0;
  repeat(3)@(negedge clk);#1;rst_n=1;
  run_case(1,1,0);run_case(7,1,9);run_case(8,1,0);run_case(9,1,17);run_case(15,1,0);run_case(16,1,0);
  run_case(17,1,3);run_case(63,1,0);run_case(64,1,0);run_case(127,1,0);run_case(1024,1,0);
  run_case(8,2,0);run_case(8,80,0);run_case(16,3,0);run_case(32,16,0);run_case(64,16,0);
  run_case(8,128,5);run_case(16,64,0);run_case(64,2,3);run_case(1023,1,2);
  allow_fault=1;
  bad_case(descriptor(8,129),6,10); bad_case(descriptor(1025,1),6,10); bad_case(descriptor(8,256),6,10);
  bad_case(descriptor(8,2048+5),6,10); bad_case(descriptor(2047,1),6,10); bad_case(descriptor(9,2),6,10);
  bad_case(descriptor(8,1)^(227'd1<<133),6,10); bad_case(descriptor(8,1),2,10); bad_case(descriptor(8,1),6,9);
  bad_case({descriptor(8,1)}&~(227'hfffff<<186),6,10);
  // VM aperture end through the (rows-1)*stride product: rows 65 from base 63488 ends at 67648 > 65536
  bad_case((descriptor(8,65)&~(227'hff_ffff_ffff<<5))|(227'd63488<<5),6,10);
  if(faults_seen==0)$fatal(1,"bad cases produced no fault");
  $display("DMA_VP_EQUIV PASS DESC_LAT=2 cases=%0d bad_cases=%0d fault_cycles=%0d checks=%0d beats=%0d",cases,bad_cases,faults_seen,checks,count);$finish;
 end
endmodule
