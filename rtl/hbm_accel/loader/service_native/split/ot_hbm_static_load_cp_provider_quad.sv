`default_nettype none
// SOURCE-ONLY native target integration. Existing CW308/RELF2 command format:
// {epoch16,buffer1,resolved227,drain_at32,issue_at32}. No new ISA or target ID.
// Caller supplies window-safe m1 runs, actual begin/fill/release and VMslot6.
// One target stores <=128 literal run descriptors; whole-programme paging/
// compression/dispatch remains explicit. This is not a 95313-entry ROM claim.
module ot_hbm_static_load_cp_provider_quad #(parameter integer SOURCE_QUAD=2)(
 input wire clk,rst_n,input wire[7:0]tgt,
 input wire cfg_v,input wire[7:0]cfg_target,input wire[11:0]cfg_addr,input wire[255:0]cfg_data,
 input wire desc_v,input wire[11:0]desc_base,input wire[12:0]desc_limit,input wire[15:0]desc_loops,input wire launch_v,
 input wire begin_v,begin_bank,input wire[15:0]begin_epoch,input wire[14:0]begin_row,input wire[3:0]begin_col,
 input wire[15:0]fill_v,fill_bank,input wire[95:0]fill_slot,input wire[255:0]fill_epoch,input wire[4095:0]fill_data,
 input wire release_v_i,release_buffer_i,input wire[15:0]release_epoch_i,
 output wire configured,cp_active,output wire[31:0]cycle,
 output wire[280:0]vm_dq,output wire[15:0]block_ready,output wire[7:0]leaf_fault,
 output reg busy_o,fault_o
);
 wire cmd_v,cp_fault;wire[307:0]cmd;wire provider_fault,counter_active;
 ot_hgi_dma_back_cp_collar cp(.clk(clk),.rst_n(rst_n),.tgt(tgt),.cfg_v(cfg_v),.cfg_target(cfg_target),.cfg_addr(cfg_addr),.cfg_data(cfg_data),
 .desc_v(desc_v),.desc_base(desc_base),.desc_limit(desc_limit),.desc_loops(desc_loops),.launch_v(launch_v),
 .tgt_active(busy_o),.tgt_fault(fault_o),.cmd_v(cmd_v),.cmd(cmd),.cycle(cycle),.configured(configured),.fault(cp_fault),.active(cp_active));
 wire[226:0]move=cmd[290:64];
 wire badcmd=move[205:186]!=1||move[226:206]==0||($signed(cmd[31:0]-cycle)<2)||($signed(cmd[63:32]-cmd[31:0])<=0);
 wire admit=cmd_v&&!busy_o&&!fault_o&&!badcmd;
 reg[31:0]issue_at,drain_at;
 reg wb;reg[15:0]we;reg[14:0]wr;reg[3:0]wc;
 reg[20:0]expected_words;reg[21:0]committed_words;
 wire dated_step=busy_o&&counter_active&&!fault_o&&($signed(cycle-issue_at)>=0)&&($signed(drain_at-cycle)>0);
 ot_hbm_static_load_provider_quad #(.SOURCE_QUAD(SOURCE_QUAD)) provider(.clk(clk),.rst_n(rst_n),.desc_v_i(admit),.desc_i(move),.step_i(dated_step),
 .window_buffer_i(wb),.window_epoch_i(we),.window_row_i(wr),.window_col_i(wc),
 .begin_v(begin_v),.begin_bank(begin_bank),.begin_epoch(begin_epoch),.begin_row(begin_row),.begin_col(begin_col),
 .fill_v(fill_v),.fill_bank(fill_bank),.fill_slot(fill_slot),.fill_epoch(fill_epoch),.fill_data(fill_data),
 .release_v_i(release_v_i),.release_buffer_i(release_buffer_i),.release_epoch_i(release_epoch_i),
 .active_o(counter_active),.vm_dq(vm_dq),.block_ready(block_ready),.leaf_fault(leaf_fault),.fault_o(provider_fault));
 function automatic[3:0]pop8(input[7:0]mask);
 integer k;reg[3:0]v;begin v=0;for(k=0;k<8;k=k+1)v=v+{3'd0,mask[k]};pop8=v;end endfunction
 always @(posedge clk)begin
 if(!rst_n)begin busy_o<=0;fault_o<=0;issue_at<=0;drain_at<=0;wb<=0;we<=0;wr<=0;wc<=0;expected_words<=0;committed_words<=0;end
 else begin
 if(cp_fault||provider_fault)fault_o<=1;
 if(cmd_v&&(busy_o||badcmd))fault_o<=1;
 if(admit)begin
 busy_o<=1;issue_at<=cmd[31:0];drain_at<=cmd[63:32];wb<=cmd[291];we<=cmd[307:292];wr<=move[39:25];wc<=move[21:18];
 expected_words<=move[226:206];committed_words<=0;
 end
 if(vm_dq[280])begin
 if(!busy_o||($signed(cycle-drain_at)>=0))fault_o<=1;
 committed_words<=committed_words+{18'd0,pop8(vm_dq[7:0])};
 end
 if(busy_o&&($signed(cycle-drain_at)>=0))begin
 if(counter_active||committed_words!={1'b0,expected_words})fault_o<=1;
 busy_o<=0;
 end
 end end
endmodule
`default_nettype wire
