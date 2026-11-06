module baseline(input[7:0]a,b,output[7:0]y);assign y=a*b;endmodule
module candidate(input[7:0]p00,p10,p01,p11,output[7:0]y);assign y=p00+{p10[3:0],4'd0}+{p01[3:0],4'd0};endmodule
