`default_nettype none
// Opt-in field adapter. Legacy sector bit15 is MIRROR, not regular row10.
// All payload/mask/tag bits and registered edges stay unchanged. Native-only
// high regular addresses require a genuine18-bit client, never this lift.
module ot_vms_legacy_r2048_fields #(
 parameter integer RG=5,WG=2,MUT=0
)(
 input wire[RG*17-1:0]legacy_rq,output wire[RG*18-1:0]native_rq,
 input wire[WG*281-1:0]legacy_wq,output wire[WG*282-1:0]native_wq,
 input wire[280:0]legacy_dq,legacy_kq,output wire[281:0]native_dq,native_kq,
 input wire[275:0]legacy_xq,legacy_xq2,output wire[276:0]native_xq,native_xq2,
 input wire[284:0]legacy_pq,output wire[285:0]native_pq,
 input wire[276:0]native_eg,output wire[275:0]legacy_eg,
 input wire[17:0]native_status,output wire[17:0]legacy_status
);
 for(genvar g=0;g<RG;g=g+1)begin:g_rq
  assign native_rq[g*18+:18]=(MUT==1)?{1'b0,legacy_rq[g*17+:17]}:
      {legacy_rq[g*17+15+:2],1'b0,legacy_rq[g*17+:15]};
 end
 for(genvar g=0;g<WG;g=g+1)begin:g_wq
  assign native_wq[g*282+:282]={legacy_wq[g*281+279+:2],1'b0,legacy_wq[g*281+:279]};
 end
 assign native_dq={legacy_dq[280:279],1'b0,legacy_dq[278:0]};
 assign native_kq={legacy_kq[280:279],1'b0,legacy_kq[278:0]};
 assign native_xq={legacy_xq[275:274],1'b0,legacy_xq[273:0]};
 assign native_xq2={legacy_xq2[275:274],1'b0,legacy_xq2[273:0]};
 assign native_pq={legacy_pq[284:282],1'b0,legacy_pq[281:0]};
 // Reverse narrowing cannot represent a high regular row. Suppress its
 // valid and publish an error through the EXISTING status fault bit17.
 // CE/UE and every payload/tag bit retain their original positions.
 wire bad_eg=(MUT==2)?1'b0:(native_eg[276]&&native_eg[274]);
 assign legacy_eg={native_eg[276]&&!bad_eg,native_eg[275],native_eg[273:0]};
 assign legacy_status=native_status|{bad_eg,17'd0};
endmodule
`default_nettype wire
