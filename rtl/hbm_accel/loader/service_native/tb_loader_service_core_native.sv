`timescale 1ps/1ps
module tb_loader_service_core_native;
 reg clk=0;always #416 clk=~clk;reg rst_n=0;
 reg req_v=0,req_we=0,rsp_rdy=0;reg[36:0]req_addr=0;reg[255:0]req_wdata=0;reg[15:0]req_tag=0;
 wire req_rdy,rsp_v,rsp_we,wr_v,rd_v,rd_rdy,rd_rsp_v,rd_rsp_rdy,endpoint_fault,endpoint_busy;
 wire[15:0]rsp_tag,rd_tag,rd_rsp_tag;wire[255:0]rsp_data,rd_rsp_data;wire[290:0]wr_packet;
 wire[4:0]rd_pc,rd_rsp_pc,translated_pc;wire[29:0]rd_addr,translated_addr;wire[1:0]translated_stack;wire translation_valid;
 wire[3:0]rd_rsp_beat;wire[31:0]k_v,k_rdy,k_we,kr_v,kr_rdy,k_wr_done;
 wire[959:0]k_addr;wire[127:0]k_len,kr_beat;wire[543:0]k_tag,kr_tag;wire[8191:0]k_wdata,kr_data;wire[1023:0]k_wstrb;
 wire[31:0]wq_source_g,wq_source_busy;wire wq_source_fault,wq_pending,native_fault,phy_rst_n;
 reg[7:0]ack_prev=0;wire[7:0]ack_now;
 function[7:0]ungray(input[7:0]g);integer b;begin ungray[7]=g[7];for(b=6;b>=0;b=b-1)ungray[b]=ungray[b+1]^g[b];end endfunction
 assign ack_now=ungray(wq_source_g[31:24]);
 wire wr_ack=ack_now!=ack_prev;
 always @(posedge clk or negedge rst_n)if(!rst_n)ack_prev<=0;else ack_prev<=ack_now;
 ot_hbm_loader_kport_address #(.ENABLE(1))mapper(.byte_address(req_addr),.stack_bytes(36'd22500000000),.stack(translated_stack),.pc(translated_pc),.sector_address(translated_addr),.valid(translation_valid));
 ot_hbm_loader_native_endpoint #(.ENABLE(1),.ADDR_W(37))endpoint(
 .clk(clk),.rst_n(rst_n),.req_v(req_v),.req_rdy(req_rdy),.req_we(req_we),.req_addr(req_addr),.req_wdata(req_wdata),.req_wstrb(32'hffffffff),.req_tag(req_tag),
 .translation_valid(translation_valid&&translated_stack==0),.translated_pc(translated_pc),.translated_addr(translated_addr),
 .rsp_v(rsp_v),.rsp_rdy(rsp_rdy),.rsp_we(rsp_we),.rsp_tag(rsp_tag),.rsp_data(rsp_data),
 .wr_v(wr_v),.wr_rdy(1'b1),.wr_packet(wr_packet),.wr_ack(wr_ack),
 .rd_v(rd_v),.rd_rdy(rd_rdy),.rd_pc(rd_pc),.rd_addr(rd_addr),.rd_tag(rd_tag),
 .rd_rsp_v(rd_rsp_v),.rd_rsp_rdy(rd_rsp_rdy),.rd_rsp_pc(rd_rsp_pc),.rd_rsp_tag(rd_rsp_tag),.rd_rsp_beat(rd_rsp_beat),.rd_rsp_data(rd_rsp_data),
 .service_fault(native_fault||wq_source_fault),.busy(endpoint_busy),.fault(endpoint_fault));
 ot_hbm_svc_core_native #(.NATIVE(1),.WB(1),.WB_SOURCE_ACK(1),.KVS(1),.XST(0),.WQ_ST(1))service(
 .ck(clk),.rst(rst_n),.q_d(336'b0),.q_v(8'b0),.q_fclk(8'b0),.e_d(128'b0),.e_fclk(1'b0),
 .k_v(k_v),.k_rdy(k_rdy),.k_addr(k_addr),.k_len(k_len),.k_tag(k_tag),.k_we(k_we),.k_wdata(k_wdata),.k_wstrb(k_wstrb),
 .kr_v(kr_v),.kr_rdy(kr_rdy),.kr_tag(kr_tag),.kr_beat(kr_beat),.kr_data(kr_data),
 .w_rdy(1'b1),.w_room(8'hff),.wr_v(8'b0),.wr_tag(80'b0),.wr_beat(40'b0),.wr_data(2048'b0),
 .wq_d({wr_packet,wr_v}),.wq_fclk(clk),.wq_source(2'd2),.wq_source_g(wq_source_g),.wq_source_fault(wq_source_fault),.wq_source_busy(wq_source_busy),.wq_pending(wq_pending),.k_wr_done(k_wr_done),.phy_rst_n(phy_rst_n),
 .outer_write_pending(endpoint_busy&&req_we&&!rsp_v),
 .native_v(rd_v),.native_rdy(rd_rdy),.native_pc(rd_pc),.native_addr(rd_addr),.native_tag(rd_tag),
 .native_rsp_v(rd_rsp_v),.native_rsp_rdy(rd_rsp_rdy),.native_rsp_pc(rd_rsp_pc),.native_rsp_tag(rd_rsp_tag),.native_rsp_beat(rd_rsp_beat),.native_rsp_data(rd_rsp_data),.native_fault(native_fault));
 // Actual refresh-aware controller timing and backing memory, minimum one stack.
 ot_hdc_v41x_idx_hbm #(.NPC(32),.AW(30),.DW(256),.MEM_WORDS(1024),.TAGW(17),.LENW(4),.BEATW(4),.QD(64),.REFPB(3),.MEM_MODE(0))phy(
 .clk(clk),.rst_n(phy_rst_n),.req_v(k_v),.req_rdy(k_rdy),.req_addr(k_addr),.req_len(k_len),.req_tag(k_tag),.req_we(k_we),.req_wdata(k_wdata),.req_wstrb(k_wstrb),.wr_done(k_wr_done),
 .rsp_v(kr_v),.rsp_rdy(kr_rdy),.rsp_tag(kr_tag),.rsp_beat(kr_beat),.rsp_data(kr_data));
 task tick;begin @(posedge clk);#1;end endtask
 integer p,j,cycles=0;reg[255:0]golden;
 initial begin
 #1;rst_n=0;repeat(4)tick;rst_n=1;repeat(16)tick;
 for(j=0;j<2;j=j+1)for(p=0;p<32;p=p+1)begin
 @(negedge clk);req_v=1;req_we=(j==0);req_addr=37'(p*128);req_tag=16'h8000+16'(j*32+p);golden={8{32'hdead0000+32'(p)}};req_wdata=golden;
 #1;while(!req_rdy)tick;tick; // Wait before the accepting edge, then retire the request.
 @(negedge clk);req_v=0;
 while(!rsp_v)begin tick;cycles=cycles+1;end
 if(rsp_tag!==req_tag||rsp_we!==req_we||rsp_data!==(req_we?256'd0:golden))$fatal(1,"actual service mismatchpc%0d",p);
 repeat(3)tick;
 @(negedge clk);rsp_rdy=1;tick;@(negedge clk);rsp_rdy=0;
 if(endpoint_fault||native_fault||wq_source_fault)$fatal(1,"actual service fault");
 end
 $display("PASS actual32PC service mapper37 endpoint WB sourceACK controller write/read exact64 transactions cycles%0d",cycles);$finish;
 end
 initial begin #200000000;$fatal(1,"finite transaction liveness bound");end
endmodule
