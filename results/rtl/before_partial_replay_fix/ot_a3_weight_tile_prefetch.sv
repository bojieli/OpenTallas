`timescale 1ns/1ps
// Decoupled resident-tile reader. A bounded FIFO holds copies of SRAM words,
// allowing the bank to be released after the final response is copied while
// the consumer still drains the queue. Tags/indices travel with every copy.
// Each issued read reserves a FIFO slot, including its in-flight response.
// One tile is acquired at a time; queued words from older tiles remain ordered.
// Optional stream tags relabel copied words for resident replay. SRAM access
// and release continue to use the original owner tag; queued tags never change.
// ABSOLUTE_STREAM_ADDRESS stores stream base+index at insertion, removing the
// address adder after FIFO selection on the consumer's issue-credit path.
module ot_a3_weight_tile_prefetch #(
    parameter integer TAG_BITS=64,
    parameter bit SEPARATE_STREAM_TAG=0,
    parameter bit ABSOLUTE_STREAM_ADDRESS=0,
    // All acquired tiles and queued words belong to one generation until reset.
    // Only valid with absolute stream identities; generic mixed streams stay off.
    parameter bit SINGLE_GENERATION=0,
    parameter integer FIFO_DEPTH=4,
    parameter integer PW=(FIFO_DEPTH<2)?1:$clog2(FIFO_DEPTH),
    parameter integer CW=$clog2(FIFO_DEPTH+1)
)(
    input wire clk,rst_n,
    input wire reserve_valid,reserve_bank,
    input wire [TAG_BITS-1:0] reserve_tag,
    input wire [9:0] reserve_words,
    output wire reserve_ready,
    input wire fill_valid,fill_bank,
    input wire [TAG_BITS-1:0] fill_tag,
    input wire [127:0] fill_data,
    output wire fill_ready,
    input wire cancel_valid,cancel_bank,
    input wire [TAG_BITS-1:0] cancel_tag,
    output wire cancel_ready,
    input wire tile_valid,tile_bank,tile_retain,
    input wire [TAG_BITS-1:0] tile_tag,
    input wire [TAG_BITS-1:0] tile_stream_tag,
    input wire [9:0] tile_words,
    output wire tile_ready,
    output wire word_valid,
    input wire word_ready,
    output wire [127:0] word_data,
    output wire [TAG_BITS-1:0] word_tag,
    output wire [9:0] word_index,
    output wire word_last,
    output reg tile_released,
    output reg [TAG_BITS-1:0] released_tag,
    output wire [1:0] ready_banks,active_banks,
    output wire [CW:0] reserved_slots
);
    localparam [1:0] IDLE=0, READ=1, RELEASE=2;
    reg [1:0] state;
    reg bank_q,retain_q;
    reg [TAG_BITS-1:0] tag_q,stream_tag_q;
    reg [9:0] words_q,issued,received;
    reg outstanding;
    reg [PW-1:0] head,tail;
    reg [CW-1:0] count;
    reg [127:0] data_mem[0:FIFO_DEPTH-1];
    localparam integer FIFO_TAG_BITS=SINGLE_GENERATION?32:TAG_BITS;
    reg [FIFO_TAG_BITS-1:0] tag_mem[0:FIFO_DEPTH-1];
    generate if(SINGLE_GENERATION)begin: shared_generation
      reg [TAG_BITS-33:0] generation_q;
      initial begin
        if(!ABSOLUTE_STREAM_ADDRESS || TAG_BITS<=32)
          $fatal(1,"Shared generation requires absolute stream tags wider than 32 bits");
      end
      always @(posedge clk)
        if(tile_valid && tile_ready)generation_q<=tile_stream_tag[TAG_BITS-1:32];
      assign word_tag={generation_q,tag_mem[head]};
    end else begin: per_entry_generation
      assign word_tag=tag_mem[head];
    end endgenerate
    reg [9:0] index_mem[0:FIFO_DEPTH-1];
    reg last_mem[0:FIFO_DEPTH-1];
    function automatic [PW-1:0] next_ptr(input [PW-1:0] p);
        next_ptr=(p==PW'(FIFO_DEPTH-1))?{PW{1'b0}}:p+1'b1;
    endfunction
    assign reserved_slots={1'b0,count}+{{CW{1'b0}},outstanding};
    wire acquire_ready,release_ready,read_ready,response_valid,response_bank;
    wire [127:0] response_data;
    wire [TAG_BITS-1:0] response_tag;
    // No combinational path from consumer ready into SRAM read admission.
    // A full queue may cost one bubble; otherwise reads sustain one per cycle.
    wire read_valid=rst_n && state==READ && issued<words_q &&
                    reserved_slots < (CW+1)'(FIFO_DEPTH);
    wire response_ready=rst_n && count<CW'(FIFO_DEPTH);
    wire read_fire=read_valid && read_ready;
    wire push=response_valid && response_ready;
    wire pop=word_valid && word_ready;
    assign word_valid=rst_n && count!=0;
    assign word_data=data_mem[head];
    assign word_index=index_mem[head];
    assign word_last=last_mem[head];
    // Refuse a mismatched tile length before acquisition, rather than hanging
    // on a later out-of-range read or silently discarding a reserved suffix.
    wire [9:0] acquire_words;
    wire tile_shape=tile_words!=0 && tile_words<=10'd512 && tile_words==acquire_words;
    assign tile_ready=rst_n && state==IDLE && tile_shape && acquire_ready;
    ot_a3_runtime_weight_banks #(.TAG_BITS(TAG_BITS)) banks(
      .clk(clk),.rst_n(rst_n),
      .reserve_valid(reserve_valid),.reserve_bank(reserve_bank),.reserve_tag(reserve_tag),
      .reserve_words(reserve_words),.reserve_ready(reserve_ready),
      .fill_valid(fill_valid),.fill_bank(fill_bank),.fill_tag(fill_tag),.fill_data(fill_data),.fill_ready(fill_ready),
      .cancel_valid(cancel_valid),.cancel_bank(cancel_bank),.cancel_tag(cancel_tag),.cancel_ready(cancel_ready),
      .acquire_valid(tile_valid && state==IDLE && tile_shape),.acquire_bank(tile_bank),
      .acquire_tag(tile_tag),.acquire_ready(acquire_ready),
      .acquire_words(acquire_words),
      .release_valid(state==RELEASE),.release_bank(bank_q),.release_tag(tag_q),
      .release_retain(retain_q),.release_ready(release_ready),
      .read_valid(read_valid),.read_bank(bank_q),.read_tag(tag_q),.read_index(issued),.read_ready(read_ready),
      .response_valid(response_valid),.response_ready(response_ready),.response_data(response_data),
      .response_bank(response_bank),.response_tag(response_tag),
      .ready_banks(ready_banks),.active_banks(active_banks));
    always @(posedge clk or negedge rst_n) begin
      if(!rst_n) begin
        state<=IDLE;bank_q<=0;retain_q<=0;tag_q<=0;stream_tag_q<=0;words_q<=0;
        issued<=0;received<=0;outstanding<=0;head<=0;tail<=0;count<=0;
        tile_released<=0;released_tag<=0;
      end else begin
        tile_released<=0;
        case({push,pop})
          2'b10:count<=count+1'b1;
          2'b01:count<=count-1'b1;
          default:begin end
        endcase
        case({read_fire,push})
          2'b10:outstanding<=1;
          2'b01:outstanding<=0;
          default:begin end
        endcase
        if(pop)head<=next_ptr(head);
        if(push)begin
          data_mem[tail]<=response_data;
          if(ABSOLUTE_STREAM_ADDRESS)
            tag_mem[tail]<=FIFO_TAG_BITS'({stream_tag_q[TAG_BITS-1:32],stream_tag_q[31:0]+{22'b0,received}});
          else tag_mem[tail]<=FIFO_TAG_BITS'(SEPARATE_STREAM_TAG?stream_tag_q:response_tag);
          index_mem[tail]<=received;last_mem[tail]<=received==words_q-1'b1;
          tail<=next_ptr(tail);received<=received+1'b1;
          if(received==words_q-1'b1)state<=RELEASE;
        end
        if(read_fire)issued<=issued+1'b1;
        if(tile_valid && tile_ready)begin
          state<=READ;bank_q<=tile_bank;tag_q<=tile_tag;words_q<=tile_words;retain_q<=tile_retain;
          stream_tag_q<=tile_stream_tag;issued<=0;received<=0;
        end
        if(state==RELEASE && release_ready)begin
          state<=IDLE;tile_released<=1;released_tag<=tag_q;
        end
      end
    end
endmodule
