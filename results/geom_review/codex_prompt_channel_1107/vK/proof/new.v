module old_ref(input ck,rst,d,output reg u_program__fault,hrfp_u_program__fault_0_internal_state);
wire rr_p_l3=rst,rr_p_l5=rst;wire _3129_=d;
always @(posedge ck, negedge rr_p_l5)
    if (!rr_p_l5) hrfp_u_program__fault_0_internal_state <= 1'h0;
    else hrfp_u_program__fault_0_internal_state <= _3129_;
always @(posedge ck, negedge rr_p_l3)
    if (!rr_p_l3) u_program__fault <= 1'h0;
    else u_program__fault <= _3129_;
endmodule
module candidate(input ck,rst,d,output reg u_program__fault,hrfp_u_program__fault_0_internal_state);
wire rr_p_l3=rst,rr_p_l5=rst;wire _3129_=d;
always @(posedge ck, negedge rr_p_l5)
    if (!rr_p_l5) hrfp_u_program__fault_0_internal_state <= 1'h0;
    else hrfp_u_program__fault_0_internal_state <= _3129_;
always @(posedge ck, negedge rr_p_l3)
    if (!rr_p_l3) u_program__fault <= 1'h0;
    else u_program__fault <= hrfp_u_program__fault_0_internal_state;
endmodule
module tb;
reg ck=0,rst=0,d=0;wire oq,os,nq,ns;integer count=0,errors=0;reg expected=0;
always #5 ck=~ck;
old_ref o(ck,rst,d,oq,os);candidate n(ck,rst,d,nq,ns);
always @(posedge ck) begin
 if(!rst)expected=0; else expected=oq;
 #1;
 if(nq!==expected || ns!==os) begin errors=errors+1; if(errors<4)$display("DIFF cycle%0d old%0b new%0b expected%0b state%0b/%0b",count,oq,nq,expected,os,ns);end
 count=count+1;
end
initial begin
 // First fault, sticky fault, deasserted fault, reset during active fault, and repeated reset pulses.
 #2;rst=0;#11;rst=1;d=1;#20;d=1;#20;d=0;#20;d=1;#7;rst=0;#1;
 if(nq!==0 || ns!==0)begin $display("ASYNC RESET FAIL");$fatal;end
 #6;rst=1;d=1;#30;
 repeat(256)begin @(negedge ck);d=$random;if((count%31)==0)rst=0;else rst=1;end
 @(negedge ck);rst=0;#1;if(nq!==0 || ns!==0)$fatal;
 #20;$display("LOCKSTEP cycles%0d errors%0d",count,errors);if(errors)$fatal; $finish;
end
endmodule
