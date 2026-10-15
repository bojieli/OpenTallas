`timescale 1ps/1ps
module tb_dsfd_vm_static_xio;
reg cks=0,ck=0,rss=0,rst=0; always #417 cks=~cks; always #556 ck=~ck;
reg [14:0] rq=0; reg [2203:0] cvm=0; wire [512:0] rs; wire [3:0] av,wv; wire [55:0] ar,wr; wire [2047:0] wd; wire[63:0] wm; reg[3:0] ev=0;reg [2047:0] ed=0;wire fault; wire [31:0] wt;
reg[3:0] pv[0:12]; reg[2047:0] pd[0:12]; integer i,k,n=0,got=0;
dsfd_vm_static_xio d(.cks(cks),.rss(rss),.ck(ck),.rst(rst),.n_v(1'b0),.n_d(84'd0),.a_v(av),.a_row(ar),.e_v(ev),.e_d(ed),.f_collective(cvm),.f_crq(rq),.t_crs(rs),.w_v(wv),.w_row(wr),.w_d(wd),.w_m(wm),.w_t(wt),.f_xgo(11'd0),.qSWs(3'b011),.fault(fault));
always @(posedge cks) begin
 pv[0]<=av; for(k=0;k<4;k=k+1) pd[0][512*k+:512]<={498'd0,ar[14*k+:14]};
 for(i=1;i<13;i=i+1) begin pv[i]<=pv[i-1];pd[i]<=pd[i-1];end
 ev<=pv[11];ed<=pd[11];
 #1;
 if(rss && n>=32 && n<160) begin
  if(!rs[0] || rs[512:1] !== 512'(n-12)) $fatal(1,"read latency data n%0d got %h",n,rs);
  got=got+1;
 end
 n=n+1;
end
initial begin
 for(i=0;i<13;i=i+1) begin pv[i]=0;pd[i]=0;end
 #13244;rss=1;rst=1;
 // Each tuple uses unrelated rows and masks; no landing pointer packing.
 for(k=0;k<4;k=k+1) cvm[551*k+:551]={8'(40+k),512'(100+k),16'(16'h8110+k),14'(777+101*k),1'b1};
 #1;
 for(k=0;k<4;k=k+1) if(wt[8*k+:8]!==8'(40+k)||!wv[k]||wr[14*k+:14]!==14'(777+101*k)||wm[16*k+:16]!==16'(16'h8110+k)||wd[512*k+:512]!==512'(100+k)) $fatal(1,"tuple %0d",k);
 while(n<180) begin @(negedge cks); rq={14'(n),1'b1};end
 #2; $display("TB_XIO PASS tuples/tags and %0d consecutive L12 reads",got);$finish;
end
endmodule
