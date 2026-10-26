`timescale 1ns/1ps
module tb_astk_tc_faces;
    reg ck=0; always #0.5 ck=~ck;
    reg rn=0, start=0; reg [13:0] t=0;
    reg [14:0] ref_q;
    reg [571:0] qo_d=0,qo_expected;
    wire [571:0] qo_face;
    qkd_astk_qo_face u_qo(.ck(ck),.rn(rn),.d(qo_d),.q(qo_face));
    wire [59:0] faces;
    // Reference is the existing controller's qo[14:0] register behavior.
    always @(posedge ck or negedge rn) if(!rn) ref_q[0]<=0; else ref_q[0]<=start;
    always @(posedge ck) ref_q[14:1]<=t;
    genvar f;
    generate for(f=0;f<4;f=f+1) begin:g_f
       qkd_astk_tc_face u (.ck(ck),.rn(rn),.start(start),.t(t),.q(faces[15*f+:15]));
    end endgenerate
    integer i,k,mismatches=0;
    initial begin
       repeat(5) @(negedge ck); rn=1;
       for(i=0;i<6000;i=i+1) begin
          @(negedge ck); t=$urandom;start=$urandom;rn=(i%197!=0);
          for(k=0;k<18;k=k+1) if(k<17) qo_d[32*k+:32]=$urandom;
          qo_d[571:544]=$urandom;
          qo_expected=qo_d;
          if(!rn) begin qo_expected[0]=0;qo_expected[15]=0;qo_expected[536:534]=0;end
          @(posedge ck);#0.01;
          if(qo_face!==qo_expected)mismatches=mismatches+1;
          for(k=0;k<4;k=k+1) if(faces[15*k+:15] !== ref_q) mismatches=mismatches+1;
       end
       if(mismatches==0) $display("PASS astk_tc_faces edges=6000 copies=4 mismatches=0");
       else $display("FAIL astk_tc_faces mismatches=%0d",mismatches);
       $finish;
    end
endmodule
