module fn_old(
 input wire gath,tx_result,input wire[1:0]qid,tx_dst,input wire[3:0]tx_ttl,
 input wire[2:0]tag,input wire[255:0]data,input wire signed[31:0]MUT_TAG,
 output wire[279:0]y0,y1);
function automatic [279:0] flit(input integer d,input [2:0] tag,input [255:0] data);
        flit={1'b1,gath?2'd3:(tx_result?2'd2:2'd1),qid,gath?qid:tx_dst,
              gath?tx_ttl[d*2+:2]:(tx_result?2'd3:2'd0),MUT_TAG?(tag^3'd1):tag,1'b0,11'b0,data};
    endfunction
assign y0=flit(0,tag,data);
assign y1=flit(1,tag,data);
endmodule
