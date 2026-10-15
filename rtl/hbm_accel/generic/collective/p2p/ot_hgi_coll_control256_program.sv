`timescale 1ns/1ps
`default_nettype none
// Opt-in ENGRAM control256 native catalogue, distinct HOST targets120+QID.
// Two256b operations per512b word, each op[255:238]=0. Full raw256 host
// frames; address=controlordinal=globalword*2+half. Completepairs required.
// Descriptor cycles: evenbase, exclusivelimit, loops1. Native64*NBANKS scan,
// reserve64*NBANKS+2edges beforelaunch;2edge gap between configuredwords.
// Firstcontrol rawlaunchCAPTURE+6, firstconsumer+7. Oneoperation/edge,
// outputzero outsidevalid;done onlastop. Readnextword every2fixededges.
// All clocks same logical edge, independent physical phi-R at each entry.
module ot_hgi_coll_control256_program #(
 parameter integer NBANKS=19,
 parameter [1:0] QID=2'd0,
 parameter [7:0] TARGET=8'd120+8'(QID),
 parameter integer MUT_DATA=0,MUT_HALF=0,
 parameter integer WORDS=NBANKS*64,BW=(NBANKS>1?$clog2(NBANKS):1),WW=$clog2(WORDS)
)(
 input wire clk_control,input wire [NBANKS-1:0] clk_mem,clk_capture,input wire rst_n,
 input wire cfg_v,input wire [7:0] cfg_target,input wire [11:0] cfg_addr,
 input wire [255:0] cfg_data,
 input wire desc_v,input wire [11:0] desc_base,input wire [12:0] desc_limit,
 input wire [15:0] desc_loops,input wire launch_v,program_active,
 output reg configured,init_busy,busy,done,fault,
 output reg control_v,output reg [255:0] control,
 output reg [12:0] control_cycle
);
 initial if(NBANKS<1 || NBANKS>32)$fatal(1,"control256 NBANKS1..32 fits actual12b hostframe address");
 reg cv,dv,lv;reg active_q;reg [7:0] target_q;reg [11:0] address_q,base_q;
 reg [12:0] limit_q;reg [15:0] loops_q;reg [255:0] data_q;
 always @(posedge clk_control)begin
  target_q<=cfg_target;address_q<=cfg_addr;data_q<=cfg_data;active_q<=program_active;
  base_q<=desc_base;limit_q<=desc_limit;loops_q<=desc_loops;
 end
 reg [511:0] assembly,write_data,selected_word_data;
 reg [1:0] seen;reg [10:0] selected_word;
 reg [WORDS-1:0] loaded;
 reg [NBANKS-1:0] write_v,read_v;reg [5:0] write_row,read_row;
 reg write_guard;
 wire [NBANKS*512-1:0] bank_data,bank_pin;
 for(genvar b=0;b<NBANKS;b=b+1)begin:g_mem
  ot_hgi_coll_static_program_bank u_bank(.clk(clk_mem[b]),.read_v(read_v[b]),.read_row(read_row),
   .write_v(write_v[b]),.write_row(write_row),.write_data(write_data),.data(bank_data[b*512+:512]));
  ot_hgi_coll_control256_capture u_capture(.clk(clk_capture[b]),.data(bank_data[b*512+:512]),.pin_data(bank_pin[b*512+:512]));
 end
 wire [511:0] assembled=address_q[0]?{data_q,assembly[255:0]}:{assembly[511:256],data_q};
 wire reserved_bad=(|assembled[255:238]) || (|assembled[511:494]);
 reg checking,check_bad;reg [WW-1:0] scan_word;
 reg [WW-1:0] first_word,last_word,word_index;
 reg [12:0] base,limit,pc;
 reg fetching,fetch_phase;
 reg [WW-1:0] next_fetch_word;
 reg rp0,rp1,rp2,read_high,high0,high1,high2,selected_high,low_ready,high_ready;
 reg [BW-1:0] read_bank,bank0,bank1,bank2;
 reg [511:0] selected_data;
 always @*begin
  selected_data=0;
  for(integer b=0;b<NBANKS;b=b+1)
   if(bank2==b)selected_data=selected_data|bank_pin[b*512+:512];
 end
 wire missing_word=(scan_word>=first_word && scan_word<=last_word && !loaded[scan_word]);
 always @(posedge clk_control or negedge rst_n)begin
  if(!rst_n)begin
   cv<=0;dv<=0;lv<=0;configured<=0;init_busy<=0;busy<=0;done<=0;fault<=0;
   control_v<=0;control<=0;control_cycle<=0;seen<=0;loaded<=0;
   write_v<=0;read_v<=0;write_guard<=0;checking<=0;check_bad<=0;scan_word<=0;
   base<=0;limit<=0;first_word<=0;last_word<=0;fetching<=0;fetch_phase<=0;next_fetch_word<=0;
   rp0<=0;rp1<=0;rp2<=0;read_high<=0;high0<=0;high1<=0;high2<=0;selected_high<=0;low_ready<=0;high_ready<=0;read_bank<=0;bank0<=0;bank1<=0;bank2<=0;
   selected_word<=0;pc<=0;word_index<=0;
  end else begin
   cv<=cfg_v;dv<=desc_v;lv<=launch_v;
   write_v<=0;read_v<=0;done<=0;control_v<=0;control<=0;
   rp0<=|read_v;rp1<=rp0;rp2<=rp1;
   bank0<=read_bank;bank1<=bank0;bank2<=bank1;
   high0<=read_high;high1<=high0;high2<=high1;
   low_ready<=rp2;high_ready<=low_ready && selected_high;
   if(write_guard)begin write_guard<=0;init_busy<=0;end
   if(checking)begin
    if(missing_word)check_bad<=1;
    if(scan_word==WORDS-1)begin
     checking<=0;init_busy<=0;
     if(check_bad || missing_word)fault<=1;
     else if(!fault)configured<=1;
    end else scan_word<=scan_word+1'b1;
   end
   if(rp2)begin selected_word_data<=selected_data;selected_high<=high2;end
   if(fetching)begin
    if(fetch_phase)begin
     if(next_fetch_word>=WORDS || next_fetch_word>last_word || !loaded[next_fetch_word])fault<=1;
     read_v[next_fetch_word>>6]<=1;read_row<=6'(next_fetch_word);read_bank<=BW'(next_fetch_word>>6);
     read_high<=!(next_fetch_word==last_word && limit[0]);
     if(next_fetch_word==last_word)fetching<=0;else next_fetch_word<=next_fetch_word+1'b1;
     fetch_phase<=0;
    end else fetch_phase<=1;
   end
   if(low_ready || high_ready)begin
    control_v<=1;control_cycle<=pc;pc<=pc+1'b1;
    if(low_ready)control<=(MUT_HALF?selected_word_data[511:256]:selected_word_data[255:0]) ^ (MUT_DATA?256'b1:256'b0);
    else control<=(MUT_HALF?selected_word_data[255:0]:selected_word_data[511:256]) ^ (MUT_DATA?256'b1:256'b0);
    if(pc==limit-1'b1)begin busy<=0;done<=1;end
   end
   if(cv && target_q==TARGET)begin
    if(active_q || busy || control_v || checking || write_guard || lv || dv || fault ||
      address_q[11:1]>=WORDS || loaded[address_q[11:1]] ||
      (seen!=0 && selected_word!=address_q[11:1]) || seen[address_q[0]])fault<=1;
    else begin
     selected_word<=address_q[11:1];seen[address_q[0]]<=1;init_busy<=1;
     if(address_q[0])assembly[511:256]<=data_q;else assembly[255:0]<=data_q;
     if((seen | (2'b1<<address_q[0]))==3)begin
      if(reserved_bad)fault<=1;
      else begin
       write_v[address_q[11:7]]<=1;write_row<=address_q[6:1];write_data<=assembled;
       loaded[address_q[11:1]]<=1;seen<=0;write_guard<=1;
      end
     end
    end
   end
   if(dv && target_q==TARGET)begin
    if(active_q || busy || control_v || checking || write_guard || seen!=0 || lv || cv || fault ||
       loops_q!=1 || base_q[0]!=0 || limit_q<={1'b0,base_q} || limit_q>WORDS*2)fault<=1;
    else begin
     base<={1'b0,base_q};limit<=limit_q;first_word<=WW'(base_q/2);
     last_word<=WW'((limit_q-1'b1)/2);scan_word<=0;check_bad<=0;
     checking<=1;configured<=0;init_busy<=1;
    end
   end
   if(lv && configured)begin
    if(active_q || busy || control_v || checking || write_guard || seen!=0 || cv || dv || fault)fault<=1;
    else begin
     busy<=1;word_index<=first_word;pc<=base;fetching<=first_word<last_word;next_fetch_word<=first_word+1'b1;fetch_phase<=0;
     read_v[first_word>>6]<=1;read_row<=6'(first_word);read_bank<=BW'(first_word>>6);read_high<=!(first_word==last_word && limit[0]);
    end
   end else if(lv && (checking || init_busy))fault<=1;
  end
 end
endmodule

// Separate pin capture leaf per bank keeps every clock root below15k sinks.
module ot_hgi_coll_control256_capture(input wire clk,input wire [511:0] data,output reg [511:0] pin_data);
 always @(posedge clk)pin_data<=data;
endmodule
`default_nettype wire
