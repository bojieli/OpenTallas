`timescale 1ns/1ps
// Four actual restored NC8 rows reserved before a no-ready W2 launch.
// Provider write ACK and complete payload readback precede visible completion.
// Root POR only: local CP reset never discards accepted result/provider debt.
module ot_hbm_integrated_w2_result_sink #(
 parameter integer ENABLE=0,
 parameter integer REGISTERED_SUBBLOCKS=0,
 parameter integer PROTECTED_TRANSACTION_PIPELINE=0
)(
 input wire clk,por_n,owned,installed,
 input wire reserve_v,output wire reserve_r,
 input wire pair_op,input wire [1:0] rows_a,rows_b,
 input wire [31:0] op_a,op_b,base_a,limit_a,base_b,limit_b,
 input wire [15:0] provider_tag,
 input wire [72:0] frame,
 output wire source_permit,retained,done,quiet,fault,
 input wire result_v,input wire [31:0] result_op,
 input wire [11:0] result_row,input wire [255:0] result_data,
 input wire native_done,retire_v,output wire retire_r,
 output wire req_v,input wire req_r,output wire [336:0] req,
 input wire rsp_v,output wire rsp_r,input wire [272:0] rsp
);
 generate if(!ENABLE)begin:off
 assign reserve_r=0;assign source_permit=0;assign retained=0;
 assign done=0;assign quiet=1;assign fault=0;assign retire_r=0;
 assign req_v=0;assign req=0;assign rsp_r=0;
 end else if(PROTECTED_TRANSACTION_PIPELINE)begin:transaction_pipeline
 ot_hbm_w2_sink_transaction_pipeline u_pipe(.*);
 end else if(REGISTERED_SUBBLOCKS)begin:registered_subblocks
 // Historical rejected hardware candidate: enrolled SS -733.090149ps.
 // W6 immutable/captured rows are checked before they enter protected views.
 // Live control and views use triplication with per-byte parity. One damaged
 // copy is voted and scrubbed; two parity-invalid copies veto all handshakes.
 localparam [3:0] IDLE=0,META_CHECK=1,CAPTURE=2,PAYLOAD_CHECK=3,
  BUILD_WRITE=4,WRITE=5,WAIT_WRITE=6,BUILD_READ=7,READ=8,
  WAIT_READ=9,COMPARE=10,DONE=11,FAIL=12;
 reg [71:0] metadata[0:7],payload_code[0:15];
 wire [65:0] md[0:7];wire [511:0] metadata_checked;
 wire [7:0] metadata_ue;
 for(genvar k=0;k<8;k=k+1)begin:metadata_decoder
  assign md[k]=ot_gpu_w6_secded_pkg::decode64(metadata[k]);
  assign metadata_checked[k*64+:64]=md[k][63:0];
  assign metadata_ue[k]=md[k][65];
 end
 wire [31:0] ctl;reg [31:0] ctl_next;
 wire ctl_bad,meta_bad,payload_bad,request_bad,response_bad,frame_bad;
 wire [72:0] reserved_frame;
 wire [511:0] meta;
 wire [255:0] checked_payload,checked_response;
 wire [336:0] held_request;
 wire [3:0] state=ctl[3:0],seen=ctl[7:4],verified=ctl[11:8];
 wire [1:0] slot=ctl[13:12];wire native_finished=ctl[14];
 wire [72:0] held_frame={meta[64+:9],meta[0+:64]};
 wire [31:0] held_a=meta[128+:32],held_b=meta[160+:32];
 wire [31:0] a_base=meta[192+:32],b_base=meta[320+:32];
 wire [1:0] na=meta[448+:2],nb=meta[450+:2];
 wire held_pair=meta[452];wire [15:0] tag=meta[453+:16];
 wire [3:0] expected=(4'b0011>>(2-na)) |
                         (held_pair?((4'b0011>>(2-nb))<<2):4'b0);
 wire shape=rows_a>=1&&rows_a<=2&&(!pair_op||(rows_b>=1&&rows_b<=2&&op_a!=op_b))&&
  base_a[5:0]==0&&limit_a>base_a&&({1'b0,base_a}+33'(rows_a)*33'd32<={1'b0,limit_a})&&
  (!pair_op||(base_b[5:0]==0&&limit_b>base_b&&
    ({1'b0,base_b}+33'(rows_b)*33'd32<={1'b0,limit_b})&&
    (limit_a<=base_b||limit_b<=base_a)));
 // The reservation frame has its own protected capture on the reserve edge;
 // foreign frame/owner/installation vetoes even during metadata checking.
 wire context_ok=owned&&installed&&
                  (state==IDLE||frame==reserved_frame);
 wire active=state!=IDLE&&state!=META_CHECK&&state!=DONE&&state!=FAIL;
 assign fault=ctl_bad||meta_bad||payload_bad||request_bad||response_bad||frame_bad||
              state==FAIL||(state!=IDLE&&!context_ok);
 assign retained=state!=IDLE;
 assign reserve_r=state==IDLE&&owned&&installed&&shape&&!fault;
 assign source_permit=active&&!native_finished&&!fault;
 assign done=state==DONE&&!fault;
 assign quiet=state==IDLE&&!fault;
 assign retire_r=done&&owned;
 wire belongs_a=result_op==held_a,belongs_b=held_pair&&result_op==held_b;
 wire result_shape=(belongs_a&&result_row<na)||(belongs_b&&result_row<nb);
 wire [1:0] result_slot=(belongs_b?2'd2:2'd0)+result_row[1:0];
 wire [3:0] result_mask=4'b1<<result_slot;
 wire capture_result=result_v&&active&&result_shape&&!(|(seen&result_mask))&&!fault;
 wire [65:0] pd[0:3];wire [255:0] payload_decoded;
 wire [3:0] payload_ue;
 for(genvar k=0;k<4;k=k+1)begin:payload_decoder
  assign pd[k]=ot_gpu_w6_secded_pkg::decode64(payload_code[4*integer'(slot)+k]);
  assign payload_decoded[k*64+:64]=pd[k][63:0];
  assign payload_ue[k]=pd[k][65];
 end
 wire [31:0] address=(slot[1]?b_base:a_base)+{26'b0,slot[0],5'b0};
 wire [336:0] request_next=state==BUILD_READ?
    {1'b0,held_request[335:48],32'b0,held_request[15:0]}:
    {1'b1,address,checked_payload,32'hffffffff,tag};
 assign req=held_request;
 assign req_v=(state==WRITE||state==READ)&&!fault;
 wire response_match=rsp[272:257]==held_request[15:0]&&rsp[256]==(state==WAIT_WRITE);
 assign rsp_r=(state==WAIT_WRITE||state==WAIT_READ)&&response_match&&!fault;
 wire accept_response=rsp_v&&rsp_r;
 ot_hbm_w2_sink_protected_view #(.WIDTH(73)) reservation_frame_view(
  .clk(clk),.por_n(por_n),.we(reserve_v&&reserve_r),
  .next_data(frame),.data(reserved_frame),.fault(frame_bad));
 ot_hbm_w2_sink_protected_view #(.WIDTH(32)) control_view(
  .clk(clk),.por_n(por_n),.we(1'b1),.next_data(ctl_next),.data(ctl),.fault(ctl_bad));
 ot_hbm_w2_sink_protected_view #(.WIDTH(512)) metadata_view(
  .clk(clk),.por_n(por_n),.we(state==META_CHECK&&!fault&&!(|metadata_ue)),
  .next_data(metadata_checked),.data(meta),.fault(meta_bad));
 ot_hbm_w2_sink_protected_view #(.WIDTH(256)) payload_view(
  .clk(clk),.por_n(por_n),.we(state==PAYLOAD_CHECK&&!fault&&!(|payload_ue)),
  .next_data(payload_decoded),.data(checked_payload),.fault(payload_bad));
 ot_hbm_w2_sink_protected_view #(.WIDTH(337)) request_view(
  .clk(clk),.por_n(por_n),.we((state==BUILD_WRITE||state==BUILD_READ)&&!fault),
  .next_data(request_next),.data(held_request),.fault(request_bad));
 ot_hbm_w2_sink_protected_view #(.WIDTH(256)) response_view(
  .clk(clk),.por_n(por_n),.we(accept_response&&state==WAIT_READ),
  .next_data(rsp[255:0]),.data(checked_response),.fault(response_bad));
 reg [3:0] available;integer next_slot;
 always @*begin
  ctl_next=ctl;available=seen&~verified;next_slot=0;
  for(integer k=3;k>=0;k=k-1)if(available[k])next_slot=k;
  if(capture_result)ctl_next[7:4]=seen|result_mask;
  if(native_done&&active)ctl_next[14]=1;
  case(state)
   IDLE:if(reserve_v&&reserve_r)ctl_next=32'(META_CHECK);
   META_CHECK:ctl_next[3:0]=((|metadata_ue)||{metadata_checked[64+:9],metadata_checked[0+:64]}!=reserved_frame)?FAIL:CAPTURE;
   CAPTURE:if(|available)begin ctl_next[3:0]=PAYLOAD_CHECK;ctl_next[13:12]=2'(next_slot);end
    else if(native_finished&&seen==expected&&verified==expected)ctl_next[3:0]=DONE;
   PAYLOAD_CHECK:ctl_next[3:0]=(|payload_ue)?FAIL:BUILD_WRITE;
   BUILD_WRITE:ctl_next[3:0]=WRITE;
   WRITE:if(req_v&&req_r)ctl_next[3:0]=WAIT_WRITE;
   WAIT_WRITE:if(accept_response)ctl_next[3:0]=BUILD_READ;
   BUILD_READ:ctl_next[3:0]=READ;
   READ:if(req_v&&req_r)ctl_next[3:0]=WAIT_READ;
   WAIT_READ:if(accept_response)ctl_next[3:0]=COMPARE;
   COMPARE:if(checked_response!=checked_payload)ctl_next[3:0]=FAIL;
    else begin ctl_next[11:8]=verified|(4'b1<<slot);ctl_next[3:0]=CAPTURE;end
   DONE:if(retire_v&&retire_r)ctl_next=0;
   default:begin end
  endcase
  if(fault||(reserve_v&&state==IDLE&&!reserve_r)||
     (result_v&&(!active||!result_shape|||(seen&result_mask)))||
     (native_done&&active&&((seen|(result_v?result_mask:4'b0))!=expected))||
     (rsp_v&&(state!=WAIT_WRITE&&state!=WAIT_READ||!response_match)))
   ctl_next[3:0]=FAIL;
 end
 always @(posedge clk or negedge por_n)begin
  if(!por_n)begin
   for(integer k=0;k<8;k=k+1)metadata[k]<=ot_gpu_w6_secded_pkg::encode64(0);
   for(integer k=0;k<16;k=k+1)payload_code[k]<=ot_gpu_w6_secded_pkg::encode64(0);
  end else begin
   if(reserve_v&&reserve_r)begin
    metadata[0]<=ot_gpu_w6_secded_pkg::encode64(frame[63:0]);
    metadata[1]<=ot_gpu_w6_secded_pkg::encode64({55'b0,frame[72:64]});
    metadata[2]<=ot_gpu_w6_secded_pkg::encode64({op_b,op_a});
    metadata[3]<=ot_gpu_w6_secded_pkg::encode64({32'b0,base_a});
    metadata[4]<=ot_gpu_w6_secded_pkg::encode64({32'b0,limit_a});
    metadata[5]<=ot_gpu_w6_secded_pkg::encode64({32'b0,base_b});
    metadata[6]<=ot_gpu_w6_secded_pkg::encode64({32'b0,limit_b});
    metadata[7]<=ot_gpu_w6_secded_pkg::encode64({43'b0,provider_tag,pair_op,rows_b,rows_a});
   end
   if(capture_result)for(integer k=0;k<4;k=k+1)
    payload_code[4*integer'(result_slot)+k]<=ot_gpu_w6_secded_pkg::encode64(result_data[k*64+:64]);
  end
 end
 end else begin:on
 localparam [2:0] IDLE=0,CAPTURE=1,WRITE=2,WAIT_WRITE=3,READ=4,WAIT_READ=5,DONE=6,FAIL=7;
 // metadata: frame2, original operation IDs1, extents4, shape/tag1.
 // payload4*4 protected words; control1. No result-ready substituted for rv.
 reg [71:0] code[0:24];
 wire [65:0] decoded[0:24];wire [63:0] data[0:24];
 wire [24:0] uncorrectable;
 for(genvar k=0;k<25;k=k+1)begin:protected_rows
  assign decoded[k]=ot_gpu_w6_secded_pkg::decode64(code[k]);
  assign data[k]=decoded[k][63:0];assign uncorrectable[k]=decoded[k][65];
 end
 wire [2:0] state=data[24][2:0];
 wire [3:0] seen=data[24][6:3],verified=data[24][10:7];
 wire [1:0] slot=data[24][12:11];wire native_finished=data[24][13];
 wire [72:0] held_frame={data[1][8:0],data[0]};
 wire [31:0] held_a=data[2][31:0],held_b=data[2][63:32];
 wire [31:0] a_base=data[3][31:0],a_limit=data[4][31:0];
 wire [31:0] b_base=data[5][31:0],b_limit=data[6][31:0];
 wire [1:0] na=data[7][1:0],nb=data[7][3:2];
 wire held_pair=data[7][4];wire [15:0] tag=data[7][20:5];
 wire [3:0] expected=(4'b0011>>(2-na)) |
                         (held_pair?((4'b0011>>(2-nb))<<2):4'b0);
 wire source_context=frame==held_frame&&owned;
 wire shape=rows_a>=1&&rows_a<=2&&(!pair_op||(rows_b>=1&&rows_b<=2&&op_a!=op_b))&&
  base_a[5:0]==0&&limit_a>base_a&&({1'b0,base_a}+33'(rows_a)*33'd32<={1'b0,limit_a})&&
  (!pair_op||(base_b[5:0]==0&&limit_b>base_b&&
    ({1'b0,base_b}+33'(rows_b)*33'd32<={1'b0,limit_b})&&
    (limit_a<=base_b||limit_b<=base_a)));
 wire active=state!=IDLE&&state!=DONE&&state!=FAIL;
 assign fault=(|uncorrectable)||state==FAIL||
              (state!=IDLE&&(!source_context||!installed));
 assign retained=state!=IDLE;
 assign reserve_r=state==IDLE&&owned&&installed&&shape&&!fault;
 assign source_permit=active&&!native_finished&&!fault;
 assign done=state==DONE&&!fault;
 assign quiet=state==IDLE&&!fault;
 assign retire_r=done&&owned;
 wire belongs_a=result_op==held_a;
 wire belongs_b=held_pair&&result_op==held_b;
 wire result_shape=(belongs_a&&result_row<na)||(belongs_b&&result_row<nb);
 wire [1:0] result_slot=(belongs_b?2'd2:2'd0)+result_row[1:0];
 wire [3:0] result_mask=4'b1<<result_slot;
 wire [255:0] payload={data[8+4*integer'(slot)+3],data[8+4*integer'(slot)+2],
                      data[8+4*integer'(slot)+1],data[8+4*integer'(slot)]};
 wire [31:0] address=(slot[1]?b_base:a_base)+{26'b0,slot[0],5'b0};
 assign req_v=(state==WRITE||state==READ)&&!fault;
 assign req={state==WRITE,address,payload,state==WRITE?32'hffffffff:32'b0,tag};
 wire response_match=rsp[272:257]==tag&&rsp[256]==(state==WAIT_WRITE);
 assign rsp_r=(state==WAIT_WRITE||state==WAIT_READ)&&response_match&&!fault;
 reg [63:0] control_next;
 reg [3:0] available;integer next_slot;
 always @*begin
  control_next=data[24];available=seen&~verified;next_slot=0;
  for(integer k=3;k>=0;k=k-1)if(available[k])next_slot=k;
  if(result_v&&active)control_next[6:3]=seen|result_mask;
  if(native_done&&active)control_next[13]=1;
  case(state)
   CAPTURE:if(|available)begin control_next[2:0]=WRITE;control_next[12:11]=2'(next_slot);end
    else if(native_finished&&seen==expected&&verified==expected)control_next[2:0]=DONE;
   WRITE:if(req_v&&req_r)control_next[2:0]=WAIT_WRITE;
   WAIT_WRITE:if(rsp_v&&rsp_r)control_next[2:0]=READ;
   READ:if(req_v&&req_r)control_next[2:0]=WAIT_READ;
   WAIT_READ:if(rsp_v&&rsp_r)begin
    if(rsp[255:0]!=payload)control_next[2:0]=FAIL;
    else begin control_next[10:7]=verified|(4'b1<<slot);control_next[2:0]=CAPTURE;end
   end
   DONE:if(retire_v&&retire_r)control_next=0;
   default:begin end
  endcase
  if(fault||(reserve_v&&state==IDLE&&!reserve_r)||
     (result_v&&(!active||!result_shape|||(seen&result_mask)))||
     (native_done&&active&&((seen|(result_v?result_mask:4'b0))!=expected))||
     (rsp_v&&(state!=WAIT_WRITE&&state!=WAIT_READ||!response_match)))
   control_next[2:0]=FAIL;
 end
 always @(posedge clk or negedge por_n)begin
  if(!por_n)for(integer k=0;k<25;k=k+1)code[k]<=ot_gpu_w6_secded_pkg::encode64(0);
  else begin
   code[24]<=ot_gpu_w6_secded_pkg::encode64(control_next);
   if(reserve_v&&reserve_r)begin
    code[0]<=ot_gpu_w6_secded_pkg::encode64(frame[63:0]);
    code[1]<=ot_gpu_w6_secded_pkg::encode64({55'b0,frame[72:64]});
    code[2]<=ot_gpu_w6_secded_pkg::encode64({op_b,op_a});
    code[3]<=ot_gpu_w6_secded_pkg::encode64({32'b0,base_a});
    code[4]<=ot_gpu_w6_secded_pkg::encode64({32'b0,limit_a});
    code[5]<=ot_gpu_w6_secded_pkg::encode64({32'b0,base_b});
    code[6]<=ot_gpu_w6_secded_pkg::encode64({32'b0,limit_b});
    code[7]<=ot_gpu_w6_secded_pkg::encode64({43'b0,provider_tag,pair_op,rows_b,rows_a});
    code[24]<=ot_gpu_w6_secded_pkg::encode64(64'(CAPTURE));
   end
   if(result_v&&active&&result_shape&&!(|(seen&result_mask))&&!fault)
    for(integer k=0;k<4;k=k+1)
     code[8+4*integer'(result_slot)+k]<=ot_gpu_w6_secded_pkg::encode64(result_data[k*64+:64]);
  end
 end
 end endgenerate
endmodule

// Registered views: triplicated data plus independent parity per eight bits.
// No unprotected authoritative shadow. Vote a single damaged copy and scrub;
// two odd-error copies in any byte are fail-closed rather than majority-used.
module ot_hbm_w2_sink_protected_view #(parameter integer WIDTH=32)(
 input wire clk,por_n,we,input wire [WIDTH-1:0] next_data,
 output wire [WIDTH-1:0] data,output wire fault
);
 localparam integer BYTES=(WIDTH+7)/8, PAD=BYTES*8;
 reg [PAD-1:0] a,b,c;reg [BYTES-1:0] pa,pb,pc;
 wire [PAD-1:0] vote=(a&b)|(a&c)|(b&c);
 wire [PAD-1:0] padded={{(PAD-WIDTH){1'b0}},next_data};
 wire [BYTES-1:0] bad,parity;
 for(genvar k=0;k<BYTES;k=k+1)begin:byte_check
  wire ea=(^a[k*8+:8])!=pa[k],eb=(^b[k*8+:8])!=pb[k],ec=(^c[k*8+:8])!=pc[k];
  assign bad[k]=(ea&&eb)||(ea&&ec)||(eb&&ec);
  assign parity[k]=^padded[k*8+:8];
 end
 assign data=vote[WIDTH-1:0];assign fault=|bad;
 always @(posedge clk or negedge por_n)begin
  if(!por_n)begin a<=0;b<=0;c<=0;pa<=0;pb<=0;pc<=0;end
  else if(we&&!fault)begin a<=padded;b<=padded;c<=padded;pa<=parity;pb<=parity;pc<=parity;end
  else if(!fault)begin
   a<=vote;b<=vote;c<=vote;
   for(integer k=0;k<BYTES;k=k+1)begin
    pa[k]<=^vote[k*8+:8];pb[k]<=^vote[k*8+:8];pc[k]<=^vote[k*8+:8];
   end
  end
 end
endmodule

// One finite protected transaction pipeline. Every stored authority is W6.
// Normal data extraction has no correction mux. CE service holds all external
// permissions and accepted debt through snapshot/mask/apply/recheck/scrub.
module ot_hbm_w2_sink_transaction_pipeline(
 input wire clk,por_n,owned,installed,
 input wire reserve_v,output wire reserve_r,
 input wire pair_op,input wire [1:0] rows_a,rows_b,
 input wire [31:0] op_a,op_b,base_a,limit_a,base_b,limit_b,
 input wire [15:0] provider_tag,input wire [72:0] frame,
 output wire source_permit,retained,done,quiet,fault,
 input wire result_v,input wire [31:0] result_op,
 input wire [11:0] result_row,input wire [255:0] result_data,
 input wire native_done,retire_v,output wire retire_r,
 output wire req_v,input wire req_r,output wire [336:0] req,
 input wire rsp_v,output wire rsp_r,input wire [272:0] rsp
);
 import ot_gpu_w6_secded_pkg::*;
 // Sized in hbm_w2_publication_model before RTL. Four arrival seats, not a
 // second owner/GO ledger. Canonical row identity is checked after selection.
 localparam integer NW=78, CTRL=71, FINISH=72, CE_CTL=73;
 localparam [5:0] IDLE=0,META=1,CAPTURE=2,SYNDROME=3,CHECK=4,
  CHECKED_CAPTURE=5,BUILD_WRITE=6,WRITE=7,WAIT_WRITE=8,ACK_FENCE=9,
  BUILD_READ=10,READ=11,WAIT_READ=12,RESPONSE_CHECK=13,
  VERIFIED_FENCE=14,COMPLETION_FENCE=15,DONE=16,FAIL=17;
 reg [71:0] code[0:NW-1];
 wire [63:0] data[0:NW-1];wire [7:0] syndrome[0:NW-1];
 wire [NW-1:0] ce,ue;
 function automatic [63:0] extract64(input [71:0] c);
  integer p,j;begin j=0;extract64=0;
   for(p=1;p<=71;p=p+1)if((p&(p-1))!=0)begin extract64[j]=c[p-1];j=j+1;end
  end
 endfunction
 function automatic [7:0] check72(input [71:0] c);
  integer p,k;begin check72=0;check72[7]=^c;
   for(k=0;k<7;k=k+1)for(p=1;p<=71;p=p+1)
    if((p&(1<<k))!=0)check72[k]=check72[k]^c[p-1];
  end
 endfunction
 for(genvar k=0;k<NW;k=k+1)begin:words
  assign data[k]=extract64(code[k]);assign syndrome[k]=check72(code[k]);
  assign ue[k]=(syndrome[k][6:0]!=0)&&(!syndrome[k][7]||syndrome[k][6:0]>71);
  assign ce[k]=syndrome[k][7]&&syndrome[k][6:0]<=71;
 end
 wire any_ue=|ue,any_ce=|ce;
 wire repair_record_ok=!(|ce[77:73])&&!(|ue[77:73]);
 wire normal=!(any_ue||any_ce)&&data[CE_CTL][2:0]==0;
 wire ctl_ok=!ce[CTRL]&&!ue[CTRL];
 wire [5:0] state=data[CTRL][5:0];
 wire [3:0] seen=data[CTRL][9:6],verified=data[CTRL][13:10];
 wire [1:0] slot=data[CTRL][15:14],seat=data[CTRL][17:16];
 wire finished=data[FINISH][0];
 wire [72:0] reserved_frame={data[70][8:0],data[69]};
 wire frame_ok=!ce[69]&&!ce[70]&&!ue[69]&&!ue[70];
 wire context_bad=ctl_ok&&state!=IDLE&&
  (!owned||!installed||(frame_ok&&frame!=reserved_frame));
 assign fault=any_ue||(ctl_ok&&state==FAIL)||context_bad;
 assign retained=(ctl_ok&&state!=IDLE)||any_ce||any_ue;
 wire active=ctl_ok&&state!=IDLE&&state!=META&&state!=DONE&&state!=FAIL;
 wire [31:0] held_a=data[2][31:0],held_b=data[2][63:32];
 wire [31:0] a_base=data[3][31:0],b_base=data[5][31:0];
 wire [1:0] na=data[7][1:0],nb=data[7][3:2];
 wire held_pair=data[7][4];wire [15:0] tag=data[7][20:5];
 wire [3:0] expected=(4'b0011>>(2-na))|
  (held_pair?((4'b0011>>(2-nb))<<2):4'b0);
 wire shape=rows_a>=1&&rows_a<=2&&(!pair_op||(rows_b>=1&&rows_b<=2&&op_a!=op_b))&&
  base_a[5:0]==0&&limit_a>base_a&&({1'b0,base_a}+33'(rows_a)*33'd32<={1'b0,limit_a})&&
  (!pair_op||(base_b[5:0]==0&&limit_b>base_b&&
    ({1'b0,base_b}+33'(rows_b)*33'd32<={1'b0,limit_b})&&
    (limit_a<=base_b||limit_b<=base_a)));
 assign reserve_r=normal&&state==IDLE&&owned&&installed&&shape&&!fault;
 assign source_permit=normal&&active&&!finished&&!fault;
 assign done=normal&&state==DONE&&!fault;
 assign quiet=normal&&state==IDLE&&!fault;
 assign retire_r=done&&owned;
 wire [383:0] request_raw={data[63],data[62],data[61],data[60],data[59],data[58]};
 assign req=request_raw[336:0];
 assign req_v=normal&&(state==WRITE||state==READ)&&!fault;
 wire response_match=rsp[272:257]==req[15:0]&&rsp[256]==(state==WAIT_WRITE);
 assign rsp_r=normal&&(state==WAIT_WRITE||state==WAIT_READ)&&response_match&&!fault;
 wire accept_response=rsp_v&&rsp_r;
 wire [319:0] response_raw={data[68],data[67],data[66],data[65],data[64]};
 wire [255:0] payload={data[54],data[53],data[52],data[51]};
 wire [72:0] selected_frame={data[41][8:0],data[40]};
 wire [72:0] checked_frame={data[56][8:0],data[55]};
 // valid/op/row live in the third identity word; first two are unchanged
 // reservation codewords, including any CE awaiting service. No raw cached
 // frame/slot is allowed to authorise selection, requests or completion.
 integer free_seat,pending_seat,first_ce;
 reg have_free,have_pending,have_ce;
 always @*begin
  free_seat=0;pending_seat=0;first_ce=0;have_free=0;have_pending=0;have_ce=0;
  for(integer k=3;k>=0;k=k-1)begin
   if(!ce[26+3*k]&&!ue[26+3*k])begin
    if(!data[26+3*k][44])begin free_seat=k;have_free=1;end
    else begin pending_seat=k;have_pending=1;end
   end
  end
  for(integer k=72;k>=0;k=k-1)if(ce[k])begin first_ce=k;have_ce=1;end
 end
 wire [63:0] pending_id=data[26+3*pending_seat];
 wire [31:0] pending_op=pending_id[31:0];wire [11:0] pending_row=pending_id[43:32];
 wire belongs_a=pending_op==held_a,belongs_b=held_pair&&pending_op==held_b;
 wire result_shape=(belongs_a&&pending_row<na)||(belongs_b&&pending_row<nb);
 wire [1:0] pending_slot=(belongs_b?2'd2:2'd0)+pending_row[1:0];
 wire [3:0] pending_mask=4'b1<<pending_slot;
 wire capture_result=result_v&&retained&&owned&&installed&&!fault&&have_free;
 wire [31:0] address=(slot[1]?b_base:a_base)+{26'b0,slot[0],5'b0};
 wire [336:0] request_next={state==BUILD_WRITE,address,payload,
  state==BUILD_WRITE?32'hffffffff:32'b0,tag};
 wire [7:0] repair_syndrome=data[75][22:15];
 wire [6:0] repair_index=data[75][14:8];
 wire [71:0] repair_original={data[75][7:0],data[74]};
 wire [71:0] repair_mask={data[77][7:0],data[76]};
 wire [71:0] mask_next=72'b1<<(repair_syndrome[6:0]==0?7'd71:repair_syndrome[6:0]-1);
 reg [63:0] next_ctl;
 always @*begin
  next_ctl=data[CTRL];
  case(state)
   IDLE:if(reserve_v&&reserve_r)next_ctl=64'(META);
   META:next_ctl[5:0]=({data[1][8:0],data[0]}!=reserved_frame)?FAIL:CAPTURE;
   CAPTURE:if(have_pending)begin
    if(!result_shape|||(seen&pending_mask))next_ctl[5:0]=FAIL;
    else begin next_ctl[5:0]=SYNDROME;next_ctl[9:6]=seen|pending_mask;
     next_ctl[15:14]=pending_slot;next_ctl[17:16]=2'(pending_seat);end
   end else if(finished)next_ctl[5:0]=(seen==expected&&verified==expected)?COMPLETION_FENCE:FAIL;
   SYNDROME:next_ctl[5:0]=CHECK;
   CHECK:next_ctl[5:0]=(data[50][31:0]!=0)?SYNDROME:CHECKED_CAPTURE;
   CHECKED_CAPTURE:next_ctl[5:0]=selected_frame==reserved_frame?BUILD_WRITE:FAIL;
   BUILD_WRITE:next_ctl[5:0]=checked_frame==reserved_frame?WRITE:FAIL;
   WRITE:if(req_v&&req_r)next_ctl[5:0]=WAIT_WRITE;
   WAIT_WRITE:if(accept_response)next_ctl[5:0]=ACK_FENCE;
   ACK_FENCE:next_ctl[5:0]=(response_raw[272:257]==tag&&response_raw[256])?BUILD_READ:FAIL;
   BUILD_READ:next_ctl[5:0]=READ;
   READ:if(req_v&&req_r)next_ctl[5:0]=WAIT_READ;
   WAIT_READ:if(accept_response)next_ctl[5:0]=RESPONSE_CHECK;
   RESPONSE_CHECK:next_ctl[5:0]=(response_raw[272:257]==tag&&!response_raw[256]&&
    response_raw[255:0]==payload)?VERIFIED_FENCE:FAIL;
   VERIFIED_FENCE:begin next_ctl[13:10]=verified|(4'b1<<slot);next_ctl[5:0]=CAPTURE;end
   COMPLETION_FENCE:next_ctl[5:0]=DONE;
   DONE:if(retire_v&&retire_r)next_ctl=0;
   default:begin end
  endcase
  if(context_bad||(reserve_v&&state==IDLE&&!reserve_r)||
   (result_v&&(!active||finished||!have_free))||
   (native_done&&!active)||
   (rsp_v&&(state!=WAIT_WRITE&&state!=WAIT_READ||!response_match)))next_ctl[5:0]=FAIL;
 end
 always @(posedge clk or negedge por_n)begin
  if(!por_n)for(integer k=0;k<NW;k=k+1)code[k]<=encode64(0);
  else begin
   // Correction is serial and separated from the normal extraction path.
   // An upset in a repair record stalls safely; DUE always vetoes globally.
   if(!any_ue&&repair_record_ok)begin
    case(data[CE_CTL][2:0])
     0:if(have_ce)begin
      code[74]<=encode64(code[first_ce][63:0]);
      code[75]<=encode64({41'b0,syndrome[first_ce],7'(first_ce),code[first_ce][71:64]});
      code[CE_CTL]<=encode64(1);
     end
     1:begin code[76]<=encode64(mask_next[63:0]);code[77]<=encode64({56'b0,mask_next[71:64]});code[CE_CTL]<=encode64(2);end
     2:begin
      // Never apply an old snapshot over a new no-ready arrival/finish event.
      if(code[repair_index]==repair_original)code[repair_index]<=repair_original^repair_mask;
      code[CE_CTL]<=encode64(3);
     end
     3:code[CE_CTL]<=encode64(4);
     4:code[CE_CTL]<=encode64(0);
     default:begin end
    endcase
   end
   if(normal&&!fault)begin
    code[CTRL]<=encode64(next_ctl);
    if(reserve_v&&reserve_r)begin
     code[0]<=encode64(frame[63:0]);code[1]<=encode64({55'b0,frame[72:64]});
     code[2]<=encode64({op_b,op_a});code[3]<=encode64({32'b0,base_a});code[4]<=encode64({32'b0,limit_a});
     code[5]<=encode64({32'b0,base_b});code[6]<=encode64({32'b0,limit_b});
     code[7]<=encode64({43'b0,provider_tag,pair_op,rows_b,rows_a});
     code[69]<=encode64(frame[63:0]);code[70]<=encode64({55'b0,frame[72:64]});code[FINISH]<=encode64(0);
     for(integer k=8;k<36;k=k+1)code[k]<=encode64(0);
    end
    if(state==CAPTURE&&have_pending&&result_shape&&!(|(seen&pending_mask)))begin
     for(integer k=0;k<4;k=k+1)code[36+k]<=code[8+4*pending_seat+k];
     for(integer k=0;k<3;k=k+1)code[40+k]<=code[24+3*pending_seat+k];
    end
    if(state==SYNDROME)begin
     for(integer k=0;k<7;k=k+1)code[43+k]<=code[36+k];
     code[50]<=encode64({32'b0,syndrome[39],syndrome[38],syndrome[37],syndrome[36]});
    end
    if(state==CHECKED_CAPTURE&&selected_frame==reserved_frame)
     for(integer k=0;k<7;k=k+1)code[51+k]<=code[43+k];
    if(state==BUILD_WRITE||state==BUILD_READ)
     for(integer k=0;k<6;k=k+1)code[58+k]<=encode64(64'(384'(request_next)>>(64*k)));
    if(accept_response)for(integer k=0;k<5;k=k+1)code[64+k]<=encode64(64'(320'(rsp)>>(64*k)));
    if(state==VERIFIED_FENCE)code[26+3*integer'(seat)]<=encode64(0);
    if(state==DONE&&retire_v&&retire_r)code[FINISH]<=encode64(0);
   end
   // Reserved ingress stays live during CE stalls: no result-ready exists.
   // Copy protected owner code, never a freshly stamped unchecked authority.
   if(capture_result)begin
    for(integer k=0;k<4;k=k+1)code[8+4*free_seat+k]<=encode64(result_data[k*64+:64]);
    code[24+3*free_seat]<=code[69];code[25+3*free_seat]<=code[70];
    code[26+3*free_seat]<=encode64({19'b0,1'b1,result_row,result_op});
   end
   if(native_done&&retained&&!fault)code[FINISH]<=encode64(1);
  end
 end
endmodule
