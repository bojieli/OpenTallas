`timescale 1ns/1ps
`default_nettype none
// A heterogeneous native programme target. Configuration is a bank/row/word
// transaction, never an address hidden in the 256-bit SRAM payload.
module host_su_target #(
 parameter integer LINE_BITS=9688, EDGES=7111,
 parameter integer COLS=(LINE_BITS+255)/256,
 parameter integer INDEX_GROUPS=(COLS+15)/16, INDEX_BANKS=(EDGES+127)/128,
 parameter integer DICT_ENTRIES[0:COLS-1]='{default:1},
 parameter integer DICT_BANKS[0:COLS-1]='{default:1},
 parameter integer MACROS=INDEX_GROUPS*INDEX_BANKS+COLS,
 parameter integer MUT_READY=0
)(input wire clk,rst_n,input wire[MACROS-1:0] clk_macro,
 input wire cfg_v,input wire[15:0] cfg_bank,input wire[6:0] cfg_row,
 input wire[255:0] cfg_data,output wire cfg_ready,cfg_accept,
 input wire validate_v,launch_v,input wire[15:0] length,
 output wire block_ready,output wire busy,valid,done,output wire fault,
 output wire[15:0] edge_index,output wire[LINE_BITS-1:0] command);
 function automatic integer required_rows(input integer b);
  integer remain,base;
  begin
   required_rows=0;
   if(b<INDEX_GROUPS*INDEX_BANKS) begin
    remain=EDGES-(b%INDEX_BANKS)*128;
    required_rows=(remain>128)?128:remain;
   end else begin
    base=INDEX_GROUPS*INDEX_BANKS;
    for(integer c=0;c<COLS;c=c+1) begin
     if(b>=base && b<base+DICT_BANKS[c]) begin
      remain=DICT_ENTRIES[c]-(b-base)*128;
      required_rows=(remain>128)?128:remain;
     end
     base=base+DICT_BANKS[c];
    end
   end
  end
 endfunction
 localparam integer BW=(MACROS<2)?1:$clog2(MACROS);
 reg[MACROS*128-1:0] loaded;
 reg scanning,validated,local_fault;
 reg[BW-1:0] scan_bank;
 reg[6:0] scan_row;
 reg[1:0] commit_guard;
 wire native_fault;
 reg index_bad;
 wire address_ok=cfg_bank<MACROS && {25'b0,cfg_row}<required_rows(int'(cfg_bank));
 always_comb begin
  index_bad=0;
  if(cfg_bank<INDEX_GROUPS*INDEX_BANKS) begin
   for(integer c=0;c<COLS;c=c+1)
    if(int'(cfg_bank)/INDEX_BANKS==c/16 && int'(cfg_data[(c%16)*16+:16])>=DICT_ENTRIES[c]) index_bad=1;
  end
 end
 assign fault=local_fault|native_fault;
 assign cfg_ready=rst_n&&!busy&&!scanning&&!fault;
 assign cfg_accept=cfg_v&&cfg_ready&&address_ok&&!index_bad&&!validate_v&&!launch_v;
 assign block_ready=validated&&!scanning&&commit_guard==0&&!busy&&!fault;
 wire native_start=launch_v&&block_ready&&!cfg_v&&!validate_v&&length!=0&&length<=EDGES;
 ot_hbm_su_programme #(.LINE_BITS(LINE_BITS),.EDGES(EDGES),.COLS(COLS),.DICT_BANKS(DICT_BANKS),.MACROS(MACROS)) programme(
  .clk(clk),.rst_n(rst_n),.clk_macro(clk_macro),
  .cfg_we(cfg_accept),.cfg_bank(cfg_bank),.cfg_row(cfg_row),.cfg_data(cfg_data),
  .start(native_start),.length(length),.busy(busy),.valid(valid),.done(done),.fault(native_fault),
  .edge_index(edge_index),.command(command));
 initial begin
  if(MACROS>65536 || EDGES<1 || EDGES>65535) $fatal(1,"SU target capacity");
  for(integer b=0;b<MACROS;b=b+1)
   if(required_rows(b)<1 || required_rows(b)>128) $fatal(1,"SU target required rows");
  for(integer c=0;c<COLS;c=c+1)
   if(DICT_ENTRIES[c]<1 || DICT_ENTRIES[c]>65536 || DICT_BANKS[c]!=(DICT_ENTRIES[c]+127)/128)
    $fatal(1,"SU target dictionary capacity");
 end
 always @(posedge clk or negedge rst_n) begin
  if(!rst_n) begin
   loaded<='0;scanning<=0;validated<=0;local_fault<=0;
   scan_bank<=0;scan_row<=0;commit_guard<=0;
  end else begin
   commit_guard<={commit_guard[0],cfg_accept};
   if(cfg_v) begin
    validated<=0;
    if(!cfg_accept) local_fault<=1;
    else loaded[int'(cfg_bank)*128+int'(cfg_row)]<=1;
   end
   if(validate_v) begin
    validated<=0;
    if(busy||scanning||commit_guard!=0||cfg_v||launch_v||fault) local_fault<=1;
    else begin scanning<=1;scan_bank<=0;scan_row<=0;end
   end
   if(scanning) begin
    if(!loaded[int'(scan_bank)*128+int'(scan_row)] && MUT_READY==0) begin
     scanning<=0;local_fault<=1;
    end else if(int'(scan_row)+1==required_rows(int'(scan_bank))) begin
     scan_row<=0;
     if(int'(scan_bank)==MACROS-1) begin scanning<=0;validated<=1;end
     else scan_bank<=scan_bank+1'b1;
    end else scan_row<=scan_row+1'b1;
   end
   if(launch_v) begin
    if(!native_start) local_fault<=1;
   end
  end
 end
endmodule
`default_nettype wire
