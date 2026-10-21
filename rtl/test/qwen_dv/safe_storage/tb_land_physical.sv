`timescale 1ns/1ps
module tb_land_physical #(parameter integer MUT=0);
reg ck=0,rsi=0;always #5 ck=~ck;integer cycle=0;
always@(negedge ck)begin cycle=cycle+1;rsi=(cycle>=8&&!(cycle>=701&&cycle<711));end
for(genvar dkind=0;dkind<3;dkind=dkind+1)begin:g_depth
 localparam integer D=(dkind==0)?2:(dkind==1)?4:8;
 for(genvar t=0;t<4;t=t+1)begin:g_width
  localparam integer W=(t==0)?1:(t==1)?32:(t==2)?97:1073;
  if(D==4||t!=3)begin:g_shape
   localparam integer C=(W+23)/24;
   reg[W-1:0] data_i=0;always@(negedge ck)for(integer b=0;b<W;b=b+1)data_i[b]=$random;
   for(genvar k=1;k<D;k=k+1)begin:g_k
    wire[D*W-1:0] bank_a,bank_b;wire[D*C-1:0] valid_a,valid_b;
    wire[D*($clog2(D)+1)-1:0] epo;wire[W-1:0] a,b;
    ot_pl_land_phys_chunk_w #(.W(W),.D(D),.CHUNK_BITS(24)) pw(.ck(ck),.rsi(rsi),.i(data_i),.bank(bank_a),.vld(valid_a));
    ot_pl_land_chunk_w #(.W(W),.D(D),.CHUNK_BITS(24)) rw(.ck(ck),.rsi(rsi),.i(data_i),.bank(bank_b),.epo(epo),.vld(valid_b));
    ot_pl_land_phys_chunk_r #(.W(W),.D(D),.K((MUT!=0&&D==4&&k==2)?3:k),.CHUNK_BITS(24)) pr(.ck(ck),.rsi(rsi),.bank(bank_a),.vld(valid_a),.o(a));
    ot_pl_land_chunk_r #(.W(W),.D(D),.K(k),.CHUNK_BITS(24)) rr(.ck(ck),.rsi(rsi),.bank(bank_b),.epo(epo),.vld(valid_b),.o(b));
    always@(posedge ck)begin #1;if({bank_a,valid_a,a}!=={bank_b,valid_b,b})$fatal(1,"PHYSICAL_RING_MISMATCH W%0d D%0d K%0d edge%0d",W,D,k,cycle);end
    for(genvar c=0;c<C;c=c+1)begin:g_state
     always@(posedge ck)begin #1;
      if({pw.g_chunk[c].u_local.rq,pw.g_chunk[c].u_local.write_oh,pw.g_chunk[c].u_local.valid}!=={rw.g_chunk[c].u_local.rq,rw.g_chunk[c].u_local.write_oh,rw.g_chunk[c].u_local.valid})$fatal(1,"PHYSICAL_WRITER_STATE");
      if(MUT==0&&{pr.g_chunk[c].u_local.rq,pr.g_chunk[c].u_local.rc,pr.g_chunk[c].u_local.warm,pr.g_chunk[c].u_local.read_oh}!=={rr.g_chunk[c].u_local.rq,rr.g_chunk[c].u_local.rc,rr.g_chunk[c].u_local.warm,rr.g_chunk[c].u_local.read_oh})$fatal(1,"PHYSICAL_READER_STATE");
     end
    end
   end
  end
 end
end
initial begin repeat(1600)@(negedge ck);$display("PHYSICAL_RING_EQ PASS1600edges tworesets D2/4/8 allK widths1/32/97 plusD4W1073 bank/vld/output/functionalwriter+readerstate");$finish;end
endmodule
