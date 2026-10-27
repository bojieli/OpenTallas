module cal_cmd(input [15:0] beat, input [93:0] current, output [47:0] y);
 assign y = {(beat+16'd1==current[47:32]),current[79:64]+16'(beat*4),current[63:48]+16'(beat*4)+16'd1,current[93:86],current[85:80],1'b1};
endmodule
