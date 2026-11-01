`timescale 1ns/1fs
module tb_vq_slots;
reg ck=0;always #0.416500 ck=~ck;
reg rst_n=0;reg[3:0]sid=0;integer cyc=0,ph,k,f,st,idx,h,m,v,errors=0,total=0,current_fault_cases=0;
reg[4:0]xv[0:2],xs[0:2];reg[1379:0]xd[0:2];wire[5:0]fault;wire[2:0]gv[0:5];wire[20:0]gi[0:5];wire[3071:0]gd[0:5];
integer count[0:1];integer bad[0:1];integer seen[0:1];reg[1103:0]word_;
function automatic integer age(input integer s,input integer l);begin case(5*s+l)
5:age=11;
6:age=5;
7:age=23;
8:age=26;
9:age=37;
0:age=11;
1:age=5;
2:age=21;
3:age=22;
4:age=35;
15:age=11;
16:age=5;
17:age=20;
18:age=26;
19:age=33;
10:age=11;
11:age=5;
12:age=25;
13:age=23;
14:age=39;
25:age=56;
26:age=5;
27:age=23;
28:age=24;
29:age=35;
20:age=11;
21:age=5;
22:age=21;
23:age=21;
24:age=36;
35:age=10;
36:age=4;
37:age=18;
38:age=18;
39:age=26;
30:age=10;
31:age=4;
32:age=21;
33:age=23;
34:age=34;
45:age=50;
46:age=5;
47:age=26;
48:age=26;
49:age=36;
40:age=11;
41:age=5;
42:age=20;
43:age=22;
44:age=32;
55:age=11;
56:age=5;
57:age=23;
58:age=21;
59:age=32;
50:age=11;
51:age=5;
52:age=24;
53:age=26;
54:age=36;
65:age=11;
66:age=5;
67:age=25;
68:age=21;
69:age=36;
60:age=11;
61:age=5;
62:age=25;
63:age=22;
64:age=39;
75:age=11;
76:age=5;
77:age=23;
78:age=26;
79:age=37;
70:age=11;
71:age=5;
72:age=25;
73:age=21;
74:age=36;
default:age=0;endcase end endfunction
function automatic integer kk(input integer l);begin case(5*int'(sid)+l)
5:kk=1;
6:kk=0;
7:kk=4;
8:kk=1;
9:kk=2;
0:kk=2;
1:kk=0;
2:kk=2;
3:kk=3;
4:kk=2;
15:kk=1;
16:kk=0;
17:kk=0;
18:kk=1;
19:kk=3;
10:kk=1;
11:kk=0;
12:kk=1;
13:kk=4;
14:kk=1;
25:kk=0;
26:kk=0;
27:kk=2;
28:kk=4;
29:kk=3;
20:kk=2;
21:kk=0;
22:kk=2;
23:kk=3;
24:kk=2;
35:kk=0;
36:kk=0;
37:kk=0;
38:kk=4;
39:kk=4;
30:kk=0;
31:kk=4;
32:kk=1;
33:kk=3;
34:kk=4;
45:kk=0;
46:kk=0;
47:kk=2;
48:kk=3;
49:kk=2;
40:kk=1;
41:kk=0;
42:kk=0;
43:kk=2;
44:kk=3;
55:kk=1;
56:kk=0;
57:kk=4;
58:kk=2;
59:kk=3;
50:kk=1;
51:kk=0;
52:kk=4;
53:kk=1;
54:kk=2;
65:kk=2;
66:kk=0;
67:kk=1;
68:kk=3;
69:kk=2;
60:kk=2;
61:kk=0;
62:kk=1;
63:kk=3;
64:kk=1;
75:kk=1;
76:kk=0;
77:kk=4;
78:kk=1;
79:kk=2;
70:kk=2;
71:kk=0;
72:kk=1;
73:kk=3;
74:kk=2;
default:kk=0;endcase end endfunction
function automatic[1023:0]payload(input integer i);begin for(integer j=0;j<64;j=j+1)payload[16*j+:16]=16'h3f00+16'(i);end endfunction
ot_s81sl_rstop u0(.clk(ck),.rst_n(rst_n),.sid(sid),.ri_w(1104'd0),.ri_e(1104'd0),.vi(276'd0),.nx_eo(173'd0),.nx_wo(173'd0),.ci_dir(3'd0),.ci_b(1104'd0),.xf_v(xv[0]),.xf_s(xs[0]),.xf(xd[0]),.g_v(gv[0]),.g_idx(gi[0]),.g_d(gd[0]),.fault(fault[0]));
ot_s81sl_rstop u1(.clk(ck),.rst_n(rst_n),.sid(sid),.ri_w(1104'd0),.ri_e(1104'd0),.vi(276'd0),.nx_eo(173'd0),.nx_wo(173'd0),.ci_dir(3'd0),.ci_b(1104'd0),.xf_v(xv[1]),.xf_s(xs[1]),.xf(xd[1]),.g_v(gv[1]),.g_idx(gi[1]),.g_d(gd[1]),.fault(fault[1]));
ot_s81sl_rstop u2(.clk(ck),.rst_n(rst_n),.sid(sid),.ri_w(1104'd0),.ri_e(1104'd0),.vi(276'd0),.nx_eo(173'd0),.nx_wo(173'd0),.ci_dir(3'd0),.ci_b(1104'd0),.xf_v(xv[2]),.xf_s(xs[2]),.xf(xd[2]),.g_v(gv[2]),.g_idx(gi[2]),.g_d(gd[2]),.fault(fault[2]));
ot_s81sl_rstopt_xo u3(.clk(ck),.rst_n(rst_n),.sid(sid),.ri_w(1104'd0),.ri_e(1104'd0),.vi(276'd0),.nx_eo(173'd0),.nx_wo(173'd0),.ci_dir(3'd0),.ci_b(1104'd0),.xf_v(xv[0]),.xf_s(xs[0]),.xf(xd[0]),.g_v(gv[3]),.g_idx(gi[3]),.g_d(gd[3]),.fault(fault[3]));
ot_s81sl_rstopt_xo u4(.clk(ck),.rst_n(rst_n),.sid(sid),.ri_w(1104'd0),.ri_e(1104'd0),.vi(276'd0),.nx_eo(173'd0),.nx_wo(173'd0),.ci_dir(3'd0),.ci_b(1104'd0),.xf_v(xv[1]),.xf_s(xs[1]),.xf(xd[1]),.g_v(gv[4]),.g_idx(gi[4]),.g_d(gd[4]),.fault(fault[4]));
ot_s81sl_rstopt_xo u5(.clk(ck),.rst_n(rst_n),.sid(sid),.ri_w(1104'd0),.ri_e(1104'd0),.vi(276'd0),.nx_eo(173'd0),.nx_wo(173'd0),.ci_dir(3'd0),.ci_b(1104'd0),.xf_v(xv[2]),.xf_s(xs[2]),.xf(xd[2]),.g_v(gv[5]),.g_idx(gi[5]),.g_d(gd[5]),.fault(fault[5]));
initial begin count[0]=0;count[1]=0;bad[0]=0;bad[1]=0;seen[0]=0;seen[1]=0;end
always @(negedge ck)begin ph=cyc%256;sid=4'(cyc/256);rst_n=(ph>=32);
 for(integer mode_=0;mode_<3;mode_=mode_+1)begin xv[mode_]=0;xs[mode_]=0;xd[mode_]=0;
  for(integer leaf=0;leaf<5;leaf=leaf+1)begin for(integer family_=0;family_<2;family_++)begin
   st=80+age(int'(sid),leaf)+4*(mode_==0?leaf:kk(leaf))+20*family_;
   if(ph>=st&&ph<st+4)begin
    word_=0;word_[0]=1;word_[3:1]=3'(family_+1);word_[8:4]=5'd1;word_[12:9]=sid;word_[20:13]=8'(5*int'(sid)+leaf+((mode_==2&&leaf==2)?1:0));word_[21+:1024]=payload(5*int'(sid)+leaf);
    xv[mode_][leaf]=1;xs[mode_][leaf]=(ph==st);xd[mode_][276*leaf+:276]=276'(word_>>(276*(ph-st)));
   end
  end end
 end
 if(ph==0)begin count[0]=0;count[1]=0;bad[0]=0;bad[1]=0;seen[0]=0;seen[1]=0;end
end
always @(posedge ck)begin cyc=cyc+1;#0.000001;
 if(rst_n)for(integer cls=0;cls<2;cls=cls+1)begin
  if(fault[3*cls])seen[cls]=1;
  if(fault[3*cls+1])errors=errors+1;
  if(gv[3*cls+1][0])begin
   idx=int'(gi[3*cls+1][6:0]);if(idx<5*int'(sid)||idx>=5*int'(sid)+5||gd[3*cls+1][1023:0]!==payload(idx))errors=errors+1;
   count[cls]=count[cls]+1;total=total+1;
  end
  if(gv[3*cls+2][0])begin idx=int'(gi[3*cls+2][6:0]);if(gd[3*cls+2][1023:0]!==payload(idx))bad[cls]=bad[cls]+1;end
 end
 if(cyc%256==220)begin
  for(integer cls=0;cls<2;cls=cls+1)begin if(count[cls]!=10||bad[cls]!=2||seen[cls]!=1)begin errors=errors+1;$display("BAD sid%0d cls%0d count%0d bad%0d oldfault%0d",sid,cls,count[cls],bad[cls],seen[cls]);end if(seen[cls])current_fault_cases=current_fault_cases+1;end
 end
 if(cyc==4095)begin $display("VQ_SLOTS_CAPTURE current_fault_cases%0d candidate_words%0d errors%0d clock_ps833",current_fault_cases,total,errors);if(errors==0&&total==320&&current_fault_cases==32)$display("VQ_SLOTS_CAPTURE_PASS");else $fatal(1,"VQ_SLOTS_CAPTURE_FAIL");$finish;end
end
endmodule
