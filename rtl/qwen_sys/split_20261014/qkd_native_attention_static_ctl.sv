`timescale 1ns/1ps
// One compiler-loaded operation. No queue, ready-based issue, runtime credits,
// local epoch allocation, compute or memory emulation. Link codec and native59
// guard are actual source instances. The service pins must bind to the actual
// w16 native service; this module cannot supply missing arithmetic/memory.
// Timing: run edge is age 0. RX CMD at age RX_CMD; Q at RX_CMD+1..+32.
// Codec CMD appears one edge later. Q has one additional register so service
// samples Q beat0 two edges after request, as its start_qk/q_window require.
// RESULT age TX_FIRST..+31 and idle +32, STATUS +33 are TX codec input events; STATUS carries the namespace
// word {q_ready 0, done, fault, busy 0, ready} (qkd_native_status_word).
// KV-ATTNKIT 10-18 (qkd_kvs_attn-g1 EARLY_FAIL_SETUP TT -480.8 ps, 2,413 endpoints: 94% d2d rx_payload -> the codec's
// 548-bit record check -> the capture enables of 1,100 flops, i.e. logic between the tile pins and the first flop; plus
// the fault OR gating tx_valid AFTER its flop and the run/age update).  LAND=1 (opt-in, die knob OT_KV_ATTN_LAND):
//  * the codec is qkd_native_attention_record_ld: the RX pins land straight in flops, the checks run one edge later on
//    the landed copy and the outputs are corrected combinationally -- rx_valid / rx fields / fault / fault_cause /
//    tx_valid are edge-for-edge the original's (no added RX latency);
//  * tx_valid / tx_payload leave through a launch flop pair (tile pin = flop): +1 edge on the K.tx_record bundle;
//  * the run edge updates busy / age / loaded independently of fault (fault still sets local_fault): differs only
//    after fault is set, when every tile output it could touch is fault-gated (tx_valid, request_valid, q_valid).
// MUT (bench, LAND=1): 4 = the TX launch flop drops the fault gate; 5 / 6 = codec MUT 3 / 4 (qkd_native_attention_record_ld).
module qkd_native_attention_static_ctl #(
 parameter integer MUT=0,
 parameter integer LAND=0
)(
 input wire ck,rst_n,
 input wire load,run,
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
 output wire request_valid,input wire request_ready,
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
 qkd_native59_command_guard guard(.ck(ck),.rst_n(rst_n),.command_valid(load),
  .command(command),.command_tag(command_tag),.fused_program_capability(fused_program_capability),
  .authority_valid(authority_valid),.authority_epoch(authority_epoch),.authority_token(authority_token),
  .authority_position(authority_position),.authority_stage(authority_stage),.accepted(accepted),
  .accepted_command(ac),.accepted_tag(at),.native_xbase(),.native_obase(),.native_nout(),.native_k(),
  .native_position(pos),.native_epoch(ep),.native_layer(layer),.fault(guard_fault),.fault_cause());
 reg loaded,local_fault,loading;reg [175:0] cal;
 reg [15:0] rx_cmd,tx_first,last;
 // age: run selects between two kept candidates, so the run pin is one mux from the age flops (KV-ATTNKIT g2: i_ctl
 // run -> age 10 levels).  Same function as 'if(run){if(ok)age<=0} else if(busy)age<=age+1'.
 wire run_ok=(LAND!=0)?(loaded&&!busy):!(!loaded||busy||fault);
 (* keep *) wire [15:0] age_hold=busy?age+16'd1:age;
 (* keep *) wire [15:0] age_run=run_ok?16'd0:age;
 wire [15:0] age_nx=run?age_run:age_hold;
 // Guard consumes the registered descriptor one edge after load. Keep the
 // compiled values with that descriptor, independently of link record fields.
 always @(posedge ck or negedge rst_n)begin
  if(!rst_n)begin loaded<=0;loading<=0;local_fault<=0;busy<=0;age<=0;cal<=0;rx_cmd<=0;tx_first<=0;last<=0;end
  else begin
   age<=age_nx;
   if(load)begin
    if(busy||loading||loaded||compiled_rx_cmd<2||compiled_tx_first<=compiled_rx_cmd+34||compiled_end!=compiled_tx_first+34)
     local_fault<=1;
    cal<=compiled_calendar;rx_cmd<=compiled_rx_cmd;tx_first<=compiled_tx_first;last<=compiled_end;
    loading<=1;
   end
   if(accepted)begin loaded<=1;loading<=0;end
   if(run)begin
    if(!loaded||busy||fault)local_fault<=1;
    if(run_ok)begin busy<=1;loaded<=0;end
   end else if(busy)begin
    if(age==last)busy<=0;
   end
   if(request_valid&&!request_ready)local_fault<=1;
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
 wire status_slot=busy&&age==tx_first+33;
 assign result_reserved=busy&&age>=tx_first&&age<tx_first+32;
 wire rx_valid;wire [3:0] rx_kind;wire [4:0] rx_beat;wire [511:0] rx_data;wire record_fault;wire codec_tx_valid;
 // STATUS (age TX_FIRST+33): the namespace word {q_ready, done, fault, busy, ready} (QXF-LINK F2; was 512'd0, which the
 // compute consumer rejects: it completes only on done).  done = result_done seen on its compiled age TX_FIRST+32;
 // the operation holds no Q / work after its last RESULT (q_ready 0, busy 0); ready = it can take the next load.
 // MUT 3 (bench): the legacy all-zero STATUS word.
 reg done_seen;
 always @(posedge ck or negedge rst_n)
  if(!rst_n)done_seen<=0;
  else if(run)done_seen<=0;
  else if(busy&&age==tx_first+32&&result_done)done_seen<=1;
 wire [511:0] status_data;
 qkd_native_status_word u_status(.q_ready(1'b0),.done(done_seen),.fault(fault),.busy(1'b0),.ready(done_seen&&!fault),.word(status_data));
 wire [511:0] tx_data=status_slot?((MUT==3)?512'd0:status_data):result_data;
 wire [547:0] codec_tx_payload;
 generate if(LAND!=0)begin:g_ld
 qkd_native_attention_record_ld #(.MUT(MUT==5?3:(MUT==6?4:0))) codec(.ck(ck),.rst_n(rst_n),
  .tx_event(result_valid||status_slot),.tx_expected(tx_expected),.tx_kind(status_slot?4'd4:4'd3),
  .tx_expected_kind(status_slot?4'd4:4'd3),.tx_epoch(ep),.tx_expected_epoch(ep),
  .tx_layer(layer),.tx_expected_layer(layer),.tx_beat(status_slot?5'd0:result_beat),
  .tx_expected_beat(status_slot?5'd0:result_expected_beat),.tx_data(tx_data),.tx_valid(codec_tx_valid),.tx_payload(codec_tx_payload),
  .rx_event(rx_event),.rx_expected(MUT==1?rx_event:rx_expected),.rx_payload(rx_payload),
  .rx_expected_kind(rx_kind_expected),.rx_expected_epoch(ep),.rx_expected_layer(layer),
  .rx_expected_beat(age==rx_cmd?5'd0:rb),.rx_valid(rx_valid),.rx_kind(rx_kind),
  .rx_epoch(),.rx_layer(),.rx_beat(rx_beat),.rx_data(rx_data),.fault(record_fault),.fault_cause());
 end else begin:g_cd
 qkd_native_attention_record codec(.ck(ck),.rst_n(rst_n),
  .tx_event(result_valid||status_slot),.tx_expected(tx_expected),.tx_kind(status_slot?4'd4:4'd3),
  .tx_expected_kind(status_slot?4'd4:4'd3),.tx_epoch(ep),.tx_expected_epoch(ep),
  .tx_layer(layer),.tx_expected_layer(layer),.tx_beat(status_slot?5'd0:result_beat),
  .tx_expected_beat(status_slot?5'd0:result_expected_beat),.tx_data(tx_data),.tx_valid(codec_tx_valid),.tx_payload(codec_tx_payload),
  .rx_event(rx_event),.rx_expected(MUT==1?rx_event:rx_expected),.rx_payload(rx_payload),
  .rx_expected_kind(rx_kind_expected),.rx_expected_epoch(ep),.rx_expected_layer(layer),
  .rx_expected_beat(age==rx_cmd?5'd0:rb),.rx_valid(rx_valid),.rx_kind(rx_kind),
  .rx_epoch(),.rx_layer(),.rx_beat(rx_beat),.rx_data(rx_data),.fault(record_fault),.fault_cause());
 end endgenerate
 reg slot_fault;
 // LAND: the TX slot pins (d2d att_tx_slot / kind / beat) land in flops with their expectation; the check runs one edge
 // later and slot_fault_o = slot_fault | that check (= the original sticky flop, edge for edge)
 reg ls_slot,ls_exp;reg [8:0] ls_kb,ls_ekb;
 always @(posedge ck or negedge rst_n)
  if(!rst_n)begin ls_slot<=0;ls_exp<=0;ls_kb<=0;ls_ekb<=0;end
  else begin ls_slot<=tx_slot;ls_exp<=tx_expected;ls_kb<={tx_slot_kind,tx_slot_beat};
   ls_ekb<={status_slot?4'd4:4'd3,status_slot?5'd0:result_expected_beat};end
 wire slot_chk=(LAND!=0)&&(ls_slot!=ls_exp||(ls_slot&&ls_kb!=ls_ekb));
 wire slot_fault_o=slot_fault||slot_chk;
 always @(posedge ck or negedge rst_n)begin
  if(!rst_n)begin q_valid<=0;q_beat<=0;q_data<=0;slot_fault<=0;end
  else begin
   q_valid<=!fault&&rx_valid&&rx_kind==2;q_beat<=rx_beat;q_data<=rx_data;
   if(LAND==0&&(tx_slot!=tx_expected||(tx_slot&&{tx_slot_kind,tx_slot_beat}!={status_slot?4'd4:4'd3,status_slot?5'd0:result_expected_beat})))slot_fault<=1;
   if(LAND!=0&&slot_chk)slot_fault<=1;
  end
 end
 generate if(LAND!=0)begin:g_txl
  reg tx_v_l;reg [547:0] tx_p_l;
  always @(posedge ck or negedge rst_n)if(!rst_n)tx_v_l<=0;else tx_v_l<=codec_tx_valid&&(MUT==4||!fault);
  always @(posedge ck)tx_p_l<=codec_tx_payload;
  assign tx_valid=tx_v_l;assign tx_payload=tx_p_l;
 end else begin:g_txc
  assign tx_valid=codec_tx_valid&&!fault;assign tx_payload=codec_tx_payload;
 end endgenerate
 assign request_valid=rx_valid&&rx_kind==1&&!fault;
 assign request_epoch=ep;assign request_layer=layer;assign request_position=pos;assign request_calendar=cal;
 assign fault=local_fault||guard_fault||record_fault||slot_fault_o||service_fault;
endmodule

// KV-ATTNKIT 10-18: qkd_native_attention_record with a LANDED RX face (qkd_native_attention_static_ctl LAND=1).
// The original evaluates the 548-bit RX record check (legal(): a 493-bit zero test, direction, expected kind / epoch /
// layer / beat) on the PINS and uses the result as the capture enable of every rx / tx register.  Here the RX pins and
// the RX expectations go straight into flops on the original capture edge (the landing: no logic, no enable on the
// payload), the TX check bits are registered on the same edge, and the check runs one edge later on the landed copy.
// With bad = the check of edge e, evaluated on the landed copy after e, and f_r / c_r = fault / fault_cause of the
// previous cycle:
//   fault = f_r | bad,  fault_cause = f_r ? c_r : {rx_record_bad, tx_record_bad, rx_time_bad, tx_time_bad},
//   tx_valid = (tx_event & !fault)@e & !bad,  rx_valid = rx_event@e & !f_r & !bad
// = the original's values edge for edge (it sets fault / cause on e when bad and holds both after; valids only when
// neither).  The rx fields are the landed payload (equal to the original whenever rx_valid; free otherwise), tx_payload
// loads on tx_event & !fault (the original also requires !bad: differs only on the bad edge, after which fault holds
// and every valid is 0).  No added RX latency: rx_valid / rx fields appear on the original edge.
// MUT (bench negative controls): 1 / 2 as the original (no time check / no expected compare); 3 = the landed event is
// checked against the CURRENT expectation (one edge misaligned); 4 = fault shows the deferred check one edge late
// (fault = f_r: the gating the landing must preserve).
module qkd_native_attention_record_ld #(
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
    output reg fault,output reg [3:0] fault_cause
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
    // TX check bits: internal operands, evaluated on the original edge and registered with the landing
    wire tx_time_bad=MUT!=1 && tx_event!=tx_expected;
    wire tx_record_bad=tx_event && (!legal(tx_kind,tx_layer,tx_beat,tx_data)||!direction(tx_kind,1'b1)||
        (MUT!=2 && {tx_kind,tx_epoch,tx_layer,tx_beat}!={tx_expected_kind,tx_expected_epoch,tx_expected_layer,tx_expected_beat}));
    reg l_ev,l_exp;reg [3:0] l_ek;reg [15:0] l_ee;reg [5:0] l_el;reg [4:0] l_eb;
    reg [547:0] l_pl;
    reg t_time_bad,t_record_bad,f_r,txv_r;reg [3:0] c_r;
    wire [3:0] rk=l_pl[542:539];
    wire [5:0] rl=l_pl[538:533];
    wire [15:0] re=l_pl[532:517];
    wire [4:0] rb=l_pl[516:512];
    wire rx_time_bad=MUT!=1 && l_ev!=((MUT==3)?rx_expected:l_exp);
    wire rx_record_bad=l_ev && (l_pl[547:543]!=0||!legal(rk,rl,rb,l_pl[511:0])||!direction(rk,1'b0)||
        (MUT!=2 && {rk,re,rl,rb}!={l_ek,l_ee,l_el,l_eb}));
    wire [3:0] bits={rx_record_bad,t_record_bad,rx_time_bad,t_time_bad};
    wire bad=|bits;
    always @* begin
        fault=f_r|((MUT==4)?1'b0:bad);
        fault_cause=f_r?c_r:bits;
        tx_valid=txv_r&&!bad;
        rx_valid=l_ev&&!f_r&&!bad;
        rx_kind=rk;rx_epoch=re;rx_layer=rl;rx_beat=rb;rx_data=l_pl[511:0];
    end
    always @(posedge ck or negedge rst_n)begin
        if(!rst_n)begin
            l_ev<=0;l_exp<=0;l_ek<=0;l_ee<=0;l_el<=0;l_eb<=0;t_time_bad<=0;t_record_bad<=0;f_r<=0;c_r<=0;txv_r<=0;
        end else begin
            l_ev<=rx_event;l_exp<=rx_expected;l_ek<=rx_expected_kind;l_ee<=rx_expected_epoch;l_el<=rx_expected_layer;
            l_eb<=rx_expected_beat;t_time_bad<=tx_time_bad;t_record_bad<=tx_record_bad;
            f_r<=f_r|bad;c_r<=fault_cause;txv_r<=tx_event&&!fault;
        end
    end
    // the landing flops (payload) and the TX record register: no reset, no logic before the payload flop
    always @(posedge ck)begin
        l_pl<=rx_payload;
        if(tx_event&&!fault)tx_payload<={5'd0,tx_kind,tx_layer,tx_epoch,tx_beat,tx_data};
    end
endmodule
