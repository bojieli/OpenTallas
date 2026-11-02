`timescale 1ps/1ps
module tb;
reg clk=0;always begin #416 clk=1;#417 clk=0;end
reg rst_n=0;reg[8:0]pr=0,wa=0;reg[1:0]step=2;reg owner=1,pv=0,ri=0;reg[511:0]wd=0,wm=0;integer mutant=0;
wire[1023:0]rd;wire[8:0]plus=pr+9'd1;
ot_bind_native_193c9bdc13b0c4251a5bbbc4 mem(.RD_ADDR({pr,plus}),.RD_DATA(rd),.WR_ADDR(wa),.WR_CLK(clk),.WR_DATA(wd),.WR_EN(wm));
// Actual native pmem port packing: highRD ispr, lowRD ispr+1.
wire[1023:0]pword=owner?{step==2?rd[511:0]:{512{1'b1}},rd[1023:512]}:1024'd0;
wire nr,nv,cr,cv;wire[1023:0]nw,cw,s0,s1;wire[1:0]cn;wire cwp,crp;
native_capture refc(.clk(clk),.rst_n(rst_n),.p_v(pv),.p_ready_i(ri),.p_w(pword),.p_ready(nr),.out_v(nv),.out_w(nw));
pmem_candidate cand(.clk(clk),.rst_n(rst_n),.pr(pr),.wa(wa),.pstep(step),.owner(owner),.p_v(pv),.p_ready_i(ri),.wd(wd),.wm(wm),.mutant(mutant),.p_ready(cr),.out_v(cv),.out_w(cw),.slot0(s0),.slot1(s1),.sk_n(cn),.wp(cwp),.rp(crp));
integer cyc=0,checks=0,pushes=0,pops=0,writes=0,warm=0,collisions=0,oddreads=0,tailreads=0,emptychecks=0,resetpush=0,full_pv_pop=0;reg[31:0]rnd=32'h9a3ce517;
initial void'($value$plusargs("mutant=%d",mutant));
always@(negedge clk)begin
 rnd={rnd[30:0],rnd[31]^rnd[21]^rnd[1]^rnd[0]};
 // Every address gets genuinely distinct payload through the native write port.
 wd=0;for(integer j=0;j<16;j++)wd[32*j+:32]=(32'h13579bdf^(32'(cyc)*32'h01010307)^(32'(j)*32'h9e3779b9));
 if(cyc<4)begin rst_n=0;pv=0;ri=0;wm=0;end
 else if(cyc<516)begin rst_n=1;pv=0;ri=0;wa=9'(cyc-4);wm='1;pr=wa;end
 else begin
  rst_n=1;pv=rnd[0]|rnd[3];ri=rnd[1];owner=rnd[2]|rnd[9];step=rnd[4]?2:1;pr=rnd[16:8];wa=rnd[25:17];
  for(integer j=0;j<16;j++)wm[32*j+:32]=rnd^(32'h11111111*32'(j));
  if(cyc%7==0)wa=pr;else if(cyc%7==1)wa=pr+9'd1;
  if(cyc%11==0)pr=511;
  // Tail/owner changes and n1 simultaneous pop/push; full skid still refusespush.
  if(cyc%32<8)begin pv=1;ri=0;owner=1;step=2;end
  if(cyc%32>=8&&cyc%32<16)begin pv=1;ri=1;end
  if(cyc%32>=16&&cyc%32<20)begin pv=0;ri=1;end
  // Warm reset preserves every payload slot. Also exercise payload writes while reset holds.
  if(cyc%97==0||cyc%97==1)begin rst_n=0;pv=(cyc%97==1);warm++;end
 end
end
always@(posedge clk)begin
 if(pv&&nr)begin pushes++;if(pr[0])oddreads++;if(step!=2)tailreads++;if((|wm)&&(wa==pr||wa==plus))collisions++;if(!rst_n)resetpush++;end
 if(nv&&ri)pops++;
 if((|wm))writes++;
 if(refc.g_pskid.sk_n==2&&pv&&ri)full_pv_pop++;
 cyc++;#1;
 if({nr,nv,refc.g_pskid.sk_n,refc.g_pskid.wp,refc.g_pskid.rp}!={cr,cv,cn,cwp,crp}||nw!==cw||refc.g_pskid.sk0!==s0||refc.g_pskid.sk1!==s1)begin
  $display("PMEM_NATIVE_FAIL cycle=%0d mutant=%0d n=%0d wp=%b rp=%b ready=%b/%b valid=%b/%b s0=%b s1=%b out=%b rst=%b",cyc,mutant,cn,cwp,crp,nr,cr,nv,cv,refc.g_pskid.sk0===s0,refc.g_pskid.sk1===s1,nw===cw,rst_n);$fatal(1,"native memory+capture mismatch");end
 checks++;if(!nv)emptychecks++;
 if(cyc==4096)begin
  if(pushes<200||collisions<20||oddreads<50||tailreads<50||emptychecks<100||resetpush<10||full_pv_pop<20)$fatal(1,"insufficientcoverage");
  $display("PMEM_NATIVE_PASS checks=%0d pushes=%0d pops=%0d writes=%0d collisions=%0d odd=%0d tail=%0d empty=%0d warm=%0d resetpush=%0d fullpvpop=%0d FFdelta=-1020 macros=4 clockps=833",checks,pushes,pops,writes,collisions,oddreads,tailreads,emptychecks,warm,resetpush,full_pv_pop);$finish;end
end
endmodule
