`timescale 1ns/1ps
// Actual SOURCE PROMPT/LAUNCH/CFG word, not bootstrap RAW sector data.
// bit63 reserved0; invalid word becomes existing unknown-op refusal in hostcq.
module ot_s81_source_command_decode(
    input wire [63:0] word,
    output wire [1:0] op,
    output wire [7:0] tag,user,
    output wire [20:0] pos,token,
    output wire [2:0] token_type
);
    assign op=word[63]?2'd0:word[1:0];
    assign tag=word[9:2];assign user=word[17:10];
    assign pos=word[38:18];assign token=word[59:39];
    assign token_type=word[62:60];
endmodule
