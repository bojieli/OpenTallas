`timescale 1ns/1ps
module tb;
reg clk=0;always #5 clk=~clk;reg rst_n=0;reg [611:0] to=0;reg [71:0] co=0;
wire done,fault,toc,coc;wire [337:0] vmq;wire [89:0] fs;wire [1047:0] qb;wire [344:0] kin;
`ifdef LEGACY
 ot_hgi_idx_index
`else
 ot_hgi_idx_index_native
`endif
 d(.clk(clk),.rst_n(rst_n),.go(1'b0),.k(12'd1),.cand_en(1'b1),.keep_en(1'b0),.n(32'd0),.rank(7'd0),.pos(20'd0),.a_base(18'd0),.b_base(18'd0),.c_base(18'd0),.o_base(18'd0),.r_base(18'd0),.d_base(18'd0),.d_stride(18'd0),.c_stride(18'd0),.c_n(12'd0),.has_r(1'b0),.done(done),.fault(fault),.vmq(vmq),.vmr(274'd0),.fs(fs),.qb(qb),.qbr(1'b0),.kin(kin),.to(to),.toc(toc),.co(co),.coc(coc),.ev(2'd0));
integer i,tc=0,cc=0;always @(posedge clk)begin
if(d.st==5 && d.tfn!=0 && d.tl==15 && !d.pk_full[0] && d.th[292+:20]!==tc) $fatal(1,"topk FIFO order");
if(d.st==5 && d.cfn!=0 && d.cl==1 && !d.pk_full[2] && d.ch[38+:17]!==cc) $fatal(1,"candidate FIFO order");
#1;if(toc)tc=tc+1;if(coc)cc=cc+1;end
initial begin repeat(3)@(negedge clk);rst_n=1;@(negedge clk);
d.st=5;d.bad=0;d.qblk=128;d.qfull=0;d.qcred=0;d.a_req=512;d.sel_done=1;d.to_last=0;d.co_last=0;d.tl=0;d.cl=0;d.nout=0;d.ncand=0;
force d.wp_v=1'b0; // No valid lanes: suppress artificial packer requests while forced blocked.
force d.pk_full=4'b1111;
for(i=0;i<8;i=i+1)begin to=0;co=0;to[0]=1;co[0]=1;to[292+:20]=i;co[38+:17]=i;to[1]=(i==7);co[1]=(i==7);@(negedge clk);end
to=0;co=0;
`ifdef OVERFLOW
 to[0]=1;co[0]=1;@(negedge clk);to=0;co=0;
`endif
release d.pk_full;d.pk_full=0;
for(i=0;i<300;i=i+1)begin @(negedge clk);
`ifdef OVERFLOW
 if(fault)begin $display("PASS refused ninth beat beyond eight credits");$finish;end
`else
 if(fault)$fatal(1,"unexpected fault");if(done)begin if(tc!=8||cc!=8)$fatal(1,"lost credits %0d %0d",tc,cc);$display("PASS drain eight full credited beats topk+candidate");$finish;end
`endif
end $fatal(1,"full eight-beat FIFO failed to drain tc%0d cc%0d",tc,cc);end
endmodule
