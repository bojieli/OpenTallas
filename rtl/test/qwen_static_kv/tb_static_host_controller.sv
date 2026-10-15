`timescale 1ns/1ps
// Persistent native controller component, including actual host CDC, pcport,
// raw PHY pin stage and ECC. Common-clock ABI proof only: production dual-clock
// insertion/phase and full compiled host program remain separate qualification.
module tb_static_host_controller;
 localparam CYCLES=2400,RL=23;
 reg ck=0;always #0.512 ck=~ck;
 reg [1:0] rst=0;
 reg owner=0;reg [42:0] cmd=0;reg reserved=0;
 reg [287:0] es=0;reg [288:0] pi=0;
 wire [327:0] po[0:1];wire [293:0] co[0:1];wire [260:0] er[0:1];wire [1:0] fault,cv,cw,cf;
 reg slots[0:CYCLES-1],rawslots[0:CYCLES-1];
 reg rawslot=0;wire [15:0] out_epoch[0:1];
 genvar g;
 generate for(g=0;g<2;g++)begin:controllers
  qkd_ctrl_pc_host_static #(.PROFILE(g==0?1:0))dut(
   .pll_hbm(ck),.hrst(rst[g]),.ck(ck),.rsi(rst[g]),.pc(5'd13),.ci(319'b0),.co(co[g]),
   .es(es),.er(er[g]),.po(po[g]),.pi(pi),.ki(33'b0),.ko(),.fi(1'b0),.fo(fault[g]),
   .static_cmd_owner(owner),.static_cmd(cmd),.reserved_rd(reserved),
   .static_epoch(16'd7),.expected_raw_valid(rawslot),.corrected_epoch(out_epoch[g]),.completion_v(cv[g]),.completion_we(cw[g]),.completion_fault(cf[g]));
 end endgenerate
 function automatic [255:0] data(input integer row,sector);
  for(integer i=0;i<8;i++)data[32*i+:32]=32'h981ac500^32'(row*65537)^32'(sector*71+i*31);
 endfunction
 function automatic [71:0] ecc(input [63:0] d);
  reg [71:0] c;integer j;begin
   c=0;j=0;for(integer p=1;p<=71;p++)if((p&(p-1))!=0)begin c[p-1]=d[j];j++;end
   for(integer k=0;k<7;k++)for(integer p=1;p<=71;p++)if((p&(1<<k))!=0)c[(1<<k)-1]^=c[p-1];
   c[71]=^c[70:0];ecc=c;
  end
 endfunction
 function automatic [287:0] encode(input [255:0] d);
  for(integer w=0;w<4;w++)encode[72*w+:72]=ecc(d[64*w+:64]);
 endfunction
 reg [18:0] openrow[0:31];
 reg due[0:CYCLES+RL];reg [287:0] word[0:CYCLES+RL];
 reg wdue[0:CYCLES+8];reg [287:0] wword[0:CYCLES+8];
 integer errors=0,mode=0,landed,hostreads,hostwrites,commits,reads;
 task automatic bad(input string message);
  if(errors<12)$display("BAD %s",message);errors++;
 endtask
 task automatic drive(input integer t);
  es=0;cmd=0;owner=t>=220;
  if(t==100)es={1'b1,1'b1,5'd5,5'd7,19'd24427,data(24427,157),1'b1};
  if(t==160)es={1'b0,1'b0,5'd5,5'd7,19'd24427,256'b0,1'b1};
  if(t==230)cmd={10'd0,2'b0,11'd256,19'd67,1'b1};
  if(t==300||t==1360)cmd={10'b0,2'd1,30'b0,1'b1};
  if(t==1300)cmd={10'd512,2'b0,11'd768,19'd67,1'b1};
 endtask
 initial begin
  void'($value$plusargs("faultmode=%d",mode));
  for(integer phase=0;phase<2;phase++)begin
   rst=0;owner=0;cmd=0;reserved=0;es=0;pi=0;
   for(integer t=0;t<CYCLES+RL+1;t++)begin due[t]=0;word[t]=0;end
   for(integer t=0;t<CYCLES+9;t++)begin wdue[t]=0;wword[t]=0;end
   for(integer b=0;b<32;b++)openrow[b]=0;
   landed=0;hostreads=0;hostwrites=0;commits=0;reads=0;
   repeat(16)@(negedge ck);rst[phase]=1;
   for(integer t=0;t<CYCLES;t++)begin
    drive(t);
    if(phase==0)reserved=0;else reserved=slots[t];
    if(phase==1&&mode==1&&t>0)reserved=slots[t-1];
    if(phase==1&&mode==2&&t==1300)cmd[42:33]=10'd513;
    pi={word[t],due[t]};
    rawslot=phase==0?due[t]:rawslots[t];
    if(phase==0)rawslots[t]=due[t];
    if(phase==1&&mode==3&&t==400)pi[0]=0;
    @(posedge ck);
    // Wrapper has two RD reservation pin stages ahead of its actual core.
    if(phase==0&&t>=2)slots[t-2]=controllers[0].dut.u_ctl.core.on.legal_rd;
    if(po[phase][0]&&po[phase][3:1]==3'd1)openrow[po[phase][8:4]]=po[phase][27:9];
    if(po[phase][28])begin
     automatic integer bank=po[phase][34:30];
     automatic integer col=po[phase][39:35];
     automatic integer sec=((bank>>2)<<7)|(col<<2)|(bank&3);
     automatic integer row=openrow[bank];
     if(po[phase][29])begin wdue[t+5]=1;wword[t+5]=encode(data(row,sec));hostwrites++;end
     else begin due[t+RL]=1;word[t+RL]=encode(data(row,sec));reads++;end
    end
    if(wdue[t]&&po[phase][327:40]!==wword[t])bad($sformatf("PHY write data phase%0d t%0d",phase,t));
    if(co[phase][0])begin
     automatic integer expected_sector=landed<256?landed:512+landed-256;
     automatic integer sec={co[phase][11:9],co[phase][7:1]};
     if(out_epoch[phase]!=7||sec!=expected_sector||co[phase][281:26]!==data(67,expected_sector))bad($sformatf("KV row phase%0d index%0d sec%0d",phase,landed,sec));
     landed++;
    end
    if(er[phase][0])begin
     hostreads++;
     if(er[phase][256:1]!==data(24427,157))bad("host native read data");
    end
    if(cv[phase])commits++;
    if(fault[phase]||cf[phase])bad($sformatf("controller sticky fault phase%0d t%0d",phase,t));
    @(negedge ck);
   end
   if(phase==0)begin slots[CYCLES-2]=0;slots[CYCLES-1]=0;end
   if(landed!=512||hostreads!=1||hostwrites!=1||commits!=2||reads!=513)
    bad($sformatf("counts phase%0d land%0d hostread%0d write%0d commit%0d rawread%0d",phase,landed,hostreads,hostwrites,commits,reads));
  end
  if(errors)begin $display("FAIL persistent staticKV host controller errors%0d mode%0d",errors,mode);$fatal(1);end
  $display("PASS persistent staticKV host controller K256 V256 hostNativeWriteRead bootCompletion2 rawPHYRL23 sameControllerNoResetBetweenPhases commonClockOnly");$finish;
 end
endmodule
