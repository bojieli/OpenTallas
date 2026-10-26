// Wires-only regional station. lp.py inserts the actual ring/read landing on
// every input seam; this module contributes no unpriced edge or state.
module dsdv_bk_plana_station #(parameter integer W=24)(input wire ck,rst,input wire[W-1:0]i,output wire[W-1:0]o);
 assign o=i;
endmodule
