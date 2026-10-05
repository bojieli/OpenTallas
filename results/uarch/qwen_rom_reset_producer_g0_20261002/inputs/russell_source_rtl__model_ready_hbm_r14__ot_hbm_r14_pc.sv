`timescale 1ps/1fs
// One real32bank PC. No absolute simulation timestamps in synthesizable state.
// Full64bit cycle deadlines retained; 1GHz domain adds conservative ceil guards.
// Queue macro is actual1R1W. First16 frozen entries scan serially; selected
// word and head are shifted as WHOLE472bit records, including both epochs.
module ot_hbm_r14_pc #(parameter integer PC=0)(
 input wire clk,rst_n,input wire [63:0] cyc,
 input wire qv,output wire qr,input ot_hbm_r14_pkg::queued_t qi,
 output wire cmd_v,input wire cmd_r,output ot_hbm_r14_pkg::command_t cmd,
 output wire reserve_v,input wire reserve_r,input wire [1:0] reserve_slot,
 output wire [471:0] reserve_word,output wire [1:0] write_slot,
 input wire pv,input wire [15:0] ptag,input wire [4:0] pbeat,input wire [255:0] pdata,
 output wire pr,output wire rv,input wire rr,output ot_hbm_r14_pkg::returned_t ro,
 output reg fault,output wire [6:0] qcount,output wire [5:0] rcount,
 output reg [7:0] journal_kind,output reg [471:0] journal_word);
 import ot_hbm_r14_pkg::*;
 localparam integer IDLE=0,PREFETCH=1,SCAN=2,CHOOSE=3,SWAP0=4,SWAP1=5,
   PAD=6,RESERVE=7,SCHEDULE=8,POP=9,RWAIT=10,RPUT=11;
 reg [3:0] state;reg [5:0] head,tail;reg [6:0] n;
 reg [4:0] scan_issue,scan_capture,window,best_index,pad;
 reg read_pending;reg [63:0] best_est;
 queued_t held,best;
 reg [4:0] selected_index,shift_index;reg [1:0] wslot;
 reg [33:0] scan_address[0:15];reg scan_write[0:15];reg [63:0] scan_arrival[0:15];reg [4:0] skips;
 reg refresh_only,refresh_resume;reg candidate_legal;wire queued_t scanned=queued_t'(qrd[471:0]);
 reg [31:0] opened;reg [18:0] rows[0:31];
 reg [63:0] act_t[0:31],pre_ok[0:31],act_ok[0:31];
 reg [63:0] last_act,last_col,last_rd,last_wr;
 reg [63:0] act_bg[0:3],col_bg[0:3],faw[0:3],next_ref,ref_block;
 reg rd_valid,wr_valid;reg [1:0] wr_bg;
 reg qce,qwe;reg [5:0] qa,qwa;reg [511:0] qwd;wire [511:0] qrd;
 reg rce,rwe;reg [5:0] ra,rwa;reg [511:0] rwd;wire [511:0] rrd;
 reg [4:0] rh,rt;reg [5:0] rn;reg return_read,return_held;
 returned_t out_reg,rd_pending;reg have_pending;
 reg response_staged;returned_t response_reg;
 wire [4:0] bk=bank_of(held.sector);wire [1:0] bg=bk[1:0];
 wire [18:0] row=held.sector>>15;
 reg [63:0] earliest;reg [2:0] op;
 integer b,g;
 function automatic logic [63:0] estimate(input queued_t word);
   logic [4:0] bi;logic [1:0] group;logic [63:0] a;
   begin bi=bank_of(word.sector);group=bi[1:0];a=later(cyc,word.arrived+10);
     if(opened[bi]&&rows[bi]==(word.sector>>15))a=act_t[bi];
     else begin if(opened[bi])a=later(a,pre_ok[bi])+17;
       a=later(a,act_ok[bi]);a=later(a,last_act+3);
       a=later(a,act_bg[group]+4);a=later(a,faw[0]+15);end
     estimate=later(later(later(cyc,word.arrived+10),a+(word.we?10:20)),later(last_col+2,col_bg[group]+3));
   end
 endfunction
 assign qr=(state==IDLE)&&n<64;
 assign qcount=n;assign rcount=rn;
 assign reserve_v=(state==RESERVE)&&held.we;
 assign reserve_word=held;assign write_slot=wslot;
 assign pr=have_pending&&!response_staged;
 assign rv=return_held;assign ro=out_reg;
 always @* begin
   op=held.we?WR:RD;earliest=later(later(cyc,held.arrived+10),ref_block);
   if(cyc>=next_ref)begin
     if(|opened)begin op=PREALL;for(integer k=0;k<32;k=k+1)if(opened[k])earliest=later(earliest,pre_ok[k]);end
     else begin op=REF;earliest=later(earliest,last_col+2);end
   end else if(opened[bk]&&rows[bk]!=row)begin op=PRE;earliest=later(earliest,pre_ok[bk]);end
   else if(!opened[bk])begin op=ACT;earliest=later(earliest,act_ok[bk]);
     earliest=later(earliest,last_act+3);earliest=later(earliest,act_bg[bg]+4);earliest=later(earliest,faw[0]+15);end
   else begin earliest=later(earliest,act_t[bk]+(held.we?10:20));
     earliest=later(earliest,last_col+2);earliest=later(earliest,col_bg[bg]+3);
     if(!held.we&&wr_valid)earliest=later(earliest,last_wr+7+2+((wr_bg==bg)?7:5));
     if(held.we&&rd_valid)earliest=later(earliest,last_rd+10);
   end
 end
 assign cmd_v=(state==SCHEDULE)&&cyc>=earliest;
 assign cmd='{op:op,pc:5'(PC),bank:bk,row:row,sector:held.sector,
              tag:held.tag[11:0],beat:held.beat,data:held.data};
 // Actual compiled source SRAMs; synthesis substitutes pinned blackbox views.
 ot_sram_1r1w_64x512_m1_r2c2 request_ram(.clk(clk),.r_ce_in(qce),.r_addr_in(qa),.rd_out(qrd),
   .w_ce_in(qwe),.w_addr_in(qwa),.wd_in(qwd),.w_mask_in({512{1'b1}}),
   .rr_en(2'b0),.rr_addr(12'b0),.cr_en(2'b0),.cr_sel(18'b0));
 ot_sram_1r1w_64x512_m1_r2c2 return_ram(.clk(clk),.r_ce_in(rce),.r_addr_in(ra),.rd_out(rrd),
   .w_ce_in(rwe),.w_addr_in(rwa),.wd_in(rwd),.w_mask_in({512{1'b1}}),
   .rr_en(2'b0),.rr_addr(12'b0),.cr_en(2'b0),.cr_sel(18'b0));
 // Macro strobes are combinational, one write and one read at most per edge.
 always @* begin
   qce=0;qa=0;qwe=0;qwa=0;qwd=0;rce=0;ra=0;rwe=0;rwa=0;rwd=0;
   if(qv&&qr)begin qwe=1;qwa=tail;qwd[471:0]=qi;end
   if(state==PREFETCH)begin qce=1;qa=head;end
   if(state==SCAN&&scan_issue<window)begin qce=1;qa=head+6'(scan_issue);end
   if(state==SWAP0)begin qce=1;qa=head+6'(shift_index-1'b1);end
   if(state==SWAP1)begin qwe=1;qwa=head+6'(shift_index);qwd=qrd;
     if(shift_index>1)begin qce=1;qa=head+6'(shift_index-2);end end
   if(state==RWAIT)begin qwe=1;qwa=head;qwd[471:0]=best;end
   if(response_staged)begin rwe=1;rwa={1'b0,rt};rwd[470:0]=response_reg;end
   if(rn!=0&&!return_held&&!return_read)begin rce=1;ra={1'b0,rh};end
 end
 always @(posedge clk or negedge rst_n)begin
   if(!rst_n)begin
     state<=IDLE;head<=0;tail<=0;n<=0;scan_issue<=0;scan_capture<=0;window<=0;read_pending<=0;shift_index<=0;skips<=0;refresh_only<=0;refresh_resume<=0;
     best_est<=0;best_index<=0;selected_index<=0;pad<=0;held<='0;best<='0;wslot<=0;
     opened<=0;last_act<=0;last_col<=0;last_rd<=0;last_wr<=0;rd_valid<=0;wr_valid<=0;wr_bg<=0;
     next_ref<=3900+(3900*PC)/32;ref_block<=0;
     rh<=0;rt<=0;rn<=0;return_read<=0;return_held<=0;out_reg<='0;
     have_pending<=0;rd_pending<='0;response_staged<=0;response_reg<='0;fault<=0;journal_kind<=0;journal_word<=0;
     for(b=0;b<32;b=b+1)begin rows[b]<=0;act_t[b]<=0;pre_ok[b]<=0;act_ok[b]<=0;end
     for(g=0;g<4;g=g+1)begin act_bg[g]<=0;col_bg[g]<=0;faw[g]<=0;end
     for(g=0;g<16;g=g+1)begin scan_address[g]<=0;scan_write[g]<=0;scan_arrival[g]<=0;end
   end else begin
     journal_kind<=0;
     if(qv&&qr)begin tail<=tail+1'b1;n<=n+1'b1;journal_kind<=1;journal_word<=qi;end
     if(pv&&pr)begin
       if(ptag!=rd_pending.tag||pbeat!=rd_pending.beat||cyc<rd_pending.due)fault<=1;
       else begin response_reg<=rd_pending;response_reg.data<=pdata;response_staged<=1;have_pending<=0;end
     end
     if(response_staged)begin response_staged<=0;rt<=rt+1'b1;end
     case({response_staged,rv&&rr})
       2'b10:rn<=rn+1'b1;2'b01:rn<=rn-1'b1;default:;
     endcase
     if(rce)return_read<=1;
     else if(return_read)begin out_reg<=returned_t'(rrd[470:0]);return_held<=1;return_read<=0;end
     if(rv&&rr)begin return_held<=0;rh<=rh+1'b1;end
     case(state)
       IDLE:if(!(qv&&qr)&&n!=0)begin state<=PREFETCH;end
         else if(n==0&&!(qv&&qr)&&cyc>=next_ref)begin refresh_only<=1;refresh_resume<=0;state<=SCHEDULE;end
       PREFETCH:begin state<=SCAN;scan_issue<=1;scan_capture<=0;window<=5'd16;
         read_pending<=1;best_est<=64'hffffffffffffffff;end
       SCAN:begin
         // Head prefetch completes before the first sequential candidate read.

         if(scan_issue<window)scan_issue<=scan_issue+1'b1;
         read_pending<=(scan_issue<window);
         if(read_pending)begin
           scan_address[scan_capture]<=scanned.sector;
           scan_write[scan_capture]<=scanned.we;
           scan_arrival[scan_capture]<=scanned.arrived;
           candidate_legal=(scan_capture<n)&&((skips<16)||scan_capture==0);
           for(integer h=0;h<16;h=h+1)if(h<scan_capture && h<n && scan_address[h]==scanned.sector && (scan_write[h]||scanned.we))candidate_legal=0;
           if(candidate_legal && estimate(queued_t'(qrd[471:0]))<best_est)begin
             best_est<=estimate(queued_t'(qrd[471:0]));best<=queued_t'(qrd[471:0]);best_index<=scan_capture;
           end
           scan_capture<=scan_capture+1'b1;
           if(scan_capture+1==window)state<=CHOOSE;
         end
       end
       CHOOSE:begin held<=best;selected_index<=best_index;
         if(best_index!=0)begin shift_index<=best_index;skips<=skips+1'b1;state<=SWAP0;end
         else begin skips<=0;pad<=0;state<=PAD;end
       end
       SWAP0:state<=SWAP1;
       SWAP1:if(shift_index>1)shift_index<=shift_index-1'b1;else state<=RWAIT;
       RWAIT:begin pad<=0;state<=PAD;journal_kind<=2;journal_word<=best;end
       PAD:if(pad!=0)pad<=pad-1'b1;else state<=RESERVE;
       RESERVE:begin
         if(cyc>=next_ref)begin refresh_only<=1;refresh_resume<=1;state<=SCHEDULE;end
         else if(held.we&&reserve_r)begin wslot<=reserve_slot;state<=SCHEDULE;end
         else if(!held.we&&rn<32&&!have_pending&&!response_staged)begin state<=SCHEDULE;end
       end
       SCHEDULE:if(cmd_v&&cmd_r)begin
         case(op)
           PRE:begin opened[bk]<=0;act_ok[bk]<=later(act_ok[bk],cyc+17);end
           PREALL:begin opened<=0;for(b=0;b<32;b=b+1)act_ok[b]<=later(act_ok[b],cyc+17);ref_block<=cyc+17;end
           REF:begin if(refresh_only)begin state<=refresh_resume?RESERVE:IDLE;refresh_only<=0;end opened<=0;ref_block<=cyc+350;next_ref<=next_ref+3900;
             for(b=0;b<32;b=b+1)act_ok[b]<=later(act_ok[b],cyc+350);end
           ACT:begin opened[bk]<=1;rows[bk]<=row;act_t[bk]<=cyc;pre_ok[bk]<=cyc+29;
             act_ok[bk]<=cyc+29+17;last_act<=cyc;act_bg[bg]<=cyc;
             faw[0]<=faw[1];faw[1]<=faw[2];faw[2]<=faw[3];faw[3]<=cyc;end
           RD,WR:begin last_col<=cyc;col_bg[bg]<=cyc;
             if(op==WR)begin last_wr<=cyc;wr_bg<=bg;wr_valid<=1;pre_ok[bk]<=later(pre_ok[bk],cyc+7+2+21);end
             else begin last_rd<=cyc;rd_valid<=1;pre_ok[bk]<=later(pre_ok[bk],cyc+6);
               have_pending<=1;rd_pending<='{due:cyc+13+2+10,tag:held.tag,beat:held.beat,data:256'b0,sector:held.sector,transport:held.transport,producer:held.producer};end
             state<=POP;
           end
           default:fault<=1;
         endcase
       end
       POP:begin head<=head+1'b1;n<=n-1'b1;state<=IDLE;journal_kind<=3;journal_word<=held;end
       default:state<=IDLE;
     endcase
   end
 end
endmodule
