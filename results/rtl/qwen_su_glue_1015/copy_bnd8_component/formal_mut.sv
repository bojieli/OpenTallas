module copy_bounds_formal(input[23:0]base,input[6:0]count,output equal);
 function automatic bounds_bad(input [23:0] base,input [6:0] count);
 reg [7:0] low_sum;
 begin
 low_sum={1'b0,base[12:6]}+{1'b0,count};
 bounds_bad=(|base[23:13]) && low_sum[7] && ((|low_sum[6:0]) || (|base[5:0]));
 end
 endfunction
wire old_bad={1'b0,base}+({18'd0,count}<<6)>25'h1000000;
assign equal=(old_bad==bounds_bad(base,count));
endmodule
