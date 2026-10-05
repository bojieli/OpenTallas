`timescale 1ns/1ps
// Joint transport exactness only: real landed bridge + shared borrower.
// No SU arithmetic, full gather, physical memory or routed-clock claim.
module tb_hbm_gather_borrow_joint;
 reg clk=0; always #5 clk=~clk;
 reg por_n=0;
 integer cycles=0;
 reg desc_v=0,start_v=0,book=1;
 reg [2:0] desc_index=0;
 reg [63:0] desc_data=0;
 wire desc_r,start_r,borrow_v,retained,arena_visible,sink_visible,bridge_fault;
 wire [2:0] grants;
 wire borrow_fault,idle;
 reg req_v=0; wire req_r;
 reg [2:0] req_kind=0;
 reg [31:0] req_addr=0;
 reg [15:0] req_tag=0;
 reg [511:0] req_data=0;
 wire rsp_v,rsp_checked;reg rsp_r=0;
 wire [511:0] rsp_data;
 wire [31:0] rsp_addr;wire [15:0] rsp_tag;wire [2:0] rsp_kind;
 wire [31:0] held_job;wire [3:0] held_gen;
 wire [16:0] held_token;wire [19:0] held_pos;
 wire bridge_req_v,bridge_req_r,bridge_req_we;
 wire [31:0] bridge_addr,bridge_strb;
 wire [255:0] bridge_wdata;wire [15:0] bridge_tag;
 wire bridge_rsp_v,bridge_rsp_r,bridge_rsp_we;
 wire [255:0] bridge_rdata;wire [15:0] bridge_rtag;
 wire release_r,borrow_release;
 wire [2:0] release_ready;
 reg release_v=0,result_published=0,source_reverse_done=0;
 reg native_v=0,native_rsp_r=0,native_drained=1,cdc_drained=1;
 reg [31:0] native_addr=32'h10000;
 wire [3:0] client_ready,client_rsp_v,client_rsp_we;
 wire [63:0] client_rsp_tag;wire [1023:0] client_rsp_data;
 wire m_req_v,m_req_we,m_rsp_rdy;
 wire [31:0] m_req_addr,m_req_strb;wire [255:0] m_req_data;
 wire [15:0] m_req_tag;
 wire m_req_rdy;
 reg m_rsp_v=0,m_rsp_we=0;
 reg [15:0] m_rsp_tag=0;
 reg [255:0] m_rsp_data=0;
 reg pending=0;integer delay_count=0;
 reg [255:0] mem[0:65535];
 reg [255:0] saved_data;
 reg saved_we;reg [15:0] saved_tag;
 reg corrupt_read=0,foreign_tag=0;
 integer accepted=0,read_sectors=0,write_sectors=0;
 reg [3:0] previous_state=0;
 localparam [31:0] JOB=32'h12345678, BASE=32'h100000;
 localparam [3:0] GEN=4'h9;
 localparam [16:0] TOKEN=17'd1165;
 localparam [19:0] POS=20'd4095;
 assign bridge_req_r=client_ready[1];
 assign bridge_rsp_v=client_rsp_v[1];
 assign bridge_rsp_we=client_rsp_we[1];
 assign bridge_rtag=client_rsp_tag[16+:16];
 assign bridge_rdata=client_rsp_data[256+:256];
 ot_hbm_integrated_gather_bridge #(.ENABLE(1),.VM_AW(21)) bridge(
  .clk(clk),.por_n(por_n),.desc_v(desc_v),.desc_r(desc_r),.desc_index(desc_index),.desc_data(desc_data),
  .start_v(start_v),.start_r(start_r),.installed_book_valid(book),
  .job(JOB),.gen(GEN),.token(TOKEN),.pos(POS),
  .borrow_v(borrow_v),.borrow_granted(grants[0]),.borrow_fault(borrow_fault),
  .retained(retained),.arena_visible(arena_visible),.sink_visible(sink_visible),.fault(bridge_fault),
  .req_v(req_v),.req_r(req_r),.req_kind(req_kind),.req_addr(req_addr),.req_tag(req_tag),
  .req_rank(7'd0),.req_word(6'd0),.req_data(req_data),
  .req_job(JOB),.req_gen(GEN),.req_token(TOKEN),.req_pos(POS),
  .rsp_v(rsp_v),.rsp_r(rsp_r),.rsp_data(rsp_data),.rsp_addr(rsp_addr),.rsp_tag(rsp_tag),
  .rsp_kind(rsp_kind),.rsp_checked(rsp_checked),
  .held_job(held_job),.held_gen(held_gen),.held_token(held_token),.held_pos(held_pos),
  .m_req_v(bridge_req_v),.m_req_rdy(bridge_req_r),.m_req_we(bridge_req_we),
  .m_req_addr(bridge_addr),.m_req_wdata(bridge_wdata),.m_req_wstrb(bridge_strb),.m_req_tag(bridge_tag),
  .m_rsp_v(bridge_rsp_v),.m_rsp_rdy(bridge_rsp_r),.m_rsp_we(bridge_rsp_we),.m_rsp_data(bridge_rdata),.m_rsp_tag(bridge_rtag),
  .release_v(release_v),.release_r(release_r),.release_job(JOB),.release_gen(GEN),.release_token(TOKEN),.release_pos(POS),
  .result_published(result_published),.source_reverse_done(source_reverse_done),
  .borrow_release(borrow_release),.borrow_release_ack(release_ready[0]));
 ot_hbm_integrated_sm0_borrow #(.ENABLE(1)) arb(
  .clk(clk),.por_n(por_n),.native_clients_drained(native_drained),.cdc_drained(cdc_drained),
  .lease_v({2'b0,borrow_v}),.borrower_quiet(3'b111),
  .lease_job({64'b0,JOB}),.lease_gen({8'b0,GEN}),.lease_token({34'b0,TOKEN}),.lease_pos({40'b0,POS}),
  .lease_granted(grants),.release_v({2'b0,borrow_release}),.release_r(release_ready),
  .release_job({64'b0,JOB}),.release_gen({8'b0,GEN}),.release_token({34'b0,TOKEN}),.release_pos({40'b0,POS}),
  .req_v({2'b0,bridge_req_v,native_v}),.req_rdy(client_ready),.req_we({2'b0,bridge_req_we,1'b0}),
  .req_addr({64'b0,bridge_addr,native_addr}),.req_wdata({512'b0,bridge_wdata,256'b0}),
  .req_wstrb({64'b0,bridge_strb,32'b0}),.req_tag({32'b0,bridge_tag,16'hf00d}),
  .rsp_v(client_rsp_v),.rsp_rdy({2'b0,bridge_rsp_r,native_rsp_r}),.rsp_we(client_rsp_we),
  .rsp_tag(client_rsp_tag),.rsp_data(client_rsp_data),
  .m_req_v(m_req_v),.m_req_rdy(m_req_rdy),.m_req_we(m_req_we),.m_req_addr(m_req_addr),
  .m_req_wdata(m_req_data),.m_req_wstrb(m_req_strb),.m_req_tag(m_req_tag),
  .m_rsp_v(m_rsp_v),.m_rsp_rdy(m_rsp_rdy),.m_rsp_we(m_rsp_we),.m_rsp_tag(m_rsp_tag),.m_rsp_data(m_rsp_data),
  .idle(idle),.fault(borrow_fault));
 assign m_req_rdy=por_n&&!pending&&!m_rsp_v&&(cycles%4!=0);
 always @(posedge clk)begin
  if(por_n && bridge.on.state!=previous_state)
   $display("BRIDGE state=%0d grants=%b start=%b req=%b legal=%b frame=%b shared_fault=%b",bridge.on.state,grants,start_v,req_v,bridge.on.legal,bridge.on.frame_match,borrow_fault);
  if(por_n && bridge.on.state==2)
   $display("READY predicates fault=%b bad=%b grant=%b release=%b release_match=%b req=%b legal=%b frame=%b",bridge_fault,bridge.on.bad,bridge.borrow_granted,bridge.release_v,bridge.on.release_match,bridge.req_v,bridge.on.legal,bridge.on.frame_match);
  if(por_n && bridge.on.bad)
   for(integer row=0;row<39;row++)
    if(bridge.on.dec[row][65])$display("BAD_ROW row=%0d code=%h decoded=%h",row,bridge.on.code[row],bridge.on.dec[row]);
  previous_state<=bridge.on.state;
  cycles<=cycles+1;
  if(!por_n)begin pending<=0;m_rsp_v<=0;accepted<=0;read_sectors<=0;write_sectors<=0;end
  else begin
   if(m_req_v&&m_req_rdy)begin
    if(m_req_addr[4:0]!=0||m_req_addr>=32'h200000)$fatal(1,"bad sector address");
    accepted<=accepted+1;
    pending<=1;delay_count<=3;saved_we<=m_req_we;saved_tag<=m_req_tag;
    if(m_req_we)begin
     if(m_req_strb!==32'hffffffff)$fatal(1,"write strobe mismatch");
     mem[m_req_addr>>5]<=m_req_data;saved_data<=0;write_sectors<=write_sectors+1;
    end else begin saved_data<=mem[m_req_addr>>5];read_sectors<=read_sectors+1;end
   end
   if(pending)begin
    if(delay_count==0)begin
     m_rsp_v<=1;pending<=0;m_rsp_we<=saved_we;
     m_rsp_tag<=saved_tag^(foreign_tag?16'h1:16'h0);
     m_rsp_data<=saved_data^((corrupt_read&&!saved_we)?256'd1:256'd0);
    end else delay_count<=delay_count-1;
   end
   if(m_rsp_v&&m_rsp_rdy)m_rsp_v<=0;
  end
 end
 task automatic step;
  @(posedge clk);#1;@(negedge clk);
 endtask
 task automatic reset;
  por_n=0;req_v=0;start_v=0;desc_v=0;rsp_r=0;native_v=0;native_rsp_r=0;
  corrupt_read=0;foreign_tag=0;release_v=0;
  native_drained=1;cdc_drained=1;
  repeat(3)step();por_n=1;step();
 endtask
 task automatic descriptors;
  reg [63:0] v[0:7];
  v[0]=0;v[1]={32'h20000,32'h10000};v[2]={32'h160000,BASE};
  v[3]={32'h180800,32'h180000};v[4]=64'h8000000;
  v[5]=64'd96|(64'd512<<16)|(64'd32<<32);v[6]=0;v[7]=0;
  for(integer i=0;i<8;i++)begin
   if(!desc_r)$fatal(1,"descriptor not ready");
   desc_index=3'(i);desc_data=v[i];desc_v=1;step();
  end
  desc_v=0;
 endtask
 task automatic acquire;
  start_v=1;
  while(!start_r)begin
   if(bridge_fault||borrow_fault)$fatal(1,"fault at admission");step();
  end
  step();start_v=0;
  repeat(18)step();
  if(bridge_fault||borrow_fault)$fatal(1,"fault before first request state=%0d",bridge.on.state);
  if(grants!==3'b001||!retained||held_job!==JOB||held_gen!==GEN||held_token!==TOKEN||held_pos!==POS)
   $fatal(1,"lease/frame mismatch");
 endtask
 task automatic send(input [2:0] kind,input [31:0] addr,input [15:0] tag,input [511:0] data);
  req_kind=kind;req_addr=addr;req_tag=tag;req_data=data;req_v=1;
  #1;
  while(!req_r)begin
   if(bridge_fault)$fatal(1,"request fault state=%0d bad=%0d shared=%0d legal=%0d frame=%0d",bridge.on.state,bridge.on.bad,borrow_fault,bridge.on.legal,bridge.on.frame_match);
   step();
  end
  step();req_v=0;
 endtask
 task automatic exact_return(input [2:0] kind,input [31:0] addr,input [15:0] tag,input [511:0] data);
  integer before_hold;
  while(!rsp_v)begin if(bridge_fault||borrow_fault)$fatal(1,"transport fault");step();end
  before_hold=accepted;
  repeat(9)begin
   if(!rsp_v||!rsp_checked||rsp_data!==data||rsp_addr!==addr||rsp_tag!==tag||rsp_kind!==kind)
    $fatal(1,"payload or held identity mismatch");
   if(grants!==3'b001||!retained||accepted!=before_hold||release_r||borrow_release)
    $fatal(1,"lease/debt lost under consumer stall");
   step();
  end
  rsp_r=1;step();rsp_r=0;step();
 endtask
 reg [511:0] source,write_value;
 initial begin
  source=512'h0123456789abcdef_fedcba9876543210_aabbccddeeff0011_0011223344556677_12345678abcdef09_76543210fedcba98_0102030405060708_f1f2f3f4f5f6f7f8;
  write_value=~source;
  mem[32'h10000>>5]=source[255:0];mem[32'h10020>>5]=source[511:256];
  reset();descriptors();
  // A native request and held response must retire before index ownership.
  native_drained=0;native_v=1;
  while(!client_ready[0])step();step();native_v=0;start_v=1;
  while(!client_rsp_v[0])step();
  repeat(7)begin if(grants!=0||start_r)$fatal(1,"native debt bypassed");step();end
  if(client_rsp_data[255:0]!==source[255:0]||client_rsp_tag[15:0]!==16'hf00d)
   $fatal(1,"native routed response mismatch");
  native_rsp_r=1;step();native_rsp_r=0;native_drained=1;start_v=0;
  acquire();
  send(0,32'h10000,16'hbb01,0);
  exact_return(0,32'h10000,16'hbb01,source);
  if(read_sectors!=3||write_sectors!=0)$fatal(1,"read sector count mismatch");
  send(1,BASE,16'hbb02,write_value);
  exact_return(1,BASE,16'hbb02,write_value);
  if(read_sectors!=5||write_sectors!=2||arena_visible||sink_visible)
   $fatal(1,"postverified write count/visibility mismatch");
  if({mem[(BASE+32)>>5],mem[BASE>>5]}!==write_value)$fatal(1,"stored bytes mismatch");
  // A real readback mismatch must refuse publication, not return success.
  reset();descriptors();acquire();corrupt_read=1;
  send(1,BASE,16'hbb03,write_value);
  while(!bridge_fault)begin if(rsp_v)$fatal(1,"corrupt writeback published");step();end
  if(rsp_checked||arena_visible||sink_visible||borrow_release)$fatal(1,"fault released ownership");
  // A foreign physical ACK cannot retire the shared request debt.
  reset();descriptors();acquire();foreign_tag=1;
  send(0,32'h10000,16'hbb04,0);
  while(!borrow_fault)begin if(rsp_v)$fatal(1,"foreign ACK published");step();end
  if(m_rsp_rdy||rsp_v||borrow_release)$fatal(1,"foreign ACK consumed/released");
  $display("PASS joint gather/shared borrower: exact native+two-sector read+verified write, stalls, corrupt readback and foreign ACK rejection");
  $finish;
 end
endmodule
