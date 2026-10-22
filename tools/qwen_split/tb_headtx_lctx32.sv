`timescale 1ns/1ps
// Actual component emitter comparison; alias copies are functional test inputs,
// never evidence of physical producer replication (the wrapper owns that).
module tb_headtx_lctx32;
reg ck=0;always #5 ck=~ck;
reg rst_n=0,dv=0,slot=0;reg[58:0]tag=0;reg[1:0]gen=0,user=0;
reg ready=1,cap=1;reg[15:0]epoch=16'h1234;reg[63:0]digest=64'h123456789abcdef0;
wire av,bv,af,bf;wire[547:0]ar,br;wire[22:0]pub;integer i,j,n=0,events=0;
qfd_mu_head_context_tx a(.ck(ck),.rst_n(rst_n),.descriptor_v(dv),.descriptor_tag(tag),.descriptor_generation(gen),.send_slot(slot),.send_user(user),.program_ready(ready),.installed_fusedcap(cap),.program_epoch(epoch),.program_digest(digest),.tx_v(av),.tx_record(ar),.fault(af));
qfd_mu_head_context_tx_lctx32 b(.ck(ck),.rst_leaf({40{rst_n}}),.source_copies({6{slot}}),.descriptor_v(dv),.descriptor_tag(tag),.descriptor_generation(gen),.send_slot(slot),.send_user(user),.program_ready(ready),.installed_fusedcap(cap),.program_epoch(epoch),.program_digest(digest),.tx_v(bv),.tx_record(br),.fault(bf),.tx_v_pub(pub));
always @(posedge ck)begin #1;n=n+1;
 if({av,ar,af}!=={bv,br,bf} || pub!=={23{av}})$fatal(1,"HEADTX_SOURCE_DIFF edge%0d",n);
 if(av)events=events+1;
end
initial begin
 repeat(3)@(negedge ck);rst_n=1;
 for(j=0;j<8;j=j+1)begin
  for(i=0;i<4;i=i+1)begin dv=1;tag=(59'(i)<<43)|(59'(123+j)<<19);gen=j%4;@(negedge ck);end
  dv=0;
  for(i=0;i<4;i=i+1)begin slot=1;user=i;@(negedge ck);end
  slot=0;repeat(2)@(negedge ck);
 end
 // Underflow, overwrite and invalid descriptor paths retain actual faults.
 slot=1;user=3;@(negedge ck);slot=0;dv=1;tag=59'h123f;@(negedge ck);dv=0;
 repeat(4)@(negedge ck);rst_n=0;repeat(3)@(negedge ck);rst_n=1;repeat(5)@(negedge ck);
 $display("PASS HEADTX_EMITTER edges=%0d records=%0d all548bits/fault and23same-D tx_v publications",n,events);$finish;
end
endmodule
