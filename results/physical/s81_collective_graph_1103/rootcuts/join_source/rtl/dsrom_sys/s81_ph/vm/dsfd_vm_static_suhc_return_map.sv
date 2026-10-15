`timescale 1ns/1ps
// Fixed-edge native identity restoration after compiler release. Combinational
// leaf; no storage, waiting or schedule extension. Fourteen SU lanes are wires;
// only sparse SU0/1 and HC0/1 use bounded selector muxes. Compiler selectors
// arrive on the exact return edge; unsupported immutable-template maps fault.
module dsfd_vm_static_suhc_return_map #(parameter integer DW=128)(
 input wire [31:0] i_v,input wire [32*DW-1:0] i_data,
 input wire [17:0] expected_v,input wire [89:0] release_slot,
 output wire [17:0] o_v,output wire [18*DW-1:0] o_data,output wire fault
);
 wire [17:0] bad;
 genvar p;generate for(p=0;p<18;p=p+1)begin:port_map
  reg [DW-1:0] d;reg valid,legal;integer k;
  always @*begin
   d=0;valid=0;legal=0;
   for(k=0;k<32;k=k+1)begin
    if((p==0 &&k<4)||(p==1 &&k<8)||(p>=2 &&p<16 &&k==p)||(p>=16 &&k>=16 &&k<20))begin
     if(release_slot[5*p+:5]==k)begin legal=1;
`ifdef OT_VM_SUHC_MAP_MUT_SELECT
     d=d|i_data[DW*(k^1)+:DW];
`else
     d=d|i_data[DW*k+:DW];
`endif
valid=valid|i_v[k];end
    end
   end
  end
  assign o_data[DW*p+:DW]=d;assign o_v[p]=expected_v[p]&&legal&&valid;
  assign bad[p]=expected_v[p]&&(!legal||!valid);
 end endgenerate
 assign fault=|bad;
endmodule
