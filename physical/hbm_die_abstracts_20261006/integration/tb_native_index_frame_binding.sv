`timescale 1ps/1fs
module tb_native_index_frame_binding;
 reg [72:0] source_cp_frame=0;
 reg [72:0] parent_held_frame=0;
 reg  vm_read_v=0;
 wire  vm_read_r;
 reg [31:0] vm_read_addr=0;
 reg [31:0] vm_read_job=0;
 reg [3:0] vm_read_gen=0;
 reg [19:0] vm_read_pos=0;
 reg [6:0] vm_read_rank=0;
 reg [7:0] vm_read_tag=0;
 reg [5:0] vm_read_words=0;
 wire  vm_rsp_v;
 reg  vm_rsp_r=0;
 wire [1023:0] vm_rsp_data;
 wire [7:0] vm_rsp_tag;
 wire [31:0] vm_rsp_job;
 wire [3:0] vm_rsp_gen;
 wire [19:0] vm_rsp_pos;
 wire [6:0] vm_rsp_rank;
 wire  index_read_v;
 reg  index_read_r=0;
 wire [31:0] index_read_addr;
 wire [72:0] index_read_frame;
 wire [6:0] index_read_rank;
 wire [7:0] index_read_tag;
 wire [5:0] index_read_words;
 reg  index_rsp_v=0;
 wire  index_rsp_r;
 reg [1023:0] index_rsp_data=0;
 reg [7:0] index_rsp_tag=0;
 reg [72:0] index_rsp_frame=0;
 reg [6:0] index_rsp_rank=0;
 wire  binding_fault;
 ot_hbm_native_index_frame_binding #(.ENABLE(1)) dut(.source_cp_frame(source_cp_frame),.parent_held_frame(parent_held_frame),.vm_read_v(vm_read_v),.vm_read_r(vm_read_r),.vm_read_addr(vm_read_addr),.vm_read_job(vm_read_job),.vm_read_gen(vm_read_gen),.vm_read_pos(vm_read_pos),.vm_read_rank(vm_read_rank),.vm_read_tag(vm_read_tag),.vm_read_words(vm_read_words),.vm_rsp_v(vm_rsp_v),.vm_rsp_r(vm_rsp_r),.vm_rsp_data(vm_rsp_data),.vm_rsp_tag(vm_rsp_tag),.vm_rsp_job(vm_rsp_job),.vm_rsp_gen(vm_rsp_gen),.vm_rsp_pos(vm_rsp_pos),.vm_rsp_rank(vm_rsp_rank),.index_read_v(index_read_v),.index_read_r(index_read_r),.index_read_addr(index_read_addr),.index_read_frame(index_read_frame),.index_read_rank(index_read_rank),.index_read_tag(index_read_tag),.index_read_words(index_read_words),.index_rsp_v(index_rsp_v),.index_rsp_r(index_rsp_r),.index_rsp_data(index_rsp_data),.index_rsp_tag(index_rsp_tag),.index_rsp_frame(index_rsp_frame),.index_rsp_rank(index_rsp_rank),.binding_fault(binding_fault));
 integer checks=0;
 task check(input bit condition);begin if(!condition)$fatal(1,"native binding check%0d",checks);checks++;end endtask
 initial begin
 source_cp_frame={20'hfffff,17'h1ffff,4'hd,32'h91fedcba};parent_held_frame=source_cp_frame;
 vm_read_job=source_cp_frame[31:0];vm_read_gen=source_cp_frame[35:32];vm_read_pos=source_cp_frame[72:53];
 vm_read_addr=32'd8288;vm_read_words=32;vm_read_tag=8'h80;vm_read_rank=95;vm_read_v=1;
 #1;check(index_read_v&&!vm_read_r&&!binding_fault);
 check(index_read_frame===source_cp_frame&&index_read_addr==8288&&index_read_words==32&&index_read_tag==8'h80&&index_read_rank==95);
 index_read_r=1;#1;check(vm_read_r&&index_read_v);
 vm_read_pos=vm_read_pos^(20'd1<<19);#1;check(binding_fault&&!index_read_v&&!vm_read_r);
 vm_read_pos=source_cp_frame[72:53];vm_read_job=vm_read_job^1;#1;check(binding_fault&&!index_read_v&&!vm_read_r);
 vm_read_job=source_cp_frame[31:0];vm_read_gen=vm_read_gen^1;#1;check(binding_fault&&!index_read_v&&!vm_read_r);
 vm_read_gen=source_cp_frame[35:32];source_cp_frame=source_cp_frame^(73'd1<<52);#1;check(binding_fault&&!index_read_v&&!vm_read_r);
 source_cp_frame=parent_held_frame;vm_read_v=0;
 index_rsp_v=1;index_rsp_frame=source_cp_frame;index_rsp_data={32{32'h7f123456}};index_rsp_tag=8'h80;index_rsp_rank=95;
 #1;check(vm_rsp_v&&!index_rsp_r&&!binding_fault);
 check(vm_rsp_data===index_rsp_data&&vm_rsp_tag==8'h80&&vm_rsp_rank==95&&vm_rsp_job==32'h91fedcba&&vm_rsp_gen==4'hd&&vm_rsp_pos==20'hfffff);
 repeat(3)begin #1;check(vm_rsp_v&&!index_rsp_r&&vm_rsp_data===index_rsp_data);end
 vm_rsp_r=1;#1;check(index_rsp_r&&vm_rsp_v);
 index_rsp_frame=index_rsp_frame^(73'd1<<52);#1;check(binding_fault&&!index_rsp_r&&!vm_rsp_v);
 index_rsp_frame=source_cp_frame;source_cp_frame=source_cp_frame^(73'd1<<72);#1;check(binding_fault&&!index_rsp_r&&!vm_rsp_v);
 source_cp_frame=parent_held_frame;#1;check(index_rsp_r&&vm_rsp_v&&!binding_fault);
 $display("PASS_NATIVE_INDEX_FRAME_BINDING checks=%0d full73=1 word32=1 data1024=1 tag8=1 foreign_tuple_refused=1 wrong_response_no_ACK=1",checks);$finish;
 end
endmodule
