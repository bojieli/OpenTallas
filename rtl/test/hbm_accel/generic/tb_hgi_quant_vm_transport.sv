`timescale 1ns/1ps
module tb_hgi_quant_vm_transport;
`ifndef MUTANT
 `define MUTANT 0
`endif
 reg clk=0;always #0.416666667 clk=~clk;
 reg rst_n=0;reg [1408:0] cmd=0;wire ready,done,fault,drained;
 wire req_v,rsp_r;wire [336:0] req;reg req_r=0,rsp_v=0;
 reg [272:0] rsp=0;reg provider_fault=0;
 ot_hgi_quant_vm_transport #(.ENABLE(1),.MUTANT(`MUTANT)) dut(.*);
 reg [31:0] vm[0:8191];reg [31:0] expected[0:8191];
 reg corrupt_tag=0;reg pv=0;reg [336:0] held;integer delay_count=0;
 integer dest_base=4096,layout_rows=1,layout_ostride=1,layout_wstride=0,published_words=0;
 reg layout_mode=0;
 integer cycles=0,writes=0,acks=0,cases=0,nwords=0,reads=0;
 reg [19:0] current_n;
 wire ref_vo,ref_fault,ref_dec;wire [511:0] ref_y;
 ot_hgi_quant_decode ref_core(.clk(clk),.rst_n(rst_n),.v(dut.launch),
 .generic_enable(1'b1),.legacy_fp4(1'b0),.header(dut.header),.x(dut.x),
 .vo(ref_vo),.y(ref_y),.fault(ref_fault),.decode_fault(ref_dec));
 integer rbeat=0;
 reg use_vector=0;reg [1023:0] vx;reg [511:0] vy;
 reg [1023:0] gi8[0:48],gi4[0:48],gie[0:85];
 reg [511:0] go8[0:48],go4[0:48],goe[0:85];
 string vectors;
 always @(negedge clk)begin
  cycles=cycles+1;req_r=!pv&&!rsp_v&&(cycles%7!=0);
  if(req_v&&req_r)begin
   held=req;pv=1;delay_count=2+cycles%13;
   if(req[336])begin
    writes=writes+1;
    for(integer k=0;k<8;k=k+1)if(|req[16+k*4+:4])begin
     published_words=published_words+1;
     if(!layout_mode && req[335:304]/4+k>=dest_base+current_n)$fatal(1,"tail neighbor overwrite");
     if(req[303:48]>>k*32!==expected[req[335:304]/4+k])begin
      // Compare32bits only, preserve true lane extraction.
      if(req[48+k*32+:32]!==expected[req[335:304]/4+k])$fatal(1,"WRITE mismatch cases=%0d vector=%0d n=%0d addr=%0d lane=%0d actual=%h expected=%h head=%0d tail=%0d queued=%0d reserved=%0d",cases,use_vector,current_n,req[335:304]/4,k,req[48+k*32+:32],expected[req[335:304]/4+k],dut.head,dut.tail,dut.queued,dut.reserved);
     end
     vm[req[335:304]/4+k]=req[48+k*32+:32];
    end
   end else reads=reads+1;
  end
  if(pv)begin
   if(delay_count==0)begin
    rsp={held[15:0]^(corrupt_tag?16'h0001:16'h0000),held[336],256'd0};
    if(!held[336])for(integer k=0;k<8;k=k+1)rsp[k*32+:32]=vm[held[335:304]/4+k];
    rsp_v=1;pv=0;
   end else delay_count=delay_count-1;
  end
 end
 always @(posedge clk)begin
  if(rsp_v&&rsp_r)begin if(rsp[256])acks=acks+1;#0.01;rsp_v=0;end
 end
 always @(posedge clk)begin
  if(ref_vo&&!use_vector)begin
   for(integer k=0;k<32;k=k+1)
    if((rbeat%((current_n+31)/32))*32+k<current_n)expected[dest_base+(rbeat/((current_n+31)/32))*layout_wstride+((rbeat%((current_n+31)/32))*32+k)*layout_ostride]={ref_y[k*16+:16],16'd0};
   rbeat=rbeat+1;
  end
 end
 task run(input integer op,input integer size);
  reg [127:0] h;reg [255:0] a,o;integer start_cycle;
  begin
   while(!ready)@(negedge clk);
   current_n=size;rbeat=0;writes=0;acks=0;reads=0;published_words=0;layout_mode=0;layout_rows=1;layout_ostride=1;layout_wstride=0;
   for(integer i=0;i<8192;i=i+1)begin vm[i]=32'hdeadbeef;expected[i]=32'hbadbad00;end
   for(integer i=0;i<size;i=i+1)vm[i]=32'h3f800000+((i/32%64)<<23)+((i%8)<<19);
   if(use_vector)for(integer i=0;i<size;i=i+1)begin
    vm[i]=vx[i*32+:32];expected[dest_base+i]={vy[i*16+:16],16'd0};
   end
   h=0;a=0;o=0;h[127:124]=4;h[123:118]=op;h[99:93]=17;
   if(op==6)h[71:64]=16;
   a[1:0]=1;a[67:48]=size;a[87:68]=1;
   o=a;o[47:8]=dest_base;
   @(negedge clk);cmd={o,512'd0,a,256'd0,h,1'b1};
   @(negedge clk);cmd=0;start_cycle=cycles;
   while(!done&&cycles-start_cycle<200000)@(negedge clk);
   if(!done)$fatal(1,"DROP/CREDIT timeout");
   if(fault)$fatal(1,"unexpected fault");
   if(writes!=size/8||acks!=size/8)$fatal(1,"EARLY_DONE actualACK accounting");
   if(vm[dest_base+size]!==32'hdeadbeef)$fatal(1,"TAIL clobber");
   cases=cases+1;nwords=nwords+size;
  end
 endtask
 task run_layout(input integer op,width,rows,ist,ost,rs,ws,ib,ob,bcast);
  reg [127:0]h;reg[255:0]a,o;integer begin_cycle;
  begin
   while(!ready)@(negedge clk);
   current_n=width;layout_rows=rows;layout_ostride=ost;layout_wstride=ws;dest_base=ob;layout_mode=1;
   use_vector=0;rbeat=0;writes=0;acks=0;reads=0;published_words=0;
   for(integer i=0;i<8192;i=i+1)begin vm[i]=32'hdeadbeef;expected[i]=32'hbadbad00;end
   for(integer row=0;row<rows;row=row+1)
    for(integer col=0;col<width;col=col+1)vm[ib+row*rs+col*(bcast?0:ist)]=32'h3f800000+((row*4+col/32)<<23)+(col%8<<19);
   h=0;a=0;o=0;h[127:124]=4;h[123:118]=op;h[99:93]=17;if(op==6)h[71:64]=16;
   a[1:0]=1;a[47:8]=ib;a[67:48]=width;a[87:68]=rows;a[119:88]=rs;a[135:120]=ist;a[5]=bcast;
   o=a;o[47:8]=ob;o[119:88]=ws;o[135:120]=ost;o[5]=0;
   @(negedge clk);cmd={o,512'd0,a,256'd0,h,1'b1};
   @(negedge clk);cmd=0;begin_cycle=cycles;
   while(!done&&cycles-begin_cycle<500000)@(negedge clk);
   if(!done||fault)$fatal(1,"MULTIROW/STRIDE status");
   if(published_words!=width*rows||acks!=writes)$fatal(1,"MULTIROW/STRIDE actualACK count");
   cases=cases+1;nwords=nwords+width*rows;
   dest_base=4096;layout_mode=0;layout_rows=1;layout_ostride=1;layout_wstride=0;
  end
 endtask
 task error_record(input integer kind);
  reg [127:0]h;reg [255:0]a,o;integer begin_cycle;
  begin
   while(!ready)@(negedge clk);
   current_n=32;use_vector=0;rbeat=0;writes=0;acks=0;reads=0;
   for(integer i=0;i<32;i=i+1)vm[i]=32'h3f800000;
   if(kind==2)vm[0]=32'h7fc00000;
   if(kind==3)vm[0]=32'h7f800000;
   if(kind==4)vm[0]=32'hff800000;
   h=0;a=0;h[127:124]=4;h[123:118]=4;h[99:93]=17;
   a[1:0]=1;a[67:48]=32;a[87:68]=1;o=a;o[47:8]=dest_base;
   @(negedge clk);cmd={o,512'd0,a,256'd0,h,1'b1};
   @(negedge clk);cmd=0;begin_cycle=cycles;
   if(kind==0)begin while(!dut.pending)@(negedge clk);provider_fault=1;
    @(negedge clk);provider_fault=0;end
   if(kind==1)corrupt_tag=1;
   while(!done&&cycles-begin_cycle<200000)@(negedge clk);
   corrupt_tag=0;
   if(!done||!fault||!drained||pv||rsp_v)$fatal(1,"FAULT drain/status");
   if(writes!=0)$fatal(1,"faulted record published");
   cases=cases+1;
  end
 endtask
 initial begin
  repeat(4)@(negedge clk);rst_n=1;
  run(4,32);run(5,64);run(6,16);run(6,48);run(4,2048);
  dest_base=0;run(4,2048);run(5,64);run(6,48);dest_base=4096;
  if($value$plusargs("VECTORS=%s",vectors))begin
   $readmemh({vectors,"/fp8_e8m0.in.hex"},gi8);$readmemh({vectors,"/fp8_e8m0.out.hex"},go8);
   $readmemh({vectors,"/fp4_e8m0.in.hex"},gi4);$readmemh({vectors,"/fp4_e8m0.out.hex"},go4);
   $readmemh({vectors,"/fp4_e4m3.in.hex"},gie);$readmemh({vectors,"/fp4_e4m3.out.hex"},goe);
   use_vector=1;
   for(integer i=0;i<49;i=i+1)begin vx=gi8[i];vy=go8[i];run(4,32);end
   for(integer i=0;i<49;i=i+1)begin vx=gi4[i];vy=go4[i];run(5,32);end
   for(integer i=0;i<86;i=i+1)begin vx=gie[i];vy=goe[i];run(6,32);end
   vx=gie[0];vy=goe[0];run(6,16);use_vector=0;
  end
  run_layout(4,32,3,2,3,128,160,3,4099,0);
  run_layout(5,64,2,1,1,96,128,5,4101,0);
  run_layout(6,48,3,3,2,160,128,1,4097,0);
  run_layout(6,16,2,1,1,32,32,3,4099,1);
  run_layout(4,32,3,2,2,96,96,3,3,0);
  // Illegal partialUEblock must fault with zero VM requests.
  while(!ready)@(negedge clk);
  begin reg [127:0]h;reg[255:0]a,o;
   h=0;a=0;h[127:124]=4;h[123:118]=4;h[99:93]=17;
   a[1:0]=1;a[67:48]=16;a[87:68]=1;o=a;o[47:8]=dest_base;
   @(negedge clk);cmd={o,512'd0,a,256'd0,h,1'b1};
   @(negedge clk);cmd=0;while(!done)@(negedge clk);if(!fault||req_v)$fatal(1,"invalid shape accepted");
  end
  error_record(0);error_record(1);error_record(2);error_record(3);error_record(4);
  // GH7 v1 block-size domain: all255 otherparameters fault beforeVM allocation.
  for(integer param_value=0;param_value<256;param_value=param_value+1)if(param_value!=16)begin
   reg [127:0]h;reg [255:0]a,o;integer oldreads;
   while(!ready)@(negedge clk);oldreads=reads;
   h=0;a=0;h[127:124]=4;h[123:118]=6;h[99:93]=17;h[71:64]=param_value;
   a[1:0]=1;a[67:48]=32;a[87:68]=1;o=a;o[47:8]=4096;
   @(negedge clk);cmd={o,512'd0,a,256'd0,h,1'b1};
   @(negedge clk);cmd=0;while(!done)@(negedge clk);
   if(!fault||req_v||reads!=oldreads||dut.reserved!=0)$fatal(1,"GH7 invalidblock allocatedbeat");
   cases=cases+1;
  end
  @(negedge clk);rst_n=0;repeat(3)@(negedge clk);rst_n=1;#0.01;
  if(!ready||req_v||!drained)$fatal(1,"cold reset leftovers");
  $display("PASS QUANT_TRANSPORT cases=%0d words=%0d arbitraryCPstall ACKdelay tail16/48 illegalUE",cases,nwords);$finish;
 end
endmodule
