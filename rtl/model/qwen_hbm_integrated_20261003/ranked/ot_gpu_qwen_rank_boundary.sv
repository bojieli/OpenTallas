`timescale 1ps/1ps
// Pure rank admission/refusal boundary. No new grant, timer or cached rank.
// Sender reverse_rank is independent of the retained grant. A refused offer
// remains the sender's debt; this module never ACKs it or retires ownership.
module ot_gpu_qwen_rank_boundary #(parameter bit ENABLE=0)(
 input wire grant_live,
 input wire [206:0] grant_identity,
 input wire alloc_valid,map_valid,map_rank,
 input wire [126:0] alloc_source,
 input wire [6:0] map_PC,
 input wire raw_alloc_ready,
 input wire reverse_valid,reverse_rank,raw_reverse_ready,
 output wire alloc_valid_checked,map_valid_checked,alloc_ready,
 output wire reverse_valid_checked,reverse_ready,
 output wire [6:0] selected_PC,
 output wire [7:0] selected_index,
 output wire rank_refusal
);
 wire map_match=map_rank==alloc_source[56];
 wire reverse_match=grant_live && reverse_rank==grant_identity[136];
 wire selected_rank=grant_live ? grant_identity[136] : map_rank;
 assign selected_PC=grant_live ? grant_identity[45:39] : map_PC;
 assign selected_index={selected_rank,selected_PC};
 assign alloc_valid_checked=ENABLE && alloc_valid && map_match;
 assign map_valid_checked=ENABLE && map_valid && map_match;
 assign alloc_ready=ENABLE && raw_alloc_ready && map_match;
 assign reverse_valid_checked=ENABLE && reverse_valid && reverse_match;
 assign reverse_ready=ENABLE && raw_reverse_ready && reverse_match;
 assign rank_refusal=ENABLE && ((alloc_valid && !map_match) ||
                               (reverse_valid && !reverse_match));
endmodule
