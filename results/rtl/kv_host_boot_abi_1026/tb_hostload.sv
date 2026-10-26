`timescale 1ns/1ps
// KV-TOK 10-26 unit replay: exact B33 HOST ingress (qkd_host_program_rx_target) + loader (qkd_host_program_loader_target)
// fed the exact B33 boot9 frames.hex (image7: target 10 = 96 words AGES1, target 1 = 471 words MU1); one image at a time
// (next BEGIN only after the previous replay is ready).  LPARAMS = loader parameters, FRAMES = frames.hex path.
module tb_hostload;
 reg ck=0; always #0.4165 ck=~ck; reg rst_n=0;
 reg rx_v=0; reg [527:0] rx_d=0; wire rx_cr;
 wire normal_v; wire [527:0] normal_d;
 wire begin_image,word_v,word_desc,seal,auth_v,ing_fault,prog_fault,ready; wire [15:0] image_epoch,auth_epoch,pepoch;
 wire [3:0] image_target,auth_target,replay_target; wire [10:0] pw_count; wire [3:0] dw_count; wire [9:0] word_addr;
 wire [63:0] word_data,auth_digest,digest,ftr; wire [142:0] pr; wire ftr_v;
 qkd_host_program_rx_target u_rx(.ck(ck),.rst_n(rst_n),.rx_v(rx_v),.rx_d(rx_d),.rx_cr(rx_cr),.normal_v(normal_v),.normal_d(normal_d),.normal_cr(1'b0),
  .begin_image(begin_image),.image_epoch(image_epoch),.image_target(image_target),.auth_target(auth_target),.pw_count(pw_count),.dw_count(dw_count),
  .word_v(word_v),.word_desc(word_desc),.word_addr(word_addr),.word_data(word_data),.seal(seal),.auth_v(auth_v),.auth_epoch(auth_epoch),.auth_digest(auth_digest),.fault(ing_fault));
 qkd_host_program_loader_target #(`LPARAMS) u_ld(.ck(ck),.rst_n(rst_n),.begin_image(begin_image),.image_epoch(image_epoch),.pw_count(pw_count),.dw_count(dw_count),
  .word_v(word_v),.word_desc(word_desc),.word_addr(word_addr),.word_data(word_data),.seal(seal),.auth_v(auth_v),.auth_epoch(auth_epoch),.auth_digest(auth_digest),
  .image_target(image_target),.auth_target(auth_target),.replay_target(replay_target),.execution_active(1'b0),.pr(pr),.program_ready(ready),.fault(prog_fault),
  .digest(digest),.program_epoch(pepoch),.authorized_footer_valid(ftr_v),.authorized_footer(ftr));
 reg [527:0] F [0:7403]; integer i, nimg, cyc=0, failed=0; reg pf_q=0, if_q=0;
 always @(posedge ck) begin cyc<=cyc+1;
  if (begin_image) $display("BEGIN cyc %0d target %0d pw %0d dw %0d -> loader state %0d", cyc, image_target, pw_count, dw_count, u_ld.state);
  if (prog_fault && !pf_q) $display("PROGRAM_FAULT cyc %0d state %0d replay_target %0d", cyc, u_ld.state, replay_target);
  if (ing_fault && !if_q) $display("INGRESS_FAULT cyc %0d", cyc);
  pf_q<=prog_fault; if_q<=ing_fault;
 end
 initial begin
  $readmemh(`FRAMES, F); nimg=0;
  repeat(5) @(posedge ck); rst_n=1; repeat(3) @(posedge ck);
  for (i=0;i<7404;i++) begin
   rx_v<=1; rx_d<=F[i]; @(posedge ck); rx_v<=0; @(posedge ck);
   if (F[i][7:0]==4) begin : waitimg
     integer w; for (w=0; w<3000 && !(ready && !begin_image) && !prog_fault && !ing_fault; w++) @(posedge ck);
     $display("IMAGE %0d target %0d ready %0b fault %0b/%0b digest %h epoch %0d", nimg, replay_target, ready, prog_fault, ing_fault, digest, pepoch);
     nimg++; if (prog_fault||ing_fault) begin $display("HOSTLOAD FAIL at frame %0d images_ok %0d", i, nimg-1); failed=1; break; end
   end
  end
  if (!failed) $display("HOSTLOAD PASS images %0d", nimg);
  $finish;
 end
endmodule
