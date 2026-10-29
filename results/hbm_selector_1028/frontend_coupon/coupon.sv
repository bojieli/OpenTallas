module coupon #(parameter STRUCT=0,N=4,EW=37)(input [N-1:0] choose,input [N*EW-1:0] raw,input [2*N*EW-1:0] old,input [$clog2(2*N)-1:0] fill,output reg [2*N*EW-1:0] out);
if(STRUCT) begin:bounded
always @* out=old ^ {{N*EW{1'b0}},raw};
end else begin:legacy
integer f;
always @* begin
out=old;f=fill;
for(integer k=0;k<N;k=k+1)if(choose[k])begin out[f*EW+:EW]=raw[k*EW+:EW];f=f+1;end
end
end
endmodule
