module tb;
parameter integer LOCALMODE=1;
reg clk=0;always #5 clk=~clk;
reg rst_n=0;reg[63:0]we=0;reg[2047:0]wd=0;reg[1535:0]wa=0;reg[17:0]ep=0;reg eb=0,iv=0;reg[1:0]ik=0;reg[17:0]nin=0;reg slot=0;reg[1:0]ix=0;
wire wv,idle,drained,fault;wire[10:0]tag;wire[511:0]data;wire[7:0]fc;
ot_qfd_su_kv_static_posted #(.ENABLE(1),.HEADS(1),.SAFE(2),.LOCAL_CTL(0),.SEAT_HT(1),.LOCAL_DIM_INPUT(LOCALMODE)) u(.clk(clk),.rst_n(rst_n),.epoch_begin(eb),.epoch_pos(ep),.issue_v(iv),.issue_kind(ik),.issue_nout(18'd1),.issue_nin(nin),.kv_we(we),.kv_waddr(wa),.kv_wdata(wd),.epoch_idle(idle),.drained(drained),.word_v(wv),.word_tag(tag),.word_data(data),.word_slot(slot),.word_index(ix),.word_ctl_pub(),.word_index_pub(16'd0),.epoch_begin_pub(2'd0),.word_slot_pub(2'd0),.fault(fault),.fault_code(fc));
integer fd,od,rc,c;reg[3690:0]v;string inp,outp;
initial begin
 if(!$value$plusargs("INPUT=%s",inp)||!$value$plusargs("OUTPUT=%s",outp))$fatal(1,"paths");fd=$fopen(inp,"r");od=$fopen(outp,"w");if(!fd||!od)$fatal(1,"open");repeat(8)@(negedge clk);rst_n=1;repeat(8)@(negedge clk);
 for(c=0;c<110;c=c+1)begin rc=$fscanf(fd,"%h\n",v);if(rc!=1)$fatal(1,"short");{ix,slot,nin,ik,iv,eb,ep,wa,wd,we}=v;@(posedge clk);if(wv)$fwrite(od,"WORD %0d %03h %0128h\n",c,tag,data);if(fault)$fwrite(od,"FAULT %0d %02h\n",c,fc);@(negedge clk);end
 $fclose(fd);$fclose(od);$finish;
end
endmodule
