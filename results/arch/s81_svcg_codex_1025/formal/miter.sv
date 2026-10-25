module miter #(parameter MUT=0)(input ck,input rn,input v,input [3:0] d);
wire [3:0] link;wire rv,tf,rf;wire[3:0] rd;
dsdv_svc_f2b_tx #(.W(5),.MUT(MUT)) tx(ck,rn,v,d,link,tf);
dsdv_svc_f2b_rx #(.W(5)) rx(ck,rn,link,rv,rd,rf);
reg [2:0] vv;reg[3:0] dd0,dd1,dd2;reg[3:0] age=0;reg pv=0;
always @(posedge ck) begin
age<=age+1;pv<=v;vv<={vv[1:0],v};dd0<=d;dd1<=dd0;dd2<=dd1;
if(age<2) assume(!rn);else assume(rn);
assume(!v || !pv);
if(age>6 && age<14)begin assert(rv==vv[2]);if(rv)assert(rd==dd2);assert(!tf);assert(!rf);end
end
endmodule
