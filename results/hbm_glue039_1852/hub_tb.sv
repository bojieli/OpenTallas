`timescale 1ns/1ps
module hub_tb #(parameter integer NC=0);localparam integer N=NC+1,CW=(NC<1)?1:$clog2(N);reg clk=0;always #5 clk=~clk;integer checks=0,bad=0,mut=0;
reg [(1)-1:0] rst_n=0;
reg [(2)-1:0] sid=0;
reg [(N*338)-1:0] cq=0;
reg [(N*2)-1:0] client_seq=0;
reg [(8)-1:0] bank_enable=0;
reg [(8*CW)-1:0] bank_client=0;
reg [(1)-1:0] cw_enable=0;
reg [(CW)-1:0] cw_client=0;
reg [(1)-1:0] ccw_enable=0;
reg [(CW)-1:0] ccw_client=0;
reg [(8*266)-1:0] pr=0;
reg [(264)-1:0] cco0=0;
reg [(264)-1:0] cco1=0;
reg [(N)-1:0] response_enable=0;
reg [(N*2)-1:0] response_seq=0;
wire [(N*274)-1:0] g_cr;
wire [(8*285)-1:0] g_pq;
wire [(290)-1:0] g_cwi;
wire [(290)-1:0] g_cci;
wire [(3)-1:0] g_status;
wire [(N*274)-1:0] d_cr;
wire [(8*285)-1:0] d_pq;
wire [(290)-1:0] d_cwi;
wire [(290)-1:0] d_cci;
wire [(3)-1:0] d_status;
wire [(N*274)-1:0] m_cr;
wire [(8*285)-1:0] m_pq;
wire [(290)-1:0] m_cwi;
wire [(290)-1:0] m_cci;
wire [(3)-1:0] m_status;
ot_vms_hub_reference #(.NC(NC)) g (.clk(clk),.rst_n(rst_n),.sid(sid),.cq(cq),.client_seq(client_seq),.bank_enable(bank_enable),.bank_client(bank_client),.cw_enable(cw_enable),.cw_client(cw_client),.ccw_enable(ccw_enable),.ccw_client(ccw_client),.pr(pr),.cco0(cco0),.cco1(cco1),.response_enable(response_enable),.response_seq(response_seq),.cr(g_cr),.pq(g_pq),.cwi(g_cwi),.cci(g_cci),.status(g_status));
ot_vms_hub_static #(.NC(NC),.LOCAL_RETURN_REGIONS(1)) d (.clk(clk),.rst_n(rst_n),.sid(sid),.cq(cq),.client_seq(client_seq),.bank_enable(bank_enable),.bank_client(bank_client),.cw_enable(cw_enable),.cw_client(cw_client),.ccw_enable(ccw_enable),.ccw_client(ccw_client),.pr(pr),.cco0(cco0),.cco1(cco1),.response_enable(response_enable),.response_seq(response_seq),.cr(d_cr),.pq(d_pq),.cwi(d_cwi),.cci(d_cci),.status(d_status));
ot_vms_hub_mutant #(.NC(NC),.LOCAL_RETURN_REGIONS(1)) m (.clk(clk),.rst_n(rst_n),.sid(sid),.cq(cq),.client_seq(client_seq),.bank_enable(bank_enable),.bank_client(bank_client),.cw_enable(cw_enable),.cw_client(cw_client),.ccw_enable(ccw_enable),.ccw_client(ccw_client),.pr(pr),.cco0(cco0),.cco1(cco1),.response_enable(response_enable),.response_seq(response_seq),.cr(m_cr),.pq(m_pq),.cwi(m_cwi),.cci(m_cci),.status(m_status));
initial begin repeat(3) @(negedge clk);
for(integer c=0;c<4000;c=c+1) begin @(negedge clk);
for(integer j=0;j<(2);j=j+1) sid[j]=$random;
for(integer j=0;j<(N*338);j=j+1) cq[j]=$random;
for(integer j=0;j<(N*2);j=j+1) client_seq[j]=$random;
for(integer j=0;j<(8);j=j+1) bank_enable[j]=$random;
for(integer j=0;j<(8*CW);j=j+1) bank_client[j]=$random;
for(integer j=0;j<(1);j=j+1) cw_enable[j]=$random;
for(integer j=0;j<(CW);j=j+1) cw_client[j]=$random;
for(integer j=0;j<(1);j=j+1) ccw_enable[j]=$random;
for(integer j=0;j<(CW);j=j+1) ccw_client[j]=$random;
for(integer j=0;j<(8*266);j=j+1) pr[j]=$random;
for(integer j=0;j<(264);j=j+1) cco0[j]=$random;
for(integer j=0;j<(264);j=j+1) cco1[j]=$random;
for(integer j=0;j<(N);j=j+1) response_enable[j]=$random;
for(integer j=0;j<(N*2);j=j+1) response_seq[j]=$random;
for(integer b=0;b<8;b=b+1) begin pr[b*266+260+:4]=4'(c%N);pr[b*266+265]=1;end
response_enable='1;rst_n=(c%113!=0);
@(posedge clk);#1;checks=checks+1;
if({g_cr,g_pq,g_cwi,g_cci,g_status}!=={d_cr,d_pq,d_cwi,d_cci,d_status})begin bad=bad+1;if(bad<3)$display("HUB_MISMATCH %0d",c);end
if({g_cr,g_pq,g_cwi,g_cci,g_status}!=={m_cr,m_pq,m_cwi,m_cci,m_status})mut=mut+1;
end
$display("GLUE039_HUB NC=%0d checks=%0d mismatches=%0d mutant=%0d",NC,checks,bad,mut);if(bad||!mut)$fatal(1,"hub return region");$finish;end endmodule
