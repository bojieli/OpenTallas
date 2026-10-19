`timescale 1ns/1ps
// The compiler transports the real returned beats to this face in reserved
// order: low code half, high code half (same identity), or one packed scale.
// Output is one registered edge after the high half/scale slot. Faults do not
// extend the schedule. No payload is produced from expected/reference data.
module qkd_embedding_static_join(
    input wire ck,rst_n,beat_slot,beat_v,
    input wire [255:0] beat_data,
    input wire [17:0] beat_token,input wire [5:0] beat_word,
    input wire beat_half,beat_scale,input wire [15:0] beat_epoch,
    output reg word_v,output reg [511:0] word_data,
    output reg [17:0] word_token,output reg [5:0] word_index,
    output reg word_scale,output reg [15:0] word_epoch,
    output reg fault
);
    reg low_valid;
    reg [255:0] low_data;
    reg [17:0] low_token;
    reg [5:0] low_word;
    reg [15:0] low_epoch;
    always @(posedge ck) begin
        if(beat_slot&&!beat_scale&&!beat_half) begin
            low_data<=beat_data;low_token<=beat_token;low_word<=beat_word;low_epoch<=beat_epoch;
        end
        word_data<=beat_scale?{496'd0,beat_data[beat_token[3:0]*16+:16]}:{beat_data,low_data};
        word_token<=beat_token;word_index<=beat_word;word_scale<=beat_scale;word_epoch<=beat_epoch;
    end
    always @(posedge ck or negedge rst_n)
        if(!rst_n) begin low_valid<=0;word_v<=0;fault<=0;end
        else begin
            word_v<=beat_slot&&(beat_scale||beat_half);
            if(beat_slot!=beat_v) fault<=1;
            if(beat_slot) begin
                if(beat_token>=151936 || (beat_scale&&beat_half)) fault<=1;
                if(beat_scale) begin if(low_valid) fault<=1;end
                else if(!beat_half) begin if(low_valid) fault<=1;low_valid<=1;end
                else begin
                    low_valid<=0;
                    if(!low_valid||low_token!=beat_token||low_word!=beat_word||low_epoch!=beat_epoch) fault<=1;
                end
            end
        end
endmodule
