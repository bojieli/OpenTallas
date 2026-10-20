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
primitive altos_dff_sr_0 (q, v, clk, d, s, r, xcr);
	output q;
	reg q;
	input v, clk, d, s, r, xcr;

	table
	//	v,  clk, d, s, r : q' : q;

		*  ?   ?   ?   ?   ? : ? : x;
		?  ?   ?   ?   1   ? : ? : 0;
		?  ?   ?   1   0   ? : ? : 1;
		?  b   ? (1?)  0   ? : 1 : -;
		?  x   1 (1?)  0   ? : 1 : -;
		?  ?   ? (10)  0   ? : ? : -;
		?  ?   ? (x0)  0   ? : ? : -;
		?  ?   ? (0x)  0   ? : 1 : -;
		?  b   ?  0   (1?) ? : 0 : -;
		?  x   0  0   (1?) ? : 0 : -;
		?  ?   ?  0   (10) ? : ? : -;
		?  ?   ?  0   (x0) ? : ? : -;
		?  ?   ?  0   (0x) ? : 0 : -;
		? (x1) 0  0    ?   0 : ? : 0;
		? (x1) 1  ?    0   0 : ? : 1;
		? (x1) 0  0    ?   1 : 0 : 0;
		? (x1) 1  ?    0   1 : 1 : 1;
		? (x1) ?  ?    0   x : ? : -;
		? (x1) ?  0    ?   x : ? : -;
		? (1x) 0  0    ?   ? : 0 : -;
		? (1x) 1  ?    0   ? : 1 : -;
		? (x0) 0  0    ?   ? : ? : -;
		? (x0) 1  ?    0   ? : ? : -;
		? (x0) ?  0    0   x : ? : -;
		? (0x) 0  0    ?   ? : 0 : -;
		? (0x) 1  ?    0   ? : 1 : -;
		? (01) 0  0    ?   ? : ? : 0;
		? (01) 1  ?    0   ? : ? : 1;
		? (10) ?  0    ?   ? : ? : -;
		? (10) ?  ?    0   ? : ? : -;
		?  b   *  0    ?   ? : ? : -;
		?  b   *  ?    0   ? : ? : -;
		?  ?   ?  ?    ?   * : ? : -;
	endtable
endprimitive
module tb;
reg ck=0,d=0,rn=1,sn=1;wire gold,got;integer ini,rv,sv,dv,cv,prev,next,checks=0;
altos_dff_sr_0 refudp(gold,1'b0,ck,~d,~rn,~sn,1'b0);
DFFASRHQNx1_ASAP7_75t_R dut(.CLK(ck),.D(d),.RESETN(rn),.SETN(sn),.QN(got));
initial begin
 for(ini=0;ini<2;ini=ini+1)for(rv=0;rv<2;rv=rv+1)for(sv=0;sv<2;sv=sv+1)for(dv=0;dv<2;dv=dv+1)begin
  ck=0;rn=ini?0:1;sn=ini?1:0;#2;rn=1;sn=1;#2;d=dv;rn=rv;sn=sv;#2;ck=1;#2;
  checks=checks+1;if(gold!==got)begin $display("ASR_UDP_FAIL ini=%0d rn=%0d sn=%0d d=%0d canonical=%b normalized=%b",ini,rv,sv,dv,gold,got);$fatal(1);end
  ck=0;#2;checks=checks+1;if(gold!==got)$fatal(1,"ASR_UDP_FAIL hold");
 end
 for(ini=0;ini<2;ini=ini+1)for(cv=0;cv<2;cv=cv+1)for(dv=0;dv<2;dv=dv+1)for(prev=0;prev<4;prev=prev+1)for(next=0;next<4;next=next+1)begin
  ck=0;rn=ini?0:1;sn=ini?1:0;#2;rn=1;sn=1;#2;d=dv;#2;ck=cv;#2;
  rn=prev[1];sn=prev[0];#2;checks=checks+1;if(gold!==got)begin $display("ASR_TRANS_FAIL previous prev=%b next=%b clk=%b init=%b d=%b gold=%b got=%b",prev[1:0],next[1:0],ck,ini[0],dv[0],gold,got);$fatal(1);end
  rn=next[1];sn=next[0];#2;checks=checks+1;if(gold!==got)begin $display("ASR_TRANS_FAIL prev=%b next=%b clk=%b init=%b d=%b gold=%b got=%b",prev[1:0],next[1:0],ck,ini[0],dv[0],gold,got);$fatal(1);end
  d=~d;#2;checks=checks+1;if(gold!==got)$fatal(1,"ASR_TRANS_FAIL datahold");
  ck=0;#2;checks=checks+1;if(gold!==got)$fatal(1,"ASR_TRANS_FAIL falling");
 end
 $display("ASR_UDP_PASS checks=%0d",checks);$finish;end
endmodule
