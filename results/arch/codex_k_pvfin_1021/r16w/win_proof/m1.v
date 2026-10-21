module m(input[15:0]x,lo,output same);
 function automatic gold(input [15:0] x,input [15:0] lo);gold=(x>=lo)&&(x<lo+16'd32);endfunction

function automatic dut(input [15:0] x,input [15:0] lo);
  reg low_ge;
  reg [10:0] next_hi;
  begin
   low_ge=(x[4:0]>=lo[4:0]);
   next_hi=lo[15:5]+11'd1;
   dut=(lo[15:5]!=11'h7ff)&&
       (((x[15:5]==lo[15:5])&&!low_ge)||((x[15:5]==next_hi)&&!low_ge));
  end
 endfunction
assign same=(gold(x,lo)==dut(x,lo));
endmodule
