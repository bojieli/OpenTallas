`timescale 1ns/1ps
module tb_hgi_att_record_adapter;
 parameter integer MUT_RING=0,MUT_COUNTS=0,MUT_FIELDS=0,MUT_EARLY_DONE=0;
 reg clk=0;always #416.6665 clk=~clk;
 reg rst_n=0,rec_v=0,att_r=0,att_done=0,att_fault=0;
 reg [127:0] hdr=0;reg [255:0] sut=0;reg [1023:0] desc=0;
 reg [20:0] pos1=0;reg [31:0] bn=0,cn=0;
 wire rec_r,att_v,rcv,rcr,rring,busy,done,fault,rdone,rfault;
 wire [127:0] ah;wire [1023:0] ad;
 wire [20:0] rp,rn,rm,rc;
 reg cidv=0,rowr=0;reg [31:0] cid=0;
 wire cidr,rowv,rs,rl;wire [19:0] ri;wire [20:0] ro;
 integer cases=0,rows=0;
 ot_hgi_att_record_adapter #(.MUT_RING(MUT_RING),.MUT_COUNTS(MUT_COUNTS),.MUT_FIELDS(MUT_FIELDS),.MUT_EARLY_DONE(MUT_EARLY_DONE)) dut(
  .clk(clk),.rst_n(rst_n),.rec_v(rec_v),.rec_r(rec_r),.rec_hdr(hdr),.rec_sut(sut),.rec_desc(desc),
  .rec_pos1(pos1),.rec_b_count(bn),.rec_c_count(cn),.att_v(att_v),.att_r(att_r),.att_hdr(ah),.att_desc(ad),
  .att_done(att_done),.att_fault(att_fault),.rows_cmd_v(rcv),.rows_cmd_r(rcr),.rows_ring(rring),
  .rows_pos1(rp),.rows_b_n(rn),.rows_b_m(rm),.rows_c_n(rc),.rows_done(rdone),.rows_fault(rfault),
  .busy(busy),.u_done(done),.u_fault(fault));
 ot_hgi_att_row_sources_p leaf(.clk(clk),.rst_n(rst_n),.cmd_v(rcv),.cmd_r(rcr),.ring(rring),.pos1(rp),.b_n(rn),.b_m(rm),.c_n(rc),
  .c_id_v(cidv),.c_id_r(cidr),.c_id(cid),.row_v(rowv),.row_r(rowr),.row_source(rs),.row_last(rl),.row_index(ri),.row_ordinal(ro),
  .busy(),.done(rdone),.fault(rfault));
 function automatic integer sel(input integer i);sel=(i*977+53)%1048576;endfunction
 task automatic init_record(input integer op,ringflag,p,n,m,k,dyn);
  begin
   hdr=0;desc=0;sut=0;
   hdr[127:124]=5;hdr[123:118]=op;hdr[99:93]=k?7'b0010111:7'b0010011;
   hdr[88:64]=25'd20|(ringflag<<8); //4 lanes, two64-element slices
   hdr[63:32]=32'h3d3504f3;hdr[31:0]=32'h31415926;
   desc[47:8]=40'h0000014000;desc[67:48]=128; // A query/VM
   desc[256+47:256+8]=40'h0a00300000;desc[256+67:256+48]=dyn?0:n;
   desc[256+87:256+68]=m;desc[256+119:256+88]=544;
   desc[256+206:256+201]=dyn?6'd2:6'd0;
   desc[512+47:512+8]=40'h0b00400000;desc[512+67:512+48]=k;desc[512+119:512+88]=288;
   desc[768+47:768+8]=40'h0000020000;desc[768+67:768+48]=n+k;
   pos1=p;bn=n;cn=k;
  end
 endtask
 task automatic run_good(input integer op,ringflag,p,n,m,k,dyn);
  integer got,sent,t,gap,expidx,setupacks,rowcmdacks;
  reg sawrows,sawdone;
  begin
   @(negedge clk);init_record(op,ringflag,p,n,m,k,dyn);if(!rec_r)$fatal(1,"rec not ready");rec_v=1;
   @(negedge clk);rec_v=0;t=0;got=0;sent=0;gap=0;sawrows=0;sawdone=0;setupacks=0;rowcmdacks=0;
   while(!sawdone)begin
    att_r=(t>=4);rowr=(t%7>=2);cidv=(sent<k &&t%5!=0);cid=sel(sent);att_done=sawrows &&gap==8;
    @(posedge clk);
    if(att_v)begin
     if(ah!==hdr||ad!==desc)$fatal(1,"record field mutation");
     if(att_r)setupacks=setupacks+1;
    end
    if(rcv)begin
     if(setupacks!=1)$fatal(1,"row command before real ATT setup");
     if(rp!==p[20:0]||rn!==n[20:0]||rm!==m[20:0]||rc!==k[20:0]||rring!==ringflag[0])$fatal(1,"typed count/ring mutation");
     if(rcr)rowcmdacks=rowcmdacks+1;
    end
    if(rowv&&rowr)begin
     expidx=got<n?(ringflag?((p-n+got)%m):got):sel(got-n);
     if(ri!==expidx[19:0]||rs!==(got>=n)||ro!==got[20:0]||rl!==(got==n+k-1))$fatal(1,"row sequence mutation");
     got=got+1;rows=rows+1;
    end
    if(cidv&&cidr)sent=sent+1;
    @(negedge clk);
    if(rfault||fault)$fatal(1,"valid record fault");
    if(rdone)sawrows=1;
    if(done)begin
     if(!att_done &&gap<8)$fatal(1,"retired without actual ATT completion");
     sawdone=1;
    end
    if(sawrows)gap=gap+1;
    if(t>(n+k)*10+100)$fatal(1,"bounded deterministic record flow failed");
    t=t+1;
   end
   if(got!=n+k||setupacks!=1||rowcmdacks!=1)$fatal(1,"work/ACK count failed");
   att_done=0;cidv=0;cases=cases+1;
  end
 endtask
 task automatic run_bad(input integer which);
  integer t;
  begin
   @(negedge clk);init_record(0,0,128,128,0,0,0);
   case(which)
    0:hdr[127:124]=4;1:hdr[123:118]=2;2:hdr[92]=1;
    3:hdr[99:93]=7'b0000011;4:hdr[99:93]=7'b0011011;
    5:pos1=1048577;6:bn=1048577;7:cn=1;
    8:bn=127;9:begin desc[256+206:256+201]=2;bn=127;end
    10:begin hdr[72]=1;desc[256+87:256+68]=127;end
    11:begin hdr=0;hdr[127:124]=5;hdr[103:100]=15;end //legacy header cannot pass normative gate
   endcase
   rec_v=1;@(negedge clk);rec_v=0;
   for(t=0;t<4;t=t+1)begin
    if(att_v||rcv)$fatal(1,"invalid record launched work");
    if(done)begin if(!fault)$fatal(1,"invalid record not faulted");cases=cases+1;end
    @(negedge clk);
   end
  end
 endtask
 integer j;
 initial begin
  repeat(3)@(negedge clk);rst_n=1;
  run_good(0,1,4097,128,128,17,0);
  run_good(1,1,1048576,128,128,2048,0);
  run_good(0,0,8192,8192,0,0,1);
  run_good(1,0,1048576,1048576,0,0,1);
  run_good(0,0,0,0,0,0,0);
  for(j=0;j<12;j=j+1)run_bad(j);
  $display("PASS G12_RECORD cases=%0d rows=%0d",cases,rows);$finish;
 end
endmodule
