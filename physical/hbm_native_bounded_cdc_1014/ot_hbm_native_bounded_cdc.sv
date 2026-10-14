`timescale 1ps/1fs
// Distinct bounded request/token backend: sixteen actual SECDED codeword entries on wclk.
// Synchronous FF-codebank reads prefetch into eight held SECDED-coded slots.
// Slots remain stable until the consumer's protected retirement reaches source.
// Every record protects payload, 32-bit epoch and AW+1-bit sequence together.
// Reset/flush requires a new matching caller epoch in both domains. This module
// does not establish analog metastability, die phase, physical closure or price.
module ot_hbm_native_bounded_cdc #(parameter integer W=16,AW=4,MUT=0)(
 input wire wclk,wrst_n,we,input wire [W-1:0] wdata,
 input wire [31:0] wepoch,output wire full,output wire [2:0] rd_freed,output wire w_fault,
 input wire rclk,rrst_n,re,input wire [31:0] repoch,
 output wire [W-1:0] rdata,output wire empty,output wire r_fault
);
 localparam integer D=1<<AW,PW=AW+1,RAW=W+32+PW,N=(RAW+31)/32,CW=N*39;
 initial begin
  if(AW!=4||W<1||W>16)$fatal(1,"BOUNDED_CDC unsupported W/AW");
 end
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
 (* keep=1 *) reg [PW-1:0] wb,wb_n,commit_seq,commit_n,fetch_seq,fetch_n,publish_seq,publish_n,freed,freed_n;
 (* keep=1 *) reg [PW-1:0] rb,rb_n,enc_addr,enc_addr_n,read_addr,read_addr_n;
 (* keep=1 *) reg [31:0] w_epoch,w_epoch_n,r_epoch,r_epoch_n;
 (* keep=1 *) reg enc_v,enc_v_n,read_v,read_v_n,rx_v,rx_v_n,out_v,out_v_n,wf,wf_n,rf,rf_n;
 (* async_reg="true" *) reg [PW-1:0] ack1,ack2,ackn1,ackn2,pub1,pub2,pubn1,pubn2;
 (* async_reg="true" *) reg [31:0] re1,re2,ren1,ren2,we1,we2,wen1,wen2;
 reg [CW-1:0] enc_code,slots[0:7],rx_code;
 reg [W-1:0] out_data;
 wire [PW-1:0] ack_gray=gray(rb),pub_gray=gray(publish_seq);
 wire [PW-1:0] released=graybin(ack2);
 wire ack_ok=(ack2==~ackn2),pub_ok=(pub2==~pubn2);
 wire source_epoch_ok=(re2==~ren2)&&(re2==w_epoch)&&(wepoch==w_epoch);
 wire dest_epoch_ok=(we2==~wen2)&&(we2==r_epoch)&&(repoch==r_epoch);
 wire wbad=(wb!=~wb_n)||(commit_seq!=~commit_n)||(fetch_seq!=~fetch_n)||(publish_seq!=~publish_n)||
  (freed!=~freed_n)||(enc_addr!=~enc_addr_n)||(read_addr!=~read_addr_n)||(w_epoch!=~w_epoch_n)||
  (enc_v!=~enc_v_n)||(read_v!=~read_v_n)||(wf!=~wf_n);
 wire rbad=(rb!=~rb_n)||(r_epoch!=~r_epoch_n)||(rx_v!=~rx_v_n)||(out_v!=~out_v_n)||(rf!=~rf_n);
 wire [PW-1:0] full_release=(MUT==4)?fetch_seq:released;
 wire [PW-1:0] occupancy=wb-full_release;
 assign full=!wrst_n||wf||wbad||!ack_ok||!source_epoch_ok||(occupancy>=D);
 assign empty=!rrst_n||rf||rbad||output_bad||!dest_epoch_ok||!out_v;
 assign w_fault=wf||wbad;assign r_fault=rf||rbad||output_bad;
 assign rdata=out_data;
 wire accept=we&&!full;
 wire [PW-1:0] free_delta=released-freed;
 assign rd_freed=wrst_n&&ack_ok&&source_epoch_ok&&!wbad&&!wf ? ((free_delta>7)?3'd7:free_delta[2:0]):3'd0;
 wire source_safe=wrst_n&&source_epoch_ok&&ack_ok&&!wbad&&!wf;
 wire [PW-1:0] slot_used=fetch_seq-released;
 wire issue=source_safe&&(fetch_seq!=commit_seq)&&((MUT==1)||(slot_used<8));
 wire [N*32-1:0] encode_raw={{(N*32-RAW){1'b0}},wb,w_epoch,wdata};
 wire [CW-1:0] coded_in;
 for(genvar g=0;g<N;g=g+1)begin:g_codec
  assign coded_in[g*39+:39]=encode32(encode_raw[g*32+:32]);
 end
 wire [CW-1:0] sram_rd;
 // Actual FF-backed codeword storage, including read landing state. No raw payload array.
 ot_hbm_native_bounded_codebank #(.CW(CW),.AW(AW)) u_codebank(
  .clk(wclk),.r_ce(issue),.r_addr(fetch_seq[AW-1:0]),.r_code(sram_rd),
  .w_ce(source_safe&&enc_v),.w_addr(enc_addr[AW-1:0]),.w_code(enc_code));
 wire [N*32-1:0] decoded;
 wire [N-1:0] decode_ue,decode_ce;
 for(genvar g=0;g<N;g=g+1)begin:g_decode
  wire [33:0] d=decode32(rx_code[g*39+:39]);
  assign decoded[g*32+:32]=d[31:0];assign decode_ue[g]=d[33];assign decode_ce[g]=d[32];
 end
 wire record_ok=!(|decode_ue)&&(decoded[W+:32]==r_epoch)&&(decoded[W+32+:PW]==rb);
 wire output_bad=(MUT==2)?1'b0:out_v&&(!record_ok||(out_data!=decoded[W-1:0]));
 always @(posedge wclk or negedge wrst_n)begin
  if(!wrst_n)begin
   wb<=0;wb_n<='1;commit_seq<=0;commit_n<='1;fetch_seq<=0;fetch_n<='1;publish_seq<=0;publish_n<='1;freed<=0;freed_n<='1;
   enc_addr<=0;enc_addr_n<='1;read_addr<=0;read_addr_n<='1;enc_v<=0;enc_v_n<=1;read_v<=0;read_v_n<=1;wf<=0;wf_n<=1;
   w_epoch<=wepoch;w_epoch_n<=~wepoch;ack1<=0;ack2<=0;ackn1<='1;ackn2<='1;re1<=~wepoch;re2<=~wepoch;ren1<=wepoch;ren2<=wepoch;
  end else begin
   ack1<=ack_gray;ack2<=ack1;ackn1<=~ack_gray;ackn2<=ackn1;
   re1<=r_epoch;re2<=re1;ren1<=r_epoch_n;ren2<=ren1;
   if(wepoch!=w_epoch)begin
    if((wb!=released)||enc_v||read_v)begin wf<=1;wf_n<=0;end
    else begin
    w_epoch<=wepoch;w_epoch_n<=~wepoch;wb<=0;wb_n<='1;commit_seq<=0;commit_n<='1;fetch_seq<=0;fetch_n<='1;publish_seq<=0;publish_n<='1;freed<=0;freed_n<='1;
    enc_addr<=0;enc_addr_n<='1;read_addr<=0;read_addr_n<='1;enc_v<=0;enc_v_n<=1;read_v<=0;read_v_n<=1;wf<=0;wf_n<=1;
    end
   end else if(wbad)begin wf<=1;wf_n<=0;end
   else if(source_safe)begin
    freed<=freed+rd_freed;freed_n<=~(freed+rd_freed);
    enc_v<=accept;enc_v_n<=~accept;
    if(accept)begin wb<=wb+1'b1;wb_n<=~(wb+1'b1);enc_addr<=wb;enc_addr_n<=~wb;enc_code<=coded_in;end
    if(enc_v)begin commit_seq<=enc_addr+1'b1;commit_n<=~(enc_addr+1'b1);end
    read_v<=issue;read_v_n<=~issue;
    if(issue)begin read_addr<=fetch_seq;read_addr_n<=~fetch_seq;fetch_seq<=fetch_seq+1'b1;fetch_n<=~(fetch_seq+1'b1);end
    if(read_v)begin slots[read_addr[2:0]]<=sram_rd[CW-1:0];publish_seq<=read_addr+1'b1;publish_n<=~(read_addr+1'b1);end
   end
  end
 end
 always @(posedge rclk or negedge rrst_n)begin
  if(!rrst_n)begin
   rb<=0;rb_n<='1;rx_v<=0;rx_v_n<=1;out_v<=0;out_v_n<=1;rf<=0;rf_n<=1;r_epoch<=repoch;r_epoch_n<=~repoch;
   pub1<=0;pub2<=0;pubn1<='1;pubn2<='1;we1<=~repoch;we2<=~repoch;wen1<=repoch;wen2<=repoch;
  end else begin
   pub1<=pub_gray;pub2<=pub1;pubn1<=~pub_gray;pubn2<=pubn1;we1<=w_epoch;we2<=we1;wen1<=w_epoch_n;wen2<=wen1;
   if(repoch!=r_epoch)begin
    if(out_v||rx_v||((we2==r_epoch)&&pub_ok&&(gray(rb)!=pub2)))begin rf<=1;rf_n<=0;end
    else begin r_epoch<=repoch;r_epoch_n<=~repoch;rb<=0;rb_n<='1;rx_v<=0;rx_v_n<=1;out_v<=0;out_v_n<=1;rf<=0;rf_n<=1;end
   end
   else if(rbad||output_bad)begin rf<=1;rf_n<=0;out_v<=0;out_v_n<=1;end
   else if(dest_epoch_ok&&!rf)begin
    if(out_v&&re)begin rb<=rb+1'b1;rb_n<=~(rb+1'b1);out_v<=0;out_v_n<=1;end
    if(rx_v)begin
     rx_v<=0;rx_v_n<=1;
     if(record_ok||(MUT==2))begin out_data<=decoded[W-1:0];out_v<=1;out_v_n<=0;end
     else begin rf<=1;rf_n<=0;out_v<=0;out_v_n<=1;end
    end
    if(!out_v&&!rx_v&&pub_ok&&(gray(rb)!=pub2))begin rx_code<=slots[rb[2:0]];rx_v<=1;rx_v_n<=0;end
   end
  end
 end
endmodule

// Source-clock physical codeword state. Every stored bit is covered by the consumer SECDED decoder.
// Data is not reset; protected epoch/sequence prevents old entries being valid after a new reset epoch.
module ot_hbm_native_bounded_codebank #(parameter integer CW=78,AW=4)(
 input wire clk,r_ce,w_ce,input wire[AW-1:0] r_addr,w_addr,
 input wire[CW-1:0] w_code,output reg[CW-1:0] r_code
);
 (* keep=1 *) reg[CW-1:0] codewords[0:(1<<AW)-1];
 always @(posedge clk) begin
  if(w_ce)codewords[w_addr]<=w_code;
  if(r_ce)r_code<=codewords[r_addr];
 end
endmodule
