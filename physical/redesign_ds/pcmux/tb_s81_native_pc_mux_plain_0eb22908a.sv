`timescale 1ns/1ps
module tb_s81_native_pc_mux;
 reg ck=0;always #0.416667 ck=~ck;
 reg rst_n=0,live=0;reg[1363:0] inq=0;wire[3:0] cr;wire[340:0] rq;
 reg rk=0,wd=0,rv=0;reg[255:0] data=0;reg[16:0] tag=0;reg[3:0] beat=0;
 wire[3:0] sw,srv,sdone;wire[1023:0] sd;wire[67:0] st;wire[15:0] sb;wire pending,ce,fault;
`ifdef INJECT_SINGLE
 localparam[431:0] INJECT=432'd1;
`elsif INJECT_DOUBLE
 localparam[431:0] INJECT=432'd3;
`else
 localparam[431:0] INJECT=0;
`endif
 ot_s81_native_pc_mux_plain #(.ENABLE(1),.QUEUE_INJECT(INJECT),.PICK(`ifdef PCMUX_PICK 1 `else 0 `endif),.PRE(`ifdef PCMUX_PRE 1 `else 0 `endif)) dut(ck,rst_n,live,inq,cr,rq,rk,wd,rv,data,tag,beat,sw,srv,sdone,sd,st,sb,pending,ce,fault);
 integer credit[0:3],seq[0:3],sent[0:3],retired[0:3];
 integer qtag[0:3][0:8191],qwe[0:3][0:8191],qlen[0:3][0:8191];
 integer w[0:3],r[0:3];integer i,c,n,active_sid=-1,remaining=0,timer=0,credit_delay=0;
 integer issues=0,completions=0,done_count=0,returns=0,corrected=0,prioritychecks=0;
 reg active_we;reg[16:0] active_tag;reg[3:0] active_len;reg[31:0] rng=32'h13579117;
 initial begin
  for(i=0;i<4;i=i+1)begin credit[i]=8;seq[i]=0;sent[i]=0;retired[i]=0;w[i]=0;r[i]=0;end
  repeat(5)@(negedge ck);rst_n=1;live=1;repeat(3)@(negedge ck);
  for(c=0;c<3500;c=c+1)begin
   rng={rng[30:0],rng[31]^rng[21]^rng[1]^rng[0]};inq=0;rk=0;wd=0;rv=0;
   for(i=0;i<4;i=i+1)if(c<1800&&credit[i]>0&&(rng[i]||c<10))begin
    tag={2'(i),15'(seq[i])};n=(rng[(i+4)%32]?1:4);
    inq[i*341+:341]={256'(seq[i]*7+i),32'hffffffff,tag,4'(n),30'(i*64+seq[i]),rng[(i+8)%32],1'b1};
    qtag[i][w[i]]=tag;qwe[i][w[i]]=rng[(i+8)%32];qlen[i][w[i]]=n;w[i]=w[i]+1;
    seq[i]=seq[i]+1;credit[i]=credit[i]-1;sent[i]=sent[i]+1;
   end
   if(credit_delay>0)begin credit_delay=credit_delay-1;if(credit_delay==0)rk=1;end
   if(active_sid>=0)begin
    if(timer>0)timer=timer-1;
    else if(active_we)begin wd=1;active_sid=-1;completions=completions+1;end
    else begin
     rv=1;data=256'(active_tag*19+remaining);tag=active_tag;beat=remaining-1;
     remaining=remaining-1;if(remaining==0)begin active_sid=-1;completions=completions+1;end
    end
   end
   @(posedge ck);
   if(rq[0])begin
    if(active_sid>=0)$fatal(1,"overlapped untagged controller ownership");
    active_tag=rq[52:36];active_sid=active_tag[16:15];active_we=rq[1];active_len=rq[35:32];
    if(r[active_sid]==w[active_sid]||active_tag!=qtag[active_sid][r[active_sid]]||active_we!=qwe[active_sid][r[active_sid]]||active_len!=qlen[active_sid][r[active_sid]])$fatal(1,"issue reordered within source or payload wrong");
    r[active_sid]=r[active_sid]+1;remaining=active_len;timer=5;credit_delay=3;issues=issues+1;
   end
   #0.1;
   if(ce)corrected=corrected+1;
`ifdef INJECT_DOUBLE
   if(fault)begin $display("S81_NATIVE_PC DOUBLE_DETECTED");$finish;end
`else
   if(fault)$fatal(1,"unexpected native endpoint fault cycle%0d",c);
`endif
   for(i=0;i<4;i=i+1)begin
    if(sdone[i])begin
     if(i!=active_tag[16:15]||!(wd||(rv&&beat==0)))$fatal(1,"wrong or premature source retirement");
     done_count=done_count+1;
    end
    if(cr[i])credit[i]=credit[i]+1;
    if(sw[i])begin if(!wd||i!=active_tag[16:15])$fatal(1,"wrong writecompletion source");retired[i]=retired[i]+1;end
    if(srv[i])begin
     if(!rv||i!=active_tag[16:15]||st[i*17+:17]!=tag||sb[i*4+:4]!=beat||sd[i*256+:256]!=data)$fatal(1,"wrongread source/tag/beat/data");
     returns=returns+1;if(beat==0)retired[i]=retired[i]+1;
    end
   end
   @(negedge ck);
  end
  for(i=0;i<4;i=i+1)if(sent[i]!=retired[i]||credit[i]!=8)$fatal(1,"source inventory not drained");
  if(pending||issues!=completions||done_count!=completions||issues<50||returns==0)$fatal(1,"gate did not exercise/drain full mechanism");
`ifdef INJECT_SINGLE
  if(corrected==0)$fatal(1,"singlebit correction not exercised");
`endif
  $display("S81_NATIVE_PC PASS issues=%0d complete=%0d readbeats=%0d corrected=%0d",issues,completions,returns,corrected);$finish;
 end
endmodule
