`timescale 1ns/1ps
module tb_s81_pq_ctl_static;
`ifdef OT_PQ_CTL_CALCAP
 localparam integer IDLE_LAG=1;   // CALCAP: idle is a registered status (+1 edge, never gates events)
`else
 localparam integer IDLE_LAG=0;
`endif
 reg clk=0;always #5 clk=~clk;
 reg rst_n=0,go=0,calendar_v=0,x_rv=0;
 reg[74:0] action=0;
 reg[9:0] ph=0;reg[2:0] np=0;
 reg[191:0] ga=0;
 wire q_consume,b_consume,aq_vin,ba_v,ready,idle,x_re,fault,ev_go,ev_end;
 wire[9:0] aqi;wire[1:0] ba_wv,ev_tag;wire[7:0] ba_blk;
 wire[47:0] hw;wire[35:0] hi;wire[15:0] b0,b1;
 wire[457:0] mdr;wire[609:0] bc;
 wire[18:0] x_addr;wire[31:0] phase_cycles;
 wire[10:0] pa0,pa1;wire[13:0] sa;
 reg[63:0] pq0a,pq0b,pq1a,pq1b;
 reg[47:0] sqa,sqb;
 integer test,c,k,pos,rvk,rvpos,total,lastbeat,retire,checks=0,beats=0;
 integer badvm=0,badcount=0;
 reg expected_head,expected_bc,expected_aqi;reg[9:0] expected_aqi_data;
 reg fam;reg[1:0] tag;
 reg[47:0] words[0:191];
 reg[63:0] header;
 function automatic [47:0] word(input integer i,input bit f);
  reg[47:0] w;integer g;
  begin
   w=48'd1;
   if(f)begin w=w|(48'(i%8)<<1)|(48'd15<<4);for(g=0;g<4;g=g+1)w=w|(48'((i+13*g)%48)<<(8*(g+1)));end
   else begin w=w|(48'((i/8)%12)<<1)|(48'(i%8)<<9)|(48'd3<<12);for(g=2;g<5;g=g+1)w=w|(48'((i/8)%12)<<(8*g));end
   word=w;
  end
 endfunction
 always @(posedge clk)begin
  pq0a<=header;pq0b<=pq0a;pq1a<=0;pq1b<=pq1a;
  sqa<=sa>=14'd8192&&sa<14'd8384 ? words[sa-14'd8192] : 48'd0;sqb<=sqa;
 end
 ot_s81_pq_ctl_static_native dut(.clk(clk),.rst_n(rst_n),.calendar_v(calendar_v),.calendar_action(action),
 .go(go),.i_ph(ph),.i_np(np),.i_xbase(19'd64),.i_xps(19'd8192),.i_obase(19'd98304),.i_ops(19'd2048),.i_fmt(2'd0),
 .q_consume(q_consume),.b_consume(b_consume),.aq_vin(aq_vin),.aqf(2'd0),.aqi_o(aqi),.ba_v_o(ba_v),.ba_wv_o(ba_wv),.ba_blk_o(ba_blk),
 .hw_o(hw),.h_hi_o(hi),.h_b0_o(b0),.h_b1_o(b1),.mdr_o(mdr),.q2f_i(12'd0),.ga_i(ga),.bc_hr_o(bc),
 .ready(ready),.idle(idle),.x_re(x_re),.x_addr(x_addr),.x_rv(x_rv),.f_fault(1'b0),.fault(fault),.phase_cycles(phase_cycles),
 .ev_go(ev_go),.ev_end(ev_end),.ev_tag(ev_tag),.rom_pa0(pa0),.rom_pa1(pa1),.rom_pq0(pq0b),.rom_pq1(pq1b),.rom_sa(sa),.rom_sq(sqb));
`ifdef OT_PQ_CTL_INCAP
 localparam integer INCAP=1;
`else
 localparam integer INCAP=0;
`endif
 localparam integer DRAIN=INCAP;
 initial begin
  k=$value$plusargs("badvm=%d",badvm);k=$value$plusargs("badcount=%d",badcount);
  for(test=0;test<4;test=test+1)begin
   rst_n=0;go=0;action=0;calendar_v=0;ga=0;x_rv=0;fam=test%2;np=3'(test/2);tag=2'(test);ph=10'(512+test*43);
   header=64'(fam)|(64'd6144<<1)|(64'd192<<14)|(64'd32<<46);
   for(k=0;k<192;k=k+1)words[k]=word(k,fam);
   repeat(8)@(negedge clk);rst_n=1;repeat(8)@(negedge clk);
   lastbeat=170+400*np+191+5;retire=lastbeat+40+11;total=32*(np+1);
   for(c=0;c<retire+8;c=c+1)begin
    go=0;action=0;calendar_v=1;ga=0;x_rv=0;
    if(c==16)begin go=1;action[1:0]=tag;end
    if(c==20)begin action[62]=1;action[64:63]=tag;end
    if(c==60)begin action[65]=1;action[67:66]=tag;end
    for(pos=0;pos<=np;pos=pos+1)begin
     k=c-(32+400*pos);
     if(k>=0&&k<96)begin action[2]=1;action[21:3]=19'(64+8192*pos+64*k);end
     rvk=c-(39+400*pos);
     if(rvk>=0&&rvk<96)begin
      action[22]=1;action[36:23]=14'(64*rvk);action[37]=tag[0]^1'(pos);action[38]=fam;
      x_rv=!(badvm&&rvk==17);
     end
     k=c-(170+400*pos);
     if(k>=0&&k<192)begin
      action[39]=1;action[53:40]=14'(8192+k);action[55:54]=tag;action[58:56]=3'(pos);action[59]=fam;
      action[60]=k==191;action[61]=k==191&&pos==np;
     end
    end
    if(c==lastbeat+40&&!badcount)for(k=0;k<12;k=k+1)ga[16*k+4*tag+:4]=4'((total+11-k)/12);
    if(c==retire)action[68+tag]=1;
    if(c==retire+1)action[72]=1;
    expected_head=0;expected_bc=0;expected_aqi=0;expected_aqi_data=0;
    for(pos=0;pos<=np;pos=pos+1)begin
     if(c>=175+400*pos&&c<175+400*pos+192)expected_head=1;
     if(c>=178+400*pos&&c<178+400*pos+192)expected_bc=1;
     rvk=c-(39+400*pos+26);
     if(rvk>=0&&rvk<96&&!fam)begin expected_aqi=1;expected_aqi_data={1'b1,8'(2*rvk),tag[0]^1'(pos)};end
    end
    #1;if(go&&(pa0!=={ph,1'b0}||pa1!=={ph,1'b1}))$fatal(1,"STATIC_CTL FAIL phase width");
    @(posedge clk);#1;
    if({q_consume,b_consume}!=={expected_head&&!fam,expected_head&&fam})$fatal(1,"STATIC_CTL FAIL consume pin edge c=%0d",c);
    if({bc[591],bc[39]}!=={expected_bc&&!fam,expected_bc&&fam})$fatal(1,"STATIC_CTL FAIL broadcast edge c=%0d",c);
    if(bc[609]!==(c==22)||bc[595]!==(c==62))$fatal(1,"STATIC_CTL FAIL broadcast cfg/go edge c=%0d",c);
    if(c==22&&(bc[608:599]!==ph||bc[598:596]!==np))$fatal(1,"STATIC_CTL FAIL configuration fields c=%0d",c);
    if(aqi[9]!==expected_aqi||(expected_aqi&&aqi!==expected_aqi_data))$fatal(1,"STATIC_CTL FAIL AQ metadata edge c=%0d",c);
    // exact drain edge: ga captured at the pin under OT_PQ_CTL_INCAP is one edge later (+44 vs +43)
    if(c==lastbeat+42+DRAIN&&!badcount&&dut.rows_seen[tag]===19'(total))$fatal(1,"STATIC_CTL FAIL count drained early c=%0d",c);
    if(c==lastbeat+43+INCAP&&!badcount&&dut.rows_seen[tag]!==19'(total))$fatal(1,"STATIC_CTL FAIL measured count drain c=%0d",c);
    if(x_re!==action[2] || (x_re&&x_addr!==action[21:3]))$fatal(1,"STATIC_CTL FAIL VM request shifted c=%0d",c);
    if(ev_end!==(c==retire)||(ev_end&&ev_tag!==tag))$fatal(1,"STATIC_CTL FAIL retire event c=%0d",c);
    if(ev_go!==(c==60))$fatal(1,"STATIC_CTL FAIL launch shifted c=%0d",c);
    if(c>=16+IDLE_LAG && idle!==(c>=retire+IDLE_LAG))$fatal(1,"STATIC_CTL FAIL retirement moved c=%0d",c);
    for(pos=0;pos<=np;pos=pos+1)begin
     k=c-(170+400*pos+5);
     if(k>=0&&k<192)begin
      if({q_consume,b_consume}!=={!fam,fam}||hw!==words[k])$fatal(1,"STATIC_CTL FAIL native stream c=%0d k=%0d hw=%h expected=%h",c,k,hw,words[k]);
      if(!fam&&(b0!==16'(192*(tag[0]^1'(pos))+((k/8)%12)*16+k%8)||b1!==b0+16'd8))$fatal(1,"STATIC_CTL FAIL native index c=%0d",c);
      beats=beats+1;
     end
    end
    checks=checks+1;
    if(c>retire+2 && fault!==(badvm||badcount))$fatal(1,"STATIC_CTL FAIL fault diagnosis c=%0d fault=%0d",c,fault);
    @(negedge clk);
   end
  end
  $display("STATIC_CTL PASS checks=%0d stream_beats=%0d productionK=6144 tags=4 positions=1,2 badvm=%0d badcount=%0d response_fault_only=1 retire_fixed=1 PHW=10 SAW=14 phases=512,555,598,641 stream_base=8192",checks,beats,badvm,badcount);
  $finish;
 end
endmodule
