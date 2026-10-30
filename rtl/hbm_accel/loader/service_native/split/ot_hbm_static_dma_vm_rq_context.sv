`default_nettype none
// Parent-local VM read namespace adapter for the existing BACK engine.
// BACK .stk remains the physical HBM stack (currently2 on both northern
// engines). Its ordinary read sector embeds that stack in the VM SID field;
// the receiving geographic VM bank instead requires its own SID. Rewrite only
// that context field. Mirror requests keep their mandatory zero SID field and
// retain all existing local-mirror semantics. Zero cycles, no arbitration.
// R7: strap_vm_qid is a physical quasi-static ID pin, no pin register; the
// parent must declare its value, tie it at the pin and false-path it. All four
// values are supported by this same master. This does NOT convert a global VM
// word to the BACK-local operand namespace or change HBM address checking.
module ot_hbm_static_dma_vm_rq_context #(parameter integer NB=8)(
 input wire [NB*17-1:0] rq_i,
 input wire [1:0] strap_vm_qid,
 output wire [NB*17-1:0] rq_o
);
 genvar b;
 generate for(b=0;b<NB;b=b+1)begin:g_bank
   wire [16:0] p=rq_i[b*17+:17];
   assign rq_o[b*17+:17]={p[16],p[15],p[15]?p[14:13]:strap_vm_qid,p[12:0]};
 end endgenerate
endmodule
`default_nettype wire
