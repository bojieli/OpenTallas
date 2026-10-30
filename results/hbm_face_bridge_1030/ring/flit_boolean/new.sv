module fn_new(
 input wire gath,tx_result,input wire[1:0]qid,tx_dst,input wire[3:0]tx_ttl,
 input wire[2:0]tag,input wire[255:0]data,input wire signed[31:0]MUT_TAG,
 output wire[279:0]y0,y1);
function automatic [279:0] flit(
        input integer d,input [2:0] tag,input [255:0] data,
        input gather_mode,result_mode,input [1:0] source_qid,target_qid,
        input [3:0] ttl_by_direction,input integer tag_mutant
    );
        flit={1'b1,gather_mode?2'd3:(result_mode?2'd2:2'd1),source_qid,gather_mode?source_qid:target_qid,
              gather_mode?ttl_by_direction[d*2+:2]:(result_mode?2'd3:2'd0),tag_mutant?(tag^3'd1):tag,1'b0,11'b0,data};
    endfunction
assign y0=flit(0,tag,data,gath,tx_result,qid,tx_dst,tx_ttl,MUT_TAG);
assign y1=flit(1,tag,data,gath,tx_result,qid,tx_dst,tx_ttl,MUT_TAG);
endmodule
