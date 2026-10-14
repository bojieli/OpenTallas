`timescale 1ns/1ps
module tb_qwen_context_admission;
 reg clk=0,rst_n=0,offer_go=0,core_ready=0,core_idle=0;
 reg [47:0] offered_identity=48'h111112345678,accepted_identity=0;
 reg accept_ack_toggle=0,transport_fence=0;wire core_go,accept_toggle,fault;
 integer accepted=0;
 ot_qwen_context_admission dut(.*);
 // Model only the accepted-register seam; production u_me arithmetic is a separate gate.
 always @(posedge clk)if(rst_n&&core_go)begin accepted_identity<=offered_identity;accepted<=accepted+1;end
 task step;begin #2;clk=1;#2;clk=0;#2;end endtask
 initial begin
  #1;rst_n=1;#1;rst_n=0;#1;rst_n=1;
  offer_go=1;repeat(3)step();if(accept_toggle||accepted)$fatal(1,"offeredbeforeactualaccept");
  core_ready=1;step();core_ready=0;
  if(accept_toggle!==1||accepted!=1||accepted_identity!==48'h111112345678)$fatal(1,"toggle notsameactualedge");
  // Immediate full core pause: ACK must observe event without another core edge.
  #120;if(accept_toggle!==1||accepted_identity!==48'h111112345678)$fatal(1,"pausedacceptpayload");
  core_ready=1;core_idle=1;repeat(15)step();if(accepted!=1)$fatal(1,"heldGO withoutACKduplicate");
  accept_ack_toggle=1;repeat(30)step();if(accepted!=1)$fatal(1,"heldGO throughcompletion duplicate");
  offered_identity=48'h222212345678;step();
  if(accept_toggle!==0||accepted!=2||accepted_identity!==48'h222212345678)$fatal(1,"newidentity notaccepted");
  offered_identity=48'h3333abcdef01;repeat(8)step();
  if(accepted!=2||accepted_identity!==48'h222212345678)$fatal(1,"payloadchangedbeforelateACK");
  accept_ack_toggle=0;step();if(accepted!=3||accept_toggle!==1)$fatal(1,"lateACK admission");
  accept_ack_toggle=1;offer_go=0;transport_fence=1;step();transport_fence=0;
  offer_go=1;step();if(accepted!=4||accept_toggle!==0||fault)$fatal(1,"explicitfencedreuse");
  $display("PASS actual-edge toggle;offerbeforeaccept;immediatecorepause;heldGO30afterACK;lateACKpayloadhold;explicitfencedreuse");$finish;
 end
endmodule
