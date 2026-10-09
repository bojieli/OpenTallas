`timescale 1ns/1ps
// Minimum facade + real publication endpoint + two actual SRAM macros as a
// 512-bit VM read fixture. Arbiter grant/response routing is explicit here;
// this fixture does not qualify the selected NP8 arbiter or E3 address map.
module tb_shared_reader;
 reg clk=0;always #0.416667 clk=~clk;
 reg rst_n=0,cmd_valid=0,lease_valid=1,cmd_native_write_retired=1;
 reg [73:0] cmd_context={3'd5,2'd3,2'd2,4'd7,21'd1048575,10'd865,32'd123};
 reg [73:0] lease_context;
 reg [13:0] cmd_base=64;reg [14:0] cmd_region_rows=256;
 wire cmd_ready,lease_release,busy,reader_fault;
 wire [73:0] release_context,pub_cmd_context,req_context,pub_context;
 wire pub_cmd_valid,pub_cmd_ready,req_valid,req_ready,pub_valid,pub_ready;
 wire [13:0] req_row;wire [6:0] req_word,pub_word;
 wire [511:0] pub_data;wire pub_last,pub_fmt_fp32,pub_error;
 reg rsp_valid=0,rsp_fault=0;reg [511:0] rsp_data=0;
 reg [73:0] rsp_context=0;reg [6:0] rsp_word=0;
 wire out_valid,out_ready,out_last,out_corrected,publisher_busy,publisher_fault;
 wire [511:0] out_data;wire [73:0] out_context;wire [6:0] out_word;
 wire pub_retired=out_valid&&out_ready&&out_last;
 wire [73:0] pub_retired_context=out_context;
 ot_dsrom_mtp_shared_reader #(.ENABLE(1)) reader(
  .clk(clk),.rst_n(rst_n),.cmd_valid(cmd_valid),.cmd_ready(cmd_ready),.cmd_context(cmd_context),
  .cmd_base(cmd_base),.cmd_region_rows(cmd_region_rows),.cmd_native_write_retired(cmd_native_write_retired),
  .lease_valid(lease_valid),.lease_context(lease_context),.lease_release(lease_release),.release_context(release_context),
  .pub_cmd_valid(pub_cmd_valid),.pub_cmd_ready(pub_cmd_ready),.pub_cmd_context(pub_cmd_context),
  .req_valid(req_valid),.req_ready(req_ready),.req_row(req_row),.req_context(req_context),.req_word(req_word),
  .rsp_valid(rsp_valid),.rsp_data(rsp_data),.rsp_fault(rsp_fault),.rsp_context(rsp_context),.rsp_word(rsp_word),
  .pub_valid(pub_valid),.pub_ready(pub_ready),.pub_data(pub_data),.pub_context(pub_context),.pub_word(pub_word),
  .pub_last(pub_last),.pub_fmt_fp32(pub_fmt_fp32),.pub_error(pub_error),
  .pub_retired(pub_retired),.pub_retired_context(pub_retired_context),.busy(busy),.fault(reader_fault));
`ifdef READER_CE
 localparam [71:0] INJECT=72'd1;
`elsif READER_UE
 localparam [71:0] INJECT=72'd3;
`else
 localparam [71:0] INJECT=72'd0;
`endif
 ot_dsrom_mtp_shared_producer #(.ECC_PIPE(1),.READ_INJECT(INJECT)) publisher(
  .clk(clk),.rst_n(rst_n),.cmd_valid(pub_cmd_valid),.cmd_ready(pub_cmd_ready),.cmd_context(pub_cmd_context),
  .in_valid(pub_valid),.in_ready(pub_ready),.in_data(pub_data),.in_context(pub_context),.in_word(pub_word),
  .in_last(pub_last),.in_fmt_fp32(pub_fmt_fp32),.in_error(pub_error),
  .out_valid(out_valid),.out_ready(out_ready),.out_data(out_data),.out_context(out_context),.out_word(out_word),
  .out_last(out_last),.out_corrected(out_corrected),.busy(publisher_busy),.fault(publisher_fault));
 reg vm_write=0;reg [7:0] vm_waddr=0;reg [511:0] vm_wdata=0;
 wire [511:0] vm_rdata;
 assign req_ready=cyc%4!=1;
 assign out_ready=cyc%7!=2;
 for(genvar k=0;k<2;k=k+1)begin:g_vm
  ot_sram_1r1w_256x256_m2_r2c2 mem(.clk(clk),
   .r_ce_in(req_valid&&req_ready),.r_addr_in(req_row[7:0]),.rd_out(vm_rdata[256*k+:256]),
   .w_ce_in(vm_write),.w_addr_in(vm_waddr),.wd_in(vm_wdata[256*k+:256]),.w_mask_in({256{1'b1}}),
   .rr_en(2'd0),.rr_addr(14'd0),.cr_en(2'd0),.cr_sel(16'd0));
 end
 integer cyc=0,bad=0,nreq=0,nout=0,start=0;
 reg route_v=0,pending=0;reg [73:0] route_context,pending_context;
 reg [6:0] route_word,pending_word;reg [511:0] pending_data;reg [1:0] response_delay;
 function automatic [31:0] value(input integer row);
  case(row)
   0:value=32'h00000000;1:value=32'h80000000;
   2:value=32'h00010000;3:value=32'h80010000;
   default:value={((row%2)!=0),8'(110+row%30),7'((row*17)%128),16'd0};
  endcase
 endfunction
 always @(posedge clk)begin
  cyc<=cyc+1;
  if(rst_n)begin
   route_v<=req_valid&&req_ready;rsp_valid<=0;
   if(req_valid&&req_ready)begin
    nreq<=nreq+1;route_context<=req_context;route_word<=req_word;
    if(req_row!==14'(64+nreq)||req_word!==7'(nreq))$fatal(1,"request address/order mismatch");
   end
   if(route_v)begin
    if(pending)$fatal(1,"fixture outstanding read overflow");
    pending_data<=vm_rdata;pending_context<=route_context;pending_word<=route_word;
    pending<=1;response_delay<=route_word%4;
   end else if(pending)begin
    if(response_delay!=0)response_delay<=response_delay-1'b1;
    else begin
    pending<=0;rsp_valid<=1;rsp_data<=pending_data;
    rsp_context<=pending_context;rsp_word<=pending_word;rsp_fault<=0;
    if(pending_word==17)case(bad)
     4:rsp_context<=pending_context^74'd1;
     5:rsp_word<=16;
     6:rsp_data<=pending_data|512'd1;
     7:rsp_fault<=1;
    endcase
    end
   end
   if(bad==8&&req_valid&&req_word==17)lease_valid<=0;
   if(out_valid&&out_ready)begin
    if(bad||out_context!==cmd_context||out_word!==7'(nout)||out_last!==(nout==79))$fatal(1,"reader publication identity/order mismatch");
    for(integer j=0;j<16;j=j+1)if(out_data[32*j+:32]!==value(16*nout+j))$fatal(1,"reader publication payload mismatch");
    nout<=nout+1;
`ifdef READER_CE
    if(!out_corrected)$fatal(1,"reader CE not corrected/reported");
`endif
   end
   // The fixed fixture's grant and response/calendar bounds are <2000 cycles.
   if(cyc>4096)$fatal(1,"fixture did not retire within its finite calendar");
  end
 end
 initial begin
  if($value$plusargs("bad=%d",bad))begin end
  lease_context=cmd_context;repeat(8)@(negedge clk);rst_n=1;
  for(integer w=0;w<80;w=w+1)begin
   vm_write=1;vm_waddr=64+w;
   for(integer j=0;j<16;j=j+1)vm_wdata[32*j+:32]=value(16*w+j);
   @(negedge clk);
  end
  vm_write=0;repeat(2)@(negedge clk);
  case(bad)
   1:cmd_native_write_retired=0;
   2:lease_context=cmd_context^74'd1;
   3:cmd_region_rows=100;
  endcase
  start=cyc;cmd_valid=1;@(negedge clk);cmd_valid=0;
  if(bad)begin
   wait(reader_fault);repeat(2)@(negedge clk);
   if(req_valid||pub_valid||lease_release||nout!=0)$fatal(1,"reader negative escaped");
   if(bad<=3&&nreq!=0)$fatal(1,"reader published before native retirement/range lease");
   $display("SHARED_READER_NEGATIVE PASS bad=%0d",bad);$finish;
  end
`ifdef READER_UE
  wait(publisher_fault);repeat(2)@(negedge clk);
  if(lease_release||nout!=0||!busy)$fatal(1,"reader UE released lease or published payload");
  $display("SHARED_READER_UE PASS leaseheld=1");$finish;
`endif
  wait(lease_release);@(negedge clk);
  if(nreq!=80||nout!=80||busy||publisher_busy||reader_fault||publisher_fault||release_context!==cmd_context)$fatal(1,"reader retirement mismatch");
  $display("SHARED_READER PASS reads=%0d rows=1280 output_flits=%0d elapsed_cycles=%0d",nreq,nout,cyc-start);$finish;
 end
endmodule
