    reg scheduler_sent=0;
    wire scheduler_ready,reserve_valid,reserve_bank,fill_valid,fill_bank,tile_valid,tile_bank;
    wire [63:0] reserve_tag,fill_tag,tile_tag;
    wire [9:0] fill_words,acquire_words;
    wire [127:0] fill_data;
    wire fetch_valid,fetch_ready,weight_response_ready,weight_response_mismatch;
    wire [63:0] fetch_tag;
    wire [31:0] fetch_address;
    wire [9:0] fetch_words;
    reg backing_active=0;
    reg [63:0] backing_tag=0;
    reg [31:0] backing_address=0;
    reg [9:0] backing_words=0,backing_index=0;
    assign fetch_ready=!backing_active && ticks[1:0]!=0;
    wire backing_valid=backing_active && ticks[2:0]!=0;
    ot_a3_weight_tile_scheduler #(.TILE_WORDS(TILE_WORDS)) scheduler(
        .clk(clk),.rst_n(runtime_reset_n),.clear(1'b0),
        .command_valid(record_valid && !geometry_error && operand_request && !scheduler_sent),.command_ready(scheduler_ready),
        .command_generation(record_generation),.command_base(record_w),.command_words(record_stream_words),
        .active(),.scheduled(),.command_error(),
        .reserve_valid(reserve_valid),.reserve_ready(reserve_ready),.reserve_bank(reserve_bank),
        .reserve_tag(reserve_tag),.reserve_words(fill_words),
        .fetch_valid(fetch_valid),.fetch_ready(fetch_ready),.fetch_tag(fetch_tag),
        .fetch_address(fetch_address),.fetch_words(fetch_words),
        .response_valid(backing_valid),.response_ready(weight_response_ready),.response_mismatch(weight_response_mismatch),
        .response_tag(backing_tag),.response_index(backing_index),
        .response_data(w_mem[backing_address+{22'b0,backing_index}]),
        .fill_valid(fill_valid),.fill_bank(fill_bank),.fill_ready(fill_ready),.fill_tag(fill_tag),.fill_data(fill_data),
        .tile_valid(tile_valid),.tile_ready(tile_ready),.tile_bank(tile_bank),.tile_tag(tile_tag),.tile_words(acquire_words));
    always @(posedge clk)begin
        if(!runtime_reset_n)begin scheduler_sent<=0;backing_active<=0;end
        else begin
            if(record_valid && !geometry_error && operand_request && !scheduler_sent && scheduler_ready)scheduler_sent<=1;
            if(fetch_valid && fetch_ready)begin
                backing_active<=1;backing_tag<=fetch_tag;backing_address<=fetch_address;
                backing_words<=fetch_words;backing_index<=0;
            end
            if(backing_valid && weight_response_ready)begin
                if(backing_index==backing_words-1'b1)backing_active<=0;
                else backing_index<=backing_index+1'b1;
            end
            if(weight_response_mismatch)$fatal(1,"scheduler response mismatch");
        end
    end
