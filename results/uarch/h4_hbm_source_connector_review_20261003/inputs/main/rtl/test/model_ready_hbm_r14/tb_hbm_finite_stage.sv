`timescale 1ps/1fs
module tb_hbm_finite_stage;
 import ot_hbm_r14_pkg::*;
 reg CORE=0,FAST=0,SER=0,rst_n=0;
 always #500 CORE=~CORE;
 always #(2500.0/6.0) FAST=~FAST;
 always #(10000.0/18.0) SER=~SER;
 integer fd,CASE_ID,MUTANT,limit_cycles;reg [63:0] wallcycles;
 initial begin
   CASE_ID=1;MUTANT=0;limit_cycles=500000;
   void'($value$plusargs("CASE=%d",CASE_ID));void'($value$plusargs("MUTANT=%d",MUTANT));
   void'($value$plusargs("MAX_CYCLES=%d",limit_cycles));fd=$fopen("journal.tsv","w");
   $fwrite(fd,"event\tobserve_ps\tstack\tcycle\top\tpc\tbank\trow\tsector\ttag\tbeat\tproducer\ttransport\tcaller\tIRSslot\tIRSserial\taux\n");
 end
 initial begin #10000;@(negedge CORE);rst_n=1;end
 always @(posedge CORE)if(!rst_n)wallcycles<=0;else begin
   wallcycles<=wallcycles+1;if(wallcycles>=64'(limit_cycles))$fatal(1,"FAIL_CYCLE_LIMIT");
 end
 // Emitted ROM functions contain address/mask metadata only, not payload.
 `include "qwen_stage_metadata_r14.svh"
 reg start_v;wire start_r;identity_t start_id;reg [255:0] start_data;reg [31:0] mask;reg reader_mode;
 wire reserve_v,reserve_r,req_v,req_r,result_v,result_r,store_v,store_r;
 reg [33:0] burst_base;reg burst_start,burst_mode;wire burst_req_v,burst_req_r,burst_result_r,burst_done,burst_fault;wire [31:0] burst_seen;request_t burst_req;
 identity_t reserve_id;request_t client_req;owned_t result,store;
 wire reader_result_v,reader_result_r,reader_retire_v,reader_reverse_v;
 identity_t reader_retire_id,reader_reverse_id;wire reverse_v,reverse_r;
 owned_t reverse_packet;wire RF_commit,RMW_retire,client_done,client_fault;wire [1:0] selected_stack;wire [31:0] checksum;
 reg consumer_pause;wire result_we,result_credit;
 ot_hbm_r14_finite_client #(.ENABLE(1)) client(.clk(SER),.rst_n(rst_n),.start_v(start_v),.start_r(start_r),
   .start_id(start_id),.start_data(start_data),.byte_mask(mask),.is_reader(reader_mode),
   .reserve_v(reserve_v),.reserve_r(reserve_r),.reserve_id(reserve_id),
   .req_v(req_v),.req_r(req_r),.req(client_req),.result_v(result_v&&!consumer_pause),.result_r(result_r),
   .result_we(result_we),.result_credit(result_credit),.result(result),
   .store_v(store_v),.store_r(store_r),.store(store),.reader_result_v(reader_result_v),.reader_result_r(reader_result_r),
   .reader_retire_v(reader_retire_v),.reader_retire_id(reader_retire_id),
   .reader_reverse_v(reader_reverse_v),.reader_reverse_id(reader_reverse_id),
   .retire_reverse_v(reverse_v),.retire_reverse_r(reverse_r),.retire_reverse(reverse_packet),
   .RF_commit(RF_commit),.RMW_retire(RMW_retire),.done(client_done),.fault(client_fault),.selected_stack(selected_stack),.result_checksum(checksum));
 wire [3:0] ingress_v,ingress_r,reply_v,reply_r,credit_v,credit_r;
 request_t link_request;wire link_req_v;wire [1:0] link_stack;
 assign link_request=burst_mode?burst_req:client_req;assign link_req_v=burst_mode?burst_req_v:req_v;assign link_stack=burst_mode?2'b0:selected_stack;
 assign burst_req_r=SERreq_r[0];
 wire [454:0] ingress[0:3];wire [466:0] reply[0:3];wire [403:0] credit[0:3];
 wire [3:0] SERreply_v,SERreply_r,SERcredit_r,SERreq_r;
 wire [466:0] SERreply[0:3];
 wire [3:0] provider_fault,backing_fault;wire [63:0] cycles[0:3];wire [2:0] WRres[0:3];wire [15:0] taglive[0:3];
 wire [3:0] commands_v,commands_r;command_t commands[0:3],physical_commands[0:3];
 wire [31:0] rsp_v[0:3],rsp_r[0:3],commit_v[0:3],commit_r[0:3];
 wire [511:0] rsp_tag[0:3];wire [159:0] rsp_beat[0:3];wire [8191:0] rsp_data[0:3];wire [63:0] commit_slot[0:3];
 owned_t core_owned[0:3],tested_owned[0:3];wire [3:0] core_we,core_grant;request_t core_req[0:3];identity_t core_credit_id[0:3];
 owned_t SERowned[0:3];wire [3:0] SERwe,SERgrant;
 wire retire_v,retire_r,retire_cancelled,grant_r,store_fault,store_drained;
 owned_t retire_packet;wire [271:0] bitmap;wire [8:0] writer_count;
 reg store_clear,writer_cancel;identity_t cancel_id;
 wire [403:0] outgoing_credit;
 wire reverse_send_v=retire_v||reverse_v;
 owned_t reverse_selected;wire reverse_we=retire_v;
 assign reverse_selected=retire_v?retire_packet:reverse_packet;
 assign outgoing_credit={193'b0,reverse_we,reverse_selected.id,reverse_selected.physical_tag,reverse_selected.beat,1'b0};
 assign retire_r=SERcredit_r[reverse_selected.id.stack];assign reverse_r=!retire_v&&SERcredit_r[reverse_selected.id.stack];
 assign req_r=SERreq_r[selected_stack];
 assign result_v=SERreply_v[selected_stack]&&!burst_mode;assign result=SERowned[selected_stack];
 assign result_we=SERwe[selected_stack];assign result_credit=SERgrant[selected_stack];
 assign reserve_r=reader_mode?lease_reader_r:store_reserve_r;
 wire store_reserve_r;
 ot_hbm_sector_completion_store #(.ENABLE(1)) completion_store(.clk(SER),.rst_n(rst_n),.clear(store_clear),
   .reserve_v(reserve_v&&!reader_mode),.reserve_r(store_reserve_r),.reserve_id(reserve_id),
   .visible_v(store_v),.visible_r(store_r),.visible(store),.cancel_v(writer_cancel),.cancel_id(cancel_id),
   .retire_v(retire_v),.retire_r(retire_r),.retire(retire_packet),.retire_cancelled(retire_cancelled),
   .grant_v(result_v&&result_credit&&!reader_mode&&!consumer_pause),.grant_r(grant_r),.grant(result),
   .completed(bitmap),.count(writer_count),.drained(store_drained),.fault(store_fault));
 genvar s;
 generate for(s=0;s<4;s=s+1)begin: stacks
   always @*begin physical_commands[s]=commands[s];physical_commands[s].sector={3'b0,commands[s].sector[30:0]};end
   assign core_req[s]=request_t'(ingress[s]);
   always @*begin tested_owned[s]=core_owned[s];if(MUTANT==4)tested_owned[s].id.producer=64'd9;end
   assign reply[s]={core_grant[s],core_we[s],tested_owned[s]};
   assign core_credit_id[s]=identity_t'(credit[s][209:18]);
   assign SERowned[s]=owned_t'(SERreply[s][464:0]);
   assign SERwe[s]=SERreply[s][465];assign SERgrant[s]=SERreply[s][466];
   assign SERreply_r[s]=burst_mode?(s==0&&burst_result_r):((selected_stack==2'(s))&&result_r&&!consumer_pause);
   ot_hbm_r14_clock_bridge #(.WIDTH(455)) request_link(.src_clk(SER),.fast_clk(FAST),.dst_clk(CORE),.rst_n(rst_n),
     .iv(link_req_v&&link_stack==2'(s)),.ir(SERreq_r[s]),.id(link_request),.ov(ingress_v[s]),.ore(ingress_r[s]),.od(ingress[s]));
   ot_hbm_r14_clock_bridge #(.WIDTH(467)) response_link(.src_clk(CORE),.fast_clk(FAST),.dst_clk(SER),.rst_n(rst_n),
     .iv(reply_v[s]),.ir(reply_r[s]),.id(reply[s]),.ov(SERreply_v[s]),.ore(SERreply_r[s]),.od(SERreply[s]));
   ot_hbm_r14_clock_bridge #(.WIDTH(404)) reverse_link(.src_clk(SER),.fast_clk(FAST),.dst_clk(CORE),.rst_n(rst_n),
     .iv(reverse_send_v&&reverse_selected.id.stack==2'(s)),.ir(SERcredit_r[s]),.id(outgoing_credit),.ov(credit_v[s]),.ore(credit_r[s]),.od(credit[s]));
   ot_hbm_causal_command_provider #(.ENABLE(1),.STACK(s)) provider(.clk(CORE),.rst_n(rst_n),.req_v(ingress_v[s]),.req_r(ingress_r[s]),.req(core_req[s]),
     .cmd_v(commands_v[s]),.cmd_r(commands_r[s]),.cmd(commands[s]),.rsp_v(rsp_v[s]),.rsp_r(rsp_r[s]),
     .rsp_tag(rsp_tag[s]),.rsp_beat(rsp_beat[s]),.rsp_data(rsp_data[s]),.commit_v(commit_v[s]),.commit_r(commit_r[s]),.commit_slot(commit_slot[s]),
     .owned_v(reply_v[s]),.owned_r(reply_r[s]),.owned_we(core_we[s]),.owned_credit(core_grant[s]),.owned(core_owned[s]),
     .credit_v(credit_v[s]),.credit_we(credit[s][210]),.credit_r(credit_r[s]),.credit_id(core_credit_id[s]),.credit_tag(credit[s][17:6]),.credit_beat(credit[s][5:1]),
     .fault(provider_fault[s]),.cycle(cycles[s]),.WRresidents(WRres[s]),.live_tags(taglive[s]));
   ot_hbm_r14_backing_fixture #(.STACK(s)) hbm(.clk(CORE),.rst_n(rst_n),.cyc(cycles[s]),
     .cv(commands_v[s]),.cr(commands_r[s]),.cmd(physical_commands[s]),.rv(rsp_v[s]),.rr(rsp_r[s]),.rtag(rsp_tag[s]),.rbeat(rsp_beat[s]),.rdata(rsp_data[s]),
     .wv(commit_v[s]),.wr(commit_r[s]),.wslot(commit_slot[s]),.mutant(4'(MUTANT)),.fault(backing_fault[s]));
   always @(posedge CORE)if(rst_n)begin
     if(ingress_v[s]&&ingress_r[s])$fwrite(fd,"ACCEPT\t%0.6f\t%0d\t%0d\t%0d\t0\t0\t0\t%0d\t%0d\t0\t%0d\t%0d\t%0d\t%0d\t%0d\t%0d\n",$realtime,s,cycles[s],core_req[s].we,core_req[s].id.sector,stacks[s].provider.on.next_tag,core_req[s].id.producer,core_req[s].id.transport,core_req[s].id.caller,core_req[s].id.irs_slot,core_req[s].id.irs_serial,core_req[s].len);
     if(commands_v[s]&&commands_r[s])$fwrite(fd,"CMD\t%0.6f\t%0d\t%0d\t%0d\t%0d\t%0d\t%0d\t%0d\t%0d\t%0d\t0\t0\t0\t0\t0\t0\n",$realtime,s,cycles[s],commands[s].op,commands[s].pc,commands[s].bank,commands[s].row,commands[s].sector,commands[s].tag,commands[s].beat);
     for(integer p=0;p<32;p=p+1)if(hbm.writing[p]&&cycles[s]>=hbm.wr_due[p]&&!hbm.wv[p])$fwrite(fd,"BACKING_WRITE\t%0.6f\t%0d\t%0d\t3\t%0d\t0\t0\t%0d\t%0d\t%0d\t0\t0\t0\t0\t0\t0\n",$realtime,s,cycles[s],p,hbm.write_cmd[p].sector,hbm.write_cmd[p].tag,hbm.write_cmd[p].beat);
     if(reply_v[s]&&reply_r[s])$fwrite(fd,"OWNED\t%0.6f\t%0d\t%0d\t%0d\t0\t0\t0\t%0d\t%0d\t%0d\t%0d\t%0d\t%0d\t%0d\t%0d\t0\n",$realtime,s,cycles[s],{core_grant[s],core_we[s]},core_owned[s].id.sector,core_owned[s].physical_tag,core_owned[s].beat,core_owned[s].id.producer,core_owned[s].id.transport,core_owned[s].id.caller,core_owned[s].id.irs_slot,core_owned[s].id.irs_serial);
     if(credit_v[s]&&credit_r[s])$fwrite(fd,"REVERSE\t%0.6f\t%0d\t%0d\t%0d\t0\t0\t0\t%0d\t%0d\t%0d\t%0d\t%0d\t%0d\t%0d\t%0d\t0\n",$realtime,s,cycles[s],credit[s][210],core_credit_id[s].sector,credit[s][17:6],credit[s][5:1],core_credit_id[s].producer,core_credit_id[s].transport,core_credit_id[s].caller,core_credit_id[s].irs_slot,core_credit_id[s].irs_serial);
     if(provider_fault[s]||backing_fault[s])$fatal(1,"FAIL_PROVIDER stack=%0d",s);
   end
 end endgenerate
 // Real pinned genericIRS; no helper fabricates retirement callbacks.
 reg alloc_v,complete_v,complete_fault,bind_v;reg [4:0] alloc_slot,complete_slot;
 reg [31:0] alloc_serial,alloc_event;reg [2:0] bind_kind;
 wire alloc_r,irs_v,irs_protocol;wire [4:0] free_slot,retire_slot;
 wire [31:0] retire_serial,retire_event;wire retire_fault;
 ot_a3_issue_record_store IRS(.clk(SER),.rst_n(rst_n),.clear(1'b0),.alloc_queue(5'b0),.alloc_ready(alloc_r),.free_slot(free_slot),
   .alloc_valid(alloc_v),.alloc_slot(alloc_slot),.alloc_serial(alloc_serial),.alloc_pc(alloc_event),.alloc_event_id(alloc_event),.alloc_release(1'b0),
   .complete_valid(complete_v),.complete_slot(complete_slot),.complete_fault(complete_fault),.complete_trap_class(16'hca11),
   .retire_valid(irs_v),.retire_slot(retire_slot),.retire_serial(retire_serial),.retire_event_id(retire_event),.retire_fault(retire_fault),.irs_protocol_error(irs_protocol));
 reg lease_clear,publish_prior,acquire_v,lease_cancel,release_v,discard_v;
 wire acquire_r,lease_live,lease_reader_r,release_r,lease_fault;wire [9:0] reader_count;
 wire operator_ready,operator_complete,operator_commit;reg operator_v,operator_take;reg [2:0] operator_kind;
 wire [2:0] result_kind;wire [63:0] result_producer;wire [31:0] result_transport,RF_scalar;
 ot_hbm_r14_result_producer scalar(.clk(SER),.rst_n(rst_n),.iv(operator_v),.ir(operator_ready),.kind(operator_kind),
   .input_result(checksum),.producer(64'd7),.transport(32'd8),.commit(operator_commit),.complete_v(operator_complete),.complete_r(operator_take),
   .result_kind(result_kind),.result_producer(result_producer),.result_transport(result_transport),.RF_result(RF_scalar));
 ot_hbm_reader_lease #(.ENABLE(1)) lease(.clk(SER),.rst_n(rst_n),.clear(lease_clear),
   .writer_count(writer_count),.writer_drained(store_drained),.publish_prior(publish_prior),.producer(64'd7),.transport(32'd8),
   .irs_v(irs_v),.irs_fault(retire_fault),.irs_slot(retire_slot),.irs_serial(retire_serial),.irs_event(retire_event),
   .bind_v(bind_v),.bind_slot(alloc_slot),.bind_serial(alloc_serial),.bind_kind(bind_kind),
   .result_commit_v(operator_commit),.result_commit_kind(result_kind),.result_commit_producer(result_producer),.result_commit_transport(result_transport),
   .acquire_v(acquire_v),.acquire_r(acquire_r),.lease_live(lease_live),
   .reader_v(reserve_v&&reader_mode),.reader_r(lease_reader_r),.reader_id(reserve_id),
   .result_v(reader_result_v),.result_r(reader_result_r),.result(store),
   .retire_v(reader_retire_v),.retire_id(reader_retire_id),.reverse_v(reader_reverse_v),.reverse_id(reader_reverse_id),
   .cancel_v(lease_cancel),.discard_v(discard_v),.discard_kind(3'b0),.discard_slot(5'b0),.discard_serial(32'b0),.discard_producer(64'd7),.discard_transport(32'd8),
   .release_v(release_v),.release_r(release_r),.count(reader_count),.fault(lease_fault));
 function automatic [255:0] payload(input integer pos,i);
   reg [255:0] value;begin for(integer b=0;b<32;b=b+1)value[b*8+:8]=8'(pos*73+i+b*3);payload=value;end
 endfunction
 function automatic [255:0] expected_data(input integer stack,input [33:0] sector,input integer completed_position);
   reg [255:0] value,pv;reg [31:0] bm;begin
     for(integer b=0;b<32;b=b+1)value[b*8+:8]=8'((sector+34'(b)+34'(stack*17))&255);
     for(integer pp=0;pp<2;pp=pp+1)if(pp<=completed_position)
       for(integer j=0;j<272;j=j+1)if(writer_stack(pp,j)==2'(stack)&&writer_sector(pp,j)==sector)begin
         pv=payload(pp,j);bm=writer_mask(pp,j);for(integer b=0;b<32;b=b+1)if(bm[b])value[b*8+:8]=pv[b*8+:8];
       end
     expected_data=value;
   end
 endfunction
 function automatic [255:0] expected_burst(input [33:0] sector);
   reg [255:0] value;begin for(integer b=0;b<32;b=b+1)value[b*8+:8]=8'((sector+34'(b))&255);
     for(integer j=0;j<4;j=j+1)if(sector==34'(j*4096))value=payload(1,j);
     expected_burst=value;
   end
 endfunction
 task automatic issue_opcode(input integer kind,serial,output reg [4:0] slot);
   begin @(negedge SER);while(!alloc_r)@(negedge SER);slot=free_slot;
     alloc_slot=slot;alloc_serial=32'(serial);alloc_event=32'(10+kind);bind_kind=3'(kind);alloc_v=1;bind_v=1;
     @(negedge SER);alloc_v=0;bind_v=0;end
 endtask
 task automatic finish_opcode(input reg [4:0] slot);
   begin @(negedge SER);complete_slot=slot;complete_v=1;
     @(negedge SER);complete_v=0;while(!irs_v)@(negedge SER);@(negedge SER);end
 endtask
 task automatic transaction(input identity_t id,input [255:0] data,input [31:0] bm,input bit read_only);
   begin @(negedge SER);while(!start_r)@(negedge SER);
     start_id=id;start_data=data;mask=bm;reader_mode=read_only;start_v=1;
     @(negedge SER);start_v=0;while(!client_done)@(negedge SER);end
 endtask
 ot_hbm_r14_burst_client burst(.clk(SER),.rst_n(rst_n),.start(burst_start),.base(burst_base),.req_v(burst_req_v),.req_r(burst_req_r),.req(burst_req),
   .result_v(SERreply_v[0]&&burst_mode),.result_r(burst_result_r),.result(SERowned[0]),.result_we(SERwe[0]),.result_credit(SERgrant[0]),.done(burst_done),.fault(burst_fault),.seen(burst_seen));
 identity_t id;reg [4:0] opcode_slot;integer phase,i;
 initial begin
   burst_start=0;burst_mode=0;burst_base=0;start_v=0;start_id='0;start_data=0;mask=0;reader_mode=0;consumer_pause=0;
   store_clear=0;writer_cancel=0;cancel_id='0;alloc_v=0;complete_v=0;complete_fault=0;bind_v=0;
   alloc_slot=0;complete_slot=0;alloc_serial=0;alloc_event=0;bind_kind=0;lease_clear=0;publish_prior=0;
   acquire_v=0;lease_cancel=0;release_v=0;discard_v=0;operator_v=0;operator_take=0;operator_kind=0;
   wait(rst_n);repeat(12)@(negedge SER);
   if(CASE_ID==0)begin
     issue_opcode(0,1,opcode_slot);
     for(i=0;i<4;i=i+1)begin id='{die:1'b0,stack:2'b0,sector:34'(i*4096),producer:64'd7,transport:32'd8,caller:16'(i),client:6'd1,irs_slot:opcode_slot,irs_serial:32'd1};
       fork
         transaction(id,payload(1,i),32'hffffffff,0);
         begin wait(SERreply_v[0]);@(negedge SER);consumer_pause=1;repeat(5)@(negedge SER);consumer_pause=0;end
       join
     end
     for(i=0;i<2;i=i+1)begin @(negedge SER);burst_base=(i==0)?34'b0:BURST_BASE;burst_mode=1;burst_start=1;@(negedge SER);burst_start=0;while(!burst_done)@(negedge SER);burst_mode=0;end
     $display("PASS_FINITE_CHANNEL prerequisite_only writer_count=%0d",writer_count);
   end else if(CASE_ID==4)begin
     issue_opcode(0,1,opcode_slot);id='{die:1'b0,stack:2'b0,sector:34'd4294967296,producer:64'd7,transport:32'd8,caller:16'd0,client:6'd1,irs_slot:opcode_slot,irs_serial:32'd1};
     transaction(id,payload(1,0),32'hffffffff,0);$fatal(1,"FAIL_INVALID_ADDRESS_ACCEPTED");
   end else if(CASE_ID==2)begin
     issue_opcode(0,1,opcode_slot);id='{die:1'b0,stack:2'b0,sector:34'd4096,producer:64'd7,transport:32'd8,caller:16'd0,client:6'd1,irs_slot:opcode_slot,irs_serial:32'd1};
     fork
       transaction(id,payload(1,0),32'hffffffff,0);
       begin wait(commands_v[0]&&commands_r[0]&&commands[0].op==WR);@(posedge CORE);@(negedge SER);cancel_id=id;writer_cancel=1;@(negedge SER);writer_cancel=0;end
     join
     if(writer_count!=0||!store_drained||WRres[0]!=0)$fatal(1,"FAIL_CANCEL_DRAIN");
     $display("PASS_WR_CANCEL real_backing_and_retire_reverse_grant normal_quorum=0");
   end else begin
     // Position0 is REALLY produced/published before position1. No initialized
     // priorquorum or fake leaseACK. Both use exact metadata-ROM addresses.
     for(phase=0;phase<2;phase=phase+1)begin
       issue_opcode(0,phase*2+1,opcode_slot);
       for(i=0;i<272;i=i+1)begin
         id='{die:1'b0,stack:writer_stack(phase,i),sector:writer_sector(phase,i),producer:64'd7,transport:32'd8,
           caller:16'(i),client:6'(phase),irs_slot:opcode_slot,irs_serial:32'(phase*2+1)};
         transaction(id,payload(phase,i),writer_mask(phase,i),0);
       end
       if(writer_count!=272||!store_drained)$fatal(1,"FAIL_WRITER_QUORUM");
       finish_opcode(opcode_slot);issue_opcode(1,phase*2+2,opcode_slot);finish_opcode(opcode_slot);
       if(phase==0)begin @(negedge SER);publish_prior=1;@(negedge SER);publish_prior=0;store_clear=1;@(negedge SER);store_clear=0;end
     end
     @(negedge SER);if(!acquire_r)$fatal(1,"FAIL_ACQUIRE_PREREQUISITE");acquire_v=1;@(negedge SER);acquire_v=0;
     issue_opcode(2,5,opcode_slot);
     for(i=0;i<288;i=i+1)begin
       id='{die:1'b0,stack:reader_stack(i),sector:reader_sector(i),producer:64'd7,transport:32'd8,
         caller:16'(i),client:6'd2,irs_slot:opcode_slot,irs_serial:32'd5};
       if(CASE_ID==3&&i==0)begin
         fork
           transaction(id,256'b0,32'hffffffff,1);
           begin wait(client.on.phase==3);@(negedge SER);lease_cancel=1;@(negedge SER);lease_cancel=0;end
         join
         break;
       end else transaction(id,256'b0,32'hffffffff,1);
     end
     if(CASE_ID==3)begin if(reader_count!=0)$fatal(1,"FAIL_CANCEL_READER_QUORUM");complete_fault=1;finish_opcode(opcode_slot);complete_fault=0;end
     else begin if(reader_count!=288)$fatal(1,"FAIL_READER_QUORUM");finish_opcode(opcode_slot);end
     for(i=3;i<6&&CASE_ID!=3;i=i+1)begin
       issue_opcode(i,i+3,opcode_slot);@(negedge SER);operator_kind=3'(i);operator_v=1;
       @(negedge SER);operator_v=0;while(!operator_complete)@(negedge SER);
       operator_take=1;@(negedge SER);operator_take=0;finish_opcode(opcode_slot);
     end
     @(negedge SER);if(!release_r)$fatal(1,"FAIL_LEASE_RELEASE");release_v=1;@(negedge SER);release_v=0;
     $display("PASS_FINITE_STAGE prerequisite_only writers_position0=272 writers_position1=%0d readers=%0d arithmetic_credit=0",writer_count,reader_count);
   end
   repeat(20)@(negedge CORE);$fclose(fd);$finish;
 end
 reg stalled;reg [466:0] stalled_packet;
 always @(posedge SER)if(!rst_n)begin stalled<=0;stalled_packet<=0;end else begin
   if(stalled&&consumer_pause&&SERreply_v[0]&&SERreply[0]!=stalled_packet)$fatal(1,"FAIL_HELD_RETURN_MUTATED");
   stalled<=consumer_pause&&SERreply_v[0];stalled_packet<=SERreply[0];
 end
 always @(posedge SER)if(rst_n)begin
   if(operator_commit)$fwrite(fd,"OP_RF_COMMIT\t%0.6f\t0\t0\t%0d\t0\t0\t0\t0\t0\t0\t%0d\t%0d\t0\t0\t0\t0\n",$realtime,result_kind,result_producer,result_transport);
   if(RF_commit)$fwrite(fd,"RF_COMMIT\t%0.6f\t%0d\t0\t0\t0\t0\t0\t%0d\t0\t0\t%0d\t%0d\t%0d\t%0d\t%0d\t0\n",$realtime,selected_stack,start_id.sector,start_id.producer,start_id.transport,start_id.caller,start_id.irs_slot,start_id.irs_serial);
   if(RMW_retire)$fwrite(fd,"RMW_RETIRE\t%0.6f\t%0d\t0\t0\t0\t0\t0\t%0d\t0\t0\t%0d\t%0d\t%0d\t%0d\t%0d\t0\n",$realtime,selected_stack,start_id.sector,start_id.producer,start_id.transport,start_id.caller,start_id.irs_slot,start_id.irs_serial);
   if(store_v&&store_r)$fwrite(fd,"SECTOR_STORE_ACCEPT\t%0.6f\t%0d\t0\t0\t0\t0\t0\t%0d\t%0d\t%0d\t%0d\t%0d\t%0d\t%0d\t%0d\t0\n",$realtime,store.id.stack,store.id.sector,store.physical_tag,store.beat,store.id.producer,store.id.transport,store.id.caller,store.id.irs_slot,store.id.irs_serial);
   if(completion_store.on.phase==1)$fwrite(fd,"SECTOR_STORE_VISIBLE\t%0.6f\t%0d\t0\t0\t0\t0\t0\t%0d\t%0d\t%0d\t%0d\t%0d\t%0d\t%0d\t%0d\t0\n",$realtime,completion_store.on.packet.id.stack,completion_store.on.packet.id.sector,completion_store.on.packet.physical_tag,completion_store.on.packet.beat,completion_store.on.packet.id.producer,completion_store.on.packet.id.transport,completion_store.on.packet.id.caller,completion_store.on.packet.id.irs_slot,completion_store.on.packet.id.irs_serial);
   if(retire_v&&retire_r)$fwrite(fd,"SECTOR_RETIRE\t%0.6f\t%0d\t0\t0\t0\t0\t0\t%0d\t%0d\t%0d\t%0d\t%0d\t%0d\t%0d\t%0d\t%0d\n",$realtime,retire_packet.id.stack,retire_packet.id.sector,retire_packet.physical_tag,retire_packet.beat,retire_packet.id.producer,retire_packet.id.transport,retire_packet.id.caller,retire_packet.id.irs_slot,retire_packet.id.irs_serial,retire_cancelled);
   if(reader_result_v&&reader_result_r)$fwrite(fd,"READER_RESULT\t%0.6f\t%0d\t0\t0\t0\t0\t0\t%0d\t%0d\t%0d\t%0d\t%0d\t%0d\t%0d\t%0d\t0\n",$realtime,store.id.stack,store.id.sector,store.physical_tag,store.beat,store.id.producer,store.id.transport,store.id.caller,store.id.irs_slot,store.id.irs_serial);
   if(reader_retire_v)$fwrite(fd,"READER_RETIRE\t%0.6f\t%0d\t0\t0\t0\t0\t0\t%0d\t0\t0\t%0d\t%0d\t%0d\t%0d\t%0d\t0\n",$realtime,reader_retire_id.stack,reader_retire_id.sector,reader_retire_id.producer,reader_retire_id.transport,reader_retire_id.caller,reader_retire_id.irs_slot,reader_retire_id.irs_serial);
   if(reader_reverse_v)$fwrite(fd,"READER_GRANT\t%0.6f\t%0d\t0\t0\t0\t0\t0\t%0d\t0\t0\t%0d\t%0d\t%0d\t%0d\t%0d\t0\n",$realtime,reader_reverse_id.stack,reader_reverse_id.sector,reader_reverse_id.producer,reader_reverse_id.transport,reader_reverse_id.caller,reader_reverse_id.irs_slot,reader_reverse_id.irs_serial);
   if(irs_v)$fwrite(fd,"IRS_RETIRE\t%0.6f\t0\t0\t0\t0\t0\t0\t0\t0\t0\t7\t8\t0\t%0d\t%0d\t%0d\n",$realtime,retire_slot,retire_serial,retire_event);
   if(acquire_v&&acquire_r)$fwrite(fd,"LEASE_ACQUIRE\t%0.6f\t0\t0\t0\t0\t0\t0\t0\t0\t0\t7\t8\t0\t0\t0\t0\n",$realtime);
   if(release_v&&release_r)$fwrite(fd,"LEASE_RELEASE\t%0.6f\t0\t0\t0\t0\t0\t0\t0\t0\t0\t7\t8\t0\t0\t0\t0\n",$realtime);
   if(burst_mode&&SERreply_v[0]&&SERreply_r[0]&&SERowned[0].data!=expected_burst(SERowned[0].id.sector))$fatal(1,"FAIL_BURST_DATA_OR_AW_ALIAS");
   if(CASE_ID!=0&&result_v&&result_r&&!result_we&&!result_credit&&!consumer_pause&&result.data!=expected_data(integer'(result.id.stack),result.id.sector,reader_mode?1:phase-1))$fatal(1,"FAIL_RAW_RMW_DATA");
   if(client_fault||store_fault||lease_fault||irs_protocol||burst_fault)$fatal(1,"FAIL_ENDPOINT");
 end
endmodule
