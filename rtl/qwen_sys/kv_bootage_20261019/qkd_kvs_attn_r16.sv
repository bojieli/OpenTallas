`timescale 1ns/1ps
// KV-ATTN2 2026-10-19: qkd_kvs_attn_r16 = qkd_kvs_attn_r16 (same function, same edges, same pair bench) with every kept-copy
// family re-cut to <= 16 flops per copy (<= ~32 terminal pins incl. enable-mux pairs), run landing copies, a root running copy,
// an unconditional face calendar pipe, a guard whose accept enable is split over kept valid copies, and a producer whose tag
// capture needs no fault term (the tag is read only under descriptor_valid, which already requires !fault).
// The header of qkd_kvs_attn_r16 follows (module names there carry _rv; here _r16).
// KV-ATTN2 2026-10-19 (LEAD2-KV lane KV-ATTN2, tree K.STA.ATTN): STRUCTURALLY SAFE attention tile qkd_kvs_attn_rv.
// Distinct default-off module names; every earlier ba4/ba5/safe_pr source and closed view stays byte-identical.
// Behavioural ancestor = qkd_kvs_attn_ba5 (the safe-control/pr32/pr32b27 native lineage).  Changes (SAFE-DESIGN checklist):
//  (1) REGISTERED RX VALIDATION (the core TT -569 ps / upstream 816 ps cone: landed RX record -> 493-bit zero test + 31-bit
//      expectation compare + direction -> fault -> rx_valid -> request -> root accept enable of ~300 flops).
//      qkd_native_attention_record_r16 evaluates the whole RX check (record AND time) flop -> flop into b_rbad / b_tbad one
//      edge after the landing; the record fields move with it (b_pl).  Every RX observation (rx_valid, fields, RX fault
//      causes) is ONE edge later than ba5 = +1 edge K.rx_record, handed to the die schedule (lanes/KV-GEN9.md).
//  (2) REGISTERED ADMISSION: request_valid leaves the controller as NRV kept register copies computed on the landing edge
//      from the landed record (check + kind + the controller fault of that cycle); the root accept enable of each <=36-flop
//      slice is one copy AND ready.  Same edge as (1): no further edge.
//  (3) Everything downstream of the RX record (root start_qk / start_pv / ctx / ep / cal, the face window, RESULT / STATUS TX,
//      prg, arh) is exactly ba5 shifted by +1 edge; the calendar generator adds TX_SHIFT = 1 to tx_first / end (compiler law
//      kv_static_programme TX_FIRST = RX_CMD + 2 + SERVICE_END - 31 + TX_SHIFT).
//  (4) Fan-out <= ~32 per register in the critical cones (kept copies, physical/common_flow/ot_keep_regs.tcl):
//      issue (pin -> NIS landing copies, programme captures), load (NLD descriptor-valid copies, controller captures),
//      status_slot (NSS precomputed copies, the 512-bit TX data select), calendar S10 strobe v9 (NV9 copies);
//      the result face captures the 512-bit beat unconditionally (validity alone authorizes observation: no fin[0] enable on
//      512 flops, ba4 census fin[0] Q 1038 loads); calendar S1..S9 capture unconditionally (fixed-latency pipeline).
//  (5) First-contact pin registers: RX zero flags are no longer computed from raw pins (landed copy only); the fault root
//      lands every ufk pin in its own flop (OR after the flops: exact).
// Equivalence: tb_kvs_attn_rv_pair (A = qkd_kvs_attn_fl_ba5, B = qkd_kvs_attn_fl rv) -- B's ports equal A's one edge later on
// every edge (valid-masked data), legal and 10 fault modes; mutants MUT 1..6 must FAIL.
// MUT (bench only): 1 codec fields one edge early vs valid, 2 registered record check against the next edge's expectation (misaligned), 3 admission ignores the record
// check, 4 calendar TX_SHIFT 0, 5 status_slot copy one age early, 6 face captures the previous beat, 7 fault root ORs one pin.

module qkd_native_attention_record_r16 #(
    parameter integer KV_SIDE=1,
    parameter integer MUT=0
)(
    input wire ck,rst_n,
    input wire tx_event,tx_expected,
    input wire [3:0] tx_kind,tx_expected_kind,
    input wire [15:0] tx_epoch,tx_expected_epoch,
    input wire [5:0] tx_layer,tx_expected_layer,
    input wire [4:0] tx_beat,tx_expected_beat,
    input wire [511:0] tx_data,
    output reg tx_valid,output reg [547:0] tx_payload,
    input wire rx_event,rx_expected,
    input wire [547:0] rx_payload,
    input wire [3:0] rx_expected_kind,
    input wire [15:0] rx_expected_epoch,
    input wire [5:0] rx_expected_layer,
    input wire [4:0] rx_expected_beat,
    output reg rx_valid,
    output reg [3:0] rx_kind,
    output reg [15:0] rx_epoch,
    output reg [5:0] rx_layer,
    output reg [4:0] rx_beat,
    output reg [511:0] rx_data,
    output reg fault,output reg [3:0] fault_cause,
    // landing-edge view for the registered admission (controller): the landed record is a legal, expected CMD
    output wire a_cmd_ok
);
    localparam [3:0] CMD=1,Q=2,RESULT=3,STATUS=4;
    function legal(input [3:0] kind,input [5:0] layer,input [4:0] beat,input [511:0] data);
        begin
            legal=layer<36 && ((kind==Q)||(kind==RESULT)||
                (kind==CMD && beat==0 && data[511:19]==0 && data[18:1]<8192)||
                (kind==STATUS && beat==0 && data[511:5]==0));
        end
    endfunction
    function direction(input [3:0] kind,input bit transmit);
        begin
            if((KV_SIDE!=0)==transmit)direction=kind==RESULT||kind==STATUS;
            else direction=kind==CMD||kind==Q;
        end
    endfunction
    // TX check bits (internal operands, registered on their edge, as ba4)
    wire tx_time_bad=tx_event!=tx_expected;
    wire tx_record_bad=tx_event && (!legal(tx_kind,tx_layer,tx_beat,tx_data)||!direction(tx_kind,1'b1)||
        ({tx_kind,tx_epoch,tx_layer,tx_beat}!={tx_expected_kind,tx_expected_epoch,tx_expected_layer,tx_expected_beat}));
    // stage A: the landing (pins straight into flops, no logic, no enable)
    reg l_ev,l_exp;reg [3:0] l_ek;reg [15:0] l_ee;reg [5:0] l_el;reg [4:0] l_eb;
    reg [547:0] l_pl;
    reg t_time_bad,t_record_bad,f_r,txv_r;reg [3:0] c_r;
    wire [3:0] ak=l_pl[542:539];
    wire [5:0] al=l_pl[538:533];
    wire [15:0] ae=l_pl[532:517];
    wire [4:0] ab=l_pl[516:512];
    // the full RX check of the landed record, flop -> flop (stage B)
    wire a_time_bad=l_ev!=l_exp;
    wire a_record_bad=l_ev && (l_pl[547:543]!=0||!legal(ak,al,ab,l_pl[511:0])||!direction(ak,1'b0)||
        ({ak,ae,al,ab}!=((MUT==2)?{rx_expected_kind,rx_expected_epoch,rx_expected_layer,rx_expected_beat}:{l_ek,l_ee,l_el,l_eb})));
    assign a_cmd_ok=l_ev && ak==CMD && ((MUT==3)||(!a_record_bad && !a_time_bad));
    // stage B: registered check + the record it judges
    reg b_ev,b_rbad,b_tbad;reg [547:0] b_pl;
    wire [3:0] bits={b_rbad,t_record_bad,b_tbad,t_time_bad};
    wire bad=|bits;
    wire [547:0] o_pl=(MUT==1)?l_pl:b_pl;
    always @* begin
        fault=f_r|bad;
        fault_cause=f_r?c_r:bits;
        tx_valid=txv_r&&!bad;
        rx_valid=b_ev&&!f_r&&!bad;
        rx_kind=o_pl[542:539];rx_layer=o_pl[538:533];rx_epoch=o_pl[532:517];rx_beat=o_pl[516:512];rx_data=o_pl[511:0];
    end
    always @(posedge ck or negedge rst_n)begin
        if(!rst_n)begin
            l_ev<=0;l_exp<=0;l_ek<=0;l_ee<=0;l_el<=0;l_eb<=0;t_time_bad<=0;t_record_bad<=0;f_r<=0;c_r<=0;txv_r<=0;
            b_ev<=0;b_rbad<=0;b_tbad<=0;
        end else begin
            l_ev<=rx_event;l_exp<=rx_expected;l_ek<=rx_expected_kind;l_ee<=rx_expected_epoch;l_el<=rx_expected_layer;
            l_eb<=rx_expected_beat;t_time_bad<=tx_time_bad;t_record_bad<=tx_record_bad;
            b_ev<=l_ev;b_rbad<=a_record_bad;b_tbad<=a_time_bad;
            f_r<=f_r|bad;c_r<=fault_cause;txv_r<=tx_event&&!fault;
        end
    end
    always @(posedge ck)begin
        l_pl<=rx_payload;
        b_pl<=l_pl;
        tx_payload<={5'd0,tx_kind,tx_layer,tx_epoch,tx_beat,tx_data};
    end
endmodule

// Controller: qkd_native_attention_static_ctl_ba4 LAND=1 with the rv codec, the registered admission copies, load copies
// and precomputed status_slot copies.  Edge for edge ba4 except: every RX observation +1 (codec), request_valid = registered
// copies (landing edge), and the TX side runs on tx_first (+1 from the calendar generator).
module qkd_native_attention_static_ctl_r16 #(
 parameter integer MUT=0,
 parameter integer NRV=19,
 parameter integer NLD=16,
 parameter integer NSS=33
)(
 input wire ck,rst_n,
 input wire [NLD-1:0] load,
 input wire [2:0] run_c,             // run landing copies: [0] age[7:0] select, [1] age[15:8] select, [2] control
 input wire [379:0] command,
 input wire [58:0] command_tag,
 input wire fused_program_capability,authority_valid,
 input wire [15:0] authority_epoch,
 input wire [17:0] authority_token,authority_position,
 input wire [5:0] authority_stage,
 input wire [175:0] compiled_calendar,
 input wire [15:0] compiled_rx_cmd,compiled_tx_first,compiled_end,
 input wire rx_event,input wire [547:0] rx_payload,
 input wire tx_slot,input wire [3:0] tx_slot_kind,input wire [4:0] tx_slot_beat,
 output wire tx_valid,output wire [547:0] tx_payload,
 output wire [NRV-1:0] request_valid,input wire request_ready,
 output wire [15:0] request_epoch,output wire [5:0] request_layer,
 output wire [17:0] request_position,output wire [175:0] request_calendar,
 output reg q_valid,output reg [4:0] q_beat,output reg [511:0] q_data,
 input wire result_valid,input wire [4:0] result_beat,input wire [511:0] result_data,
 input wire [15:0] result_epoch,input wire [5:0] result_layer,
 input wire result_done,service_fault,
 output wire result_reserved,
 output reg busy,output wire fault,output reg [15:0] age
);
 wire accepted,guard_fault;wire [379:0] ac;wire [58:0] at;
 wire [17:0] pos;wire [15:0] ep;wire [5:0] layer;
 qkd_native59_command_guard_r16 guard(.ck(ck),.rst_n(rst_n),.command_valid(load[0]),
  .command(command),.command_tag(command_tag),.fused_program_capability(fused_program_capability),
  .authority_valid(authority_valid),.authority_epoch(authority_epoch),.authority_token(authority_token),
  .authority_position(authority_position),.authority_stage(authority_stage),.accepted(accepted),
  .accepted_command(ac),.accepted_tag(at),.native_xbase(),.native_obase(),.native_nout(),.native_k(),
  .native_position(pos),.native_epoch(ep),.native_layer(layer),.fault(guard_fault),.fault_cause());
 reg loaded,local_fault,loading;reg [175:0] cal;
 reg [15:0] rx_cmd,tx_first,last;
 wire run_ok=loaded&&!busy;
 (* keep *) wire [15:0] age_hold=busy?age+16'd1:age;
 (* keep *) wire [15:0] age_run=run_ok?16'd0:age;
 wire run=run_c[2];
 wire [15:0] age_nx={run_c[1]?age_run[15:8]:age_hold[15:8],run_c[0]?age_run[7:0]:age_hold[7:0]};
 wire busy_nx=run?(run_ok?1'b1:busy):((busy&&age==last)?1'b0:busy);
 wire [15:0] tx_first_nx=load[0]?compiled_tx_first:tx_first;
 // status_slot = busy && age == tx_first + 33, as NSS kept copies computed from the next state (exact every edge)
 (* keep = "true", dont_touch = "true" *) reg [NSS-1:0] ss_c;
 wire ss_nx=busy_nx&&(age_nx==tx_first_nx+((MUT==5)?16'd32:16'd33));
 always @(posedge ck or negedge rst_n)if(!rst_n)ss_c<=0;else ss_c<={NSS{ss_nx}};
 wire status_slot=ss_c[NSS-1];
 // compiled values: the load capture is split over the NLD-1 load copies (<= 32 flops each)
 always @(posedge ck or negedge rst_n)begin
  if(!rst_n)begin cal<=0;rx_cmd<=0;tx_first<=0;last<=0;end
  else begin
   for(integer k=0;k<11;k=k+1)if(load[1+k])cal[16*k+:16]<=compiled_calendar[16*k+:16];
   if(load[12])last<=compiled_end;
   if(load[13])rx_cmd<=compiled_rx_cmd;
   if(load[14])tx_first<=compiled_tx_first;
  end
 end
 wire rx_valid;wire [3:0] rx_kind;wire [4:0] rx_beat;wire [511:0] rx_data;wire record_fault;wire codec_tx_valid;
 wire a_cmd_ok;
 always @(posedge ck or negedge rst_n)begin
  if(!rst_n)begin loaded<=0;loading<=0;local_fault<=0;busy<=0;age<=0;end
  else begin
   age<=age_nx;busy<=busy_nx;
   if(load[0])begin
    if(busy||loading||loaded||compiled_rx_cmd<2||compiled_tx_first<=compiled_rx_cmd+34||compiled_end!=compiled_tx_first+34)
     local_fault<=1;
    loading<=1;
   end
   if(accepted)begin loaded<=1;loading<=0;end
   if(run)begin
    if(!loaded||busy||fault)local_fault<=1;
    if(run_ok)loaded<=0;
   end
   if(request_valid[NRV-1]&&!request_ready)local_fault<=1;
   if(rx_valid&&rx_kind==1&&rx_data!={493'd0,5'd0,pos[12:0],1'b1})local_fault<=1;
   if(result_valid!=result_reserved)local_fault<=1;
   if(result_valid&&({result_epoch,result_layer,result_beat}!={ep,layer,result_expected_beat}))local_fault<=1;
   if(result_done!=(busy&&age==tx_first+32))local_fault<=1;
  end
 end
 wire [4:0] result_expected_beat=age-tx_first;
 wire rx_expected=busy&&(age>=rx_cmd)&&(age<=rx_cmd+32);
 wire [3:0] rx_kind_expected=(age==rx_cmd)?4'd1:4'd2;
 wire [4:0] rb=age-rx_cmd-1;
 wire tx_expected=result_reserved||status_slot;
 assign result_reserved=busy&&age>=tx_first&&age<tx_first+32;
 reg done_seen;
 always @(posedge ck or negedge rst_n)
  if(!rst_n)done_seen<=0;
  else if(run)done_seen<=0;
  else if(busy&&age==tx_first+32&&result_done)done_seen<=1;
 wire [511:0] status_data;
 qkd_native_status_word u_status(.q_ready(1'b0),.done(done_seen),.fault(fault),.busy(1'b0),.ready(done_seen&&!fault),.word(status_data));
 // the 512-bit TX data select: one status_slot copy per 32 bits (registered one-hot select)
 wire [511:0] tx_data;
 for(genvar s=0;s<32;s=s+1)begin:g_txd
  assign tx_data[16*s+:16]=ss_c[s]?status_data[16*s+:16]:result_data[16*s+:16];
 end
 wire [547:0] codec_tx_payload;
 qkd_native_attention_record_r16 #(.MUT((MUT>=1&&MUT<=3)?MUT:0)) codec(.ck(ck),.rst_n(rst_n),
  .tx_event(result_valid||status_slot),.tx_expected(tx_expected),.tx_kind(status_slot?4'd4:4'd3),
  .tx_expected_kind(status_slot?4'd4:4'd3),.tx_epoch(ep),.tx_expected_epoch(ep),
  .tx_layer(layer),.tx_expected_layer(layer),.tx_beat(status_slot?5'd0:result_beat),
  .tx_expected_beat(status_slot?5'd0:result_expected_beat),.tx_data(tx_data),.tx_valid(codec_tx_valid),.tx_payload(codec_tx_payload),
  .rx_event(rx_event),.rx_expected(rx_expected),.rx_payload(rx_payload),
  .rx_expected_kind(rx_kind_expected),.rx_expected_epoch(ep),.rx_expected_layer(layer),
  .rx_expected_beat(age==rx_cmd?5'd0:rb),.rx_valid(rx_valid),.rx_kind(rx_kind),
  .rx_epoch(),.rx_layer(),.rx_beat(rx_beat),.rx_data(rx_data),.fault(record_fault),.fault_cause(),.a_cmd_ok(a_cmd_ok));
 // registered admission: NRV kept copies, written on the landing edge from the landed check and this cycle's fault
 (* keep = "true", dont_touch = "true" *) reg [NRV-1:0] rv_c;
 always @(posedge ck or negedge rst_n)if(!rst_n)rv_c<=0;else rv_c<={NRV{a_cmd_ok&&!fault}};
 assign request_valid=rv_c;
 // TX slot pins land with their expectation; check one edge later (ba4 LAND)
 reg slot_fault;
 reg ls_slot,ls_exp;reg [8:0] ls_kb,ls_ekb;
 always @(posedge ck or negedge rst_n)
  if(!rst_n)begin ls_slot<=0;ls_exp<=0;ls_kb<=0;ls_ekb<=0;end
  else begin ls_slot<=tx_slot;ls_exp<=tx_expected;ls_kb<={tx_slot_kind,tx_slot_beat};
   ls_ekb<={status_slot?4'd4:4'd3,status_slot?5'd0:result_expected_beat};end
 wire slot_chk=ls_slot!=ls_exp||(ls_slot&&ls_kb!=ls_ekb);
 wire slot_fault_o=slot_fault||slot_chk;
 always @(posedge ck or negedge rst_n)begin
  if(!rst_n)begin q_valid<=0;slot_fault<=0;end
  else begin
   q_valid<=!fault&&rx_valid&&rx_kind==2;
   if(slot_chk)slot_fault<=1;
  end
 end
 always @(posedge ck)begin q_beat<=rx_beat;q_data<=rx_data;end
 reg tx_v_l;reg [547:0] tx_p_l;
 always @(posedge ck or negedge rst_n)if(!rst_n)tx_v_l<=0;else tx_v_l<=codec_tx_valid&&!fault;
 always @(posedge ck)tx_p_l<=codec_tx_payload;
 assign tx_valid=tx_v_l;assign tx_payload=tx_p_l;
 assign request_epoch=ep;assign request_layer=layer;assign request_position=pos;assign request_calendar=cal;
 assign fault=local_fault||guard_fault||record_fault||slot_fault_o||service_fault;
endmodule

// Descriptor producer (qkd_native59_descriptor_producer_ld) with the descriptor-valid strobe as NLD kept register copies.
// ld_c is registered on the issue edge from the same operands the _ld landed copies check one edge later: exact.
module qkd_native59_descriptor_producer_r16 #(parameter integer NLD=16)(
 input wire ck,rst_n,
 input wire [4:0] issue,          // issue copies: [0] strobe/fault, [1..4] tag capture slices
 input wire authority_valid,
 input wire [15:0] authority_epoch,
 input wire [17:0] authority_token,authority_position,
 input wire [5:0] authority_stage,
 output wire [NLD-1:0] descriptor_valid,output reg [379:0] descriptor,
 output reg [58:0] tag,output wire fault
);
 localparam [379:0] NATIVE59={24'd0,1'b0,1'b0,1'b1,1'b1,
 24'd1,24'd1,24'd3167,1'b0,24'd0,4'd0,3'd0,
 24'd0,24'd0,24'd1,24'd13696,24'd0,24'd0,24'd0,24'd0,
 1'b1,18'd128,18'd1,18'd512,1'b1};
 reg iss_l,f_r,av_l;reg [17:0] tok_l,pos_l;reg [5:0] st_l;
 wire bad_l=!av_l||tok_l>=151936||pos_l>=8192||st_l<1||st_l>36;
 wire bad_n=!authority_valid||authority_token>=151936||authority_position>=8192||authority_stage<1||authority_stage>36;
 assign fault=f_r||(iss_l&&bad_l);
 (* keep = "true", dont_touch = "true" *) reg [NLD-1:0] dv_c;
 wire dv_ok=!fault&&!bad_n;       // one comb driver for the NLD copies
 wire [58:0] tag_n={authority_epoch,authority_stage,authority_token,authority_position[12:0],6'd0};
 always @(posedge ck or negedge rst_n)if(!rst_n)dv_c<=0;else dv_c<={NLD{issue[0]&&dv_ok}};
 assign descriptor_valid=dv_c;
 always @(posedge ck or negedge rst_n)
  if(!rst_n)begin iss_l<=0;f_r<=0;descriptor<=0;tag<=0;end
  else begin
   iss_l<=issue[0]&&!fault;f_r<=fault;
   if(issue[0]&&!fault)descriptor<=NATIVE59;
   // tag: read only under descriptor_valid (which requires !fault), so the capture needs no fault term
   for(integer k=0;k<3;k=k+1)if(issue[1+k])tag[16*k+:16]<=tag_n[16*k+:16];
   if(issue[4])tag[58:48]<=tag_n[58:48];
  end
 always @(posedge ck)begin av_l<=authority_valid;tok_l<=authority_token;pos_l<=authority_position;st_l<=authority_stage;end
endmodule

// Programme: qkd_native_attention_programme_ba4 LAND=1 with issue copies (NIS), the rv producer / controller.
module qkd_native_attention_programme_r16 #(parameter integer MUT=0,parameter integer NIS=24,parameter integer NRV=19)(
 input wire ck,rst_n,
 input wire [NIS-1:0] issue,
 input wire [2:0] run,
 input wire fused_program_capability,authority_valid,
 input wire [15:0] authority_epoch,
 input wire [17:0] authority_token,authority_position,
 input wire [5:0] authority_stage,
 input wire [175:0] compiled_calendar,
 input wire [15:0] compiled_rx_cmd,compiled_tx_first,compiled_end,
 input wire rx_event,input wire [547:0] rx_payload,
 input wire tx_slot,input wire [3:0] tx_slot_kind,input wire [4:0] tx_slot_beat,
 output wire tx_valid,output wire [547:0] tx_payload,
 output wire [NRV-1:0] request_valid,input wire request_ready,
 output wire [15:0] request_epoch,output wire [5:0] request_layer,
 output wire [17:0] request_position,output wire [175:0] request_calendar,
 output wire q_valid,output wire [4:0] q_beat,output wire [511:0] q_data,
 input wire result_valid,input wire [4:0] result_beat,input wire [511:0] result_data,
 input wire [15:0] result_epoch,input wire [5:0] result_layer,
 input wire result_done,service_fault,
 output wire result_reserved,
 output wire busy,output wire fault,output wire [15:0] age,
 output wire [536:0] prg_l
);
 localparam integer NLD=16;
 wire [NLD-1:0] load;wire producer_fault,ctl_fault;
 wire [379:0] command;wire [58:0] command_tag;
 reg authority_valid_q,capability_q;
 reg [15:0] authority_epoch_q,rx_cmd_q,tx_first_q,end_q;
 reg [17:0] authority_token_q,authority_position_q;
 reg [5:0] authority_stage_q;reg [175:0] calendar_q;
 // issue capture: one flat 284-bit word, 16-bit slices over the issue copies 5..22; copies 0..4 drive the producer
 wire [283:0] cap_d={authority_valid,fused_program_capability,authority_epoch,authority_token,authority_stage,
  authority_position,compiled_rx_cmd,compiled_tx_first,compiled_end,compiled_calendar};
 reg [283:0] cap_q;
 always @(posedge ck)for(integer i=0;i<284;i=i+1)if(issue[5+i/16])cap_q[i]<=cap_d[i];
 always @*{authority_valid_q,capability_q,authority_epoch_q,authority_token_q,authority_stage_q,
  authority_position_q,rx_cmd_q,tx_first_q,end_q,calendar_q}=cap_q;
 qkd_native59_descriptor_producer_r16 #(.NLD(NLD)) producer(.ck(ck),.rst_n(rst_n),.issue(issue[4:0]),
  .authority_valid(authority_valid),.authority_epoch(authority_epoch),.authority_token(authority_token),
  .authority_position(authority_position),.authority_stage(authority_stage),
  .descriptor_valid(load),.descriptor(command),.tag(command_tag),.fault(producer_fault));
 qkd_native_attention_static_ctl_r16 #(.MUT(MUT),.NRV(NRV),.NLD(NLD)) ctl(
  .load(load),.command(command),.command_tag(command_tag),.fault(ctl_fault),
  .ck(ck),.rst_n(rst_n),.run_c(run),
  .fused_program_capability(capability_q),.authority_valid(authority_valid_q),.authority_epoch(authority_epoch_q),
  .authority_token(authority_token_q),.authority_position(authority_position_q),.authority_stage(authority_stage_q),
  .compiled_calendar(calendar_q),.compiled_rx_cmd(rx_cmd_q),.compiled_tx_first(tx_first_q),.compiled_end(end_q),
  .rx_event(rx_event),.rx_payload(rx_payload),.tx_slot(tx_slot),.tx_slot_kind(tx_slot_kind),.tx_slot_beat(tx_slot_beat),
  .tx_valid(tx_valid),.tx_payload(tx_payload),.request_valid(request_valid),.request_ready(request_ready),
  .request_epoch(request_epoch),.request_layer(request_layer),.request_position(request_position),
  .request_calendar(request_calendar),.q_valid(q_valid),.q_beat(q_beat),.q_data(q_data),
  .result_valid(result_valid),.result_beat(result_beat),.result_data(result_data),.result_epoch(result_epoch),
  .result_layer(result_layer),.result_done(result_done),.service_fault(service_fault|producer_fault),
  .result_reserved(result_reserved),.busy(busy),.age(age));
 assign fault=ctl_fault|producer_fault;
 // prg launch (ba4 LAND): request_valid from its own admission copy
 wire [536:0] prg_w={q_data,q_beat,q_valid,request_position,request_valid[NRV-1]};
 reg prg_rv,prg_qv;reg [535:0] prg_d;
 always @(posedge ck or negedge rst_n)if(!rst_n)begin prg_rv<=0;prg_qv<=0;end else begin prg_rv<=request_valid[NRV-2];prg_qv<=q_valid;end
 always @(posedge ck)prg_d<=prg_w[536:1];
 assign prg_l={prg_d[535:19],prg_qv,prg_d[17:0],prg_rv};
endmodule

// Service root: qkd_attn_service_root_b CAL_PIPE=1 with request_valid as kept copies; each accept slice <= 36 flops.
// copy 0: control (running / start / age / faults), 1..6: cal (176), 7: ep / layer / ctx, 8: pv_t / end_t.
// boot_ok is the registered boot_count == 80 (exact: boot_count >= 79 one edge earlier).
module qkd_attn_service_root_r16 #(
 parameter integer PV_LEAD=63,
 parameter integer MUT=0
)(
 input wire ck,rst_n,
 input wire [7:0] cfg_pv_lead,
 input wire [7:0] cfg_f_dly,
 input wire [16:0] request_valid,output wire request_ready,
 input wire [15:0] request_epoch,input wire [5:0] request_layer,
 input wire [17:0] request_position,input wire fused_program_capability,
 input wire [175:0] request_calendar,
 input wire q_valid,input wire [4:0] q_beat,output wire q_ready,
 output reg running,start_qk,start_pv,
 output reg [15:0] age,
 output reg [15:0] ep,output reg [5:0] layer,output reg [13:0] ctx,
 output reg [175:0] cal,output reg [31:0] cycles,
 output reg local_fault,io_fault
);
 reg [6:0] boot_count;reg boot_ok;
 (* keep = "true", dont_touch = "true" *) reg run_cp;   // running copy: the age / cycles increment enable
 reg [16:0] pv_t,end_t;
 assign request_ready=!running&&boot_ok;
 wire [16:0] acc=request_valid&{17{request_ready}};
 wire q_window=running&&!start_qk&&age>=1&&age<=32;
 assign q_ready=q_window;
 wire [15:0] rq_pv=request_calendar[127:112],rq_p0=request_calendar[143:128];
 wire [15:0] rq_p1=request_calendar[159:144],rq_r=request_calendar[175:160];
 wire [15:0] rq_last=(rq_p0>rq_p1)?((rq_p0>rq_r)?rq_p0:rq_r):((rq_p1>rq_r)?rq_p1:rq_r);
 reg [15:0] cp_pv,cp_last;reg [63:0] cp_cal;
 always @(posedge ck)begin cp_pv<=rq_pv;cp_last<=rq_last;cp_cal<=request_calendar[175:112];end
 wire cal_moved=cp_cal!=request_calendar[175:112];
 reg [15:0] k_end;
 always @(posedge ck)k_end<=16'd47+16'(cfg_f_dly);
 wire [15:0] rq_end_m1=cp_pv+cp_last+k_end;
 reg [7:0] lead_q;reg [16:0] sub_q;reg lead_bad;
 always @(posedge ck)begin
  lead_q<=cfg_pv_lead;
  sub_q<=17'(lead_q)+17'd1;
  lead_bad<=lead_q>8'(PV_LEAD);
 end
 wire [16:0] rq_pv_t={1'b0,cp_pv}-sub_q;
 always @(posedge ck or negedge rst_n)begin
  if(!rst_n)begin boot_count<=0;boot_ok<=0;running<=0;run_cp<=0;start_qk<=0;start_pv<=0;age<=0;ep<=0;layer<=0;ctx<=0;cal<=0;
   local_fault<=0;io_fault<=0;cycles<=0;pv_t<=17'h1ffff;end_t<=17'h1ffff;end
  else begin
   start_qk<=0;start_pv<=0;
   if(boot_count<80)boot_count<=boot_count+1'b1;
   boot_ok<=boot_count>=7'd79;
   if(run_cp)begin age<=age+1'b1;cycles<=cycles+1;end
   if(running&&{1'b0,age}==pv_t)start_pv<=1;
   if(running&&{1'b0,age}==end_t)begin running<=0;run_cp<=0;end
   if(request_valid[0]&&!request_ready)io_fault<=1;
   if(q_valid!=q_window)io_fault<=1;
   if(q_window&&q_valid&&q_beat!=5'(age-1))io_fault<=1;
   if(acc[0])begin
    if(!fused_program_capability||request_position>8191)local_fault<=1;
    if(lead_q!=0&&(cp_pv<=16'(lead_q)||(rq_end_m1!=16'hffff&&cp_pv>rq_end_m1)))local_fault<=1;
    if(lead_bad)local_fault<=1;
    if(cal_moved)local_fault<=1;
    running<=1;run_cp<=1;start_qk<=1;age<=0;cycles<=0;
   end
   for(integer k=0;k<11;k=k+1)if(acc[1+k])cal[16*k+:16]<=request_calendar[16*k+:16];
   if(acc[12])ep<=request_epoch;
   if(acc[13])layer<=request_layer;
   if(acc[14])ctx<=14'(request_position+1);
   if(acc[15])pv_t<=rq_pv_t;
   if(acc[16])end_t<={rq_end_m1==16'hffff,rq_end_m1};
  end
 end
endmodule

// Result face: qkd_attn_result_face_sc CAL_PIPE=1 with an UNCONDITIONAL 512-bit beat capture (rdata <= f_data every edge;
// result_valid = emitting alone authorizes it).  Equal to sc whenever result_valid (the 32 beats arrive on consecutive
// edges, a gap faults); held invalid data is not reproduced.
module qkd_attn_result_face_r16 #(
 parameter integer NF=10,
 parameter integer F_DLY=127,
 parameter integer MUT=0
)(
 input wire ck,rst_n,
 input wire [7:0] cfg_f_dly,
 input wire running,start_qk,
 input wire [15:0] age,
 input wire [15:0] ep,input wire [5:0] layer,
 input wire [175:0] cal,
 input wire root_local_fault,root_io_fault,
 input wire f_valid,input wire [4:0] f_beat,input wire [511:0] f_data,input wire [15:0] f_epoch,
 input wire [NF-1:0] unit_fault,
 output wire result_valid,output wire [4:0] result_beat,output wire [511:0] result_data,
 output wire [15:0] result_epoch,output wire [5:0] result_layer,
 output wire result_done,output wire service_fault,
 output wire result_fault,
 output wire [7:0] hdr_l
);
 wire [15:0] c_pv=cal[127:112],c_p0=cal[143:128],c_p1=cal[159:144],c_r=cal[175:160];
 wire [15:0] c_lastp=(c_p0>c_p1)?c_p0:c_p1;
 wire [15:0] c_last=(c_lastp>c_r)?c_lastp:c_r;
 reg rf;
 reg l_win;reg [4:0] l_boff;reg [15:0] l_fe,l_ep;
 reg [15:0] res_t;
 reg [511:0] rdata,fd_d;reg [4:0] rbeat;reg emitting,done_r;
 reg fv_d;reg [4:0] fb_d;
 reg [15:0] cp_pv,cp_last;reg cp_sq;
 (* keep = "true", dont_touch = "true" *) reg [1:0] cp_sq_c;   // res_t capture strobe copies (8 bits each)
 reg [7:0] fd_q;reg [15:0] k_res;reg fd_bad;
 always @(posedge ck)begin
  fd_q<=cfg_f_dly;
  k_res<=16'd16+16'(fd_q);
  fd_bad<=fd_q<8'd1||fd_q>8'(F_DLY);
 end
 wire [15:0] res_c=cp_pv+cp_last+k_res;
 assign hdr_l={fv_d,2'b00,fb_d};
 wire [15:0] boff=age-res_t;
 wire in_win=running&&!start_qk&&(age>=res_t)&&(boff<16'd32);
 always @(posedge ck or negedge rst_n)begin
  if(!rst_n)begin emitting<=0;rbeat<=0;done_r<=0;rf<=0;l_win<=0;res_t<=16'hffff;fv_d<=0;cp_sq<=0;cp_sq_c<=0;end
  else begin
   done_r<=0;fv_d<=f_valid;cp_sq<=start_qk;cp_sq_c<={2{start_qk}};
   if(start_qk&&fd_bad)rf<=1;
   if(cp_sq_c[0])res_t[7:0]<=res_c[7:0];
   if(cp_sq_c[1])res_t[15:8]<=res_c[15:8];
   if(cp_sq&&res_c<16'd2)rf<=1;
   l_win<=in_win;if(f_chk)rf<=1;
   if(f_valid)begin rbeat<=f_beat;emitting<=1;end
   else if(emitting)begin
    if(rbeat==5'd31)begin emitting<=0;done_r<=1;end
    else rf<=1;
   end
  end
 end
 always @(posedge ck)begin
  fb_d<=f_beat;l_boff<=boff[4:0];l_fe<=f_epoch;l_ep<=ep;
  cp_pv<=c_pv;cp_last<=c_last;     // unconditional: read only on cp_sq, the edge after start_qk (root cal loaded on the accept edge)
  fd_d<=f_data;
  rdata<=(MUT==6)?fd_d:f_data;
 end
 wire f_chk=(fv_d!=l_win)||(fv_d&&(fb_d!=l_boff||l_fe!=l_ep));
 assign result_fault=rf|f_chk;
 wire sf=result_fault|root_local_fault|root_io_fault|(|unit_fault);
 assign {result_valid,result_beat,result_data,result_epoch,result_layer,result_done,service_fault}=
  {emitting,rbeat[4:0],rdata,ep,layer,done_r,sf};
endmodule

// Calendar generator: qkd_attn_cal_gen_b STRETCH=1 with TX_SHIFT on tx_first / end, unconditional S1..S9 captures (a
// fixed-latency pipeline: stage N is read only on vN, equal to the gated version there) and NV9 kept copies of the S10 strobe.
module qkd_attn_cal_gen_r16 #(
 parameter integer G3S2=1,
 parameter integer RX_CMD=2,
 parameter integer TX_SHIFT=1,
 parameter integer D_QK=255,
 parameter integer D_RL=255,
 parameter integer F_DLY=127,
 parameter integer SERVICE_END=1777,
 parameter integer NV9=16,
 parameter integer MUT=0
)(
 input wire ck,rst_n,
 input wire [23:0] cfg_cal,
 input wire go,
 input wire [13:0] ctx_t,
 input wire [15:0] epoch,
 output reg [175:0] cal,
 output reg [15:0] rx_cmd,tx_first,end_age,
 output reg [15:0] cal_epoch,
 output reg done,valid,
 output reg fault
);
 localparam integer TXF=RX_CMD+2+SERVICE_END-31+((MUT==4)?0:TX_SHIFT);
 reg [23:0] cfg_q;reg [11:0] k_dr,k_po0,k_po1;reg [15:0] k_lm,k_rl;reg cfg_bad;
 wire [7:0] c_dq=cfg_q[7:0],c_dr=cfg_q[15:8],c_fd=cfg_q[23:16];
 always @(posedge ck)begin
  cfg_q<=cfg_cal;
  k_dr<=12'(c_dr);
  k_po0<=12'd153+12'(c_dr);
  k_po1<=12'd137+12'(c_dr);
  k_lm<=16'(151+5*G3S2)+16'(c_dq);
  k_rl<=16'(SERVICE_END-48)-16'(c_fd);
  cfg_bad<=(c_dq>8'(D_QK))||(c_dr>8'(D_RL))||(c_fd<8'd1)||(c_fd>8'(F_DLY));
 end
 reg v1;reg [13:0] t1;reg [15:0] e1;
 always @(posedge ck or negedge rst_n)if(!rst_n)v1<=0;else v1<=go;
 always @(posedge ck)begin t1<=ctx_t;e1<=epoch;end
 reg v2,f2,big1;reg [15:0] e2;reg [12:0] x2[0:3];reg [3:0] p2;reg [11:0] ns2;reg [5:0] c0_2,c1_2;
 wire [8:0] tl=t1[8:0];
 always @(posedge ck or negedge rst_n)if(!rst_n)v2<=0;else v2<=v1;
 always @(posedge ck)begin
  f2<=(t1==14'd0)||(t1>14'd8192);e2<=e1;
  for(integer s=0;s<4;s=s+1)begin x2[s]<=13'(t1-14'd1-14'(128*s));p2[s]<=t1>14'(128*s);end
  ns2<=12'({t1[13:9],7'd0}+((tl>=9'd128)?14'd128:14'(tl)));
  c0_2<=6'((t1+14'd255)>>8);c1_2<=6'((t1+14'd127)>>8);big1<=t1>14'd128;
 end
 reg v3,f3;reg [15:0] e3;reg [3:0] p3,sm3,b3;reg [7:0] a3[0:3];reg [3:0] cnt3[0:3];reg [9:0] xs3[0:3];
 reg [10:0] m3,mm3;reg nbig3;reg [11:0] po0_3,po1_3;
 always @(posedge ck or negedge rst_n)if(!rst_n)v3<=0;else v3<=v2;
 always @(posedge ck)begin
  f3<=f2;e3<=e2;p3<=p2;
  for(integer s=0;s<4;s=s+1)begin
   sm3[s]<=x2[s]<13'd127;
   xs3[s]<=x2[s][12:3];
   a3[s]<=8'({x2[s][12:9],4'd0}-{4'd0,x2[s][12:9]}+8'd15);
   cnt3[s]<=(x2[s][8:3]>=6'd15)?4'd0:4'(4'd15-x2[s][6:3]);
   b3[s]<=(x2[s][8:0]<9'd120);
  end
  m3<=11'(ns2-12'd1);mm3<=11'(ns2-12'd65);nbig3<=ns2<=12'd1024;
  po0_3<=12'(k_po0+{c0_2,4'd0});
  po1_3<=big1?12'(k_po0+{c1_2,4'd0}):k_po1;
 end
 reg v4,f4;reg [15:0] e4;reg [9:0] zv4[0:3];reg [7:0] scan4;reg [11:0] po0_4,po1_4;reg [8:0] adj4;
 wire [6:0] lo7=mm3[6:0];
 always @(posedge ck or negedge rst_n)if(!rst_n)v4<=0;else v4<=v3;
 always @(posedge ck)begin
  f4<=f3;e4<=e3;po0_4<=po0_3;po1_4<=po1_3;
  for(integer s=0;s<4;s=s+1)zv4[s]<=!p3[s]?10'd0:sm3[s]?xs3[s]:10'(a3[s]-{4'd0,cnt3[s]}+{7'd0,b3[s]});
  scan4<=nbig3?8'(m3>>3):8'(8'd128+{1'b0,mm3[10:7],3'd0}+((lo7>=7'd63)?8'd7:{5'd0,lo7[5:3]}));
  adj4<=(po0_3<=12'd480)?9'(12'd481-po0_3):9'd0;
 end
 reg v5,f5;reg [15:0] e5;reg [9:0] za5,zb5;reg [15:0] lmax5;reg [11:0] po0_5,po1_5;reg [8:0] adj5;
 always @(posedge ck or negedge rst_n)if(!rst_n)v5<=0;else v5<=v4;
 always @(posedge ck)begin
  f5<=f4;e5<=e4;po0_5<=po0_4;po1_5<=po1_4;adj5<=adj4;
  za5<=(zv4[0]>zv4[1])?zv4[0]:zv4[1];zb5<=(zv4[2]>zv4[3])?zv4[2]:zv4[3];
  lmax5<=16'(scan4)+k_lm;
 end
 reg v6,f6;reg [15:0] e6;reg [9:0] zw6;reg [15:0] lmax6,exp6,zb6,hl6;reg [11:0] po0_6,po1_6;reg [8:0] adj6;
 always @(posedge ck or negedge rst_n)if(!rst_n)v6<=0;else v6<=v5;
 always @(posedge ck)begin
  f6<=f5;e6<=e5;po0_6<=po0_5;po1_6<=po1_5;adj6<=adj5;lmax6<=lmax5;
  zw6<=(za5>zb5)?za5:zb5;exp6<=lmax5+16'd15;zb6<=lmax5+16'd265;hl6<=lmax5+16'd7;
 end
 reg v7,f7;reg [15:0] e7;reg [15:0] lmax7,exp7,z7,hl7,pvo7;reg [11:0] po0_7,po1_7;
 always @(posedge ck or negedge rst_n)if(!rst_n)v7<=0;else v7<=v6;
 always @(posedge ck)begin
  f7<=f6;e7<=e6;lmax7<=lmax6;exp7<=exp6;hl7<=hl6;po0_7<=po0_6;po1_7<=po1_6;
  z7<=zb6+16'(zw6);
  pvo7<=16'(adj6)-16'd64;
 end
 reg v8,f8;reg [15:0] e8;reg [15:0] lmax8,exp8,z8,hl8,hz8,hr8,hp8,pv8;reg [11:0] po0_8,po1_8;
 always @(posedge ck or negedge rst_n)if(!rst_n)v8<=0;else v8<=v7;
 always @(posedge ck)begin
  f8<=f7;e8<=e7;lmax8<=lmax7;exp8<=exp7;z8<=z7;hl8<=hl7;po0_8<=po0_7;po1_8<=po1_7;
  hz8<=z7+16'd261;hr8<=z7+16'd342;hp8<=z7+16'd415;pv8<=z7+pvo7;
 end
 reg f9;reg [15:0] e9;reg [175:0] cal9;reg [15:0] p09;reg [16:0] r9;
 (* keep = "true", dont_touch = "true" *) reg [NV9-1:0] v9c;
 always @(posedge ck or negedge rst_n)if(!rst_n)v9c<=0;else v9c<={NV9{v8}};
 always @(posedge ck)begin
  f9<=f8;e9<=e8;
  r9<={1'b0,k_rl}-{1'b0,pv8};
  p09<=16'(po0_8);
  cal9<={k_rl-pv8,16'(po1_8),16'(po0_8),pv8,hp8,hr8,hz8,hl8,z8,lmax8,exp8};
 end
 // S10: held result, the capture split over the v9 copies (<= 32 flops each)
 always @(posedge ck or negedge rst_n)begin
  if(!rst_n)begin done<=0;valid<=0;fault<=0;cal<=0;rx_cmd<=16'(RX_CMD);tx_first<=0;end_age<=0;cal_epoch<=0;end
  else begin
   done<=v9c[0];
   if(v9c[0])valid<=1;else if(go)valid<=0;
   if(v9c[0])begin
    rx_cmd<=16'(RX_CMD);
    if(f9||r9[16]||r9[15:0]<p09||cfg_bad)fault<=1;
   end
   if(v9c[1])tx_first<=16'(TXF);
   if(v9c[2])end_age<=16'(TXF+34);
   if(v9c[3])cal_epoch<=e9;
   for(integer k=0;k<11;k=k+1)if(v9c[4+k])cal[16*k+:16]<=cal9[16*k+:16];
  end
 end
endmodule

// Fault root: qkd_attn_fault_root with every input pin landing in its own flop (the c pairs are ORed after their flops:
// cq = OR of the landed pair, exactly the original's registered OR).
module qkd_attn_fault_root_r16 #(parameter integer ND=8,parameter integer NC=4,parameter integer MUT=0)(
 input wire ck,rst_n,
 input wire [ND-1:0] d,
 input wire [NC-1:0] c,
 output wire [ND+NC/2-1:0] unit_fault
);
 reg [ND-1:0] dq;reg [NC-1:0] cl;
 always @(posedge ck or negedge rst_n)
  if(!rst_n)begin dq<=0;cl<=0;end
  else begin dq<=d;cl<=c;end
 wire [NC/2-1:0] cq;
 for(genvar j=0;j<NC/2;j=j+1)begin:g_c
  assign cq[j]=(MUT==7)?cl[2*j]:(cl[2*j]|cl[2*j+1]);
 end
 assign unit_fault={cq,dq};
endmodule

// The tile core (ports = qkd_kvs_attn_ba5 + the issue landing copies from the face wrapper).
module qkd_kvs_attn_r16 #(parameter integer MUT=0,parameter integer NIS=24)(
    input wire ck,
    input wire rst_n,
    input wire [0:0] ufs_WS,
    input wire [0:0] ufs_WN,
    input wire [0:0] ufs_ES,
    input wire [0:0] ufs_EN,
    input wire [0:0] ufh,
    input wire [0:0] ufp0,
    input wire [0:0] ufp1,
    input wire [0:0] uff,
    input wire [0:0] ufk_WS,
    input wire [0:0] ufk_WN,
    input wire [0:0] ufk_ES,
    input wire [0:0] ufk_EN,
    input wire [521:0] d2d__srx,
    input wire [547:0] d2d__rx_payload,
    input wire [0:0] d2d__att_tx_slot,
    input wire [3:0] d2d__att_tx_kind,
    input wire [4:0] d2d__att_tx_beat,
    input wire [533:0] fin,
    output wire [0:0] attn__tx_valid,
    output wire [547:0] attn__tx_payload,
    output wire [30:0] pvst,
    output wire [64:0] pvfst,
    output wire [164:0] ahs,
    output wire [536:0] prg,
    output wire [47:0] acal_WS,
    output wire [47:0] acal_WN,
    output wire [47:0] acal_ES,
    output wire [47:0] acal_EN,
    output wire [7:0] arh,
    input wire [108:0] i_ctl,
    input wire [NIS-1:0] issue_c,
    input wire [2:0] run_c
);
    localparam integer NRV=19;
    wire [7:0] attn_root__cfg_pv_lead = i_ctl[7:0];
    wire [7:0] attn_cal__cfg_cal__0 = i_ctl[15:8];
    wire [7:0] attn_cal__cfg_cal__2 = i_ctl[23:16];
    wire [7:0] attn_cal__cfg_cal__1 = i_ctl[31:24];
    wire [0:0] attn__fused_program_capability = i_ctl[32:32];
    wire [0:0] attn__authority_valid = i_ctl[33:33];
    wire [13:0] attn_cal__ctx_t = i_ctl[49:36];
    wire [15:0] attn__authority_epoch = i_ctl[65:50];
    wire [17:0] attn__authority_position = i_ctl[83:66];
    wire [5:0] attn__authority_stage = i_ctl[89:84];
    wire [0:0] attn_cal__go = i_ctl[90:90];
    wire [17:0] attn__authority_token = i_ctl[108:91];
    wire [9:0] w_afr__unit_fault;
    wire [NRV-1:0] w_attn__request_valid;
    wire [15:0] w_attn__request_epoch;
    wire [5:0] w_attn__request_layer;
    wire [17:0] w_attn__request_position;
    wire [175:0] w_attn__request_calendar;
    wire w_attn__q_valid;wire [4:0] w_attn__q_beat;wire [511:0] w_attn__q_data;
    wire [175:0] w_attn_cal__cal;
    wire [15:0] w_attn_cal__rx_cmd,w_attn_cal__tx_first,w_attn_cal__end_age;
    wire w_face__result_valid;wire [4:0] w_face__result_beat;wire [511:0] w_face__result_data;
    wire [15:0] w_face__result_epoch;wire [5:0] w_face__result_layer;
    wire w_face__result_done,w_face__service_fault;wire [7:0] w_face__hdr_l;
    wire w_root__request_ready,w_root__running,w_root__start_qk,w_root__start_pv,w_root__local_fault,w_root__io_fault;
    wire [15:0] w_root__age,w_root__ep;wire [5:0] w_root__layer;wire [13:0] w_root__ctx;wire [175:0] w_root__cal;
    qkd_attn_fault_root_r16 #(.ND(8), .NC(4), .MUT(MUT)) u_afr (.ck(ck), .rst_n(rst_n),
        .d({uff, ufp1, ufp0, ufh, ufs_EN, ufs_ES, ufs_WN, ufs_WS}), .c({ufk_EN, ufk_ES, ufk_WN, ufk_WS}), .unit_fault(w_afr__unit_fault));
    qkd_native_attention_programme_r16 #(.MUT(MUT), .NIS(NIS), .NRV(NRV)) u_attn (.ck(ck), .rst_n(rst_n), .issue(issue_c), .run(run_c),
        .fused_program_capability(attn__fused_program_capability), .authority_valid(attn__authority_valid),
        .authority_epoch(attn__authority_epoch), .authority_token(attn__authority_token), .authority_position(attn__authority_position),
        .authority_stage(attn__authority_stage), .compiled_calendar(w_attn_cal__cal), .compiled_rx_cmd(w_attn_cal__rx_cmd),
        .compiled_tx_first(w_attn_cal__tx_first), .compiled_end(w_attn_cal__end_age), .rx_event(d2d__srx[0]),
        .rx_payload(d2d__rx_payload), .tx_slot(d2d__att_tx_slot[0]), .tx_slot_kind(d2d__att_tx_kind), .tx_slot_beat(d2d__att_tx_beat),
        .tx_valid(attn__tx_valid[0]), .tx_payload(attn__tx_payload), .request_valid(w_attn__request_valid),
        .request_ready(w_root__request_ready), .request_epoch(w_attn__request_epoch), .request_layer(w_attn__request_layer),
        .request_position(w_attn__request_position), .request_calendar(w_attn__request_calendar), .q_valid(w_attn__q_valid),
        .q_beat(w_attn__q_beat), .q_data(w_attn__q_data), .result_valid(w_face__result_valid), .result_beat(w_face__result_beat),
        .result_data(w_face__result_data), .result_epoch(w_face__result_epoch), .result_layer(w_face__result_layer),
        .result_done(w_face__result_done), .service_fault(w_face__service_fault), .result_reserved(), .busy(), .fault(), .age(),
        .prg_l(prg));
    qkd_attn_cal_gen_r16 #(.G3S2(1), .RX_CMD(2), .TX_SHIFT(1), .SERVICE_END(1777), .D_QK(255), .D_RL(255), .F_DLY(127), .MUT(MUT))
        u_attn_cal (.ck(ck), .rst_n(rst_n), .cfg_cal({attn_cal__cfg_cal__0, attn_cal__cfg_cal__1, attn_cal__cfg_cal__2}),
        .go(attn_cal__go), .ctx_t(attn_cal__ctx_t), .epoch(attn__authority_epoch), .cal(w_attn_cal__cal), .rx_cmd(w_attn_cal__rx_cmd),
        .tx_first(w_attn_cal__tx_first), .end_age(w_attn_cal__end_age), .cal_epoch(), .done(), .valid(), .fault());
    qkd_attn_result_face_r16 #(.NF(10), .F_DLY(127), .MUT(MUT)) u_attn_face (.ck(ck), .rst_n(rst_n), .cfg_f_dly(attn_cal__cfg_cal__0),
        .running(w_root__running), .start_qk(w_root__start_qk), .age(w_root__age), .ep(w_root__ep), .layer(w_root__layer),
        .cal(w_root__cal), .root_local_fault(w_root__local_fault), .root_io_fault(w_root__io_fault), .f_valid(fin[0]), .f_beat(fin[5:1]),
        .f_data(fin[533:22]), .f_epoch(fin[21:6]), .unit_fault(w_afr__unit_fault), .result_valid(w_face__result_valid),
        .result_beat(w_face__result_beat), .result_data(w_face__result_data), .result_epoch(w_face__result_epoch),
        .result_layer(w_face__result_layer), .result_done(w_face__result_done), .service_fault(w_face__service_fault),
        .result_fault(), .hdr_l(w_face__hdr_l));
    qkd_attn_service_root_r16 #(.PV_LEAD(63), .MUT(MUT)) u_attn_root (.ck(ck), .rst_n(rst_n), .cfg_pv_lead(attn_root__cfg_pv_lead),
        .cfg_f_dly(attn_cal__cfg_cal__0), .request_valid(w_attn__request_valid[16:0]), .request_ready(w_root__request_ready),
        .request_epoch(w_attn__request_epoch), .request_layer(w_attn__request_layer), .request_position(w_attn__request_position),
        .fused_program_capability(attn__fused_program_capability), .request_calendar(w_attn__request_calendar),
        .q_valid(w_attn__q_valid), .q_beat(w_attn__q_beat), .q_ready(), .running(w_root__running), .start_qk(w_root__start_qk),
        .start_pv(w_root__start_pv), .age(w_root__age), .ep(w_root__ep), .layer(w_root__layer), .ctx(w_root__ctx), .cal(w_root__cal),
        .cycles(), .local_fault(w_root__local_fault), .io_fault(w_root__io_fault));
    assign pvst = {w_root__ep, w_root__ctx, w_root__start_pv};
    assign pvfst = {w_root__cal[175:128], w_root__ep, w_root__start_pv};
    assign ahs = {w_root__cal[175:160], w_root__cal[127:16], w_root__ctx, w_root__layer, w_root__ep, w_root__start_qk};
    assign acal_WS = {w_root__cal[15:0], w_root__cal[47:32], w_root__cal[31:16]};
    assign acal_WN = {w_root__cal[15:0], w_root__cal[47:32], w_root__cal[31:16]};
    assign acal_ES = {w_root__cal[15:0], w_root__cal[47:32], w_root__cal[31:16]};
    assign acal_EN = {w_root__cal[15:0], w_root__cal[47:32], w_root__cal[31:16]};
    assign arh = w_face__hdr_l;
endmodule

// qkd_native59_command_guard with the accepted_tag capture enable split over 4 kept valid_q copies (<= 16 tag bits each);
// function identical (the copies are the same register; descriptor / identity / image checks are computed once).
module qkd_native59_command_guard_r16 #(
    parameter [379:0] COMMAND = {24'd0,1'b0,1'b0,1'b1,1'b1,
        24'd1,24'd1,24'd3167,1'b0,24'd0,4'd0,3'd0,
        24'd0,24'd0,24'd1,24'd13696,24'd0,24'd0,24'd0,24'd0,
        1'b1,18'd128,18'd1,18'd512,1'b1}
) (
    input wire ck, rst_n,
    input wire command_valid,
    input wire [379:0] command,
    input wire [58:0] command_tag,
    input wire fused_program_capability,
    input wire authority_valid,
    input wire [15:0] authority_epoch,
    input wire [17:0] authority_token, authority_position,
    input wire [5:0] authority_stage,
    output reg accepted,
    output reg [379:0] accepted_command,
    output reg [58:0] accepted_tag,
    output wire [23:0] native_xbase, native_obase,
    output wire [17:0] native_nout, native_k, native_position,
    output wire [15:0] native_epoch,
    output wire [5:0] native_layer,
    output reg fault,
    output reg [2:0] fault_cause
);
    reg valid_q, capability_q, authority_q;
    (* keep = "true", dont_touch = "true" *) reg [3:0] valid_c;
    reg [379:0] command_q;
    reg [58:0] tag_q;
    reg [15:0] authority_epoch_q;
    reg [17:0] authority_token_q, authority_position_q;
    reg [5:0] authority_stage_q;
    always @(posedge ck) begin
        command_q <= command; tag_q <= command_tag;
        capability_q <= fused_program_capability; authority_q <= authority_valid;
        authority_epoch_q <= authority_epoch; authority_token_q <= authority_token;
        authority_position_q <= authority_position; authority_stage_q <= authority_stage;
    end
    wire descriptor_ok = command_q == COMMAND;
    wire identity_ok =
        (authority_q && authority_token_q < 18'd151936 && authority_position_q < 18'd8192 &&
         authority_stage_q >= 6'd1 && authority_stage_q <= 6'd36 &&
         tag_q == {authority_epoch_q, authority_stage_q, authority_token_q, authority_position_q[12:0], 6'd0});
    wire image_ok = capability_q;
    wire take = !fault && descriptor_ok && identity_ok && image_ok;
    always @(posedge ck or negedge rst_n) begin
        if (!rst_n) begin
            valid_q <= 0; valid_c <= 0; accepted <= 0; accepted_command <= 0; accepted_tag <= 0;
            fault <= 0; fault_cause <= 0;
        end else begin
            valid_q <= command_valid; valid_c <= {4{command_valid}};
            accepted <= 0;
            if (valid_q && !fault) begin
                if (!descriptor_ok || !identity_ok || !image_ok) begin
                    fault <= 1;
                    fault_cause <= {!image_ok, !identity_ok, !descriptor_ok};
                end else begin
                    accepted <= 1;
                    accepted_command <= command_q;
                end
            end
            for (integer k = 0; k < 3; k = k + 1)
                if (valid_c[k] && take) accepted_tag[16*k +: 16] <= tag_q[16*k +: 16];
            if (valid_c[3] && take) accepted_tag[58:48] <= tag_q[58:48];
        end
    end
    assign native_xbase = accepted_command[175:152];
    assign native_obase = accepted_command[303:280];
    assign native_nout = accepted_command[18:1];
    assign native_k = accepted_command[54:37];
    assign native_position = {5'd0,accepted_tag[18:6]};
    assign native_epoch = accepted_tag[58:43];
    assign native_layer = accepted_tag[42:37] - 6'd1;
endmodule
