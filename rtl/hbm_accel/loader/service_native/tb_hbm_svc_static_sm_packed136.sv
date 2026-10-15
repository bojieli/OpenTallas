`timescale 1ns/1ps
`default_nettype none
module tb_hbm_svc_static_sm_packed136;
 reg clk=0;always #5 clk=~clk;reg rst_n=0;
 reg open_v=0,open_bank=0;reg [15:0] open_epoch=0;reg [6:0] open_count=0;reg [9:0] open_tag_base=0;
 reg [3:0] sector_v=0;reg [95:0] sector_index=0;reg [63:0] sector_epoch=0;reg [1023:0] sector_data=0;
 reg read_v=0,read_bank=0,retire_v=0,retire_bank=0;reg [15:0] read_epoch=0,retire_epoch=0;reg [5:0] read_row=0;reg [9:0] read_tag=0;
 wire [1:0] block_ready,bank_owned;wire busy,fault;wire [1098:0] out_packet;
 ot_hbm_svc_static_sm_packed136 #(.PACKED136(1)) dut(.*);
 wire [1098:0] off_packet;wire [1:0] off_ready,off_owned;wire off_busy,off_fault;
 ot_hbm_svc_static_sm_packed136 disabled(.clk(clk),.rst_n(rst_n),.open_v(open_v),.open_bank(open_bank),.open_epoch(open_epoch),.open_count(open_count),.open_tag_base(open_tag_base),
 .sector_v(sector_v),.sector_index(sector_index),.sector_epoch(sector_epoch),.sector_data(sector_data),.read_v(read_v),.read_bank(read_bank),.read_epoch(read_epoch),.read_row(read_row),.read_tag(read_tag),
 .retire_v(retire_v),.retire_bank(retire_bank),.retire_epoch(retire_epoch),.block_ready(off_ready),.bank_owned(off_owned),.busy(off_busy),.fault(off_fault),.out_packet(off_packet));
 // Historical assembler is a BENCH reference only. Production has no ready.
 // Requests and pops follow fixed slots; no reference ready changes the clock.
 reg [6:0] requested=0;wire ref_cfg_ready,ref_req_ready,ref_rsp_valid,ref_idle,ref_fault;
 wire [3:0] ref_sector_ready;wire [9:0] ref_tag;wire [1087:0] ref_data;
 wire ref_req=dut.g_on.running&&dut.g_on.slot_phase<4&&requested<dut.g_on.load_rows;
 ot_gpu_payload_assemble #(.ENABLE(1),.WINDOW(16),.TAG_DEPTH(16),.TAGW(10)) reference(
 .clk(clk),.rst_n(rst_n),.cfg_valid(open_v),.cfg_ready(ref_cfg_ready),.cfg_payloads({17'b0,open_count}),.cfg_req_base(32'b0),.cfg_epoch(open_epoch),
 .sector_valid(sector_v),.sector_ready(ref_sector_ready),.sector_index(sector_index),.sector_epoch(sector_epoch),.sector_data(sector_data),
 .req_valid(ref_req),.req_ready(ref_req_ready),.req_addr({25'b0,requested}),.req_tag(dut.g_on.tag_base+requested),
 .rsp_valid(ref_rsp_valid),.rsp_ready(dut.g_on.row_slot),.rsp_tag(ref_tag),.rsp_data(ref_data),.idle(ref_idle),.fault(ref_fault));
 integer compared=0,read_vectors=0,overlap_cycles=0,source_edges=0,source_sectors=0,faults=0;reg fault_mode=0;
 always @(posedge clk)begin
  if(!rst_n)requested<=0;
  else begin
   if(open_v)requested<=0;else if(ref_req)requested<=requested+1'b1;
   if(!fault_mode)begin
    if(ref_req&&!ref_req_ready)$fatal(1,"reference fixed request slot unavailable");
    if(dut.g_on.row_slot)begin
     if(!ref_rsp_valid||ref_tag!==dut.g_on.tag_base+dut.g_on.emitted||ref_data!==dut.g_on.row_data)$fatal(1,"four-phase static gather differs from original assembler");
     compared=compared+1;
    end
   end
  end
 end
 function automatic [7:0] byte_for(input integer b,input integer row,input integer pos);begin byte_for=(b*113+row*37+pos*13+(pos>>3)*17)^8'hb5;end endfunction
 function automatic [255:0] sector_for(input integer b,input integer s,input integer rows);
  integer j,off;begin for(j=0;j<32;j=j+1)begin off=s*32+j;sector_for[j*8+:8]=off<rows*136?byte_for(b,off/136,off%136):8'h00;end end
 endfunction
 function automatic [1098:0] packet_for(input integer b,input integer row);integer j;reg [1087:0] data;reg [9:0] tag;
  begin for(j=0;j<136;j=j+1)data[j*8+:8]=byte_for(b,row,j);tag=(b?300:100)+row;packet_for={1'b1,tag,data};end
 endfunction
 task tick;begin @(posedge clk);#1;end endtask
 task reset_dut;begin rst_n=0;open_v=0;sector_v=0;read_v=0;retire_v=0;tick;tick;rst_n=1;tick;end endtask
 task set_read(input bit b,input integer r);begin read_v=1;read_bank=b;read_epoch=b?16'h5678:16'h1234;read_row=r;read_tag=(b?300:100)+r;end endtask
 task check_read(input bit b,input integer r);begin if(out_packet!==packet_for(b,r))$fatal(1,"packed136 cache payload/tag mismatch bank=%0d row=%0d",b,r);read_vectors=read_vectors+1;end endtask
 task open_block(input bit b,input integer rows);begin open_v=1;open_bank=b;open_epoch=b?16'h5678:16'h1234;open_count=rows;open_tag_base=b?300:100;tick;open_v=0;end endtask
 task set_sectors(input bit b,input integer ordinal,input integer n,input integer rows);integer j;begin
  sector_v=0;sector_index=0;sector_epoch=0;sector_data=0;
  for(j=0;j<n;j=j+1)begin sector_v[j]=1;sector_index[j*24+:24]=ordinal+j;sector_epoch[j*16+:16]=b?16'h5678:16'h1234;sector_data[j*256+:256]=sector_for(b,ordinal+j,rows);end
 end endtask
 task load_block(input bit b,input integer rows,input bit overlap);integer ordinal,phase,n,total,cy,guard;begin
  open_block(b,rows);ordinal=0;phase=0;cy=0;total=((rows*136+127)/128)*4;
  while(ordinal<total)begin
   n=phase==4?1:4;if(total-ordinal<n)n=total-ordinal;
   set_sectors(b,ordinal,n,rows);if(overlap)set_read(0,cy%16);
   tick;if(overlap)begin check_read(0,cy%16);overlap_cycles=overlap_cycles+1;end
   if(fault)$fatal(1,"fixed packed source fault ordinal=%0d phase=%0d",ordinal,phase);
   ordinal=ordinal+n;phase=phase==4?0:phase+1;cy=cy+1;source_edges=source_edges+1;source_sectors=source_sectors+n;
  end
  sector_v=0;read_v=0;guard=0;
  while(busy)begin tick;if(fault)$fatal(1,"packed drain fault");guard=guard+1;if(guard>3)$fatal(1,"packed static completion rescheduled");end
  if(!block_ready[b])$fatal(1,"cache not ready after all actual packed rows");
  if(rows==16&&cy!=20||rows==64&&cy!=80)$fatal(1,"packed136 cadence price violated");
 end endtask
 task expect_fault(input integer id);begin tick;if(!fault)$fatal(1,"missing packed fault case=%0d",id);sector_v=0;read_v=0;open_v=0;tick;if(!fault||out_packet[1098])$fatal(1,"packed fault not sticky");faults=faults+1;end endtask
 integer r,c,corner_rows;
 initial begin
  reset_dut;load_block(0,16,0);load_block(1,64,1);
  for(r=0;r<16;r=r+1)begin set_read(0,r);tick;check_read(0,r);end
  for(r=0;r<64;r=r+1)begin set_read(1,r);tick;check_read(1,r);end
  read_v=0;tick;if(out_packet[1098])$fatal(1,"extra read response");
  if(compared!=80||off_packet||off_ready||off_owned||off_busy||off_fault)$fatal(1,"reference count/default-off mismatch");
  // Final block-only 128-byte alignment is exercised independently of the
  // full sixteen/four-phase groups; no record acquires160-byte padding.
  for(c=0;c<8;c=c+1)begin
   case(c)0:corner_rows=1;1:corner_rows=2;2:corner_rows=3;3:corner_rows=4;4:corner_rows=5;5:corner_rows=15;6:corner_rows=17;default:corner_rows=63;endcase
   reset_dut;load_block(0,corner_rows,0);
   for(r=0;r<corner_rows;r=r+1)begin set_read(0,r);tick;check_read(0,r);end
   read_v=0;tick;
  end
  fault_mode=1;
  reset_dut;open_block(0,16);sector_v=0;expect_fault(1); // missing fixed source edge
  reset_dut;open_block(0,16);set_sectors(0,0,4,16);sector_epoch[0+:16]=16'h9999;expect_fault(2);
  reset_dut;open_block(0,16);set_sectors(0,0,4,16);sector_index[24+:24]=0;expect_fault(3);
  reset_dut;set_read(0,0);expect_fault(4);
  reset_dut;open_block(0,16);set_read(0,0);set_sectors(0,0,4,16);expect_fault(5);
  reset_dut;open_block(0,16);set_sectors(0,0,3,16);expect_fault(6);
  reset_dut;sector_v=1;expect_fault(7);
  $display("STATIC_SM_PACKED136 PASS exact_reference_rows=%0d cache_reads=%0d crossbank_cycles=%0d packed_source_edges=%0d packed_sectors=%0d bytes_per_record=136 faults=%0d",compared,read_vectors,overlap_cycles,source_edges,source_sectors,faults);$finish;
 end
 initial begin #100000;$fatal(1,"timeout");end
endmodule
`default_nettype wire
