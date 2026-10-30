`default_nettype none
// SOURCE-ONLY single native281b packet -> actual32 ordinaryVM bank DQ inputs.
// Header/payload broadcast, valid only at exactquad/bank. No extra registers.
module ot_hbm_static_load_vm_dq_demux(
 input wire[280:0]packet_i,output wire[32*281-1:0]bank_dq_o,output wire fault_o
);
 wire[4:0]destination={packet_i[278:277],packet_i[266:264]};
 assign fault_o=packet_i[280]&&packet_i[279];
 for(genvar k=0;k<32;k=k+1)begin:g_bank
 assign bank_dq_o[k*281+:281]={packet_i[280]&&!packet_i[279]&&destination==5'(k),packet_i[279:0]};
 end
endmodule
`default_nettype wire
