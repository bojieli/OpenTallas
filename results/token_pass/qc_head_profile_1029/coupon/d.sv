module d(input[3:0]txs,tk,input emb_act,input[6:0]emb_k,input ev_stage,input[5:0]ta,output prog_head_context_slot,emb_read,l_context_seg);
parameter integer HEAD_CONTEXT=0,ROPE=0,L_CONTEXTS=0;
localparam integer ROPE_FIRST=77;
    assign prog_head_context_slot = HEAD_CONTEXT != 0 && txs[1] && tk == 4'd12;
 assign emb_read=emb_act&&(emb_k<=7'd64||(ROPE!=0&&emb_k>=7'(ROPE_FIRST)));
    assign l_context_seg = (L_CONTEXTS != 0) && ev_stage && ta[5:0] >= 6'd2 && ta[5:0] <= 6'd36;
endmodule
