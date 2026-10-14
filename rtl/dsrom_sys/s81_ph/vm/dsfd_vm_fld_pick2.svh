// Optional stateless first-two selector; index0 has highest priority.
module dsfd_vm_fld_pick2 #(parameter integer N=6)
 (input wire[N-1:0] req,output wire[N-1:0] first,second);
 generate for(genvar k=0;k<N;k=k+1) begin:g_k
  localparam[N-1:0] BEFORE=({{(N-1){1'b0}},1'b1}<<k)-1'b1;
  wire[N*N-1:0] pairs;
  for(genvar a=0;a<N;a=a+1) begin:g_a
   for(genvar b=0;b<N;b=b+1) begin:g_b
    assign pairs[a*N+b]=(a<k && b<a) ? (req[a]&req[b]) : 1'b0;
   end
  end
  assign first[k]=req[k] && !(| (req&BEFORE));
  assign second[k]=req[k] && (| (req&BEFORE)) && !(|pairs);
 end endgenerate
endmodule
