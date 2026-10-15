`timescale 1ps/1fs
// Distinct backend: the actual single-clock 64x512 SRAM runs ONLY on wclk.
// Source-clock synchronous reads prefetch into eight held SECDED-coded slots.
// Slots remain stable until the consumer's protected retirement reaches source.
// Every record protects payload, 32-bit epoch and AW+1-bit sequence together.
// Reset/flush requires a new matching caller epoch in both domains. This module
// does not establish analog metastability, die phase, physical closure or price.
module ot_hbm_native_sram_cdc #(parameter integer W=280,AW=4,MUT=0)(
 input wire wclk,wrst_n,we,input wire [W-1:0] wdata,
 input wire [31:0] wepoch,output wire full,output wire [2:0] rd_freed,output wire w_fault,
 input wire rclk,rrst_n,re,input wire [31:0] repoch,
 output wire [W-1:0] rdata,output wire empty,output wire r_fault
);
 initial begin
  if(AW<3||AW>6||((W+32+AW+1+31)/32)*39>512)$fatal(1,"SRAM_CDC unsupported W/AW");
 end
 localparam integer D=1<<AW,PW=AW+1,RAW=W+32+PW,N=(RAW+31)/32,CW=N*39;
 function automatic [38:0] encode32(input [31:0] d);
  reg [38:0] c;integer p,k,j;
  begin c=0;j=0;
   for(p=1;p<=38;p=p+1)if((p&(p-1))!=0)begin c[p-1]=d[j];j=j+1;end
   for(k=0;k<6;k=k+1)for(p=1;p<=38;p=p+1)if((p&(1<<k))!=0&&p!=(1<<k))c[(1<<k)-1]=c[(1<<k)-1]^c[p-1];
   c[38]=^c[37:0];encode32=c;
  end
 endfunction
 // {uncorrectable, corrected, data}; 32+6 Hamming positions + overall parity.
 function automatic [33:0] decode32(input [38:0] code);
  reg [38:0] c;reg [5:0] syn;reg overall,ue,ce;reg [31:0] d;integer p,k,j;
  begin c=code;syn=0;overall=^code;ue=0;ce=0;d=0;
   for(k=0;k<6;k=k+1)for(p=1;p<=38;p=p+1)if((p&(1<<k))!=0)syn[k]=syn[k]^code[p-1];
   if(syn!=0)begin if(overall&&syn<=38)begin c[syn-1]=~c[syn-1];ce=1;end else ue=1;end
   else if(overall)begin c[38]=~c[38];ce=1;end
   j=0;for(p=1;p<=38;p=p+1)if((p&(p-1))!=0)begin d[j]=c[p-1];j=j+1;end
   decode32={ue,ce,d};
  end
 endfunction
 function automatic [PW-1:0] gray(input [PW-1:0] b);gray=b^(b>>1);endfunction
 function automatic [PW-1:0] graybin(input [PW-1:0] g);
  integer i;begin for(i=PW-1;i>=0;i=i-1)graybin[i]=(i==PW-1)?g[i]:graybin[i+1]^g[i];end
 endfunction
 // ---------------------------------------------------------------------------------------------------------------
 // NATIVE PIN BOUNDARY (A4 HBM group A 2026-10-14, gate evidence 80e470016: full/empty/rd_freed/w_fault/r_fault were
 // combinational from wrst_n/rrst_n, the caller epochs and the rail compares, the 32-bit epoch compare fed 4,348
 // endpoints from the pins, and SECDED decode -> output-protection compare was 19 levels to a pin):
 //  * every input lands in a pin flop (we_p, wdata_p, wepoch_p, repoch_p); re drives only the pop (out_v/rb/empty_q);
 //  * every output is a register computed from the NEXT state (full_q, rd_freed_q, w_fault_q, empty_q, r_fault_q,
 //    out_data); resets are not combined into outputs (the reset values of the output flops fail closed);
 //  * a 2-entry write skid absorbs the writes in flight behind the registered full (sync / epoch transients and the
 //    capacity edge never drop a write); full_q reserves one slot for the write in the pin flop;
 //  * the consumer decode is its own pipeline rung (rx_code -> dec -> out) with a fetch pointer rfp, so the rate is one
 //    word per two consumer edges (was one per three); dec and out are held dual-rail (x, ~x) and checked;
 //  * dual-rail pairs are written only when their logical value changes (a corrupted rail persists until it is
 //    really updated, as before);
 //  * fault visibility: a corruption between edges is reported at the next edge (one edge, was same-cycle
 //    combinational): the native boundary rule forbids a combinational check on an output pin.
 // ---------------------------------------------------------------------------------------------------------------
 (* keep=1 *) reg [PW-1:0] wb,wb_n,commit_seq,commit_n,fetch_seq,fetch_n,publish_seq,publish_n,freed,freed_n;
 (* keep=1 *) reg [PW-1:0] rb,rb_n,rfp,rfp_n,enc_addr,enc_addr_n,read_addr,read_addr_n,rx_seq,dec_xseq;
 (* keep=1 *) reg [31:0] w_epoch,w_epoch_n,r_epoch,r_epoch_n;
 (* keep=1 *) reg enc_v,enc_v_n,read_v,read_v_n,rx_v,rx_v_n,dec_v,dec_v_n,out_v,out_v_n,wf,wf_n,rf,rf_n;
 (* keep=1 *) reg [1:0] sk_v,sk_v_n;
 (* async_reg="true" *) reg [PW-1:0] ack1,ack2,ackn1,ackn2,pub1,pub2,pubn1,pubn2;
 (* async_reg="true" *) reg [31:0] re1,re2,ren1,ren2,we1,we2,wen1,wen2;
 reg [CW-1:0] enc_code,slots[0:7],rx_code;
 reg [CW-1:0] landed_slots[0:7];
 always @(posedge rclk)begin
  for(integer landing=0;landing<8;landing=landing+1)landed_slots[landing]<=slots[landing];
 end
 // reset ports drive only a relay each (async assert, synchronous release, 2 kept region copies <= ~150 loads):
 // native audit of npin2: wrst_n / rrst_n capture 232-293 ps fanning straight out to 298 flops
 wire [1:0] wr,rr;
 ot_rst_relay #(.REGIONS(2)) u_wrst(.clk(wclk),.rst_n_in(wrst_n),.rst_n(wr));
 ot_rst_relay #(.REGIONS(2)) u_rrst(.clk(rclk),.rst_n_in(rrst_n),.rst_n(rr));
 // pin flops (data: no reset; valid: reset)
 reg we_p;reg [W-1:0] wdata_p;reg [31:0] wepoch_p,repoch_p;
 reg [W-1:0] sk_d0,sk_d1;
 (* keep=1 *) reg [W-1:0] dec_data,dec_data_n,out_data,out_data_n;
 reg [31:0] dec_epoch;reg dec_ue;reg [PW-1:0] dec_seq;
 reg full_q,w_fault_q,empty_q,r_fault_q;reg [2:0] rd_freed_q;
 assign full=full_q;assign rd_freed=rd_freed_q;assign w_fault=w_fault_q;
 assign rdata=out_data;assign empty=empty_q;assign r_fault=r_fault_q;
 always @(posedge wclk)begin wdata_p<=wdata;wepoch_p<=wepoch;end
 always @(posedge rclk)repoch_p<=repoch;
 always @(posedge wclk or negedge wr[1])if(!wr[1])we_p<=1'b0;else we_p<=we&&!full_q;
 // ---------------- source (write) domain ----------------
 wire [PW-1:0] ack_gray=gray(rb),pub_gray=gray(publish_seq);
 wire [PW-1:0] released=graybin(ack2);
 wire ack_ok=(ack2==~ackn2),pub_ok=(pub2==~pubn2);
 wire source_epoch_ok=(re2==~ren2)&&(re2==w_epoch)&&(wepoch_p==w_epoch);
 wire wbad=(wb!=~wb_n)||(commit_seq!=~commit_n)||(fetch_seq!=~fetch_n)||(publish_seq!=~publish_n)||
  (freed!=~freed_n)||(enc_addr!=~enc_addr_n)||(read_addr!=~read_addr_n)||(w_epoch!=~w_epoch_n)||
  (enc_v!=~enc_v_n)||(read_v!=~read_v_n)||(wf!=~wf_n)||(sk_v!=~sk_v_n)||(sk_v==2'b10);
 wire [PW-1:0] full_release=(MUT==4)?fetch_seq:released;
 wire [PW-1:0] occupancy=wb-full_release;
 wire [PW-1:0] free_delta=released-freed;
 wire source_safe=source_epoch_ok&&ack_ok&&!wbad&&!wf;
 wire [PW-1:0] slot_used=fetch_seq-released;
 wire issue=source_safe&&(fetch_seq!=commit_seq)&&((MUT==1)||(slot_used<8));
 wire [W-1:0] cdata=sk_v[0]?sk_d0:wdata_p;                    // oldest write: skid head, else the pin flop
 wire [N*32-1:0] encode_raw={{(N*32-RAW){1'b0}},wb,w_epoch,cdata};
 wire [CW-1:0] coded_in;
 for(genvar g=0;g<N;g=g+1)begin:g_codec
  assign coded_in[g*39+:39]=encode32(encode_raw[g*32+:32]);
 end
 reg [PW-1:0] wb_x,commit_x,fetch_x,publish_x,freed_x,enc_addr_x,read_addr_x;
 reg [31:0] w_epoch_x;reg enc_v_x,read_v_x,wf_x,commit_now,slot_we;reg [1:0] sk_v_x;reg [W-1:0] sk_d0_x,sk_d1_x;
 reg [2:0] fd_x;reg [CW-1:0] enc_code_x;
 always @* begin
  wb_x=wb;commit_x=commit_seq;fetch_x=fetch_seq;publish_x=publish_seq;freed_x=freed;enc_addr_x=enc_addr;
  read_addr_x=read_addr;w_epoch_x=w_epoch;enc_v_x=enc_v;read_v_x=read_v;wf_x=wf;enc_code_x=enc_code;
  fd_x=3'd0;commit_now=1'b0;slot_we=1'b0;
  if(wbad&&MUT!=6)wf_x=1'b1;
  else if(wepoch_p!=w_epoch)begin
   if((wb!=released)||enc_v||read_v||(sk_v!=2'b00)||we_p)wf_x=1'b1;
   else begin
    w_epoch_x=wepoch_p;wb_x=0;commit_x=0;fetch_x=0;publish_x=0;freed_x=0;enc_addr_x=0;read_addr_x=0;
    enc_v_x=1'b0;read_v_x=1'b0;wf_x=1'b0;
   end
  end else if(wbad)wf_x=1'b1;
  else if(source_safe)begin
   fd_x=(free_delta>7)?3'd7:free_delta[2:0];freed_x=freed+fd_x;
   commit_now=(sk_v[0]||we_p)&&(occupancy<D);
   enc_v_x=commit_now;
   if(commit_now)begin wb_x=wb+1'b1;enc_addr_x=wb;enc_code_x=coded_in;end
   if(enc_v)commit_x=enc_addr+1'b1;
   read_v_x=issue;if(issue)begin read_addr_x=fetch_seq;fetch_x=fetch_seq+1'b1;end
   if(read_v)begin slot_we=1'b1;publish_x=read_addr+1'b1;end
  end
  // write skid: oldest first; an accepted write is never dropped (a third pending write is a protocol fault)
  sk_v_x=sk_v;sk_d0_x=sk_d0;sk_d1_x=sk_d1;
  case({sk_v,we_p})
   3'b001:if(!commit_now)begin sk_v_x=2'b01;sk_d0_x=wdata_p;end
   3'b010:if(commit_now)sk_v_x=2'b00;
   3'b011:if(commit_now)sk_d0_x=wdata_p;else begin sk_v_x=2'b11;sk_d1_x=wdata_p;end
   3'b110:if(commit_now)begin sk_v_x=2'b01;sk_d0_x=sk_d1;end
   3'b111:if(commit_now)begin sk_d0_x=sk_d1;sk_d1_x=wdata_p;end else wf_x=1'b1;
   default:;
  endcase
 end
 // registered source outputs, from the next state
 wire [PW-1:0] released_x=graybin(ack1);
 wire [PW-1:0] full_rel_x=(MUT==4)?fetch_x:released_x;
 wire [PW-1:0] occ_x=wb_x-full_rel_x;
 wire ack_ok_x=(ack1==~ackn1);
 wire src_ep_ok_x=(re1==~ren1)&&(re1==w_epoch_x)&&(wepoch_p==w_epoch_x);
 wire w_fault_x=wf_x||wbad;
 wire full_x=w_fault_x||!ack_ok_x||!src_ep_ok_x||(sk_v_x!=2'b00)||(occ_x>=D-1);
 wire [CW-1:0] store_rd;
 always @(posedge wclk or negedge wr[0])begin
  if(!wr[0])begin
   wb<=0;wb_n<='1;commit_seq<=0;commit_n<='1;fetch_seq<=0;fetch_n<='1;publish_seq<=0;publish_n<='1;freed<=0;freed_n<='1;
   enc_addr<=0;enc_addr_n<='1;read_addr<=0;read_addr_n<='1;enc_v<=0;enc_v_n<=1;read_v<=0;read_v_n<=1;wf<=0;wf_n<=1;
   w_epoch<=0;w_epoch_n<='1;ack1<=0;ack2<=0;ackn1<='1;ackn2<='1;re1<=0;re2<=0;ren1<=0;ren2<=0;sk_v<=2'b00;sk_v_n<=2'b11;
   full_q<=1'b1;w_fault_q<=1'b0;rd_freed_q<=3'd0;
  end else begin
   ack1<=ack_gray;ack2<=ack1;ackn1<=~ack_gray;ackn2<=ackn1;
   re1<=r_epoch;re2<=re1;ren1<=r_epoch_n;ren2<=ren1;
   if(wb_x!=wb)begin wb<=wb_x;wb_n<=~wb_x;end if(commit_x!=commit_seq)begin commit_seq<=commit_x;commit_n<=~commit_x;end if(fetch_x!=fetch_seq)begin fetch_seq<=fetch_x;fetch_n<=~fetch_x;end 
   if(publish_x!=publish_seq)begin publish_seq<=publish_x;publish_n<=~publish_x;end if(freed_x!=freed)begin freed<=freed_x;freed_n<=~freed_x;end 
   if(enc_addr_x!=enc_addr)begin enc_addr<=enc_addr_x;enc_addr_n<=~enc_addr_x;end if(read_addr_x!=read_addr)begin read_addr<=read_addr_x;read_addr_n<=~read_addr_x;end 
   if(enc_v_x!=enc_v)begin enc_v<=enc_v_x;enc_v_n<=~enc_v_x;end if(read_v_x!=read_v)begin read_v<=read_v_x;read_v_n<=~read_v_x;end if(wf_x!=wf)begin wf<=wf_x;wf_n<=~wf_x;end 
   if(w_epoch_x!=w_epoch)begin w_epoch<=w_epoch_x;w_epoch_n<=~w_epoch_x;end if(sk_v_x!=sk_v)begin sk_v<=sk_v_x;sk_v_n<=~sk_v_x;end 
   full_q<=full_x;w_fault_q<=w_fault_x;rd_freed_q<=fd_x;
  end
 end
 always @(posedge wclk)begin
  sk_d0<=sk_d0_x;sk_d1<=sk_d1_x;enc_code<=enc_code_x;
  if(slot_we)slots[read_addr[2:0]]<=store_rd;
 end
 // ---------------- consumer (read) domain ----------------
 wire [N*32-1:0] decoded;
 wire [N-1:0] decode_ue,decode_ce;
 for(genvar g=0;g<N;g=g+1)begin:g_decode
  wire [33:0] d=decode32(rx_code[g*39+:39]);
  assign decoded[g*32+:32]=d[31:0];assign decode_ue[g]=d[33];assign decode_ce[g]=d[32];
 end
 wire dest_epoch_ok=(we2==~wen2)&&(we2==r_epoch)&&(repoch_p==r_epoch);
 wire rbad=(rb!=~rb_n)||(rfp!=~rfp_n)||(r_epoch!=~r_epoch_n)||(rx_v!=~rx_v_n)||(dec_v!=~dec_v_n)||(out_v!=~out_v_n)||(rf!=~rf_n);
 wire dec_bad=dec_v&&(dec_data!=~dec_data_n);
 wire output_bad=(MUT==2)?1'b0:out_v&&(out_data!=~out_data_n);
 wire dec_rec_ok=!dec_ue&&(dec_epoch==r_epoch)&&(dec_seq==dec_xseq);
 wire rx_fetch=dest_epoch_ok&&!rf&&!rbad&&!output_bad&&!dec_bad&&(repoch_p==r_epoch)&&
  (!rx_v||!dec_v||!out_v)&&pub_ok&&(gray(rfp)!=pub2);
 // the re pin reaches only an AND with a register-only enable and the rb / out_v / empty_q flops
 wire r_ok_now=!(rbad||output_bad||dec_bad)&&(repoch_p==r_epoch)&&dest_epoch_ok&&!rf;
 wire pop=re&&out_v&&r_ok_now;
 wire [PW-1:0] rb_inc=rb+1'b1;
 wire r_rebind=!(rbad||output_bad||dec_bad)&&(repoch_p!=r_epoch)&&
  !(out_v||rx_v||dec_v||((we2==r_epoch)&&pub_ok&&(gray(rb)!=pub2)));
 reg [PW-1:0] rb_x,rfp_x,rx_seq_x;reg [31:0] r_epoch_x;reg rx_v_x,dec_v_x,out_v_x,rf_x,rx_ld,dec_ld,out_ld;
 always @* begin
  rb_x=rb;rfp_x=rfp;rx_seq_x=rx_seq;r_epoch_x=r_epoch;rx_v_x=rx_v;dec_v_x=dec_v;out_v_x=out_v;rf_x=rf;
  rx_ld=1'b0;dec_ld=1'b0;out_ld=1'b0;
  if(rbad||output_bad||dec_bad)begin rf_x=1'b1;out_v_x=1'b0;end
  else if(repoch_p!=r_epoch)begin
   if(out_v||rx_v||dec_v||((we2==r_epoch)&&pub_ok&&(gray(rb)!=pub2)))rf_x=1'b1;
   else begin r_epoch_x=repoch_p;rb_x=0;rfp_x=0;rx_v_x=1'b0;dec_v_x=1'b0;out_v_x=1'b0;rf_x=1'b0;end
  end
  else if(dest_epoch_ok&&!rf)begin
   if(pop)begin rb_x=rb_inc;out_v_x=1'b0;end                    // the only use of the re pin
   if(dec_v&&!out_v)begin                                     // dec -> out (out empty at this edge)
    if(dec_rec_ok||(MUT==2))begin out_ld=1'b1;out_v_x=1'b1;dec_v_x=1'b0;end
    else begin rf_x=1'b1;out_v_x=1'b0;end
   end
   if(rx_v&&(!dec_v||!out_v))begin dec_ld=1'b1;dec_v_x=1'b1;rx_v_x=1'b0;end   // rx -> dec (SECDED decode rung)
   if(rx_fetch&&(!rx_v||!dec_v||!out_v))begin rx_ld=1'b1;rx_v_x=1'b1;rx_seq_x=rfp;rfp_x=rfp+1'b1;end
  end
 end
 wire dest_ok_x=(we1==~wen1)&&(we1==r_epoch_x)&&(repoch_p==r_epoch_x);
 always @(posedge rclk or negedge rr[0])begin
  if(!rr[0])begin
   rb<=0;rb_n<='1;rfp<=0;rfp_n<='1;rx_v<=0;rx_v_n<=1;dec_v<=0;dec_v_n<=1;out_v<=0;out_v_n<=1;rf<=0;rf_n<=1;
   r_epoch<=0;r_epoch_n<='1;pub1<=0;pub2<=0;pubn1<='1;pubn2<='1;we1<=0;we2<=0;wen1<=0;wen2<=0;
   empty_q<=1'b1;r_fault_q<=1'b0;
  end else begin
   pub1<=pub_gray;pub2<=pub1;pubn1<=~pub_gray;pubn2<=pubn1;we1<=w_epoch;we2<=we1;wen1<=w_epoch_n;wen2<=wen1;
   if(r_rebind)begin rb<=0;rb_n<='1;end else if(pop)begin rb<=rb_inc;rb_n<=~rb_inc;end if(rfp_x!=rfp)begin rfp<=rfp_x;rfp_n<=~rfp_x;end if(r_epoch_x!=r_epoch)begin r_epoch<=r_epoch_x;r_epoch_n<=~r_epoch_x;end 
   if(rx_v_x!=rx_v)begin rx_v<=rx_v_x;rx_v_n<=~rx_v_x;end if(dec_v_x!=dec_v)begin dec_v<=dec_v_x;dec_v_n<=~dec_v_x;end if(out_v_x!=out_v)begin out_v<=out_v_x;out_v_n<=~out_v_x;end if(rf_x!=rf)begin rf<=rf_x;rf_n<=~rf_x;end 
   empty_q<=rf_x||!out_v_x||!dest_ok_x;r_fault_q<=rf_x;
  end
 end
 always @(posedge rclk)begin
  if(rx_ld)begin rx_code<=landed_slots[rfp[2:0]];end
  rx_seq<=rx_seq_x;
  if(dec_ld)begin dec_data<=decoded[W-1:0];dec_data_n<=~decoded[W-1:0];dec_epoch<=decoded[W+:32];
   dec_seq<=decoded[W+32+:PW];dec_ue<=|decode_ue;dec_xseq<=rx_seq;end
  if(out_ld)begin out_data<=dec_data;out_data_n<=dec_data_n;end
 end
 wire [511:0] sram_rd;
 ot_sram_1r1w_64x512_m1_r2c2 u_sram(
  .clk(wclk),.r_ce_in(issue),.r_addr_in({{(6-AW){1'b0}},fetch_seq[AW-1:0]}),.rd_out(sram_rd),
  .w_ce_in(source_safe&&enc_v),.w_addr_in({{(6-AW){1'b0}},enc_addr[AW-1:0]}),
  .wd_in({{(512-CW){1'b0}},enc_code}),.w_mask_in({512{1'b1}}),
  .rr_en(2'b0),.rr_addr(12'b0),.cr_en(2'b0),.cr_sel(18'b0));
 assign store_rd=sram_rd[CW-1:0];
endmodule
