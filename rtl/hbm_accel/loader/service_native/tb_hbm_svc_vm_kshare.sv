`timescale 1ns/1ps
`default_nettype none
// Bench of ot_hbm_svc_vm_kshare (H-NETLIST/vmsm 2026-10-15).  Four lanes, one SM group model and four controller models
// (K-port legality of ot_hbm_svc_pc_ctrl_leaf: len 1..4, addr[1:0]+len<=4, PC hash == P; random k_rdy, responses in
// random order across outstanding requests, random kr_v gaps; data = f(addr, beat)).  The group streams random reads
// with 17-bit tickets (it may reuse any tag value, as ot_hbm_svc_prefetch_overlap_owner does); the stream side launches
// VM fill windows.  Checks: every group read gets each beat exactly once with the right data; every window delivers
// slots 0..63 of each PC exactly once with data = f(VM address of the slot), its bank/epoch; no fault.
// Plusargs: +HBM_HALF=<ps> +STR_HALF=<ps> +WINDOWS=<n>.  Exit: "PASS" line, else "FAIL".
module tb_hbm_svc_vm_kshare;
 parameter integer SM=2, MUT=0;
 integer HBM_HALF=600, STR_HALF=500, WINDOWS=6;
 reg hbm_clk=0,stream_clk=0,hbm_rst_n=0,stream_rst_n=0;
 always #(HBM_HALF*1ps) hbm_clk=~hbm_clk;
 always #(STR_HALF*1ps) stream_clk=~stream_clk;
 reg[3:0]g_k_v;wire[3:0]g_k_rdy;reg[119:0]g_k_addr;reg[15:0]g_k_len;reg[67:0]g_k_tag;
 wire[3:0]g_k_wr_done;wire[3:0]g_kr_v;reg[3:0]g_kr_rdy;wire[67:0]g_kr_tag;wire[15:0]g_kr_beat;wire[1023:0]g_kr_data;
 wire[3:0]c_k_v;reg[3:0]c_k_rdy;wire[119:0]c_k_addr;wire[15:0]c_k_len;wire[67:0]c_k_tag;wire[3:0]c_k_we;
 wire[1023:0]c_k_wdata;wire[127:0]c_k_wstrb;reg[3:0]c_kr_v;wire[3:0]c_kr_rdy;reg[67:0]c_kr_tag;reg[15:0]c_kr_beat;reg[1023:0]c_kr_data;
 reg vm_v,vm_bank;reg[15:0]vm_epoch;reg[14:0]vm_row;reg[3:0]vm_col;
 wire[3:0]fill_v,fill_bank;wire[23:0]fill_slot;wire[63:0]fill_epoch;wire[1023:0]fill_data;wire fault;
 ot_hbm_svc_vm_kshare #(.SM(SM),.MUT(MUT)) dut(.hbm_clk(hbm_clk),.hbm_rst_n(hbm_rst_n),.stream_clk(stream_clk),.stream_rst_n(stream_rst_n),
  .g_k_v(g_k_v),.g_k_rdy(g_k_rdy),.g_k_addr(g_k_addr),.g_k_len(g_k_len),.g_k_tag(g_k_tag),.g_k_we(4'b0),.g_k_wdata(1024'b0),.g_k_wstrb(128'b0),
  .g_k_wr_done(g_k_wr_done),.g_kr_v(g_kr_v),.g_kr_rdy(g_kr_rdy),.g_kr_tag(g_kr_tag),.g_kr_beat(g_kr_beat),.g_kr_data(g_kr_data),
  .c_k_v(c_k_v),.c_k_rdy(c_k_rdy),.c_k_addr(c_k_addr),.c_k_len(c_k_len),.c_k_tag(c_k_tag),.c_k_we(c_k_we),.c_k_wdata(c_k_wdata),
  .c_k_wstrb(c_k_wstrb),.c_k_wr_done(4'b0),.c_kr_v(c_kr_v),.c_kr_rdy(c_kr_rdy),.c_kr_tag(c_kr_tag),.c_kr_beat(c_kr_beat),.c_kr_data(c_kr_data),
  .vm_v(vm_v),.vm_bank(vm_bank),.vm_epoch(vm_epoch),.vm_row(vm_row),.vm_col(vm_col),
  .fill_v(fill_v),.fill_bank(fill_bank),.fill_slot(fill_slot),.fill_epoch(fill_epoch),.fill_data(fill_data),.fault(fault));
 function automatic [255:0] f(input [29:0] a, input [3:0] b);
  reg[255:0]r;integer i;begin for(i=0;i<8;i=i+1)r[32*i+:32]=32'h9e3779b9*(a+b+1)+i*32'h85ebca6b^{a[13:0],b,i[3:0],10'h2a5};f=r;end
 endfunction
 integer errors=0;
 // ---------------- controller models
 localparam integer QD=64;
 reg[29:0]qa[0:3][0:QD-1];reg[16:0]qt[0:3][0:QD-1];reg[3:0]ql[0:3][0:QD-1];reg[3:0]qs[0:3][0:QD-1];reg qv[0:3][0:QD-1];
 integer l,i,k,n;
 integer pick[0:3];
 always @(posedge hbm_clk) if(hbm_rst_n) begin : ctlm
  integer l,i,k,n;
  for(l=0;l<4;l=l+1)begin
   // response handshake
   if(c_kr_v[l]&&c_kr_rdy[l])begin
    k=pick[l];qs[l][k]=qs[l][k]|(4'b1<<c_kr_beat[4*l+:4]);
    if(qs[l][k]==((4'b1<<ql[l][k])-1))qv[l][k]=0;
    c_kr_v[l]<=0;
   end
   // request accept
   if(c_k_v[l]&&c_k_rdy[l])begin
    reg[29:0]a;reg[3:0]ln;a=c_k_addr[30*l+:30];ln=c_k_len[4*l+:4];
    if(ln<1||ln>4||{1'b0,a[1:0]}+ln>4||(a[6:2]^a[11:7]^a[16:12])!=5'(4*SM+l)||c_k_we[l])begin
     errors=errors+1;if(errors<10)$display("ILLEGAL K request lane %0d addr %h len %0d",l,a,ln);
    end
    n=-1;for(i=0;i<QD;i=i+1)if(!qv[l][i]&&n<0)n=i;
    qv[l][n]=1;qa[l][n]=a;qt[l][n]=c_k_tag[17*l+:17];ql[l][n]=ln;qs[l][n]=0;
   end
   n=0;for(i=0;i<QD;i=i+1)if(qv[l][i])n=n+1;
   c_k_rdy[l]<=($urandom%4)!=0&&n<16;
   // present a random beat of a random outstanding request
   if(!(c_kr_v[l]&&!c_kr_rdy[l])&&($urandom%3)!=0)begin
    n=0;for(i=0;i<QD;i=i+1)if(qv[l][i])n=n+1;
    if(n>0)begin
     k=$urandom%QD;while(!qv[l][k])k=(k+1)%QD;
     i=$urandom%ql[l][k];while(qs[l][k][i])i=(i+1)%ql[l][k];
     pick[l]=k;c_kr_v[l]<=1;c_kr_tag[17*l+:17]<=qt[l][k];c_kr_beat[4*l+:4]<=i;c_kr_data[256*l+:256]<=f(qa[l][k],i);
    end
   end
  end
 end
 // ---------------- group model: random reads, tickets may repeat values used by VM tags
 integer gi[0:3],gdone[0:3];reg[29:0]ga[0:3][0:1023];reg[3:0]gl[0:3][0:1023];reg[3:0]gs[0:3][0:1023];reg[16:0]gt[0:3][0:1023];
 integer GN=400;
 always @(posedge hbm_clk) if(hbm_rst_n) begin : grpm
  integer l,i,n;
  for(l=0;l<4;l=l+1)begin
  if(g_k_v[l]&&g_k_rdy[l])begin gi[l]=gi[l]+1;g_k_v[l]<=0;end
  if(!(g_k_v[l]&&!g_k_rdy[l])&&gi[l]<GN&&($urandom%3)==0)begin
   reg[3:0]ln;reg[29:0]a;reg[4:0]lo;
   ln=1+$urandom%4;lo=$urandom%(5-ln);
   a={$urandom}%30'h3fff0000;a[1:0]=lo[1:0];a[6:2]=5'(4*SM+l)^a[11:7]^a[16:12];
   ga[l][gi[l]]=a;gl[l][gi[l]]=ln;gs[l][gi[l]]=0;gt[l][gi[l]]=gi[l]%3==0?17'(gi[l]&15):17'(gi[l]*7+1);
   g_k_v[l]<=1;g_k_addr[30*l+:30]<=a;g_k_len[4*l+:4]<=ln;g_k_tag[17*l+:17]<=gt[l][gi[l]];
  end
  g_kr_rdy[l]<=($urandom%4)!=0;
  if(g_kr_v[l]&&g_kr_rdy[l])begin
   n=-1;for(i=0;i<gi[l];i=i+1)if(n<0&&gt[l][i]==g_kr_tag[17*l+:17]&&gs[l][i]!=((4'b1<<gl[l][i])-1)&&!gs[l][i][g_kr_beat[4*l+:4]]&&g_kr_beat[4*l+:4]<gl[l][i]&&g_kr_data[256*l+:256]==f(ga[l][i],g_kr_beat[4*l+:4]))n=i;
   if(n<0)begin errors=errors+1;if(errors<10)$display("GROUP lane %0d unexpected beat tag %h beat %0d",l,g_kr_tag[17*l+:17],g_kr_beat[4*l+:4]);end
   else begin gs[l][n]=gs[l][n]|(4'b1<<g_kr_beat[4*l+:4]);if(gs[l][n]==((4'b1<<gl[l][n])-1))gdone[l]=gdone[l]+1;end
  end
  end
 end
 // ---------------- VM windows (stream side) and fill checking
 reg[63:0]seen[0:3];integer fills[0:3];reg w_bank;reg[15:0]w_epoch;reg[14:0]w_row;reg[3:0]w_col;
 function automatic [29:0] vaddr(input integer pc,input [5:0] slot,input [14:0] row,input [3:0] col);
  reg[3:0]j;reg[4:0]c,h;begin j=slot[5:2];c={col,j[3]};h={row[1:0],j[2:0]};vaddr={row,j[2:0],c,5'(pc)^c^h,2'b00};end
 endfunction
 always @(posedge stream_clk) if(stream_rst_n) begin : film
  integer l;reg[5:0]s;
  for(l=0;l<4;l=l+1) if(fill_v[l])begin
s=fill_slot[6*l+:6];
  if(fill_bank[l]!==w_bank||fill_epoch[16*l+:16]!==w_epoch||seen[l][s]||
     fill_data[256*l+:256]!==f(vaddr(4*SM+l,s,w_row,w_col),s[1:0]))begin
   errors=errors+1;if(errors<10)$display("FILL lane %0d slot %0d bad (bank %b epoch %h dup %b)",l,s,fill_bank[l],fill_epoch[16*l+:16],seen[l][s]);
  end
  seen[l][s]=1;fills[l]=fills[l]+1;
 end
 end
 integer w,t;
 initial begin
  if($value$plusargs("HBM_HALF=%d",HBM_HALF));if($value$plusargs("STR_HALF=%d",STR_HALF));if($value$plusargs("WINDOWS=%d",WINDOWS));if($value$plusargs("GN=%d",GN));
  g_k_v=0;c_k_rdy=0;c_kr_v=0;g_kr_rdy=0;vm_v=0;vm_bank=0;vm_epoch=0;vm_row=0;vm_col=0;c_kr_tag=0;c_kr_beat=0;c_kr_data=0;
  g_k_addr=0;g_k_len=0;g_k_tag=0;
  for(l=0;l<4;l=l+1)begin gi[l]=0;gdone[l]=0;fills[l]=0;seen[l]=0;pick[l]=0;for(i=0;i<QD;i=i+1)qv[l][i]=0;end
  #(20ns);hbm_rst_n=1;stream_rst_n=1;
  for(w=0;w<WINDOWS;w=w+1)begin
   repeat(40+$urandom%200)@(posedge stream_clk);
   @(negedge stream_clk);
   w_bank=w[0];w_epoch=16'h100+w*3;w_row=15'($urandom);w_col=4'($urandom);
   for(l=0;l<4;l=l+1)seen[l]=0;
   vm_v=1;vm_bank=w_bank;vm_epoch=w_epoch;vm_row=w_row;vm_col=w_col;
   @(negedge stream_clk);vm_v=0;
   t=0;while(!(&{&seen[0],&seen[1],&seen[2],&seen[3]})&&t<20000)begin @(posedge stream_clk);t=t+1;end
   if(t>=20000)begin errors=errors+1;$display("window %0d timed out: %h %h %h %h",w,seen[0],seen[1],seen[2],seen[3]);end
  end
  t=0;while((gdone[0]+gdone[1]+gdone[2]+gdone[3])<4*GN&&t<40000)begin @(posedge hbm_clk);t=t+1;end
  repeat(50)@(posedge stream_clk);
  for(l=0;l<4;l=l+1)if(gdone[l]!=GN||fills[l]!=64*WINDOWS)begin errors=errors+1;$display("lane %0d group done %0d/%0d fills %0d/%0d",l,gdone[l],GN,fills[l],64*WINDOWS);end
  if(fault)begin errors=errors+1;$display("fault raised");end
  if(errors==0)$display("PASS tb_hbm_svc_vm_kshare SM=%0d MUT=%0d hbm_half=%0d str_half=%0d windows=%0d group_reads=%0d fills=%0d",SM,MUT,HBM_HALF,STR_HALF,WINDOWS,4*GN,fills[0]+fills[1]+fills[2]+fills[3]);
  else $display("FAIL tb_hbm_svc_vm_kshare MUT=%0d errors=%0d",MUT,errors);
  $finish;
 end
 initial begin #(2ms);$display("FAIL timeout");$finish;end
endmodule
`default_nettype wire
