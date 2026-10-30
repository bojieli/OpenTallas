`default_nettype none
// Genuine static SOURCE-ONLY candidate (default stack2 NW/NE): compact native227 -> actual62b NPC2 leaves.
// Every command is dated; fill arrival and VMslot6 reservation are caller duties.
// No ready/credit, runtime indexed resolver, invented refill or production plan.
module ot_hbm_static_load_provider_quad #(parameter integer SOURCE_QUAD=2,SOURCE_STACK=2,SOURCE_LOW_QUAD=2)(
 input wire clk,rst_n,
 input wire desc_v_i,input wire[226:0]desc_i,input wire step_i,
 input wire window_buffer_i,input wire[15:0]window_epoch_i,input wire[14:0]window_row_i,input wire[3:0]window_col_i,
 input wire begin_v,input wire begin_bank,input wire[15:0]begin_epoch,input wire[14:0]begin_row,input wire[3:0]begin_col,
 input wire[15:0]fill_v,fill_bank,input wire[95:0]fill_slot,input wire[255:0]fill_epoch,input wire[4095:0]fill_data,
 input wire release_v_i,release_buffer_i,input wire[15:0]release_epoch_i,
 output wire active_o,output wire[280:0]vm_dq,output wire[15:0]block_ready,output wire[7:0]leaf_fault,
 output reg fault_o
);
 initial if(SOURCE_QUAD!=SOURCE_LOW_QUAD&&SOURCE_QUAD!=SOURCE_LOW_QUAD+1)$fatal(1,"provider quad must match selected physical landing pair");
 wire counter_fault,av,last;wire[39:0]sa,da;wire[2:0]fmt;wire[3:0]count;
 ot_hbm_static_load_addr_counter counter(.clk(clk),.rst_n(rst_n),.desc_v_i(desc_v_i),.desc_i(desc_i),.step_i(step_i),
 .active_o(active_o),.fault_o(counter_fault),.addr_v_o(av),.last_o(last),.src_byte_o(sa),.dst_word_o(da),.format_o(fmt),.count_o(count));
 // Capture caller identity on exactly the counter's dated output edge.
 reg wb;reg[15:0]we;reg[14:0]wr;reg[3:0]wc;
 reg[1:0]tag_live;reg[15:0]tag_epoch[0:1];reg[14:0]tag_row[0:1];reg[3:0]tag_col[0:1];
 wire mapped_v,map_fault;wire[61:0]mapped_cmd;wire[2:0]source_leaf;wire[1:0]source_quad;
 ot_hbm_static_load_addr_map #(.SOURCE_STACK(SOURCE_STACK),.SOURCE_LOW_QUAD(SOURCE_LOW_QUAD)) mapper(.addr_v_i(av),.src_byte_i(sa),.dst_word_i(da),.fmt_i(fmt),.count_i(count),
 .buffer_i(wb),.epoch_i(we),.window_row_i(wr),.window_col_i(wc),.load_v_o(mapped_v),.fault_o(map_fault),
 .load_cmd_o(mapped_cmd),.source_leaf_o(source_leaf),.source_quad_o(source_quad));
 reg[7:0]load_v;reg[495:0]load_cmd;reg[61:0]release_cmd;integer b;
 always @*begin
 load_v=0;load_cmd=0;release_cmd=0;release_cmd[0]=release_buffer_i;release_cmd[16:1]=release_epoch_i;release_cmd[56]=1;
 if(release_v_i)begin load_v=8'hff;for(b=0;b<8;b=b+1)load_cmd[b*62+:62]=release_cmd;end
 else if(mapped_v&&source_quad==2'(SOURCE_QUAD)&&!fault_o)begin load_v=8'b1<<source_leaf;load_cmd[source_leaf*62+:62]=mapped_cmd;end
 end
 wire route_fault;
 ot_hbm_static_load_quad_vehicle leaves(.clk(clk),.rst_n(rst_n),.begin_v(begin_v),.begin_bank(begin_bank),.begin_epoch(begin_epoch),
 .fill_v(fill_v),.fill_bank(fill_bank),.fill_slot(fill_slot),.fill_epoch(fill_epoch),.fill_data(fill_data),
 .load_v(load_v),.load_cmd(load_cmd),.block_ready(block_ready),.leaf_fault(leaf_fault),.vm_dq(vm_dq),.route_fault(route_fault));
 integer k;
 always @(posedge clk)begin
 if(!rst_n)begin
 fault_o<=0;wb<=0;we<=0;wr<=0;wc<=0;tag_live<=0;
 for(k=0;k<2;k=k+1)begin tag_epoch[k]<=0;tag_row[k]<=0;tag_col[k]<=0;end
 end else begin
 if(counter_fault||map_fault||route_fault||(|leaf_fault)||(mapped_v&&source_quad!=2'(SOURCE_QUAD))||(release_v_i&&(av||begin_v||step_i)))fault_o<=1;
 if(begin_v)begin
 if(tag_live[begin_bank])fault_o<=1;
 tag_live[begin_bank]<=1;tag_epoch[begin_bank]<=begin_epoch;tag_row[begin_bank]<=begin_row;tag_col[begin_bank]<=begin_col;
 end
 if(step_i)begin
 wb<=window_buffer_i;we<=window_epoch_i;wr<=window_row_i;wc<=window_col_i;
 if(!tag_live[window_buffer_i]||tag_epoch[window_buffer_i]!=window_epoch_i||tag_row[window_buffer_i]!=window_row_i||tag_col[window_buffer_i]!=window_col_i)fault_o<=1;
 end
 if(release_v_i)begin
 if(!tag_live[release_buffer_i]||tag_epoch[release_buffer_i]!=release_epoch_i)fault_o<=1;
 tag_live[release_buffer_i]<=0;
 end
 end end
endmodule
`default_nettype wire
