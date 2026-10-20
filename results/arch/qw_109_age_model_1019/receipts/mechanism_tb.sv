`timescale 1ns/1ps
module age_case #(parameter ID=0,KIND=0,W=512,N=1,K=3,E=1,G=22,R0=1596)(input ck,output reg done=0,output reg failed=0);
integer tick=0,checks=0,misses=0;always @(negedge ck)tick<=tick+1;
wire srst=((tick>=G-1)&&(tick<2400))||(tick>=2400+G-1);
wire rrst=((tick>=R0)&&(tick<2400))||(tick>=2400+R0);
reg[31:0]pattern=0;always @(negedge ck)pattern<=tick*32'h10001+32'h0a53;
wire[W-1:0]source_pin;original_publish #(.KIND(KIND),.W(W)) src(.ck(ck),.rst(srst),.pattern(pattern),.pin(source_pin));
reg[W-1:0]extra;
always @(posedge ck)extra<=source_pin;
`ifdef MUT_STAGE
wire[W-1:0]launch=extra;
`else
wire[W-1:0]launch=source_pin;
`endif
`ifdef MUT_K
wire[2:0]strap=K[2:0]^3'd1;
`else
wire[2:0]strap=K[2:0];
`endif
wire[W-1:0]data[0:N];wire fck[0:N];wire epoch[0:N];assign data[0]=launch;assign fck[0]=ck;assign epoch[0]=srst;
wire[W-1:0]dest_pin;
genvar j;generate for(j=0;j<N;j=j+1)begin:g_lane
 if(j==N-1)begin:g_last
 ot_qfd_land #(.W(W),.FIRST(N==1)) l(.ckf(fck[j]),.ea(epoch[j]),.i(data[j]),.ck(ck),.rs(rrst),.k(strap),.o(dest_pin),.fault());
 end else begin:g_station
 ot_qfd_lane_st #(.W(W),.FIRST(j==0)) s(.ck(fck[j]),.en(epoch[j]),.a(data[j]),.b(data[j+1]),.eb(epoch[j+1]),.ck_o(fck[j+1]));
 end
end endgenerate
reg[W-1:0]history[0:5000];integer t=0;integer start;
always @(posedge ck)begin
 #0.1;history[t]=source_pin;
 start=(G>R0?G:R0)+80;
 if((tick>=start&&tick<start+256)||(tick>=2400+start&&tick<2400+start+256))begin
 checks=checks+1;
 if(dest_pin!==history[t-E-1])begin
 misses=misses+1;
 if(misses==1)$display("AGE_FIRST_FAIL id=%0d t=%0d N=%0d E=%0d K=%0d G=%0d R0=%0d src=%h dest=%h expected=%h",ID,t,N,E,K,G,R0,source_pin,dest_pin,history[t-E-1]);
 end
 end
 if(t==4800)begin failed=(misses!=0);done=1;$display("AGE_CASE id=%0d checks=%0d mismatches=%0d scope=ideal_root_register_cone",ID,checks,misses);end
 t=t+1;
end
endmodule
module mechanism_tb;
reg ck=0;always #5 ck=~ck;wire[5:0]done,failed;
age_case #(.ID(0),.KIND(0),.W(512),.N(1),.K(3),.E(1),.G(22),.R0(1596))a(.ck(ck),.done(done[0]),.failed(failed[0]));
age_case #(.ID(1),.KIND(1),.W(32),.N(4),.K(5),.E(3),.G(22),.R0(20))b(.ck(ck),.done(done[1]),.failed(failed[1]));
age_case #(.ID(2),.KIND(2),.W(1),.N(1),.K(6),.E(1),.G(1267),.R0(670))c(.ck(ck),.done(done[2]),.failed(failed[2]));
age_case #(.ID(3),.KIND(3),.W(1),.N(1),.K(6),.E(1),.G(671),.R0(1266))d(.ck(ck),.done(done[3]),.failed(failed[3]));
age_case #(.ID(4),.KIND(4),.W(512),.N(3),.K(7),.E(2),.G(1267),.R0(670))e(.ck(ck),.done(done[4]),.failed(failed[4]));
age_case #(.ID(7),.KIND(7),.W(73),.N(26),.K(6),.E(19),.G(1333),.R0(1266))f(.ck(ck),.done(done[5]),.failed(failed[5]));
initial begin wait(&done);if(|failed)$fatal(1,"AGE_MECHANISM_FAIL cases=%b",failed);$display("AGE_MECHANISM_PASS cases=6 checks=3072 resets=2 physical_phase=UNKNOWN hard_child_age=UNKNOWN");$finish;end
endmodule
