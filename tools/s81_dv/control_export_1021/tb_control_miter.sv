`timescale 1ns/1ps
module tb_control_miter;
 reg ck=0; always #5 ck=~ck;
 reg rn=0;
 reg [3459:0] fs=0; reg [1415:0] fo=0;
 wire [131:0] cs,cn,rs,rn_cmd; wire [1:0] crs,crn,rrs,rrn;
 wire [513:0] vd,rvd; wire vf;
 dsdv_bksel_c_pa_n32 dut(.ck(ck),.rst_profile({413{rn}}),
 .fs0_0(fs[0+:288]),.fs0_1(fs[288+:288]),.fs0_2(fs[576+:289]),
 .fs1_0(fs[865+:288]),.fs1_1(fs[1153+:288]),.fs1_2(fs[1441+:289]),
 .fs2_0(fs[1730+:288]),.fs2_1(fs[2018+:288]),.fs2_2(fs[2306+:289]),
 .fs3_0(fs[2595+:288]),.fs3_1(fs[2883+:288]),.fs3_2(fs[3171+:289]),
 .fo0(fo[0+:354]),.fo1(fo[354+:354]),.fo2(fo[708+:354]),.fo3(fo[1062+:354]),
 .t_c_s(cs),.t_c_n(cn),.t_cr_s(crs),.t_cr_n(crn),.vd(vd));
 dsfd_selt_c #(.SEARCH_PIPE(1),.DM(4),.PACE(2),.MRG_PIPE(1),.RQPIPE(1),.SLAT(4),.XDX(15)) refdut(
 .ck(ck),.rst(rn),.f_s(fs),.f_o(fo),.t_c({rn_cmd,rs}),.t_cr({rrn,rrs}),.vd(rvd),.vf(vf));
 integer cycle=0,checks=0,beats=0,changes=0,returned=0,epochs=0;
 integer credit[0:3]; reg[263:0]prev_cmd=0; reg[31:0]rng=32'h6ab54321;
 reg[864:0] status; reg[353:0]beat;
 function[31:0]next_rng(input[31:0]x);reg[31:0]y;begin y=x^(x<<13);y=y^(y>>17);next_rng=y^(y<<5);end endfunction
 always @(posedge ck)begin
  #1;
  if({cs,cn,crs,crn}!=={rs,rn_cmd,rrs,rrn}||vd[1:0]!==rvd[1:0]||(rvd[1]&&vd[513:2]!==rvd[513:2]))begin
   $display("CONTROL_MISMATCH cycle=%0d rn=%b command=%b valid=%b payload=%b",cycle,rn,{cs,cn,crs,crn}!=={rs,rn_cmd,rrs,rrn},vd[1:0]!==rvd[1:0],rvd[1]&&vd[513:2]!==rvd[513:2]);
   $fatal(1,"CONTROL_MITER_FAIL");
  end
  checks=checks+270+(rvd[1]?512:0);
  if(rvd[1])beats=beats+1;
  if({cs,cn}!=prev_cmd)changes=changes+1;
  prev_cmd={cs,cn};
 end
 initial begin
  for(integer q=0;q<4;q=q+1)credit[q]=4;
  for(cycle=0;cycle<4096;cycle=cycle+1)begin
   @(negedge ck);
   rn=(cycle%1024)>=8;
   if(cycle%1024==8)epochs=epochs+1;
   fs=0;fo=0;
   for(integer q=0;q<4;q=q+1)begin
    if(!rn)credit[q]=4;
    else if(({rrn,rrs}>>q)&1)begin credit[q]=credit[q]+1;returned=returned+1;end
    status=0;
    for(integer g=0;g<16;g=g+1)begin
     status[g*15+:15]=15'(g%4+1);status[240+g*15+:15]=15'(g%3);
     status[480+g*11+:11]=11'(g%3);status[656+g*11+:11]=11'(g%2);
    end
    status[837:832]={1'b0,cycle%128>=80,cycle%128>=64,cycle%128>=48,cycle%128>=32,cycle%128>=16};
    status[838]=rn;status[839]=rn;
    status[840]=rn&&cycle%128==16;
    status[850:841]=10'(1+(cycle/128)%32);status[858:851]=8'(cycle/128);
    status[859]=rn;status[861:860]=2'(q);status[864:862]=0;
    if(rn)fs[q*865+:865]=status;
    rng=next_rng(rng);beat=0;
    for(integer b=0;b<16;b=b+1)beat[1+b*20+:20]=20'(cycle*64+q*16+b);
    beat[321+:16]=16'hffff;beat[337+:16]=0;beat[353]=cycle%128>=96;
    if(rn&&credit[q]>0&&cycle%8==q)begin beat[0]=1;credit[q]=credit[q]-1;end
    fo[q*354+:354]=beat;
   end
  end
  @(negedge ck);
  $display("CONTROL_STATS cycles %0d checks %0d epochs %0d command_changes %0d vd_beats %0d credits_returned %0d",cycle,checks,epochs,changes,beats,returned);
  if(epochs!=4||changes<4||beats<1||returned<1)$fatal(1,"CONTROL_COVERAGE_FAIL");
  $display("CONTROL_MITER_PASS");$finish;
 end
endmodule
