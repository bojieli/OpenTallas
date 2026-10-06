`timescale 1ns/1ps
// Installation/transport control proof only. Deterministic protocol payloads
// are NOT released numerical scores, IDs, arithmetic gold or parent credit.
module tb_formatter_preinstall;
reg  clk;
reg  por_n;
reg  warm_req;
reg  preinstall_begin_v;
wire  preinstall_begin_r;
reg [72:0] preinstall_begin_frame;
reg [31:0] preinstall_score_base;
reg [31:0] preinstall_id_base;
reg [32:0] preinstall_capacity;
reg [7:0] preinstall_occupied_records;
reg [4:0] preinstall_layer;
reg [4:0] preinstall_candidate_source_layer;
reg  preinstall_candidate_masked;
reg  preinstall_record_v;
wire  preinstall_record_r;
reg [1:0] preinstall_record_kind;
reg [6:0] preinstall_record_rank;
reg [31:0] preinstall_record_base;
reg [31:0] preinstall_record_end;
reg [72:0] preinstall_record_frame;
reg [2:0] preinstall_other_writer_v;
reg [95:0] preinstall_other_writer_base;
reg [95:0] preinstall_other_writer_end;
reg  preinstall_source_v;
wire  preinstall_source_r;
reg [72:0] preinstall_source_frame;
reg [6:0] preinstall_source_rank;
reg  preinstall_source_plane;
reg [4:0] preinstall_source_word;
reg [511:0] preinstall_source_data;
wire  preinstall_source_ACK_v;
reg  preinstall_source_ACK_r;
wire [72:0] preinstall_source_ACK_frame;
wire [6:0] preinstall_source_ACK_rank;
wire  preinstall_source_ACK_plane;
wire [4:0] preinstall_source_ACK_word;
wire  reservation_v;
reg  reservation_r;
wire  reservation_checked;
wire  reservation_exclusive;
wire [72:0] reservation_frame;
wire [511:0] reservation_descriptor;
reg  consumer_reverse_v;
wire  consumer_reverse_r;
reg [72:0] consumer_reverse_frame;
reg  consumer_sink_ACK_drained;
wire  source_reverse_v;
reg  source_reverse_r;
wire  source_reverse_checked;
wire  source_drained;
wire [72:0] source_reverse_frame;
wire  preinstall_retained;
wire [72:0] preinstall_frame;
wire  preinstall_warm_ack;
wire  preinstall_fault;
wire  preinstall_ce;
wire  preinstall_due;
reg  desc_v;
wire  desc_r;
reg [2:0] desc_index;
reg [63:0] desc_data;
reg  start_v;
wire  start_r;
reg  installed_book_valid;
reg [31:0] job;
reg [3:0] gen;
reg [16:0] token;
reg [19:0] pos;
wire  retained;
wire  arena_visible;
wire  sink_visible;
wire  fault;
wire [31:0] bound_arena_base;
wire [31:0] bound_arena_limit;
wire  formatter_lease_valid;
wire [72:0] formatter_lease_frame;
reg  req_v;
wire  req_r;
reg [2:0] req_kind;
reg [31:0] req_addr;
reg [15:0] req_tag;
reg [6:0] req_rank;
reg [5:0] req_word;
reg [511:0] req_data;
reg [31:0] req_job;
reg [3:0] req_gen;
reg [16:0] req_token;
reg [19:0] req_pos;
wire  rsp_v;
reg  rsp_r;
wire [511:0] rsp_data;
wire [31:0] rsp_addr;
wire [15:0] rsp_tag;
wire [2:0] rsp_kind;
wire  rsp_checked;
wire [31:0] held_job;
wire [3:0] held_gen;
wire [16:0] held_token;
wire [19:0] held_pos;
wire  m_req_v;
reg  m_req_rdy;
wire  m_req_we;
wire [31:0] m_req_addr;
wire [255:0] m_req_wdata;
wire [31:0] m_req_wstrb;
wire [15:0] m_req_tag;
reg  m_rsp_v;
wire  m_rsp_rdy;
reg  m_rsp_we;
reg [255:0] m_rsp_data;
reg [15:0] m_rsp_tag;
reg  release_v;
wire  release_r;
reg [31:0] release_job;
reg [3:0] release_gen;
reg [16:0] release_token;
reg [19:0] release_pos;
reg  result_published;
reg  source_reverse_done;
reg  native_clients_drained;
reg  cdc_drained;
reg  provider_fault;
reg [3:0] observe_req;
reg [3:0] observe_rsp;
reg [3:0] observe_req_we;
reg [3:0] observe_rsp_we;
reg [63:0] observe_req_tag;
reg [63:0] observe_rsp_tag;
reg [3:0] return_offer;
wire [3:0] response_authorized;
reg [31:0] native_job;
reg [3:0] native_gen;
reg [16:0] native_token;
reg [19:0] native_pos;
wire  native_credit_empty;
wire  shared_idle;
reg [1:0] peer_lease_v;
reg [1:0] peer_quiet;
reg [1:0] peer_release_v;
reg [63:0] peer_lease_job;
reg [63:0] peer_release_job;
reg [7:0] peer_lease_gen;
reg [7:0] peer_release_gen;
reg [33:0] peer_lease_token;
reg [33:0] peer_release_token;
reg [39:0] peer_lease_pos;
reg [39:0] peer_release_pos;
wire [1:0] peer_lease_granted;
wire [1:0] peer_release_r;
reg [2:0] p_req_v;
reg [2:0] p_req_we;
wire [2:0] p_req_rdy;
reg [95:0] p_req_addr;
reg [95:0] p_req_wstrb;
reg [767:0] p_req_wdata;
reg [47:0] p_req_tag;
wire [2:0] p_rsp_v;
wire [2:0] p_rsp_we;
reg [2:0] p_rsp_rdy;
wire [47:0] p_rsp_tag;
wire [767:0] p_rsp_data;
ot_hbm_formatter_preinstall_gather_owner #(.ENABLE(1),.PREINSTALL_ENABLE(1),.VM_AW(14)) dut(
.clk(clk),
.por_n(por_n),
.warm_req(warm_req),
.preinstall_begin_v(preinstall_begin_v),
.preinstall_begin_r(preinstall_begin_r),
.preinstall_begin_frame(preinstall_begin_frame),
.preinstall_score_base(preinstall_score_base),
.preinstall_id_base(preinstall_id_base),
.preinstall_capacity(preinstall_capacity),
.preinstall_occupied_records(preinstall_occupied_records),
.preinstall_layer(preinstall_layer),
.preinstall_candidate_source_layer(preinstall_candidate_source_layer),
.preinstall_candidate_masked(preinstall_candidate_masked),
.preinstall_record_v(preinstall_record_v),
.preinstall_record_r(preinstall_record_r),
.preinstall_record_kind(preinstall_record_kind),
.preinstall_record_rank(preinstall_record_rank),
.preinstall_record_base(preinstall_record_base),
.preinstall_record_end(preinstall_record_end),
.preinstall_record_frame(preinstall_record_frame),
.preinstall_other_writer_v(preinstall_other_writer_v),
.preinstall_other_writer_base(preinstall_other_writer_base),
.preinstall_other_writer_end(preinstall_other_writer_end),
.preinstall_source_v(preinstall_source_v),
.preinstall_source_r(preinstall_source_r),
.preinstall_source_frame(preinstall_source_frame),
.preinstall_source_rank(preinstall_source_rank),
.preinstall_source_plane(preinstall_source_plane),
.preinstall_source_word(preinstall_source_word),
.preinstall_source_data(preinstall_source_data),
.preinstall_source_ACK_v(preinstall_source_ACK_v),
.preinstall_source_ACK_r(preinstall_source_ACK_r),
.preinstall_source_ACK_frame(preinstall_source_ACK_frame),
.preinstall_source_ACK_rank(preinstall_source_ACK_rank),
.preinstall_source_ACK_plane(preinstall_source_ACK_plane),
.preinstall_source_ACK_word(preinstall_source_ACK_word),
.reservation_v(reservation_v),
.reservation_r(reservation_r),
.reservation_checked(reservation_checked),
.reservation_exclusive(reservation_exclusive),
.reservation_frame(reservation_frame),
.reservation_descriptor(reservation_descriptor),
.consumer_reverse_v(consumer_reverse_v),
.consumer_reverse_r(consumer_reverse_r),
.consumer_reverse_frame(consumer_reverse_frame),
.consumer_sink_ACK_drained(consumer_sink_ACK_drained),
.source_reverse_v(source_reverse_v),
.source_reverse_r(source_reverse_r),
.source_reverse_checked(source_reverse_checked),
.source_drained(source_drained),
.source_reverse_frame(source_reverse_frame),
.preinstall_retained(preinstall_retained),
.preinstall_frame(preinstall_frame),
.preinstall_warm_ack(preinstall_warm_ack),
.preinstall_fault(preinstall_fault),
.preinstall_ce(preinstall_ce),
.preinstall_due(preinstall_due),
.desc_v(desc_v),
.desc_r(desc_r),
.desc_index(desc_index),
.desc_data(desc_data),
.start_v(start_v),
.start_r(start_r),
.installed_book_valid(installed_book_valid),
.job(job),
.gen(gen),
.token(token),
.pos(pos),
.retained(retained),
.arena_visible(arena_visible),
.sink_visible(sink_visible),
.fault(fault),
.bound_arena_base(bound_arena_base),
.bound_arena_limit(bound_arena_limit),
.formatter_lease_valid(formatter_lease_valid),
.formatter_lease_frame(formatter_lease_frame),
.req_v(req_v),
.req_r(req_r),
.req_kind(req_kind),
.req_addr(req_addr),
.req_tag(req_tag),
.req_rank(req_rank),
.req_word(req_word),
.req_data(req_data),
.req_job(req_job),
.req_gen(req_gen),
.req_token(req_token),
.req_pos(req_pos),
.rsp_v(rsp_v),
.rsp_r(rsp_r),
.rsp_data(rsp_data),
.rsp_addr(rsp_addr),
.rsp_tag(rsp_tag),
.rsp_kind(rsp_kind),
.rsp_checked(rsp_checked),
.held_job(held_job),
.held_gen(held_gen),
.held_token(held_token),
.held_pos(held_pos),
.m_req_v(m_req_v),
.m_req_rdy(m_req_rdy),
.m_req_we(m_req_we),
.m_req_addr(m_req_addr),
.m_req_wdata(m_req_wdata),
.m_req_wstrb(m_req_wstrb),
.m_req_tag(m_req_tag),
.m_rsp_v(m_rsp_v),
.m_rsp_rdy(m_rsp_rdy),
.m_rsp_we(m_rsp_we),
.m_rsp_data(m_rsp_data),
.m_rsp_tag(m_rsp_tag),
.release_v(release_v),
.release_r(release_r),
.release_job(release_job),
.release_gen(release_gen),
.release_token(release_token),
.release_pos(release_pos),
.result_published(result_published),
.source_reverse_done(source_reverse_done),
.native_clients_drained(native_clients_drained),
.cdc_drained(cdc_drained),
.provider_fault(provider_fault),
.observe_req(observe_req),
.observe_rsp(observe_rsp),
.observe_req_we(observe_req_we),
.observe_rsp_we(observe_rsp_we),
.observe_req_tag(observe_req_tag),
.observe_rsp_tag(observe_rsp_tag),
.return_offer(return_offer),
.response_authorized(response_authorized),
.native_job(native_job),
.native_gen(native_gen),
.native_token(native_token),
.native_pos(native_pos),
.native_credit_empty(native_credit_empty),
.shared_idle(shared_idle),
.peer_lease_v(peer_lease_v),
.peer_quiet(peer_quiet),
.peer_release_v(peer_release_v),
.peer_lease_job(peer_lease_job),
.peer_release_job(peer_release_job),
.peer_lease_gen(peer_lease_gen),
.peer_release_gen(peer_release_gen),
.peer_lease_token(peer_lease_token),
.peer_release_token(peer_release_token),
.peer_lease_pos(peer_lease_pos),
.peer_release_pos(peer_release_pos),
.peer_lease_granted(peer_lease_granted),
.peer_release_r(peer_release_r),
.p_req_v(p_req_v),
.p_req_we(p_req_we),
.p_req_rdy(p_req_rdy),
.p_req_addr(p_req_addr),
.p_req_wstrb(p_req_wstrb),
.p_req_wdata(p_req_wdata),
.p_req_tag(p_req_tag),
.p_rsp_v(p_rsp_v),
.p_rsp_we(p_rsp_we),
.p_rsp_rdy(p_rsp_rdy),
.p_rsp_tag(p_rsp_tag),
.p_rsp_data(p_rsp_data));
always #5 clk=~clk;
integer cycles=0,writes=0,reads=0,acks=0,receipt_count=0;
reg [255:0] memory[0:32767];reg pending=0;reg corrupt=0;
reg [31:0] held_address;reg [15:0] held_tag;reg held_we;
reg [255:0] held_data;integer delay_left=0;
// Actual shared arbiter request/response path. No grant/ready authority ties.
always @(negedge clk)begin
 cycles=cycles+1;
 m_req_rdy=!pending&&(cycles%3!=0);
 if(pending&&delay_left>0)delay_left=delay_left-1;
 m_rsp_v=pending&&delay_left==0;
 m_rsp_tag=held_tag;m_rsp_we=held_we;
 m_rsp_data=held_data^(corrupt&&!held_we?256'd1:256'd0);
end
always @(posedge clk)begin
 if(m_req_v&&m_req_rdy)begin
  if(pending)$fatal(1,"multiple physical requests");
  pending<=1;delay_left<=2;held_address<=m_req_addr;held_tag<=m_req_tag;held_we<=m_req_we;
  if(m_req_we)begin
   if(m_req_wstrb!=32'hffffffff)$fatal(1,"partial source write");
   memory[m_req_addr/32]<=m_req_wdata;held_data<=0;writes<=writes+1;
  end else begin held_data<=memory[m_req_addr/32];reads<=reads+1;end
 end
 if(m_rsp_v&&m_rsp_rdy)pending<=0;
 if(preinstall_source_ACK_v&&preinstall_source_ACK_r)begin
  if(preinstall_source_ACK_frame!=preinstall_begin_frame)$fatal(1,"wrong ACK frame");
  acks<=acks+1;
 end
 if(reservation_v&&reservation_r)receipt_count<=receipt_count+1;
end
function automatic [63:0] dw(input integer i);
 case(i)
  0:dw=0;1:dw=64'h00080800_00080000;
  2:dw=64'h00070000_00010000;3:dw=64'h00070800_00070000;
  4:dw=64'h100000;5:dw=64'd96|(64'd512<<16)|(64'd32<<32);
  default:dw=0;
 endcase
endfunction
function automatic [511:0] pattern(input integer p,r,w);
 reg [511:0] x;
 begin for(integer lane=0;lane<16;lane=lane+1)x[lane*32+:32]=32'h35a00000^(32'(p)<<24)^(32'(r)<<12)^(32'(w)<<5)^32'(lane);pattern=x;end
endfunction
task automatic edge_wait;
 begin @(posedge clk);#1;end
endtask
task automatic reset_all;
 begin
  @(negedge clk);por_n=0;begin_v_dummy();
  repeat(3)edge_wait();@(negedge clk);por_n=1;repeat(3)edge_wait();
 end
endtask
task automatic begin_v_dummy;
 begin preinstall_begin_v=0;preinstall_record_v=0;preinstall_source_v=0;desc_v=0;start_v=0;warm_req=0;end
endtask
task automatic load_desc(input integer n);
 begin for(integer j=0;j<n;j=j+1)begin
  @(negedge clk);desc_v=1;desc_index=3'(j);desc_data=dw(j);
  #1;if(!desc_r)$fatal(1,"descriptor refused");edge_wait();
  @(negedge clk);desc_v=0;
 end end
endtask
task automatic begin_install;
 begin
  @(negedge clk);preinstall_begin_v=1;#1;
  if(!preinstall_begin_r)$fatal(1,"begin refused full descriptor");edge_wait();
  @(negedge clk);preinstall_begin_v=0;
 end
endtask
task automatic records;
 begin
  for(integer p=1;p<=2;p=p+1)for(integer r=0;r<96;r=r+1)begin
   @(negedge clk);preinstall_record_v=1;preinstall_record_kind=2'(p);preinstall_record_rank=7'(r);
   preinstall_record_base=(p==1?preinstall_score_base:preinstall_id_base)+32'(r)*2048;
   preinstall_record_end=preinstall_record_base+2048;
   #1;if(!preinstall_record_r)$fatal(1,"rank record refused");edge_wait();
   @(negedge clk);preinstall_record_v=0;
  end
  repeat(6)edge_wait();
 end
endtask
task automatic send_source(input integer p,r,w);
 integer spin;
 begin
  @(negedge clk);preinstall_source_v=1;preinstall_source_plane=1'(p);
  preinstall_source_rank=7'(r);preinstall_source_word=5'(w);preinstall_source_data=pattern(p,r,w);
  #1;spin=0;
  while(!preinstall_source_r)begin edge_wait();@(negedge clk);#1;spin=spin+1;if(spin>40)$fatal(1,"source admission stalled");end
  edge_wait();@(negedge clk);preinstall_source_v=0;spin=0;
  while(!preinstall_source_ACK_v&&!preinstall_fault)begin edge_wait();spin=spin+1;if(spin>128)$fatal(1,"source transport failed to progress");end
  if(!corrupt)begin
   if(preinstall_fault)$fatal(1,"unexpected install fault");
   if(preinstall_source_ACK_rank!=r||preinstall_source_ACK_word!=w||preinstall_source_ACK_plane!=p)$fatal(1,"ACK tuple");
   @(negedge clk);preinstall_source_ACK_r=1;edge_wait();@(negedge clk);preinstall_source_ACK_r=0;
  end
 end
endtask
initial begin
 clk=0;
por_n=0;
warm_req=0;
preinstall_begin_v=0;
preinstall_begin_frame=0;
preinstall_score_base=0;
preinstall_id_base=0;
preinstall_capacity=0;
preinstall_occupied_records=0;
preinstall_layer=0;
preinstall_candidate_source_layer=0;
preinstall_candidate_masked=0;
preinstall_record_v=0;
preinstall_record_kind=0;
preinstall_record_rank=0;
preinstall_record_base=0;
preinstall_record_end=0;
preinstall_record_frame=0;
preinstall_other_writer_v=0;
preinstall_other_writer_base=0;
preinstall_other_writer_end=0;
preinstall_source_v=0;
preinstall_source_frame=0;
preinstall_source_rank=0;
preinstall_source_plane=0;
preinstall_source_word=0;
preinstall_source_data=0;
preinstall_source_ACK_r=0;
reservation_r=0;
consumer_reverse_v=0;
consumer_reverse_frame=0;
consumer_sink_ACK_drained=0;
source_reverse_r=0;
desc_v=0;
desc_index=0;
desc_data=0;
start_v=0;
installed_book_valid=0;
job=0;
gen=0;
token=0;
pos=0;
req_v=0;
req_kind=0;
req_addr=0;
req_tag=0;
req_rank=0;
req_word=0;
req_data=0;
req_job=0;
req_gen=0;
req_token=0;
req_pos=0;
rsp_r=0;
m_req_rdy=0;
m_rsp_v=0;
m_rsp_we=0;
m_rsp_data=0;
m_rsp_tag=0;
release_v=0;
release_job=0;
release_gen=0;
release_token=0;
release_pos=0;
result_published=0;
source_reverse_done=0;
native_clients_drained=0;
cdc_drained=0;
provider_fault=0;
observe_req=0;
observe_rsp=0;
observe_req_we=0;
observe_rsp_we=0;
observe_req_tag=0;
observe_rsp_tag=0;
return_offer=0;
native_job=0;
native_gen=0;
native_token=0;
native_pos=0;
peer_lease_v=0;
peer_quiet=0;
peer_release_v=0;
peer_lease_job=0;
peer_release_job=0;
peer_lease_gen=0;
peer_release_gen=0;
peer_lease_token=0;
peer_release_token=0;
peer_lease_pos=0;
peer_release_pos=0;
p_req_v=0;
p_req_we=0;
p_req_addr=0;
p_req_wstrb=0;
p_req_wdata=0;
p_req_tag=0;
p_rsp_rdy=0;
 m_req_rdy=0;m_rsp_v=0;
 native_clients_drained=1;cdc_drained=1;peer_quiet=3;
 job=32'h9234abcd;gen=4'ha;token=17'h10001;pos=20'hfffff;
 preinstall_begin_frame={pos,token,gen,job};preinstall_record_frame=preinstall_begin_frame;preinstall_source_frame=preinstall_begin_frame;
 // Fixture-only disjoint spans. Actual parent requires emitted installation.
 preinstall_score_base=32'h81000;preinstall_id_base=32'hb1000;
 preinstall_capacity=33'h100000;preinstall_layer=20;preinstall_candidate_source_layer=20;
 reset_all();load_desc(7);
 @(negedge clk);preinstall_begin_v=1;#1;
 if(preinstall_begin_r||reservation_v||dut.grants[0])$fatal(1,"partial descriptor permitted book/lease");
 edge_wait();@(negedge clk);preinstall_begin_v=0;
 if(!preinstall_fault)$fatal(1,"partial descriptor did not quarantine");
 $display("NEGATIVE partial descriptor refused");
 reset_all();load_desc(8);
 @(negedge clk);preinstall_begin_frame=preinstall_begin_frame^(73'd1<<36);preinstall_begin_v=1;#1;
 if(preinstall_begin_r)$fatal(1,"foreign TOKEN17 accepted");edge_wait();
 @(negedge clk);preinstall_begin_v=0;preinstall_begin_frame={pos,token,gen,job};
 if(!preinstall_fault)$fatal(1,"foreign begin did not quarantine");
 $display("NEGATIVE foreign full73 refused");
 reset_all();load_desc(8);begin_install();records();
 corrupt=1;send_source(0,0,0);
 if(!preinstall_fault||reservation_v||acks!=0)$fatal(1,"corrupt readback published");
 $display("NEGATIVE readback mismatch retained/no book");
 corrupt=0;pending=0;reset_all();load_desc(8);begin_install();records();
 // Real codec DUE, not a fault input: retain and suppress publication.
 @(negedge clk);dut.u_preinstall.on.control.code[0]=dut.u_preinstall.on.control.code[0]^72'd3;
 edge_wait();if(!preinstall_due||!preinstall_retained||reservation_v)$fatal(1,"DUE not quarantined");
 $display("NEGATIVE protected DUE quarantined");
 reset_all();load_desc(8);begin_install();records();
 writes=0;reads=0;acks=0;
 // Backpressure ACK, warm drains accepted IO but forbids next source capture.
 @(negedge clk);preinstall_source_v=1;preinstall_source_rank=0;preinstall_source_word=0;preinstall_source_plane=0;preinstall_source_data=pattern(0,0,0);
 #1;if(!preinstall_source_r)$fatal(1,"initial source not ready");edge_wait();
 @(negedge clk);preinstall_source_v=0;warm_req=1;
 while(!preinstall_source_ACK_v)begin edge_wait();if(preinstall_fault)$fatal(1,"warm dropped accepted source");end
 repeat(3)edge_wait();if(acks!=0||reservation_v||!preinstall_retained||preinstall_warm_ack)$fatal(1,"warm/ACK debt lost");
 @(negedge clk);preinstall_source_ACK_r=1;edge_wait();
 @(negedge clk);preinstall_source_ACK_r=0;preinstall_source_v=1;preinstall_source_rank=1;#1;
 if(preinstall_source_r)$fatal(1,"warm admitted new source");
 preinstall_source_v=0;warm_req=0;
 for(integer p=0;p<2;p=p+1)for(integer w=0;w<32;w=w+1)for(integer r=0;r<96;r=r+1)
  if(!(p==0&&w==0&&r==0))send_source(p,r,w);
 repeat(3)edge_wait();
 if(!reservation_v||!reservation_checked||!reservation_exclusive||reservation_frame!=preinstall_begin_frame||!dut.grants[0])$fatal(1,"positive real book absent");
 if(writes!=12288||reads!=12288||acks!=6144)$fatal(1,"not full checked source installation");
 repeat(3)edge_wait();if(!reservation_v)$fatal(1,"receipt not held");
 @(negedge clk);reservation_r=1;edge_wait();@(negedge clk);reservation_r=0;
 if(receipt_count!=1)$fatal(1,"receipt acceptance count");
 installed_book_valid=1;start_v=1;#1;if(!start_r)$fatal(1,"same-lease gather handoff refused");
 edge_wait();@(negedge clk);start_v=0;repeat(20)edge_wait();
 if(!retained||!formatter_lease_valid||formatter_lease_frame!=preinstall_begin_frame||!dut.grants[0])$fatal(1,"original gather lost installation lease");
 $display("PASS receipt control: ACK6144 writes12288 reads12288 full73 same-index-lease handoff; numerical=false parent=false physical=false");
 $finish;
end
endmodule
