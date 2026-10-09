`timescale 1ns/1ps
module tb_qfd_kv_skid_all_trace;
 parameter integer DEPTH=8;
 reg clk=0;always #5 clk=~clk;
 reg rst_n=0,request=0,tok_v=0;
 integer fw,ret,tile,ntiles,total,count,sent,seen,cy,bound,fh,scan,i,t,errors=0,all_sent=0,all_seen=0;
 integer offers[0:1023],pcs[0:1023],seqs[0:1023];
 reg [2047:0] trace_name;
 reg [41:0] fv;reg [33:0] rc;
 reg [518:0] fd[0:41];
 wire grant,tfault,free_credit,rfault,drained,ce;
 wire [6:0] addr;wire[511:0] data,mask;
 wire [511:0] lm={{504{1'b1}},8'h00};
 wire [511:0] tm={{504{1'b0}},8'hff};
 wire [511:0] payload={16{32'(seqs[sent]*7919+pcs[sent]+31)}};
 ot_qfd_kv_credit_tx #(.DEPTH(DEPTH)) tx(clk,rst_n,request,rc[ret-1],grant,tfault);
 ot_qfd_kv_merge_skid #(.DEPTH(DEPTH)) dut(.clk(clk),.rst_n(rst_n),
 .land_v(fv[fw-1]),.land_addr(fd[fw-1][518:512]),.land_data(fd[fw-1][511:0]),.land_mask(lm),
 .tok_v(tok_v),.tok_addr(7'(cy%128)),.tok_data({16{32'(cy*13+5)}}),.tok_mask(tm),
 .credit_free(free_credit),.kvw_ce(ce),.kvw_addr(addr),.kvw_data(data),.kvw_mask(mask),.fault(rfault),.drained(drained));
 always @(posedge clk) begin
  if(!rst_n)begin fv<=0;rc<=0;for(i=0;i<42;i=i+1)fd[i]<=0;end
  else begin
   fv<={fv[40:0],grant};rc<={rc[32:0],free_credit};fd[0]<={7'(sent%128),payload};
   for(i=1;i<42;i=i+1)fd[i]<=fd[i-1];
   if(grant)sent=sent+1;
   #1;
   if(tfault||rfault)$fatal(1,"land_fault tile%0d depth%0d",tile,DEPTH);
   if(ce && mask==lm)begin
    if(seen>=count || addr!==7'(seen%128) || data!=={16{32'(seqs[seen]*7919+pcs[seen]+31)}})
     $fatal(1,"data/order tile%0d word%0d",tile,seen);
    seen=seen+1;
   end
  end
 end
 initial begin
  fw=42;ret=34;sent=0;seen=0;cy=0;tok_v=0;fv=0;rc=0;
  if(!$value$plusargs("trace=%s",trace_name))$fatal(1,"trace required");
  fh=$fopen(trace_name,"r");if(!fh)$fatal(1,"trace missing");
  scan=$fscanf(fh,"%d %d\n",ntiles,total);if(scan!=2)$fatal(1,"header");
  for(t=0;t<ntiles;t=t+1)begin
   scan=$fscanf(fh,"%d %d %d %d\n",tile,count,fw,ret);
   if(scan!=4 || count>1024 || fw>42 || fw<1 || ret>34 || ret<1)$fatal(1,"tile header");
   for(i=0;i<count;i=i+1)begin scan=$fscanf(fh,"%d %d %d\n",offers[i],pcs[i],seqs[i]);if(scan!=3)$fatal(1,"word header");end
   @(negedge clk);rst_n=0;request=0;tok_v=0;sent=0;seen=0;
   repeat(4)@(negedge clk);rst_n=1;
   bound=offers[count-1]+(fw+ret+12)*count+32;
   for(cy=0;cy<bound;cy=cy+1)begin
    @(negedge clk);request=sent<count && cy>=offers[sent];
    tok_v=(cy>=fw && cy<fw+8);
    if(sent==count && seen==count && drained && fv==0 && rc==0)begin
     request=0;tok_v=0;cy=bound;
    end
   end
   if(sent!=count || seen!=count || !drained)$fatal(1,"trace incomplete tile%0d sent%0d seen%0d",tile,sent,seen);
   all_sent=all_sent+sent;all_seen=all_seen+seen;
  end
  if(all_sent!=total || all_seen!=total)$fatal(1,"total mismatch");
  $display("PASS every_trace_word depth%0d tiles%0d accepted%0d ordered%0d land_fault0 full512 synthetic_transport_tags",DEPTH,ntiles,all_sent,all_seen);
  $finish;
 end
endmodule
