`timescale 1ns/1ps
// Actual53sources,16dispatch,128depth3storage. Scoreboard is derived directly
// from the documented source P -> scatter sample P+6+same-bank prefix lane (registered write edge, 2026-10-15).
module tb_dsfd_vm_static_wsched_roots;
 localparam integer N=53, END=1700;
 reg ck=0,rst_n=0,skip=0;always #5 ck=~ck;
 wire payload0=ck && !skip;
 reg [N-1:0] iv=0;reg[14*N-1:0] ir=0;reg[16*N-1:0] im=0;reg[512*N-1:0] id=0;reg[8*N-1:0] it=0;
 wire[31:0] ov;wire[447:0] orow;wire[511:0] om;wire[16383:0] od;wire[255:0] ot;wire fault;
 dsfd_vm_static_wsched #(.NSRC(N)) u(.ck_control(ck),.ck_header(ck),.ck_payload({ck,ck,ck,payload0}),
 .ck_dispatch({16{ck}}),.ck_stage({128{ck}}),
 .rst_control_n(rst_n),.rst_header_n(rst_n),.rst_payload_n({4{rst_n}}),.rst_dispatch_n({16{rst_n}}),.rst_stage_n({128{rst_n}}),.i_v(iv),.i_row(ir),.i_mask(im),.i_data(id),.i_tag(it),
 .wq_v(ov),.wq_row(orow),.wq_mask(om),.wq_data(od),.wq_tag(ot),.fault(fault));
 reg[31:0] xv[0:END+20];reg[447:0] xr[0:END+20];reg[511:0] xm[0:END+20];
 reg[16383:0] xd[0:END+20];reg[255:0] xt[0:END+20];
 integer cy=0,batch=0,bad=0,got=0,sent=0,mode=0,k,c,b,l,j,hi,row,due,w;
 initial begin
  if(!$value$plusargs("mode=%d",mode))mode=0;
  for(k=0;k<=END+20;k=k+1)begin xv[k]=0;xr[k]=0;xm[k]=0;xd[k]=0;xt[k]=0;end
 end
 always @(negedge ck) begin
  rst_n=(cy>=8);iv=0;skip=0;
  if(cy>=20 && cy<END-20 && (cy-20)%8==0)begin
   for(c=0;c<N;c=c+1)begin
    b=(c/3+batch*7)%32;l=c%3;hi=(c*13+batch*17)%512;
    row=32*hi+(b^((hi%8)*4));j=8*(b%4)+b/4;due=cy+1+6+l;
    iv[c]=1;ir[14*c+:14]=14'(row);im[16*c+:16]=16'((c*701+batch*13)^16'ha56c);it[8*c+:8]=8'(batch+c);
    for(w=0;w<16;w=w+1)id[512*c+32*w+:32]=32'((batch<<20)^(c<<10)^w^32'h7be125a0);
    if(xv[due][j])$fatal(1,"scoreboard collision");
    xv[due][j]=1;xr[due][14*j+:14]=ir[14*c+:14];xm[due][16*j+:16]=im[16*c+:16];
    xd[due][512*j+:512]=id[512*c+:512];xt[due][8*j+:8]=it[8*c+:8];sent=sent+1;
   end
   batch=batch+1;
  end
  if(mode==1 && cy==101)skip=1;
 end
 always @(posedge ck)begin
  cy=cy+1;
  if(cy>=20)begin
   if(ov!==xv[cy])begin bad=bad+1;if(bad<4)$display("valid mismatch edge %0d got %h exp %h",cy,ov,xv[cy]);end
   for(integer p=0;p<32;p=p+1)if(xv[cy][p])begin
    got=got+1;
    if(orow[14*p+:14]!==xr[cy][14*p+:14]||om[16*p+:16]!==xm[cy][16*p+:16]||od[512*p+:512]!==xd[cy][512*p+:512]||ot[8*p+:8]!==xt[cy][8*p+:8])begin
     bad=bad+1;if(bad<4)$display("record mismatch edge %0d port %0d",cy,p);
    end
   end
  end
  if(cy==END)begin
   $display("WRITE_ROOTS_RESULT sent=%0d got=%0d bad=%0d fault=%b own=%b",sent,got,bad,fault,u.own);
   if(mode==1)begin if(!fault||!u.own[2])$fatal(1,"missing clock alignment fault");$display("CLOCK_FAULT_PASS");end
   else if(bad==0 && !fault && got==sent && got>10000)$display("PASS");else $display("FAIL");
   $finish;
  end
 end
endmodule
