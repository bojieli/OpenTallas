`timescale 1ns/1ps
module tb;
localparam RL=80;
reg ck=0;always #5 ck=~ck;
reg rst_n=0,kgo=0;reg [15:0] epoch=7;reg [5:0] layer=1;reg [16:0] rq=0;reg [1023:0] data=0;
reg [RL-1:0] pv=0;reg [13:0] pt[0:RL-1];reg [15:0] pe[0:RL-1];reg [5:0] pl[0:RL-1];
integer i,c,checks=0,mutdiff=0,requests=0,clean=0;
wire qv0,qk0,f0;wire [13:0]qt0;wire [15:0]qe0;wire [5:0]ql0;wire [1024:0]rs0;
old_issuer #(.RESPONSE_LAT(RL)) u0( .ck(ck),.rst_n(rst_n),.kgo(kgo),.epoch(epoch),.layer(layer),.rq(rq),.req_valid(qv0),.req_t(qt0),.req_v(qk0),.req_epoch(qe0),.req_layer(ql0),.rsp_valid(pv[RL-1]),.rsp_data(data),.rsp_t(pt[RL-1]),.rsp_v(1'b0),.rsp_epoch(pe[RL-1]),.rsp_layer(pl[RL-1]),.rs(rs0),.fault(f0));
wire qv1,qk1,f1;wire [13:0]qt1;wire [15:0]qe1;wire [5:0]ql1;wire [1024:0]rs1;
new_issuer #(.RESPONSE_LAT(RL)) u1( .ck(ck),.rst_n(rst_n),.kgo(kgo),.epoch(epoch),.layer(layer),.rq(rq),.req_valid(qv1),.req_t(qt1),.req_v(qk1),.req_epoch(qe1),.req_layer(ql1),.rsp_valid(pv[RL-1]),.rsp_data(data),.rsp_t(pt[RL-1]),.rsp_v(1'b0),.rsp_epoch(pe[RL-1]),.rsp_layer(pl[RL-1]),.rs(rs1),.fault(f1));
wire qv2,qk2,f2;wire [13:0]qt2;wire [15:0]qe2;wire [5:0]ql2;wire [1024:0]rs2;
mutant_issuer #(.RESPONSE_LAT(RL)) u2( .ck(ck),.rst_n(rst_n),.kgo(kgo),.epoch(epoch),.layer(layer),.rq(rq),.req_valid(qv2),.req_t(qt2),.req_v(qk2),.req_epoch(qe2),.req_layer(ql2),.rsp_valid(pv[RL-1]),.rsp_data(data),.rsp_t(pt[RL-1]),.rsp_v(1'b0),.rsp_epoch(pe[RL-1]),.rsp_layer(pl[RL-1]),.rs(rs2),.fault(f2));
always @(posedge ck)begin
 pv[0]<=qv1;pt[0]<=qt1;pe[0]<=qe1;pl[0]<=ql1;
 for(i=1;i<RL;i=i+1)begin pv[i]<=pv[i-1];pt[i]<=pt[i-1];pe[i]<=pe[i-1];pl[i]<=pl[i-1];end
end
initial begin
 for(i=0;i<RL;i=i+1)begin pt[i]=0;pe[i]=0;pl[i]=0;end
 for(c=0;c<900;c=c+1)begin
 @(negedge ck);
 rst_n=(c>=16 && !(c>=430 && c<446));
 kgo=(c==120 || c==550);
 rq=0;
 if((c>130 && c<380 || c>560 && c<800)&&c%5==0)begin rq={1'b1,13'(c%1024),3'b001};requests=requests+1;end
 data={32{32'(c*37)}};
 @(posedge ck);#1;
 if(c>120)begin
 checks=checks+1;
 if({qv0,qt0,qk0,qe0,ql0,rs0,f0} !== {qv1,qt1,qk1,qe1,ql1,rs1,f1})$fatal(1,"lockstep c=%0d oldfault=%b newfault=%b",c,f0,f1);
 if(f1===1'b0)clean=clean+1;
 if(f2!==f1)mutdiff=mutdiff+1;
 end
 end
 if(mutdiff<10 || clean<200 || requests<80)$fatal(1,"inadequate stimulus requests=%0d clean=%0d mutant=%0d",requests,clean,mutdiff);
 $display("PASS checks=%0d requests=%0d clean=%0d mutant_caught=%0d",checks,requests,clean,mutdiff);$finish;
end
endmodule
