`timescale 1ns/1ps
module tb_hbm_svc_dma_pc_owner #(parameter MUT=0);
 reg clk=0;always #5 clk=~clk;
 reg rst=1,dma_session=0,normal_quiescent=0,dma_outstanding=0;
 wire dma_owner;
 reg n_v=0,d_v=0,k_rdy=0,kr_v=0,n_rs_rdy=0,d_rs_rdy=0;
 reg[29:0]n_addr=30'h111,d_addr=30'h222;
 reg[3:0]n_len=4,d_len=4,kr_beat=0;
 // Deliberately the SAME entire tag in both owner domains, including DMA prefix.
 reg[16:0]n_tag=17'h1b612,d_tag=17'h1b612,kr_tag=17'h1b612;
 reg[255:0]kr_data=256'h98765432100123456789abcdef;
 wire n_rdy,d_rdy,k_v,kr_rdy,n_rs_v,d_rs_v;
 wire[29:0]k_addr;wire[3:0]k_len,n_rs_beat,d_rs_beat;
 wire[16:0]k_tag,n_rs_tag,d_rs_tag;
 wire[255:0]n_rs_data,d_rs_data;
 ot_hbm_svc_dma_pc_owner #(.MUT_BYPASS_DRAIN(MUT==1),.MUT_PREFIX_ROUTE(MUT==2),.MUT_EARLY_RELEASE(MUT==3))dut(.*);
 task tick;begin @(posedge clk);#1;end endtask
 task check_normal_response;
 begin
 if(!n_rs_v||d_rs_v||n_rs_tag!==kr_tag||n_rs_beat!==kr_beat||n_rs_data!==kr_data||kr_rdy!==n_rs_rdy)$fatal(1,"normal response owner/identity/backpressure mismatch");
 end endtask
 task check_dma_response;
 begin
 if(!d_rs_v||n_rs_v||d_rs_tag!==kr_tag||d_rs_beat!==kr_beat||d_rs_data!==kr_data||kr_rdy!==d_rs_rdy)$fatal(1,"DMA response owner/identity/backpressure mismatch");
 end endtask
 initial begin
 repeat(3)tick();@(negedge clk);rst=0;n_v=1;
 #1;if(!k_v||k_addr!==n_addr||k_tag!==n_tag||k_len!==n_len||n_rdy||d_rdy)$fatal(1,"normal request stalled identity");
 repeat(3)begin tick();if(!k_v||k_addr!==n_addr||k_tag!==n_tag)$fatal(1,"normal request unstable under backpressure");end
 @(negedge clk);k_rdy=1;#1;if(!n_rdy||d_rdy)$fatal(1,"normal request handshake");tick();
 @(negedge clk);n_v=0;dma_session=1;d_v=1;kr_v=1;d_rs_rdy=1;n_rs_rdy=0;
 #1;check_normal_response();
 repeat(4)begin tick();if(dma_owner||d_rdy)$fatal(1,"DMA granted before normal response drain");check_normal_response();end
 @(negedge clk);n_rs_rdy=1;#1;check_normal_response();tick();
 @(negedge clk);kr_v=0;
 // A separate normal write/relay debt survives the read response.
 repeat(5)begin tick();if(dma_owner||d_rdy)$fatal(1,"DMA bypassed normal write/relay drain");end
 @(negedge clk);normal_quiescent=1;k_rdy=0;tick();
 if(!dma_owner||!k_v||n_rdy||d_rdy||k_addr!==d_addr||k_tag!==d_tag||k_len!==d_len)$fatal(1,"DMA ownership grant/request identity");
 repeat(3)begin tick();if(!dma_owner||!k_v||k_addr!==d_addr||k_tag!==d_tag||k_len!==d_len)$fatal(1,"DMA request unstable under backpressure");end
 @(negedge clk);k_rdy=1;#1;if(!d_rdy||n_rdy)$fatal(1,"DMA request handshake");tick();
 @(negedge clk);d_v=0;dma_outstanding=1;dma_session=0;
 repeat(5)begin tick();if(!dma_owner)$fatal(1,"owner released with outstanding DMA lease");end
 @(negedge clk);kr_v=1;kr_beat=3;kr_data=256'hcafe1234;d_rs_rdy=0;n_rs_rdy=1;
 #1;check_dma_response();
 repeat(5)begin tick();if(!dma_owner)$fatal(1,"owner released while DMA response held");check_dma_response();end
 @(negedge clk);d_rs_rdy=1;#1;check_dma_response();tick();
 @(negedge clk);kr_v=0;dma_outstanding=0;tick();
 if(dma_owner)$fatal(1,"owner did not return after exact drain");
 @(negedge clk);n_v=1;n_addr=30'h333;#1;
 if(!n_rdy||d_rdy||!k_v||k_addr!==n_addr||k_tag!==n_tag)$fatal(1,"normal reacquisition identity");tick();
 $display("PASS minimal_one_PC same17bit_tag_namespace normal_read_and_write_drain DMA_lease_drain request_response_backpressure");$finish;
 end
endmodule
