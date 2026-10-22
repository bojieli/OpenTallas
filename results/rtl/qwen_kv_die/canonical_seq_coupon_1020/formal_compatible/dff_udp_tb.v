// BSD 3-Clause License
// 
// Copyright 2022 Lawrence T. Clark, Vinay Vashishtha, or Arizona State
// University
// 
// Redistribution and use in source and binary forms, with or without
// modification, are permitted provided that the following conditions are met:
// 
// 1. Redistributions of source code must retain the above copyright notice,
// this list of conditions and the following disclaimer.
// 
// 2. Redistributions in binary form must reproduce the above copyright
// notice, this list of conditions and the following disclaimer in the
// documentation and/or other materials provided with the distribution.
// 
// 3. Neither the name of the copyright holder nor the names of its
// contributors may be used to endorse or promote products derived from this
// software without specific prior written permission.
// 
// THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
// AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
// IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
// ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
// LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
// CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
// SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
// INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
// CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
// ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
// POSSIBILITY OF SUCH DAMAGE.

// Verilog for library /home/anolas19/Liberate/Verilog/asap7sc7p5t_SEQ_RVT_TT_211229_pex created by Liberate 18.1.0.293 on Fri Dec 31 22:59:44 MST 2021 for SDF version 2.1

// type:  
primitive altos_dff (q, v, clk, d, xcr);
	output q;
	reg q;
	input v, clk, d, xcr;

	table
		*  ?   ? ? : ? : x;
		? (x1) 0 0 : ? : 0;
		? (x1) 1 0 : ? : 1;
		? (x1) 0 1 : 0 : 0;
		? (x1) 1 1 : 1 : 1;
		? (x1) ? x : ? : -;
		? (bx) 0 ? : 0 : -;
		? (bx) 1 ? : 1 : -;
		? (x0) b ? : ? : -;
		? (x0) ? x : ? : -;
		? (01) 0 ? : ? : 0;
		? (01) 1 ? : ? : 1;
		? (10) ? ? : ? : -;
		?  b   * ? : ? : -;
		?  ?   ? * : ? : -;
	endtable
endprimitive
module tb;reg ck=0,d=0;wire gold,got;integer ini,prev,next,checks=0;
altos_dff refudp(gold,1'b0,ck,~d,1'b0);DFFHQNx1_ASAP7_75t_R dut(ck,d,got);
initial begin
 for(ini=0;ini<2;ini=ini+1)for(prev=0;prev<4;prev=prev+1)for(next=0;next<4;next=next+1)begin
  ck=0;d=!ini[0];#2;ck=1;#2;ck=0;#2;d=prev[0];#2;ck=prev[1];#2;
  checks=checks+1;if(gold!==got)$fatal(1,"DFF_UDP_FAIL previous");
  d=next[0];#2;checks=checks+1;if(gold!==got)$fatal(1,"DFF_UDP_FAIL datahold");
  ck=next[1];#2;checks=checks+1;if(gold!==got)$fatal(1,"DFF_UDP_FAIL clock");
  ck=0;#2;checks=checks+1;if(gold!==got)$fatal(1,"DFF_UDP_FAIL falling");
 end
 $display("DFF_UDP_PASS checks=%0d",checks);$finish;end endmodule
