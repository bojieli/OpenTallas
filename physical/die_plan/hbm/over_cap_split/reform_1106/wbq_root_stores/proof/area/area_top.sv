module area_top(
 input wire fifo_clk,hbm_clk,srst,hrst,
 input wire [1:0]root_id,input wire [31:0]base,
 input wire [11:0]total,committed,ordinal,
 input wire filling,fill_bank,copy_q,copy_bank,copy_start,s_stop,
 input wire [255:0]wd,input wire wd_v,fifo_re,
 output wire [287:0]fifo_head,output wire fifo_empty
);
reg[255:0]wd_q;always @(posedge fifo_clk)wd_q<=wd;
ot_wbq_root_store u(.fifo_clk(fifo_clk),.hbm_clk(hbm_clk),.srst(srst),.hrst(hrst),.root_id(root_id),.base(base),.total(total),.committed(committed),.ordinal(ordinal),.filling(filling),.fill_bank(fill_bank),.copy_q(copy_q),.copy_bank(copy_bank),.copy_start(copy_start),.s_stop(s_stop),.wd(wd_q),.wd_v(wd_v),.fifo_re(fifo_re),.fifo_head(fifo_head),.fifo_empty(fifo_empty));
endmodule
