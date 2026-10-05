`timescale 1ps/1ps
// New HA8 client route into the EXISTING scratch service. No SRAM replica,
// payload register or private clock. workspace_* are real Nash held-owner pins.
module ot_gpu_qwen_scratch_client_mux #(parameter bit ENABLE_CLIENT=0,parameter integer INDEX=0)(
 input wire clk,por_n,run_enable,local_reset,
 input wire workspace_valid,workspace_exclusive,
 input wire [54:0] workspace_owner,
 input wire [238:0] workspace_tuple,
 input wire [9:0] workspace_base,input wire [10:0] workspace_length,
 input wire client_valid,client_write,client_done_ready,
 input wire [9:0] client_addr,input wire [511:0] client_wdata,
 input wire [54:0] client_owner,input wire [238:0] client_tuple,
 output wire client_ready,client_done,output wire [511:0] client_rdata,
 input wire route_valid,route_write,route_done_ready,
 input wire [9:0] route_addr,input wire [511:0] route_wdata,
 output wire route_ready,route_done,output wire [511:0] route_rdata,
 output wire service_valid,service_write,service_done_ready,
 output wire [9:0] service_addr,output wire [511:0] service_wdata,
 input wire service_ready,service_done,input wire [511:0] service_rdata,
 output wire busy,drained,fault
);
 generate if(!ENABLE_CLIENT)begin:g_original
  assign service_valid=route_valid;assign service_write=route_write;
  assign service_addr=route_addr;assign service_wdata=route_wdata;
  assign service_done_ready=route_done_ready;
  assign route_ready=service_ready;assign route_done=service_done;assign route_rdata=service_rdata;
  assign client_ready=0;assign client_done=0;assign client_rdata=0;
  assign busy=0;assign drained=1;assign fault=0; // No ADDED client debt; router still tracks original commands.
 end else begin:g_owned
  // {fault,destination_client,busy,GO239,owner55,base10,length11}
  wire [317:0] state;reg [317:0] next_state;wire clean;
  wire held_client=state[316];wire held_busy=state[315];
  wire [238:0] held_tuple=state[314:76];wire [54:0] held_owner=state[75:21];
  wire workspace_shape=workspace_exclusive && workspace_length!=0 && workspace_length<=1024 &&
    {1'b0,workspace_base}+workspace_length<=1024 && workspace_tuple[174:164]<1737 &&
    workspace_tuple[35]==(INDEX/32) && workspace_tuple[34:30]==(INDEX%32);
  wire leased=workspace_valid && workspace_shape;
  wire client_match=leased && client_owner==workspace_owner && client_tuple==workspace_tuple &&
    client_addr>=workspace_base && {1'b0,client_addr}<{1'b0,workspace_base}+workspace_length;
  wire held_lease_match=leased && workspace_owner==held_owner && workspace_tuple==held_tuple &&
    workspace_base==state[20:11] && workspace_length==state[10:0];
  wire lease_lost=held_busy && held_client && !held_lease_match;
  wire bad_offer=!held_busy && workspace_valid && (!workspace_shape || (client_valid && !client_match));
  wire stale_return=service_done && !held_busy;
  wire active=por_n && run_enable && !local_reset && clean && !state[317];
  wire protocol_fault=lease_lost || bad_offer || stale_return;
  wire usable=active && !protocol_fault;
  wire route_overlap=leased && route_addr>=workspace_base &&
    {1'b0,route_addr}<{1'b0,workspace_base}+workspace_length;
  wire choose_client=client_valid && client_match;
  wire choose_route=route_valid && !route_overlap && !choose_client;
  assign service_valid=usable && !held_busy && (choose_client || choose_route);
  assign service_write=choose_client ? client_write : route_write;
  assign service_addr=choose_client ? client_addr : route_addr;
  assign service_wdata=choose_client ? client_wdata : route_wdata;
  assign client_ready=usable && !held_busy && client_match && service_ready;
  assign route_ready=usable && !held_busy && !route_overlap && !choose_client && service_ready;
  assign client_done=usable && held_busy && held_client && service_done;
  assign route_done=usable && held_busy && !held_client && service_done;
  assign client_rdata=held_busy && held_client ? service_rdata : 512'b0;
  assign route_rdata=held_busy && !held_client ? service_rdata : 512'b0;
  assign service_done_ready=usable && held_busy && (held_client ? client_done_ready : route_done_ready);
  assign busy=held_busy;assign fault=!clean || state[317] || (active && protocol_fault);
  assign drained=!held_busy && !fault;
  always @* begin
   next_state=state;
   if(active)begin
    if(protocol_fault)next_state[317]=1;
    else begin
     if(service_valid && service_ready)
      next_state={1'b0,choose_client,1'b1,choose_client ? client_tuple : 239'b0,
        choose_client ? client_owner : 55'b0,choose_client ? workspace_base : 10'b0,
        choose_client ? workspace_length : 11'b0};
     if(service_done && service_done_ready)next_state=0;
    end
   end
  end
  ot_gpu_qwen_scratch_mux_record #(.BITS(318),.INDEX(INDEX)) record(
   .clk(clk),.por_n(por_n),.write_enable(active && next_state!=state),
   .next_data(next_state),.data(state),.clean(clean));
 end endgenerate
endmodule

`timescale 1ps/1ps
// Source acceptance/control only. Whole-engine events are explicit real ports;
// the PC40 fragment is NOT connected as a whole terminal/result producer.
module ot_gpu_qwen_scratch_mux_record #(
 parameter integer BITS=318, WORDS=(BITS+43)/44, INDEX=0
)(input wire clk,por_n,write_enable,input wire [BITS-1:0] next_data,
 output wire [BITS-1:0] data,output wire clean);
 reg [WORDS*72-1:0] coded;
 wire [WORDS*44-1:0] padded={{(WORDS*44-BITS){1'b0}},next_data};
 wire [WORDS*44-1:0] decoded;
 wire [WORDS*72-1:0] encoded;
 wire [WORDS-1:0] word_clean;
 function automatic [71:0] reset_word(input integer word_index);
  reg [63:0] value;reg [71:0] result;integer p,j,k;
  begin
   value={3'd5,10'(word_index),7'(INDEX),44'b0};result=0;j=0;
   for(p=1;p<=71;p=p+1)if((p&(p-1))!=0)begin result[p-1]=value[j];j=j+1;end
   for(k=0;k<7;k=k+1)begin
    for(p=1;p<=71;p=p+1)if((p&(1<<k))!=0)result[(1<<k)-1]=result[(1<<k)-1]^result[p-1];
   end
   result[71]=^result[70:0];reset_word=result;
  end
 endfunction
 for(genvar w=0;w<WORDS;w=w+1)begin:g_words
  wire [6:0] syndrome;
  wire odd,cc,ce,ue,seal_ok,pad_ok;
  wire [71:0] repaired;
  ot_w2_sealed_secded72 #(.PC_ID(7'(INDEX)),.WORD_INDEX(10'(w)),.WORD_KIND(3'd5),
   .PAYLOAD_BITS(w==WORDS-1 ? BITS-w*44 : 44)) codec(
    .payload(padded[w*44+:44]),.current_word(coded[w*72+:72]),.encoded_word(encoded[w*72+:72]),
    .syndrome(syndrome),.overall_odd(odd),.clean(cc),.correctable(ce),.uncorrectable(ue),
    .seal_ok(seal_ok),.padding_ok(pad_ok),.release_clean(word_clean[w]),
    .repaired_payload(decoded[w*44+:44]),.repaired_word(repaired));
  localparam [71:0] RESET_CODE=reset_word(w);
  always @(posedge clk or negedge por_n)
   if(!por_n)coded[w*72+:72]<=RESET_CODE;
   else if(write_enable && clean)coded[w*72+:72]<=encoded[w*72+:72];
 end
 assign data=decoded[BITS-1:0];
 assign clean=&word_clean;
endmodule

