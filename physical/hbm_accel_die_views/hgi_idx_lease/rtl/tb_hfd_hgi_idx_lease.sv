`timescale 1ns/1ps
module tb;
reg ck=0;always #5 ck=~ck;reg rst=1;reg[1818:0] rec=0;reg[73:0] lease=0;
wire[75:0] ev;wire[89:0] fs;wire[2:0] ret;wire[337:0] vmq;
hfd_hgi_idx_lease d(.ck(ck),.rst(rst),.f_hgi_cmdproc(rec),.f_index_lease(lease),.t_index_lease(ev),.t_hgi_cmdproc(ret),.t_hgi_vmq(vmq),.t_sel_fs(fs),.f_hgi_vmr(274'd0),.f_sel_co(72'd0),.f_sel_ev(2'd0),.f_sel_qbr(1'b0),.f_sel_to(612'd0));
integer mode=0,i,accepted=0,completed=0,faults=0,frames=0;reg[72:0] frame=(73'd7<<53)|(73'd5<<32)|73'd42;
always @(posedge ck)begin #1;
 if(ev[0])begin accepted=accepted+1;if(ev[75:3]!==frame)$fatal(1,"accepted frame");end
 if(ev[1])begin completed=completed+1;if(ev[75:3]!==frame)$fatal(1,"done frame");end
 if(ev[2])faults=faults+1;
 if(fs[0])begin frames=frames+1;if(fs[32:1]!=42||fs[36:33]!=5||fs[56:37]!=7)$fatal(1,"native frame job/gen/pos");end
end
initial begin
 if(!$value$plusargs("MODE=%d",mode))mode=0;
 repeat(12)@(negedge ck);rst=0;repeat(12)@(negedge ck);
 rec[0]=1;rec[32:1]=2;rec[64:33]=40;rec[76:65]=1;rec[100:94]=7'b0010011;rec[1810:1791]=7;
 rec[129+:2]=1;rec[177+:20]=4096;rec[197+:20]=1;rec[385+:2]=1;rec[1153+:2]=1;rec[1155+:3]=5;
 lease={frame,1'b1};if(mode==1)lease[0]=0;if(mode==2)lease[73:54]=8;
 repeat(12)@(negedge ck);
 if(mode==0)begin
  d.u_ix.u_index.st=4;d.u_ix.u_index.kgap=0;@(negedge ck);
  repeat(6)@(negedge ck);force d.u_ix.x_done=1;@(negedge ck);release d.u_ix.x_done;
  repeat(12)@(negedge ck);if(accepted!=1||completed!=1||faults!=0||frames!=1)$fatal(1,"event counts a%0d d%0d f%0d frames%0d",accepted,completed,faults,frames);
 end else if(mode==3)begin
  force d.u_ix.held_lease_bar=73'd0;repeat(8)@(negedge ck);
  if(accepted!=1||faults!=1||completed!=0)$fatal(1,"corruption events");
 end else begin
  if(accepted!=0||completed!=0||faults!=1||vmq[337])$fatal(1,"invalid metadata accepted");
 end
 $display("PASS actual lease metadata MODE%0d captures3/launch3 a%0d d%0d f%0d",mode,accepted,completed,faults);$finish;
end endmodule
