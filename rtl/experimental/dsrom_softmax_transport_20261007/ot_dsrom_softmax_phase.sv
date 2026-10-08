// Experimental opt-in row ownership controller. event_v means an actual
// committed vector, not an unaccepted ready/valid offer. Payload, SRAM read
// pipeline, command ECC and CDC are separate explicitly required components.
module ot_dsrom_softmax_phase(
    input wire clk, rst_n,
    input wire cmd_v, cmd_short, cmd_fault,
    input wire [15:0] cmd_tag,
    output wire cmd_ready,
    input wire event_v,
    input wire [2:0] event_kind,
    input wire [15:0] event_tag,
    output wire event_ready,
    output reg [2:0] expected_kind,
    output reg [6:0] memory_row,
    output wire bf16_upper_half,
    input wire den_v,
    input wire [15:0] den_tag,
    output wire busy, fault,
    output wire [15:0] active_tag
);
    localparam [9:0] IDLE=10'b0000000001, FILL_S=10'b0000000010,
      PLAY_S=10'b0000000100, CAP_E=10'b0000001000, DRAIN_E=10'b0000010000,
      FILL_P=10'b0000100000, PLAY_P=10'b0001000000, CAP_O=10'b0010000000,
      DRAIN_O=10'b0100000000, FAILED=10'b1000000000;
    // Keep integrity replicas physically distinct during subsequent synthesis.
    (* keep="true", dont_touch="true" *) reg [9:0] state, state_n;
    (* keep="true", dont_touch="true" *) reg [5:0] count, count_n;
    (* keep="true", dont_touch="true" *) reg [15:0] tag, tag_n;
    (* keep="true", dont_touch="true" *) reg short_row, short_row_n;
    (* keep="true", dont_touch="true" *) reg denominator, denominator_n;
    (* keep="true", dont_touch="true" *) reg [1:0] settle, settle_n;
    wire integrity=(state_n==~state) && (count_n==~count) && (tag_n==~tag)
        && (short_row_n==~short_row) && (denominator_n==~denominator)
        && (settle_n==~settle) && (state!=0) && ((state&(state-10'd1))==0);
    assign fault=!integrity || state==FAILED;
    assign cmd_ready=state==IDLE && !fault;
    assign busy=state!=IDLE;
    assign active_tag=tag;
    assign event_ready=!fault && state!=IDLE && settle==0 && (state!=PLAY_P || denominator);
    assign bf16_upper_half=count[0];
    reg [9:0] next_phase;
    reg [5:0] last_index;
    reg barrier;
    always @* begin
        expected_kind=0;memory_row=0;next_phase=FAILED;last_index=31;barrier=0;
        case(state)
          FILL_S:begin expected_kind=0;memory_row={1'b0,count};next_phase=PLAY_S;last_index=short_row?7:39;barrier=1;end
          PLAY_S:begin expected_kind=1;memory_row={1'b0,count};next_phase=CAP_E;last_index=short_row?7:39;end
          CAP_E:begin expected_kind=2;memory_row=7'd72+{1'b0,count};next_phase=DRAIN_E;last_index=short_row?7:39;barrier=1;end
          DRAIN_E:begin expected_kind=3;memory_row=7'd72+{1'b0,count};next_phase=FILL_P;last_index=short_row?7:39;end
          FILL_P:begin expected_kind=4;memory_row=7'd40+{1'b0,count};next_phase=PLAY_P;barrier=1;end
          PLAY_P:begin expected_kind=5;memory_row=7'd40+{1'b0,count};next_phase=CAP_O;end
          CAP_O:begin expected_kind=6;memory_row=7'd112+{2'b0,count[5:1]};next_phase=DRAIN_O;barrier=1;end
          DRAIN_O:begin expected_kind=7;memory_row=7'd112+{2'b0,count[5:1]};next_phase=IDLE;end
          default:begin end
        endcase
    end
`ifdef SOFTMAX_PHASE_IGNORE_TAG
    wire event_tag_matches=1'b1;
`else
    wire event_tag_matches=(event_tag==tag);
`endif
    wire bad_event=event_v && (!event_ready || event_kind!=expected_kind || !event_tag_matches || count>last_index);
    wire bad_den=den_v && (den_tag!=tag || state==IDLE || state==FILL_S || state==PLAY_S);
    always @(posedge clk) begin
        if(!rst_n) begin
            state<=IDLE;state_n<=~IDLE;count<=0;count_n<=~6'd0;
            tag<=0;tag_n<=~16'd0;short_row<=0;short_row_n<=1;
            denominator<=0;denominator_n<=1;settle<=0;settle_n<=~2'd0;
        end else if(fault || bad_event || bad_den || (cmd_v && (!cmd_ready || cmd_fault))) begin
            state<=FAILED;state_n<=~FAILED;
        end else begin
            if(settle!=0) begin settle<=settle-2'd1;settle_n<=~(settle-2'd1);end
            if(den_v)begin denominator<=1;denominator_n<=0;end
            if(cmd_v && cmd_ready) begin
                state<=FILL_S;state_n<=~FILL_S;tag<=cmd_tag;tag_n<=~cmd_tag;
                short_row<=cmd_short;short_row_n<=~cmd_short;
                count<=0;count_n<=~6'd0;denominator<=0;denominator_n<=1;
            end
            if(event_v) begin
                if(count==last_index) begin
                    state<=next_phase;state_n<=~next_phase;count<=0;count_n<=~6'd0;
                    if(barrier)begin settle<=2;settle_n<=~2'd2;end
                end else begin count<=count+6'd1;count_n<=~(count+6'd1);end
            end
        end
    end
endmodule
