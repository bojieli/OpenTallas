`timescale 1ns/1ps
module tb_hbm_sm_result_provider;
 reg clk=0;always #5 clk=~clk;
 reg por_n=0,installed=1,reserve_v=0,result_v=0,native_done=0,publication_r=0;
 reg [15:0] record_id=16'h1234,provider_tag=16'habcd;
 reg [12:0] rows=4096;reg [36:0] base=37'h1000000000,limit=37'h1000020000;
 reg [11:0] result_row=0;reg [255:0] result_data=0;
 wire reserve_r,source_permit,retained,fault,publication_v,req_v,req_we,rsp_r;
 wire [15:0] publication_record,req_tag;wire [36:0] req_addr;wire [255:0] req_data;
 reg rsp_v=0,rsp_we=0,rsp_error=0;reg [15:0] rsp_tag=0;reg [255:0] rsp_data=0;
 integer cycle=0,writes=0,reads=0,mode=0,index;wire req_r=cycle%5!=0;
 reg [255:0] memory[0:4095];
 ot_hbm_sm_result_provider #(.ENABLE(1)) dut(.*);
 function automatic [255:0] payload(input integer row);
  payload={32'(row^32'h99887766),32'(row+7),32'(row*3),32'(row),32'(row^32'hdeadbeef),32'(row*13),32'(row-1),32'(row^32'h01234567)};
 endfunction
 always @(posedge clk)if(por_n)begin
  cycle<=cycle+1;
  if(cycle>100000)$fatal(1,"watchdog");
  if(rsp_v&&rsp_r)rsp_v<=0;
  if(req_v&&req_r)begin
   if(rsp_v)$fatal(1,"multiple outstanding");
   if(req_addr<base||req_addr>=limit||req_addr[4:0]!=0)$fatal(1,"bad address");
   index=(req_addr-base)>>5;
   if(req_tag!=provider_tag)$fatal(1,"bad tag");
   if(req_we)begin
    if(req_data!==payload(index))$fatal(1,"payload row %d",index);
    memory[index]<=req_data;writes<=writes+1;
   end else begin reads<=reads+1;end
   rsp_v<=1;rsp_we<=req_we;rsp_tag<=req_tag;rsp_error<=0;
   rsp_data<=req_we?0:memory[index];
   if(mode==3&&!req_we)rsp_data<=memory[index]^256'b1;
   if(mode==4)rsp_tag<=req_tag^16'b1;
  end
  if(publication_v&&(reads!=rows||writes!=rows||publication_record!=record_id))$fatal(1,"early/wrong publication");
 end
 initial begin
  if($value$plusargs("MODE=%d",mode))begin end
  if(mode!=0)begin rows=8;limit=base+256;end
  repeat(3)@(negedge clk);por_n=1;
  @(negedge clk);reserve_v=1;
  @(negedge clk);reserve_v=0;
  wait(source_permit);@(negedge clk);
  for(integer r=integer'(rows)-1;r>=0;r=r-1)begin
   result_v=1;result_row=12'(r);result_data=payload(r);
   if(mode==1&&r==0)result_row=1;
   if(mode==2&&r==0)result_row=12'(rows);
   @(negedge clk);
  end
  result_v=0;native_done=1;
  @(negedge clk);native_done=0;
  if(mode==5)begin dut.on.code[0]=dut.on.code[0]^72'b11;end
  if(mode==6) dut.on.bank[0].word[0].mem.arr[0][0]=~dut.on.bank[0].word[0].mem.arr[0][0];
  if(mode==7)begin
   dut.on.bank[0].word[0].mem.arr[0][0]=~dut.on.bank[0].word[0].mem.arr[0][0];
   dut.on.bank[0].word[0].mem.arr[0][4]=~dut.on.bank[0].word[0].mem.arr[0][4];
  end
  if(mode==0||mode==6)begin
   wait(publication_v||fault);if(fault)$fatal(1,"unexpected fault state %d",dut.on.state);
   repeat(5)@(negedge clk);if(!publication_v||!retained)$fatal(1,"publication not retained");
   publication_r=1;@(negedge clk);publication_r=0;
   if(retained)$fatal(1,"reservation not retired");
   $display("PASS rows=%0d reverse-order capture writes=%0d reads=%0d cycles=%0d",rows,writes,reads,cycle);
  end else begin
   wait(fault||publication_v);if(publication_v)$fatal(1,"bad input published");
   repeat(5)@(negedge clk);if(!fault||req_v||publication_v||source_permit)$fatal(1,"fault not retained");
   $display("PASS rejection mode=%0d cycles=%0d",mode,cycle);
  end
  $finish;
 end
endmodule
