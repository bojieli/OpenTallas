// A distinct, coherent publisher for the existing u_gi core-clock tuple.
// No HR clock enters this block. STAGES is priced in core rising edges.
module qfd_hp13_corepub39 #(parameter integer STAGES=1)(
 input wire ck, input wire[38:0] i, output wire[38:0] o
);
 (* keep=1 *) reg[38:0] q[0:STAGES-1];
 integer k;
 always @(posedge ck) begin
  q[0] <= i;
  for(k=1;k<STAGES;k=k+1) q[k] <= q[k-1];
 end
 assign o=q[STAGES-1];
 initial if(STAGES<1 || STAGES>2) $fatal(1,"core publisher STAGES must be 1 or 2");
endmodule
