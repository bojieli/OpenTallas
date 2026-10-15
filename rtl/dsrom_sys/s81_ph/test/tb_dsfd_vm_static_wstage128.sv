`timescale 1ns/1ps
module tb_dsfd_vm_static_wstage128;
 reg ck=0;always #2 ck=~ck;reg rn=0;
 reg [95:0] cv=0;reg [191:0] cs=0;reg [1343:0] cr=0;reg [383:0] cm=0;
 reg [12287:0] cd=0;reg [767:0] ct=0;reg [31:0] dv=0;reg [63:0] ds=0;
 wire [31:0] ov,fault;wire [447:0] row;wire [127:0] mask;wire [4095:0] data;wire [255:0] tag;
 localparam [63:0] DEPTHS=64'habadafa6b9adeaab;
 genvar b;generate for(b=0;b<32;b=b+1)begin:bank
 dsfd_vm_static_wstage128 #(.DEPTH((DEPTHS>>(2*b))&3)) u(.ck(ck),.rst_n(rn),
 .capture_v(cv[3*b+:3]),.capture_slot(cs[6*b+:6]),.capture_row(cr[42*b+:42]),
 .capture_mask(cm[12*b+:12]),.capture_data(cd[384*b+:384]),.capture_tag(ct[24*b+:24]),
 .drain_v(dv[b]),.drain_slot(ds[2*b+:2]),.o_v(ov[b]),.o_row(row[14*b+:14]),
 .o_mask(mask[4*b+:4]),.o_data(data[128*b+:128]),.o_tag(tag[8*b+:8]),.fault(fault[b]));
 end endgenerate
 wire [31:0] mwv,mcv;wire [447:0] mwr;wire [127:0] mwm,mcm;wire [4095:0] mwd;
 wire [255:0] mwt,mct;wire [287:0] mca;wire [1:0] mf;
 genvar k;generate for(k=0;k<32;k=k+1)begin:packet
  localparam integer J=8*(k%4)+k/4;
  assign mwv[J]=ov[k];assign mwr[14*J+:14]=row[14*k+:14];
  assign mwm[4*J+:4]=mask[4*k+:4];assign mwd[128*J+:128]=data[128*k+:128];
  assign mwt[8*J+:8]=tag[8*k+:8];
 end endgenerate
 dsfd_vm_static_slice128_rel2 mem(.ck_rscatter(ck),.ck_wscatter(ck),.ck_bank({32{ck}}),.rst_n(rn),
 .ck_relay_req({6{ck}}),.ck_relay_rsp({6{ck}}),.rq_v(32'd0),.rq_row(448'd0),.rq_tag(256'd0),
 .wq_v(mwv),.wq_row(mwr),.wq_mask(mwm),.wq_data(mwd),.wq_tag(mwt),.rs_v(),.rs_data(),.rs_tag(),
 .commit_v(mcv),.commit_addr(mca),.commit_mask(mcm),.commit_tag(mct),.fault(mf));
 reg [31:0] hv[0:6];reg [447:0] hr[0:6];reg [127:0] hm[0:6];
 reg [255:0] ht[0:6];reg [4095:0] hd[0:6];
 integer committed=0,macro_bad=0;
 generate for(k=0;k<32;k=k+1)begin:macro_trace
  always @(posedge ck)begin
   if(mem.bank[k].u_bank.u_sram.w_ce_in!==hv[4][k])macro_bad=macro_bad+1;
   if(hv[4][k])begin
    committed=committed+1;
    if(mem.bank[k].u_bank.u_sram.w_addr_in!==hr[4][14*k+5+:9] ||
       mem.bank[k].u_bank.u_sram.wd_in!==hd[4][128*k+:128] ||
       mem.bank[k].u_bank.u_sram.w_mask_in!=={{32{hm[4][4*k+3]}},{32{hm[4][4*k+2]}},{32{hm[4][4*k+1]}},{32{hm[4][4*k]}}})macro_bad=macro_bad+1;
   end
  end
 end endgenerate
 function automatic [127:0] value(input integer id);
 value={32'(id*773+19),32'(id*271+5),32'(id*127+3),32'(id*31+7)};
 endfunction
 integer ncap[0:31],erow[0:31],emask[0:31],etag[0:31],eid[0:31];
 integer fd,rc,cy,eb,kind,slot,r,m,t,id,idx,endcy=40000,bad=0,captures=0,drains=0;
 string path;
 task next_event;
 begin rc=$fscanf(fd,"%d %d %d %d %d %d %d %d\n",cy,eb,kind,slot,r,m,t,id);end
 endtask
 initial begin
  if(!$value$plusargs("TRACE=%s",path))$fatal(1,"TRACE required");
  if(!$value$plusargs("END=%d",endcy))endcy=40000;
  fd=$fopen(path,"r");if(!fd)$fatal(1,"missing trace");next_event();
  for(integer a=0;a<7;a=a+1)hv[a]=0;
  #9;rn=1;repeat(4)@(negedge ck);
  for(integer c=0;c<=endcy;c=c+1)begin
   @(negedge ck);cv=0;dv=0;
   for(integer j=0;j<32;j=j+1)ncap[j]=0;
   while(rc==8 &&cy==c)begin
    if(kind==0)begin
     idx=3*eb+ncap[eb];ncap[eb]=ncap[eb]+1;
     if(ncap[eb]>3)$fatal(1,"capture contract exceeded");
     cv[idx]=1;cs[2*idx+:2]=slot;cr[14*idx+:14]=r;cm[4*idx+:4]=m;
     cd[128*idx+:128]=value(id);ct[8*idx+:8]=t;captures=captures+1;
    end else begin
     if(dv[eb])$fatal(1,"two drains on same bankedge");
     dv[eb]=1;ds[2*eb+:2]=slot;erow[eb]=r;emask[eb]=m;etag[eb]=t;eid[eb]=id;
    end
    next_event();
   end
   #0.1;
   if(ov!==dv)bad=bad+1;
   for(integer j=0;j<32;j=j+1)if(dv[j])begin
    drains=drains+1;
    if(row[14*j+:14]!==14'(erow[j]) ||mask[4*j+:4]!==4'(emask[j]) ||
       tag[8*j+:8]!==8'(etag[j]) ||data[128*j+:128]!==value(eid[j]))bad=bad+1;
   end
   @(posedge ck);#0.1;if(fault||mf)bad=bad+1;
   if(mcv!==hv[6])bad=bad+1;
   for(integer a=0;a<32;a=a+1)if(mcv[a])begin
    if(mca[9*a+:9]!==hr[6][14*a+5+:9]||mcm[4*a+:4]!==hm[6][4*a+:4]||mct[8*a+:8]!==ht[6][8*a+:8])bad=bad+1;
   end
   for(integer a=6;a>0;a=a-1)begin hv[a]=hv[a-1];hr[a]=hr[a-1];hm[a]=hm[a-1];ht[a]=ht[a-1];hd[a]=hd[a-1];end
   hv[0]=dv;
   for(integer a=0;a<32;a=a+1)if(dv[a])begin
    hr[0][14*a+:14]=erow[a];hm[0][4*a+:4]=emask[a];ht[0][8*a+:8]=etag[a];hd[0][128*a+:128]=value(eid[a]);
   end
  end
  if(rc==8||committed!=drains||macro_bad!=0)bad=bad+1;
  // A missing compiled drain faults at that edge; it never waits for capture.
  @(negedge ck);cv=0;dv=1;ds=0;
  #0.1;if(ov!=0)bad=bad+1;
  @(posedge ck);#0.1;if(!fault[0])bad=bad+1;
  $display("RESULT captures%0d drains%0d bad%0d missing_fault%0d",captures,drains,bad,fault[0]);
  $display("MACRO committed%0d bad%0d",committed,macro_bad);
  if(bad==0&&captures==drains&&drains>0)$display("PASS");else $display("FAIL");$finish;
 end
endmodule
