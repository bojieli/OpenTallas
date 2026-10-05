`timescale 1ps/1ps
module tb_w2_fullnc6;
 localparam NC=6,AW=34,TW=32,GW=4,PW=35;
 localparam [255:0] HIGH_DATA=256'b1<<255;
 reg [5:0] caller_held=0;
 reg caller_we[0:5];reg[33:0] caller_addr[0:5];reg[31:0] caller_tag[0:5];
 reg[3:0] caller_gen[0:5];reg[255:0] caller_data[0:5];
 reg[34:0] receipt_pt[0:5][0:15];reg[3:0] receipt_pg[0:5][0:15];
 reg receipt_we[0:5][0:15],receipt_valid[0:5][0:15],receipt_active[0:5][0:15];
 reg receipt_reset_quarantined[0:5][0:15];
 reg[191:0] observed_rt,observed_wt;reg[23:0] observed_rg,observed_wg;
 reg[33:0] observed_pa;reg[255:0] observed_pd;
 reg clk=0;always #500 clk=~clk;
 reg rst_n=0,admission_stop=0,rearm_v=0,provider_fenced=0,reset_fenced=0;
 wire rearm_rdy,idle,fault,repair_busy;
 reg reverse_fenced=0;
 reg [5:0] cv=0,cwe=0,cr=0,cwr=0;wire[5:0] cready,rv,wv;
 reg [6*AW-1:0] ca=0;reg [6*TW-1:0] ct=0;reg[6*GW-1:0] cg=0;reg[6*256-1:0] cd=0;
 wire[6*TW-1:0] rt,wt;wire[6*GW-1:0] rg,wg;wire[6*256-1:0] rd;
 wire pv,pwe;reg pr=0;wire[AW-1:0] pa;wire[PW-1:0] pt;wire[GW-1:0] pg;wire[255:0] pd;
 reg prv=0,pwv=0;wire prr,pwr;reg[PW-1:0] prt=0,pwt=0;reg[GW-1:0] prg=0,pwg=0;reg[255:0] prd=0;
 wire disabled_pv,disabled_fault;
 ot_w2_nc6_protected_completion_reset_quarantine #(.OPT_EXACT(1),.OPT_RESET_QUARANTINE(1),.PC_ID(7)) dut(
  .clk(clk),.rst_n(rst_n),.admission_stop(admission_stop),.rearm_v(rearm_v),.provider_fenced(provider_fenced),.reset_fenced(reset_fenced),.rearm_rdy(rearm_rdy),.idle(idle),
  .c_req_v(cv),.c_req_we(cwe),.c_req_rdy(cready),.c_req_addr(ca),.c_req_tag(ct),.c_req_gen(cg),.c_req_data(cd),
  .c_rsp_v(rv),.c_rsp_rdy(cr),.c_rsp_tag(rt),.c_rsp_gen(rg),.c_rsp_data(rd),.c_wr_done_v(wv),.c_wr_done_rdy(cwr),.c_wr_done_tag(wt),.c_wr_done_gen(wg),
  .p_req_v(pv),.p_req_rdy(pr),.p_req_we(pwe),.p_req_addr(pa),.p_req_tag(pt),.p_req_gen(pg),.p_req_data(pd),
  .p_rsp_v(prv),.p_rsp_rdy(prr),.p_rsp_tag(prt),.p_rsp_gen(prg),.p_rsp_data(prd),
  .p_wr_done_v(pwv),.p_wr_done_ready(pwr),.p_wr_done_tag(pwt),.p_wr_done_gen(pwg),.fault(fault),.repair_busy(repair_busy),.reverse_fenced(reverse_fenced));
 ot_w2_nc6_protected_completion_reset_quarantine #(.PC_ID(7)) disabled(
  .clk(clk),.rst_n(rst_n),.admission_stop(admission_stop),.rearm_v(1'b0),.provider_fenced(1'b0),.reset_fenced(1'b0),
  .c_req_v(cv),.c_req_we(cwe),.c_req_addr(ca),.c_req_tag(ct),.c_req_gen(cg),.c_req_data(cd),.c_rsp_rdy(cr),.c_wr_done_rdy(cwr),
  .p_req_v(disabled_pv),.p_req_rdy(pr),.p_rsp_v(prv),.p_rsp_tag(prt),.p_rsp_gen(prg),.p_rsp_data(prd),
  .p_wr_done_v(pwv),.p_wr_done_tag(pwt),.p_wr_done_gen(pwg),.fault(disabled_fault),.reverse_fenced(reverse_fenced));
 integer cycles=0,scenario=0,case_pass_count=0;
 reg held_req=0;reg[329:0] held_req_tuple;
 reg[5:0] held_reads=0,held_writes=0;
 reg[291:0] held_read_tuple[0:5];reg[35:0] held_write_tuple[0:5];
 integer last_req_edge[0:5];integer accepted[0:5];reg[34:0] observed_pt;reg[3:0] observed_pg;reg observed_pwe;reg[5:0] observed_client_req;
 localparam integer CLEAN_PROGRESS_EDGES=1024; // finite fixture progress assertion with explicit peers ready; not a job cap
reg took_req,took_read,took_write,took_rearm;reg[5:0] took_client_read,took_client_write;
 // External provider receipts survive a LOCAL reset, including a pulse
 // between fixture steps. This flag is reference state, not DUT protection.
 always @(negedge rst_n)begin
  for(integer c=0;c<6;c=c+1)
   for(integer r=0;r<16;r=r+1)
    if(receipt_active[c][r])receipt_reset_quarantined[c][r]=1;
 end
 task external_receipt_counts(input integer c,output integer live_count,orphan_count);
  begin
   live_count=0;orphan_count=0;
   for(integer r=0;r<16;r=r+1)begin
    if(receipt_reset_quarantined[c][r]&&!receipt_active[c][r])
     $fatal(1,"reset orphan receipt dropped without provider disposal c%0d r%0d",c,r);
    if(receipt_active[c][r])begin
     if(!receipt_valid[c][r])$fatal(1,"active external receipt lost identity");
     if(receipt_reset_quarantined[c][r])orphan_count=orphan_count+1;
     else live_count=live_count+1;
    end
   end
   if(accepted[c]!=live_count+orphan_count)
    $fatal(1,"external accepted receipt conservation c%0d debt%0d live%0d reset_orphans%0d",c,accepted[c],live_count,orphan_count);
  end
 endtask
 task consume_external_receipt(input integer c,input reg[31:0] tag,input reg[3:0] gen,input reg we);
  integer hits,selected;
  begin
   hits=0;selected=-1;
   for(integer r=0;r<16;r=r+1)if(receipt_active[c][r]&&receipt_valid[c][r]&&
    receipt_pt[c][r][31:0]==tag&&receipt_pg[c][r]==gen&&receipt_we[c][r]==we)begin
     if(receipt_reset_quarantined[c][r])
      $fatal(1,"client terminal consumed quarantined reset orphan c%0d r%0d",c,r);
     hits=hits+1;selected=r;
   end
   if(hits!=1)$fatal(1,"terminal consumed without unique NONquarantined accepted wire receipt");
   receipt_active[c][selected]=0;accepted[c]=accepted[c]-1;
  end
 endtask
 task step;
  begin
   #1;
   for(integer c=0;c<6;c=c+1)begin
    if(!rst_n)caller_held[c]=0;
    else if(cv[c]&&!caller_held[c])begin
     caller_held[c]=1;caller_we[c]=cwe[c];caller_addr[c]=ca[c*34+:34];
     caller_tag[c]=ct[c*32+:32];caller_gen[c]=cg[c*4+:4];caller_data[c]=cd[c*256+:256];
    end
    else if(!cv[c]&&admission_stop)caller_held[c]=0;
   end
   if(rst_n&&!fault&&!repair_busy)begin
    if(held_req&&!admission_stop&&(!pv||{pwe,pa,pt,pg,pd}!==held_req_tuple))$fatal(1,"held backend request tuple changed");
    for(integer c=0;c<6;c=c+1)begin
     if(held_reads[c]&&(!rv[c]||{rt[32*c+:32],rg[4*c+:4],rd[256*c+:256]}!==held_read_tuple[c]))$fatal(1,"held client read tuple changed");
     if(held_writes[c]&&(!wv[c]||{wt[32*c+:32],wg[4*c+:4]}!==held_write_tuple[c]))$fatal(1,"held client write tuple changed");
    end
   end
   if(!rst_n)begin held_req=0;held_reads=0;held_writes=0;end
   else if(!repair_busy&&!fault)begin
    held_req=pv&&!pr;held_req_tuple={pwe,pa,pt,pg,pd};
    for(integer c=0;c<6;c=c+1)begin
     held_reads[c]=rv[c]&&!cr[c];held_writes[c]=wv[c]&&!cwr[c];
     held_read_tuple[c]={rt[32*c+:32],rg[4*c+:4],rd[256*c+:256]};
     held_write_tuple[c]={wt[32*c+:32],wg[4*c+:4]};
    end
   end
   observed_rt=rt;observed_rg=rg;observed_wt=wt;observed_wg=wg;observed_pa=pa;observed_pd=pd;observed_pt=pt;observed_pg=pg;observed_pwe=pwe;observed_client_req=cv&cready;took_req=pv&&pr;took_read=prv&&prr;took_write=pwv&&pwr;
   took_client_read=rv&cr;took_client_write=wv&cwr;
   took_rearm=rearm_v&&rearm_rdy;
   @(posedge clk);#1;cycles=cycles+1;
   if(disabled_pv||disabled_fault)$fatal(1,"defaultoff violated");
   // The oracle counts public handshakes, not cached counts or FSM state.
   if(took_req)$display("PORT_EVENT request_accept cycle%0d tag%h gen%h we%0d",cycles,observed_pt,observed_pg,observed_pwe);
   if(took_read)$display("PORT_EVENT backend_read_accept cycle%0d tag%h gen%h",cycles,prt,prg);
   if(took_write)$display("PORT_EVENT backend_write_accept cycle%0d tag%h gen%h",cycles,pwt,pwg);
   if(took_rearm)$display("PORT_EVENT fenced_rearm_accept cycle%0d",cycles);
   if(took_req)begin
     if(integer'(observed_pt[34:32])>=6)$fatal(1,"provider client namespace");
     if(!observed_client_req[integer'(observed_pt[34:32])])$fatal(1,"provider/client acceptance split");
     begin integer c,r;c=integer'(observed_pt[34:32]);r=-1;
      for(integer slot=15;slot>=0;slot=slot-1)if(!receipt_active[c][slot])r=slot;
      if(r<0)$fatal(1,"accepted request has no OLD free fixture receipt");
      for(integer slot=0;slot<16;slot=slot+1)if(receipt_active[c][slot]&&receipt_valid[c][slot]&&
       receipt_pt[c][slot]==observed_pt&&receipt_pg[c][slot]==observed_pg&&receipt_we[c][slot]==observed_pwe)
        $fatal(1,"accepted request reused live or reset-orphan identity");
      // Compare the ENTIRE330-bit accepted tuple against the independent
      // original caller capture, not a decoded/current DUT record.
      if(!caller_held[c] ||
         {observed_pwe,observed_pa,observed_pt,observed_pg,observed_pd} !==
         {caller_we[c],caller_addr[c],3'(c),caller_tag[c],caller_gen[c],caller_data[c]})
        $fatal(1,"accepted backend full tuple differs from held caller original");
      receipt_pt[c][r]=observed_pt;receipt_pg[c][r]=observed_pg;
      receipt_we[c][r]=observed_pwe;receipt_valid[c][r]=1;receipt_active[c][r]=1;receipt_reset_quarantined[c][r]=0;caller_held[c]=0;
     end
     last_req_edge[integer'(observed_pt[34:32])]=cycles;
     accepted[integer'(observed_pt[34:32])]=accepted[integer'(observed_pt[34:32])]+1;
   end
   for(integer c=0;c<6;c=c+1)begin
     if(took_client_read[c])$display("PORT_EVENT client_read_accept cycle%0d client%0d",cycles,c);
     if(took_client_write[c])$display("PORT_EVENT client_write_accept cycle%0d client%0d",cycles,c);
     if(took_client_read[c]||took_client_write[c])begin
      reg[31:0] tag;reg[3:0] gen;
      tag=took_client_write[c]?observed_wt[32*c+:32]:observed_rt[32*c+:32];
      gen=took_client_write[c]?observed_wg[4*c+:4]:observed_rg[4*c+:4];
      consume_external_receipt(c,tag,gen,took_client_write[c]);
     end
     if(accepted[c]<0)$fatal(1,"negative accepted debt");
     // Reconcile public accepted debt with the CURRENT table plus accepted
     // issue/retire journals. Cache updates lag4+4 edges and are never credits.
     begin integer live_receipts,reset_orphans;
     external_receipt_counts(c,live_receipts,reset_orphans);
     if(rst_n&&!fault&&!repair_busy&&dut.all_core_clean)begin
      integer projected,address;reg[43:0] jtarget;
      projected=0;
      for(integer slot=0;slot<16;slot=slot+1)if(dut.P[16*c+slot][1:0]!=0)projected=projected+1;
      if(dut.J[0][86]&&integer'(dut.J[0][81:72])/16==c)begin
       jtarget=44'(dut.decode_data(dut.J[0][71:0]));
       if(jtarget[1:0]==1)projected=projected+1;
      end
      for(integer role=1;role<9;role=role+1)if(dut.J[role][86]&&integer'(dut.J[role][81:72])/16==c)begin
       address=integer'(dut.J[role][81:72]);jtarget=44'(dut.decode_data(dut.J[role][71:0]));
       if(jtarget[1:0]==0&&dut.P[address][1:0]!=0)projected=projected-1;
      end
      // Original equation is unchanged for every context without reset debt.
      if(reset_orphans==0&&projected!=accepted[c])$fatal(1,"CURRENT table+journal debt mismatch c%0d observed%0d source%0d",c,accepted[c],projected);
      if(projected!=live_receipts||accepted[c]!=projected+reset_orphans)
       $fatal(1,"CURRENT local/journal plus identified reset-orphan conservation c%0d external%0d source%0d live%0d orphans%0d",c,accepted[c],projected,live_receipts,reset_orphans);
     end
     end
   end
   @(negedge clk);
  end
 endtask
 task synthetic_provider_discard_all_receipts;
  begin
   // The synthetic provider alone owns this explicit scenario-scope discard.
   // Local reset, rejected stale packets and DUT idle NEVER call this callback.
   for(integer c=0;c<6;c=c+1)begin
    accepted[c]=0;
    for(integer r=0;r<16;r=r+1)begin
     receipt_valid[c][r]=0;receipt_active[c][r]=0;receipt_reset_quarantined[c][r]=0;
    end
   end
  end
 endtask
 task cold;
  begin
   // Scenario boundary only: synthetic provider explicitly discards all copies.
   // This is not a runtime reset/recovery proof for an attached backend.
   rst_n=0;cv=0;cwe=0;cr=0;cwr=0;pr=0;prv=0;pwv=0;
   admission_stop=0;rearm_v=0;provider_fenced=0;reset_fenced=0;reverse_fenced=0;
   synthetic_provider_discard_all_receipts();
   for(integer c=0;c<6;c=c+1)begin last_req_edge[c]=0;caller_held[c]=0;end
   step();step();rst_n=1;
   // This provider actually disposed of ALL its scope receipts above.
   // Only this positive cold boundary may supply authoritative drain fences.
   admission_stop=1;provider_fenced=1;reverse_fenced=1;reset_fenced=1;
   step();
   if(!fault||pv||rv||wv||cready||prr||pwr)$fatal(1,"cold reset quarantine missing before fenced rearm");
   rearm_v=1;step();
   if(!took_rearm)$fatal(1,"cold authoritative allfences rearm not accepted");
   rearm_v=0;provider_fenced=0;reverse_fenced=0;reset_fenced=0;admission_stop=0;
   step();if(fault||repair_busy)$fatal(1,"cold fenced rearm failed to release quarantine");
   scenario=scenario+1;
  end
 endtask
 task issue(input integer c,input reg write_flag,input reg[31:0] t,input reg[3:0] g);
  integer n;
  begin
   cv[c]=1;cwe[c]=write_flag;ct[c*32+:32]=t;cg[c*4+:4]=g;ca[c*34+:34]=34'h300000020|34'(c*32);cd[c*256+:256]=HIGH_DATA|256'(t);pr=1;n=0;
   do begin step();n=n+1;if(n>CLEAN_PROGRESS_EDGES||fault)$fatal(1,"request admission");end while(!took_req);
   cv[c]=0;
  end
 endtask
 task raw_read_return(input integer c,input reg[31:0] t,input reg[3:0] g);
  integer n;
  begin prv=1;prt={3'(c),t};prg=g;prd=HIGH_DATA|(256'(t)^256'h12345678);n=0;
   do begin step();n=n+1;if(n>CLEAN_PROGRESS_EDGES)$fatal(1,"read input held forever");end while(!took_read);
   prv=0;
  end
 endtask
 task raw_write_return(input integer c,input reg[31:0] t,input reg[3:0] g);
  integer n;
  begin pwv=1;pwt={3'(c),t};pwg=g;n=0;
   do begin step();n=n+1;if(n>CLEAN_PROGRESS_EDGES)$fatal(1,"write input held forever");end while(!took_write);
   pwv=0;end
 endtask
 task accepted_echo(input integer c,input reg[31:0] t,input reg[3:0] g,input reg we,
                    output reg[34:0] echo_pt,output reg[3:0] echo_pg);
 integer hits;begin
  hits=0;echo_pt=0;echo_pg=0;
  if(c<0||c>=6)$fatal(1,"positive echo invalid client");
  for(integer r=0;r<16;r=r+1)if(receipt_active[c][r]&&receipt_valid[c][r]&&!receipt_reset_quarantined[c][r]&&receipt_pt[c][r][31:0]==t&&receipt_pg[c][r]==g)begin
   if(receipt_we[c][r]!=we)$fatal(1,"positive echo direction mismatch");
   echo_pt=receipt_pt[c][r];echo_pg=receipt_pg[c][r];hits=hits+1;
  end
  if(hits!=1)$fatal(1,"positive echo lacks unique actual backend acceptance receipt");
 end endtask
 task read_return(input integer c,input reg[31:0] t,input reg[3:0] g);
 integer n;begin
  accepted_echo(c,t,g,0,prt,prg);prv=1;prd=HIGH_DATA|(256'(t)^256'h12345678);n=0;
  do begin step();n=n+1;if(n>CLEAN_PROGRESS_EDGES)$fatal(1,"positive backend read progress");end while(!took_read);
  prv=0;
 end endtask
 task write_return(input integer c,input reg[31:0] t,input reg[3:0] g);
 integer n;begin
  accepted_echo(c,t,g,1,pwt,pwg);pwv=1;n=0;
  do begin step();n=n+1;if(n>CLEAN_PROGRESS_EDGES)$fatal(1,"positive backend write progress");end while(!took_write);
  pwv=0;
 end endtask
 task expect_fault;
  integer n;
  begin n=0;while(!fault)begin step();n=n+1;if(n>CLEAN_PROGRESS_EDGES)$fatal(1,"expected semantic fault absent");end
   if(pv||rv||wv||prr||pwr||cready)$fatal(1,"bad completion not quarantined");
  end
 endtask
 task drain_read(input integer c,input reg[31:0] t,input reg[3:0] g);
  begin
   wait_read(c);if(!rv[c]||rt[c*32+:32]!=t||rg[c*4+:4]!=g||rd[c*256+:256]!=(HIGH_DATA|(256'(t)^256'h12345678)))$fatal(1,"read identity/data");
   repeat(3)begin step();if(!rv[c]||rt[c*32+:32]!=t)$fatal(1,"held read changed");end
   cr[c]=1;step();if(!took_client_read[c])$fatal(1,"read acceptance");cr[c]=0;
  end
 endtask
 task pass(input string name);
  begin case_pass_count=case_pass_count+1;$display("CASE_PASS %s cycle=%0d",name,cycles);end
 endtask

 task wait_request;
 integer n;begin n=0;while(!pv)begin step();n=n+1;if(n>CLEAN_PROGRESS_EDGES||fault)$fatal(1,"request offer progress");end end
 endtask
 task wait_read(input integer client);
 integer n;begin n=0;while(!rv[client])begin step();n=n+1;if(n>CLEAN_PROGRESS_EDGES||fault)$fatal(1,"read offer progress");end end
 endtask
 task wait_write(input integer client);
 integer n;begin n=0;while(!wv[client])begin step();n=n+1;if(n>CLEAN_PROGRESS_EDGES||fault)$fatal(1,"write offer progress");end end
 endtask
 task wait_idle;
 integer n;begin n=0;while(!idle)begin step();n=n+1;if(n>CLEAN_PROGRESS_EDGES||fault)$fatal(1,"count/epoch drain progress");end
 for(integer c=0;c<6;c=c+1)if(accepted[c]!=0)$fatal(1,"idle with accepted public debt");end
 endtask
 function automatic [71:0] get_cw(input integer global_word);
 begin case(global_word)
0:get_cw=dut.cw[0];
1:get_cw=dut.cw[1];
2:get_cw=dut.cw[2];
3:get_cw=dut.cw[3];
4:get_cw=dut.cw[4];
5:get_cw=dut.cw[5];
6:get_cw=dut.cw[6];
7:get_cw=dut.cw[7];
8:get_cw=dut.cw[8];
9:get_cw=dut.cw[9];
10:get_cw=dut.cw[10];
11:get_cw=dut.cw[11];
12:get_cw=dut.cw[12];
13:get_cw=dut.cw[13];
14:get_cw=dut.cw[14];
15:get_cw=dut.cw[15];
16:get_cw=dut.cw[16];
17:get_cw=dut.cw[17];
18:get_cw=dut.cw[18];
19:get_cw=dut.cw[19];
20:get_cw=dut.cw[20];
21:get_cw=dut.cw[21];
22:get_cw=dut.cw[22];
23:get_cw=dut.cw[23];
24:get_cw=dut.cw[24];
25:get_cw=dut.cw[25];
26:get_cw=dut.cw[26];
27:get_cw=dut.cw[27];
28:get_cw=dut.cw[28];
29:get_cw=dut.cw[29];
30:get_cw=dut.cw[30];
31:get_cw=dut.cw[31];
32:get_cw=dut.cw[32];
33:get_cw=dut.cw[33];
34:get_cw=dut.cw[34];
35:get_cw=dut.cw[35];
36:get_cw=dut.cw[36];
37:get_cw=dut.cw[37];
38:get_cw=dut.cw[38];
39:get_cw=dut.cw[39];
40:get_cw=dut.cw[40];
41:get_cw=dut.cw[41];
42:get_cw=dut.cw[42];
43:get_cw=dut.cw[43];
44:get_cw=dut.cw[44];
45:get_cw=dut.cw[45];
46:get_cw=dut.cw[46];
47:get_cw=dut.cw[47];
48:get_cw=dut.cw[48];
49:get_cw=dut.cw[49];
50:get_cw=dut.cw[50];
51:get_cw=dut.cw[51];
52:get_cw=dut.cw[52];
53:get_cw=dut.cw[53];
54:get_cw=dut.cw[54];
55:get_cw=dut.cw[55];
56:get_cw=dut.cw[56];
57:get_cw=dut.cw[57];
58:get_cw=dut.cw[58];
59:get_cw=dut.cw[59];
60:get_cw=dut.cw[60];
61:get_cw=dut.cw[61];
62:get_cw=dut.cw[62];
63:get_cw=dut.cw[63];
64:get_cw=dut.cw[64];
65:get_cw=dut.cw[65];
66:get_cw=dut.cw[66];
67:get_cw=dut.cw[67];
68:get_cw=dut.cw[68];
69:get_cw=dut.cw[69];
70:get_cw=dut.cw[70];
71:get_cw=dut.cw[71];
72:get_cw=dut.cw[72];
73:get_cw=dut.cw[73];
74:get_cw=dut.cw[74];
75:get_cw=dut.cw[75];
76:get_cw=dut.cw[76];
77:get_cw=dut.cw[77];
78:get_cw=dut.cw[78];
79:get_cw=dut.cw[79];
80:get_cw=dut.cw[80];
81:get_cw=dut.cw[81];
82:get_cw=dut.cw[82];
83:get_cw=dut.cw[83];
84:get_cw=dut.cw[84];
85:get_cw=dut.cw[85];
86:get_cw=dut.cw[86];
87:get_cw=dut.cw[87];
88:get_cw=dut.cw[88];
89:get_cw=dut.cw[89];
90:get_cw=dut.cw[90];
91:get_cw=dut.cw[91];
92:get_cw=dut.cw[92];
93:get_cw=dut.cw[93];
94:get_cw=dut.cw[94];
95:get_cw=dut.cw[95];
96:get_cw=dut.cw[96];
97:get_cw=dut.cw[97];
98:get_cw=dut.cw[98];
99:get_cw=dut.cw[99];
100:get_cw=dut.cw[100];
101:get_cw=dut.cw[101];
102:get_cw=dut.cw[102];
103:get_cw=dut.cw[103];
104:get_cw=dut.cw[104];
105:get_cw=dut.cw[105];
106:get_cw=dut.cw[106];
107:get_cw=dut.cw[107];
108:get_cw=dut.cw[108];
109:get_cw=dut.cw[109];
110:get_cw=dut.cw[110];
111:get_cw=dut.cw[111];
112:get_cw=dut.cw[112];
113:get_cw=dut.cw[113];
114:get_cw=dut.cw[114];
115:get_cw=dut.cw[115];
116:get_cw=dut.cw[116];
117:get_cw=dut.cw[117];
118:get_cw=dut.cw[118];
119:get_cw=dut.cw[119];
120:get_cw=dut.cw[120];
121:get_cw=dut.cw[121];
122:get_cw=dut.cw[122];
123:get_cw=dut.cw[123];
124:get_cw=dut.cw[124];
125:get_cw=dut.secondary.cw[0];
126:get_cw=dut.secondary.cw[1];
127:get_cw=dut.secondary.cw[2];
128:get_cw=dut.secondary.cw[3];
129:get_cw=dut.secondary.cw[4];
130:get_cw=dut.secondary.cw[5];
131:get_cw=dut.cw[125];
132:get_cw=dut.secondary.cw[36];
133:get_cw=dut.cw[126];
134:get_cw=dut.cw[127];
135:get_cw=dut.cw[128];
136:get_cw=dut.cw[129];
137:get_cw=dut.cw[130];
138:get_cw=dut.cw[131];
139:get_cw=dut.cw[132];
140:get_cw=dut.cw[133];
141:get_cw=dut.cw[134];
142:get_cw=dut.cw[135];
143:get_cw=dut.cw[136];
144:get_cw=dut.cw[137];
145:get_cw=dut.cw[138];
146:get_cw=dut.cw[139];
147:get_cw=dut.cw[140];
148:get_cw=dut.cw[141];
149:get_cw=dut.cw[142];
150:get_cw=dut.cw[143];
151:get_cw=dut.cw[144];
152:get_cw=dut.cw[145];
153:get_cw=dut.cw[146];
154:get_cw=dut.cw[147];
155:get_cw=dut.cw[148];
156:get_cw=dut.cw[149];
157:get_cw=dut.cw[150];
158:get_cw=dut.cw[151];
159:get_cw=dut.cw[152];
160:get_cw=dut.cw[153];
161:get_cw=dut.cw[154];
162:get_cw=dut.cw[155];
163:get_cw=dut.cw[156];
164:get_cw=dut.cw[157];
165:get_cw=dut.cw[158];
166:get_cw=dut.cw[159];
167:get_cw=dut.cw[160];
168:get_cw=dut.cw[161];
169:get_cw=dut.cw[162];
170:get_cw=dut.cw[163];
171:get_cw=dut.cw[164];
172:get_cw=dut.cw[165];
173:get_cw=dut.cw[166];
174:get_cw=dut.cw[167];
175:get_cw=dut.cw[168];
176:get_cw=dut.cw[169];
177:get_cw=dut.cw[170];
178:get_cw=dut.cw[171];
179:get_cw=dut.cw[172];
180:get_cw=dut.cw[173];
181:get_cw=dut.cw[174];
182:get_cw=dut.cw[175];
183:get_cw=dut.cw[176];
184:get_cw=dut.cw[177];
185:get_cw=dut.cw[178];
186:get_cw=dut.cw[179];
187:get_cw=dut.cw[180];
188:get_cw=dut.cw[181];
189:get_cw=dut.secondary.cw[6];
190:get_cw=dut.secondary.cw[7];
191:get_cw=dut.secondary.cw[8];
192:get_cw=dut.secondary.cw[9];
193:get_cw=dut.secondary.cw[10];
194:get_cw=dut.secondary.cw[11];
195:get_cw=dut.secondary.cw[12];
196:get_cw=dut.secondary.cw[13];
197:get_cw=dut.secondary.cw[14];
198:get_cw=dut.secondary.cw[15];
199:get_cw=dut.secondary.cw[16];
200:get_cw=dut.secondary.cw[17];
201:get_cw=dut.secondary.cw[18];
202:get_cw=dut.secondary.cw[19];
203:get_cw=dut.secondary.cw[20];
204:get_cw=dut.secondary.cw[21];
205:get_cw=dut.secondary.cw[22];
206:get_cw=dut.secondary.cw[23];
207:get_cw=dut.secondary.cw[24];
208:get_cw=dut.secondary.cw[25];
209:get_cw=dut.secondary.cw[26];
210:get_cw=dut.secondary.cw[27];
211:get_cw=dut.secondary.cw[28];
212:get_cw=dut.secondary.cw[29];
213:get_cw=dut.secondary.cw[30];
214:get_cw=dut.secondary.cw[31];
215:get_cw=dut.secondary.cw[32];
216:get_cw=dut.secondary.cw[33];
217:get_cw=dut.secondary.cw[34];
218:get_cw=dut.secondary.cw[35];
 default:$fatal(1,"physical word index");endcase end
 endfunction
 task deposit_cw(input integer global_word,input reg[71:0] value);
 begin case(global_word)
0:dut.cw[0]=value;
1:dut.cw[1]=value;
2:dut.cw[2]=value;
3:dut.cw[3]=value;
4:dut.cw[4]=value;
5:dut.cw[5]=value;
6:dut.cw[6]=value;
7:dut.cw[7]=value;
8:dut.cw[8]=value;
9:dut.cw[9]=value;
10:dut.cw[10]=value;
11:dut.cw[11]=value;
12:dut.cw[12]=value;
13:dut.cw[13]=value;
14:dut.cw[14]=value;
15:dut.cw[15]=value;
16:dut.cw[16]=value;
17:dut.cw[17]=value;
18:dut.cw[18]=value;
19:dut.cw[19]=value;
20:dut.cw[20]=value;
21:dut.cw[21]=value;
22:dut.cw[22]=value;
23:dut.cw[23]=value;
24:dut.cw[24]=value;
25:dut.cw[25]=value;
26:dut.cw[26]=value;
27:dut.cw[27]=value;
28:dut.cw[28]=value;
29:dut.cw[29]=value;
30:dut.cw[30]=value;
31:dut.cw[31]=value;
32:dut.cw[32]=value;
33:dut.cw[33]=value;
34:dut.cw[34]=value;
35:dut.cw[35]=value;
36:dut.cw[36]=value;
37:dut.cw[37]=value;
38:dut.cw[38]=value;
39:dut.cw[39]=value;
40:dut.cw[40]=value;
41:dut.cw[41]=value;
42:dut.cw[42]=value;
43:dut.cw[43]=value;
44:dut.cw[44]=value;
45:dut.cw[45]=value;
46:dut.cw[46]=value;
47:dut.cw[47]=value;
48:dut.cw[48]=value;
49:dut.cw[49]=value;
50:dut.cw[50]=value;
51:dut.cw[51]=value;
52:dut.cw[52]=value;
53:dut.cw[53]=value;
54:dut.cw[54]=value;
55:dut.cw[55]=value;
56:dut.cw[56]=value;
57:dut.cw[57]=value;
58:dut.cw[58]=value;
59:dut.cw[59]=value;
60:dut.cw[60]=value;
61:dut.cw[61]=value;
62:dut.cw[62]=value;
63:dut.cw[63]=value;
64:dut.cw[64]=value;
65:dut.cw[65]=value;
66:dut.cw[66]=value;
67:dut.cw[67]=value;
68:dut.cw[68]=value;
69:dut.cw[69]=value;
70:dut.cw[70]=value;
71:dut.cw[71]=value;
72:dut.cw[72]=value;
73:dut.cw[73]=value;
74:dut.cw[74]=value;
75:dut.cw[75]=value;
76:dut.cw[76]=value;
77:dut.cw[77]=value;
78:dut.cw[78]=value;
79:dut.cw[79]=value;
80:dut.cw[80]=value;
81:dut.cw[81]=value;
82:dut.cw[82]=value;
83:dut.cw[83]=value;
84:dut.cw[84]=value;
85:dut.cw[85]=value;
86:dut.cw[86]=value;
87:dut.cw[87]=value;
88:dut.cw[88]=value;
89:dut.cw[89]=value;
90:dut.cw[90]=value;
91:dut.cw[91]=value;
92:dut.cw[92]=value;
93:dut.cw[93]=value;
94:dut.cw[94]=value;
95:dut.cw[95]=value;
96:dut.cw[96]=value;
97:dut.cw[97]=value;
98:dut.cw[98]=value;
99:dut.cw[99]=value;
100:dut.cw[100]=value;
101:dut.cw[101]=value;
102:dut.cw[102]=value;
103:dut.cw[103]=value;
104:dut.cw[104]=value;
105:dut.cw[105]=value;
106:dut.cw[106]=value;
107:dut.cw[107]=value;
108:dut.cw[108]=value;
109:dut.cw[109]=value;
110:dut.cw[110]=value;
111:dut.cw[111]=value;
112:dut.cw[112]=value;
113:dut.cw[113]=value;
114:dut.cw[114]=value;
115:dut.cw[115]=value;
116:dut.cw[116]=value;
117:dut.cw[117]=value;
118:dut.cw[118]=value;
119:dut.cw[119]=value;
120:dut.cw[120]=value;
121:dut.cw[121]=value;
122:dut.cw[122]=value;
123:dut.cw[123]=value;
124:dut.cw[124]=value;
125:dut.secondary.cw[0]=value;
126:dut.secondary.cw[1]=value;
127:dut.secondary.cw[2]=value;
128:dut.secondary.cw[3]=value;
129:dut.secondary.cw[4]=value;
130:dut.secondary.cw[5]=value;
131:dut.cw[125]=value;
132:dut.secondary.cw[36]=value;
133:dut.cw[126]=value;
134:dut.cw[127]=value;
135:dut.cw[128]=value;
136:dut.cw[129]=value;
137:dut.cw[130]=value;
138:dut.cw[131]=value;
139:dut.cw[132]=value;
140:dut.cw[133]=value;
141:dut.cw[134]=value;
142:dut.cw[135]=value;
143:dut.cw[136]=value;
144:dut.cw[137]=value;
145:dut.cw[138]=value;
146:dut.cw[139]=value;
147:dut.cw[140]=value;
148:dut.cw[141]=value;
149:dut.cw[142]=value;
150:dut.cw[143]=value;
151:dut.cw[144]=value;
152:dut.cw[145]=value;
153:dut.cw[146]=value;
154:dut.cw[147]=value;
155:dut.cw[148]=value;
156:dut.cw[149]=value;
157:dut.cw[150]=value;
158:dut.cw[151]=value;
159:dut.cw[152]=value;
160:dut.cw[153]=value;
161:dut.cw[154]=value;
162:dut.cw[155]=value;
163:dut.cw[156]=value;
164:dut.cw[157]=value;
165:dut.cw[158]=value;
166:dut.cw[159]=value;
167:dut.cw[160]=value;
168:dut.cw[161]=value;
169:dut.cw[162]=value;
170:dut.cw[163]=value;
171:dut.cw[164]=value;
172:dut.cw[165]=value;
173:dut.cw[166]=value;
174:dut.cw[167]=value;
175:dut.cw[168]=value;
176:dut.cw[169]=value;
177:dut.cw[170]=value;
178:dut.cw[171]=value;
179:dut.cw[172]=value;
180:dut.cw[173]=value;
181:dut.cw[174]=value;
182:dut.cw[175]=value;
183:dut.cw[176]=value;
184:dut.cw[177]=value;
185:dut.cw[178]=value;
186:dut.cw[179]=value;
187:dut.cw[180]=value;
188:dut.cw[181]=value;
189:dut.secondary.cw[6]=value;
190:dut.secondary.cw[7]=value;
191:dut.secondary.cw[8]=value;
192:dut.secondary.cw[9]=value;
193:dut.secondary.cw[10]=value;
194:dut.secondary.cw[11]=value;
195:dut.secondary.cw[12]=value;
196:dut.secondary.cw[13]=value;
197:dut.secondary.cw[14]=value;
198:dut.secondary.cw[15]=value;
199:dut.secondary.cw[16]=value;
200:dut.secondary.cw[17]=value;
201:dut.secondary.cw[18]=value;
202:dut.secondary.cw[19]=value;
203:dut.secondary.cw[20]=value;
204:dut.secondary.cw[21]=value;
205:dut.secondary.cw[22]=value;
206:dut.secondary.cw[23]=value;
207:dut.secondary.cw[24]=value;
208:dut.secondary.cw[25]=value;
209:dut.secondary.cw[26]=value;
210:dut.secondary.cw[27]=value;
211:dut.secondary.cw[28]=value;
212:dut.secondary.cw[29]=value;
213:dut.secondary.cw[30]=value;
214:dut.secondary.cw[31]=value;
215:dut.secondary.cw[32]=value;
216:dut.secondary.cw[33]=value;
217:dut.secondary.cw[34]=value;
218:dut.secondary.cw[35]=value;
 default:$fatal(1,"physical word index");endcase end
 endtask
 task fault_matrix;
 integer wordno,bitno,other,n;reg[71:0] original;
 begin
 // All219*72 physical singles. Primary182 and secondary37 storage are disjoint.
 for(wordno=0;wordno<219;wordno=wordno+1)for(bitno=0;bitno<72;bitno=bitno+1)begin
   cold();original=get_cw(wordno);deposit_cw(wordno,original^(72'b1<<bitno));#1;
   if(pv||cready||rv||wv||prr||pwr)$fatal(1,"single error allowed current normal handshake");
   n=0;while(get_cw(wordno)!==original||repair_busy)begin
    step();n=n+1;if(fault||n>CLEAN_PROGRESS_EDGES)$fatal(1,"single repair progress word%0d bit%0d",wordno,bitno);
   end
   if(fault)$fatal(1,"single repair fault");
 end
 $display("FAULT_MATRIX_SINGLE_PASS words219 bits72 cases15768");
 // Default samples72 cyclic adjacent pairs/word, NOT all2556pairs/word.
 // +full_double_pairs prepares all559764 controller pair cases when assigned.
 for(wordno=0;wordno<219;wordno=wordno+1)for(bitno=0;bitno<72;bitno=bitno+1)begin
   for(other=($test$plusargs("full_double_pairs")?bitno+1:(bitno+1)%72);
       other<($test$plusargs("full_double_pairs")?72:((bitno+1)%72)+1);other=other+1)begin
     cold();original=get_cw(wordno);
     deposit_cw(wordno,original^(72'b1<<bitno)^(72'b1<<other));#1;
     if(!fault||pv||cready||rv||wv||prr||pwr)$fatal(1,"double not current failclosed");
     expect_fault();
   end
 end
 $display("FAULT_MATRIX_DOUBLE_PASS scope=%s",$test$plusargs("full_double_pairs")?"ALL219x2556":"SAMPLED219x72cyclic");
 end endtask


 task extra_cases;
 integer n,first_edge,second_edge;reg seen_rd,seen_wr;reg[71:0] target;reg[43:0] payload;
 begin
  cold();issue(0,0,32'h80000001,9);first_edge=last_req_edge[0];
  issue(0,0,32'h80000002,9);second_edge=last_req_edge[0];
  $display("MEASURE SAME_CLIENT_II observed_edges=%0d source_prediction=19 first_edge=%0d second_edge=%0d",second_edge-first_edge,first_edge,second_edge);
  read_return(0,32'h80000002,9);drain_read(0,32'h80000002,9);
  read_return(0,32'h80000001,9);drain_read(0,32'h80000001,9);wait_idle();pass("sameclient_II19_measurement_no_fit");
  cold();for(integer c=0;c<6;c=c+1)issue(c,0,32'hffffffff,15);
  for(integer c=5;c>=0;c=c-1)begin read_return(c,32'hffffffff,15);drain_read(c,32'hffffffff,15);end
  wait_idle();pass("sixclients_samefulltag_separatenamespace");
  cold();issue(1,0,32'hfedcba98,1);issue(2,1,32'h81234567,2);
  accepted_echo(1,32'hfedcba98,1,0,prt,prg);prv=1;prd=HIGH_DATA|(256'hfedcba98^256'h12345678);
  accepted_echo(2,32'h81234567,2,1,pwt,pwg);pwv=1;seen_rd=0;seen_wr=0;n=0;
  while(!seen_rd||!seen_wr)begin
   step();if(took_read)begin seen_rd=1;prv=0;end
   if(took_write)begin seen_wr=1;pwv=0;end
   n=n+1;if(n>CLEAN_PROGRESS_EDGES||fault)$fatal(1,"joint backend captures");
  end
  wait_read(1);wait_write(2);repeat(6)begin step();if(!rv[1]||!wv[2])$fatal(1,"joint held outputs");end
  cr[1]=1;cwr[2]=1;step();if(!took_client_read[1]||!took_client_write[2])$fatal(1,"joint client accepts");
  cr=0;cwr=0;wait_idle();pass("readwrite_joint_capture_and_retire");
  cold();issue(1,1,10,2);issue(2,1,20,3);write_return(1,10,2);
  accepted_echo(2,20,3,1,pwt,pwg);pwv=1;n=0;
  repeat(3)begin step();if(took_write||pwr)$fatal(1,"write query did not hold second backend offer");end
  while(!took_write)begin step();n=n+1;if(fault||n>CLEAN_PROGRESS_EDGES)$fatal(1,"held backend write progress");end
  pwv=0;wait_write(1);wait_write(2);
  cwr=6'b000110;step();if(!took_client_write[1]||!took_client_write[2])$fatal(1,"two held WR terminal accepts");
  cwr=0;wait_idle();pass("held_backend_write_and_client_ready");
  cold();cv[0]=1;ct[0+:32]=32'hf0000001;cg[0+:4]=1;wait_request();
  ct[0+:32]=32'hf0000002;expect_fault();pass("source_protocol_changed_held_request");
  cold();admission_stop=1;provider_fenced=1;reset_fenced=1;reverse_fenced=0;rearm_v=1;
  expect_fault();pass("missing_reverse_allcopies_fence");
  // Runtime local reset does NOT prove external drain. Keep old backend return
  // pending over reset; source must refuse it while local table is empty.
  cold();issue(1,0,44,3);rst_n=0;step();rst_n=1;
  begin integer live_receipts,reset_orphans,orphan_slot;
   external_receipt_counts(1,live_receipts,reset_orphans);
   if(accepted[1]!=1||live_receipts!=0||reset_orphans!=1)
    $fatal(1,"local reset lost external accepted identity/debt");
   orphan_slot=-1;
   for(integer r=0;r<16;r=r+1)if(receipt_active[1][r]&&receipt_valid[1][r]&&receipt_reset_quarantined[1][r]&&
    receipt_pt[1][r]=={3'd1,32'd44}&&receipt_pg[1][r]==3&&!receipt_we[1][r])orphan_slot=r;
   if(orphan_slot<0)$fatal(1,"local reset lost exact orphan receipt identity");
   // Default-off reference mutants in THIS fixture. Each must terminate FAIL;
   // these never alter DUT signals/state or count as positive qualification.
   if($test$plusargs("oracle_reset_omit"))receipt_reset_quarantined[1][orphan_slot]=0;
   if($test$plusargs("oracle_reset_drop")&&!$test$plusargs("oracle_reset_drop_debt"))receipt_active[1][orphan_slot]=0;
   if($test$plusargs("oracle_reset_drop_debt"))accepted[1]=accepted[1]-1;
   if($test$plusargs("oracle_reset_consume"))consume_external_receipt(1,44,3,0);
   // Drive the real old wire receipt while reset quarantine is CURRENT.
   // A stale valid must remain unacknowledged; do not wait for a handshake.
   prt=receipt_pt[1][orphan_slot];prg=receipt_pg[1][orphan_slot];
   prd=HIGH_DATA|(256'd44^256'h12345678);prv=1;
   repeat(4)begin step();
    if(!fault||prr||took_read||pv||rv||wv||cready||pwr||took_req||took_client_read||took_client_write)
     $fatal(1,"unsafe reset stale ingress acknowledged or released ordinary service");
   end
   // Local clean is NOT a provider/reverse/reset drain proof.
   admission_stop=1;rearm_v=1;
   repeat(2)begin step();if(rearm_rdy||took_rearm||!fault)$fatal(1,"reset rearm used localclean as allfences");end
   // Adversarial fence assertions with an old VALID are not authority proof.
   // The RTL must independently demand quiet ingress, even if these are high.
   provider_fenced=1;reverse_fenced=1;reset_fenced=1;
   repeat(2)begin step();
    if(rearm_rdy||took_rearm||prr||took_read||!fault)$fatal(1,"reset rearm accepted held stale input");
   end
   // Attempt the exact same tuple while the old external receipt survives.
   cv[1]=1;ct[32+:32]=44;cg[4+:4]=3;cwe[1]=0;
   ca[34+:34]=34'h300000020|34'd32;cd[256+:256]=HIGH_DATA|256'd44;pr=1;
   repeat(2)begin step();
    if(cready||pv||took_req||took_rearm||prr||took_read||!fault)$fatal(1,"reset quarantine allowed samekey ABA attempt");
   end
   external_receipt_counts(1,live_receipts,reset_orphans);
   if(accepted[1]!=1||live_receipts!=0||reset_orphans!=1||!receipt_active[1][orphan_slot]||
    !receipt_reset_quarantined[1][orphan_slot])$fatal(1,"rejected stale return retired reset-orphan debt");
  end
  pass("actual_local_reset_late_return_refused");
  // Individually test all eight quiet-ingress members, not only read VALID.
  // Each cold boundary explicitly discards the preceding synthetic scope.
  for(integer ingress=0;ingress<8;ingress=ingress+1)begin
   cold();rst_n=0;step();rst_n=1;step();
   admission_stop=1;provider_fenced=1;reverse_fenced=1;reset_fenced=1;rearm_v=1;
   if(ingress==0)prv=1;
   else if(ingress==1)pwv=1;
   else cv[ingress-2]=1;
   repeat(2)begin step();
    if(!fault||rearm_rdy||took_rearm||prr||pwr||pv||rv||wv||cready||took_read||took_write||took_req)
     $fatal(1,"reset rearm accepted nonquiet ingress member%0d",ingress);
   end
  end
  pass("reset_all8_ingress_rearm_refused");
  cold();issue(1,0,32'hfedcba98,15);read_return(1,32'hfedcba98,15);wait_read(1);
  target=get_cw(112);deposit_cw(112,target^72'b1);cr[1]=1;#1;
  if(rv||pv||cready||prr||pwr)$fatal(1,"dirty held delivery allowed release");
  step();if(took_client_read[1]||accepted[1]!=1)$fatal(1,"CE released accepted debt");cr=0;n=0;
  while(get_cw(112)!==target||repair_busy)begin step();n=n+1;if(fault||n>CLEAN_PROGRESS_EDGES)$fatal(1,"held delivery repair");end
  drain_read(1,32'hfedcba98,15);wait_idle();pass("held_read_physical_CE_quarantine_restore");
  // Semantic mutant1: a freshly VALID code changes an issued row's tag.
  cold();issue(1,0,44,3);n=0;
  while(dut.P[16][1:0]!=1)begin step();n=n+1;if(n>CLEAN_PROGRESS_EDGES)$fatal(1,"issued journal commit");end
  payload=dut.P[16];payload[33:2]=45;
  deposit_cw(16,dut.seal(payload,16));#1;
  if(!dut.clean[16])$fatal(1,"row mutant is not valid coded");
  read_return(1,44,3);expect_fault();pass("semantic_validcoded_row_identity");
  // Semantic mutant2: change retained MATCH key while retaining valid encoding.
  cold();cv[1]=1;ct[32+:32]=44;cg[4+:4]=3;n=0;
  while(dut.phase[0]!=2)begin step();n=n+1;if(n>CLEAN_PROGRESS_EDGES)$fatal(1,"query CHECK progress");end
  payload=dut.P[133]^(44'b1<<16);
  deposit_cw(133,dut.seal(payload,133));#1;
  if(!dut.clean[133])$fatal(1,"query mutant is not valid coded");
  expect_fault();pass("semantic_validcoded_query_key");
  // Semantic mutant3: BOTH inner target and outer prepared journal remain
  // valid codewords; target changes to illegal WR_HELD during read reservation.
  cold();cv[1]=1;ct[32+:32]=44;cg[4+:4]=3;n=0;
  while(!dut.J[0][86])begin step();n=n+1;if(n>CLEAN_PROGRESS_EDGES)$fatal(1,"journal PREP progress");end
  payload=44'(3 | (44<<2));payload[37:34]=3;
  target=dut.seal(payload,16);
  deposit_cw(169,dut.seal(target[43:0],169));
  payload=dut.P[170];payload[27:0]=target[71:44];
  deposit_cw(170,dut.seal(payload,170));#1;
  if(!dut.clean[169]||!dut.clean[170])$fatal(1,"journal mutant is not valid coded");
  expect_fault();pass("semantic_validcoded_inner_outer_journal");
 end endtask

 initial begin
  @(negedge clk);
  cold();
  // Full original32/gen4 including occupied KV5; stall a frozen request.
  cv[5]=1;cwe[5]=0;ct[5*32+:32]=32'hfedcba98;cg[5*4+:4]=15;ca[5*34+:34]=34'h300000020;cd[5*256+:256]=HIGH_DATA|256'h9876;
  wait_request();repeat(4)begin step();if(!pv||pt!={3'd5,32'hfedcba98}||pg!=15||pa!=34'h300000020||pd!=(HIGH_DATA|256'h9876))$fatal(1,"heldrequest");end
  pr=1;step();if(!took_req)$fatal(1,"request missed");cv=0;
  read_return(5,32'hfedcba98,15);drain_read(5,32'hfedcba98,15);wait_idle();if(!idle)$fatal(1,"healthy read not idle");pass("heldrequest_read_KV5");
  cold();issue(2,1,32'hffffffff,7);write_return(2,32'hffffffff,7);
  wait_write(2);if(!wv[2])$fatal(1,"WR missing");
  repeat(4)begin step();if(!wv[2]||wt[2*32+:32]!=32'hffffffff||wg[2*4+:4]!=7||accepted[2]!=1)$fatal(1,"heldWR changed");end
  cwr[2]=1;step();cwr=0;if(!took_client_write[2])$fatal(1,"WR retirement");wait_idle();pass("heldwrite_ready");
  cold();for(integer t=0;t<16;t=t+1)issue(0,0,32'(t),1);
  // Keep the complete17th offer stable through OLD credit retirement.
  // It is not an admission-stop cancellation or a new payload under one lease.
  pr=0;cv[0]=1;ct[0+:32]=99;cg[0+:4]=1;cd[0+:256]=HIGH_DATA|256'd99;
  repeat(4)begin step();if(pv||took_req)$fatal(1,"17th credit accepted");end
  read_return(0,15,1);drain_read(0,15,1);wait_request();pr=1;step();
  if(!took_req)$fatal(1,"held17th request missed after credit release");cv=0;
  for(integer t=0;t<15;t=t+1)begin read_return(0,32'(t),1);drain_read(0,32'(t),1);end
  read_return(0,99,1);drain_read(0,99,1);wait_idle();if(!idle)$fatal(1,"full table final drain");pass("full16_oldcredit_no_bypass_outoforder");
  cold();issue(0,0,1,1);issue(0,0,2,1);issue(0,0,3,1);
  read_return(0,1,1);wait_read(0);
  accepted_echo(0,2,1,0,prt,prg);prv=1;prd=HIGH_DATA|(256'd2^256'h12345678);
  repeat(4)begin step();if(prr||took_read||!rv[0]||rt[0+:32]!=1)$fatal(1,"backend read backpressure");end
  drain_read(0,1,1);
  begin integer n;n=0;while(!took_read)begin step();n=n+1;if(n>CLEAN_PROGRESS_EDGES)$fatal(1,"backend progress after readerrelease");end end
  prv=0;drain_read(0,2,1);read_return(0,3,1);drain_read(0,3,1);wait_idle();pass("held_backend_read_and_finite_query");
  cold();cv[0]=1;ct[0+:32]=123;cg[0+:4]=2;pr=0;wait_request();
  admission_stop=1;step();if(pv)$fatal(1,"stop did not cancel unaccepted holder");cv=0;
  provider_fenced=1;reset_fenced=1;reverse_fenced=1;wait_idle();rearm_v=1;#1;if(!rearm_rdy)$fatal(1,"unaccepted reservation not retired");step();rearm_v=0;pass("stop_cancels_only_unaccepted_holder");
  cold();cv[0]=1;ct[0+:32]=42;cg[0+:4]=3;pr=0;step();
  wait_request();pr=1;prv=1;prt={3'd0,32'd42};prg=3;prd=42;step();cv=0;prv=0;
  expect_fault();if(accepted[0]!=1)$fatal(1,"sameedge false return lost debt");pass("sameedge_issue_return_refused");
  cold();issue(4,1,111,4);write_return(4,111,4);raw_write_return(4,111,4);expect_fault();pass("duplicate_write_ack");
  cold();issue(1,0,44,3);cv[1]=1;ct[32+:32]=44;cg[4+:4]=3;expect_fault();pass("duplicate_live_request");
  cold();issue(1,0,44,3);raw_read_return(1,45,3);expect_fault();pass("validcode_wrongtag");
  cold();issue(1,0,44,3);raw_read_return(1,44,2);expect_fault();pass("wronggeneration");
  cold();issue(1,1,44,3);raw_read_return(1,44,3);expect_fault();pass("wrongdirection");
  cold();issue(1,0,44,3);raw_read_return(7,44,3);expect_fault();pass("invalidclient");
  cold();issue(1,0,44,3);read_return(1,44,3);drain_read(1,44,3);wait_idle();raw_read_return(1,44,3);expect_fault();pass("duplicate_retired_return");
  cold();issue(1,1,44,3);admission_stop=1;provider_fenced=1;reset_fenced=1;reverse_fenced=1;rearm_v=1;expect_fault();
  if(accepted[1]!=1)$fatal(1,"rearm erased accepted debt");pass("rearm_live_debt_refused");
  cold();admission_stop=1;rearm_v=1;expect_fault();pass("unfenced_wrap_refused");
  cold();issue(3,0,88,15);read_return(3,88,15);drain_read(3,88,15);
  admission_stop=1;provider_fenced=1;reset_fenced=1;reverse_fenced=1;wait_idle();rearm_v=1;
  #1;if(!rearm_rdy)$fatal(1,"positive empty fenced rearm");step();rearm_v=0;admission_stop=0;
  issue(3,0,88,0);read_return(3,88,0);drain_read(3,88,0);pass("fenced_generation15_to0");
  // No installed generation oracle: tests verify stale mismatched return after
  // producer-selected wrap, not impossible detection of samekey ABA after fence.
  raw_read_return(3,88,15);expect_fault();pass("reset_stale_old_generation");
  cold();issue(0,0,7,1);read_return(0,7,1);wait_read(0);if(!rv[0])$fatal(1,"setup held read");
  raw_write_return(4,99,1);expect_fault();cr[0]=1;step();if(took_client_read[0]||accepted[0]!=1||!fault)$fatal(1,"bad query released good debt");pass("badquery_blocks_simultaneous_release");
  extra_cases();
  if($test$plusargs("fault_matrix"))fault_matrix();
  $display("COMPONENT_PASS cases=%0d cycles=%0d NC6 MAX16 PC_ID7 preparation_only_until_run",case_pass_count,cycles);$finish;
 end
endmodule
