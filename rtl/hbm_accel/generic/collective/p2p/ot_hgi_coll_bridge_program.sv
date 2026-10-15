`timescale 1ns/1ps
`default_nettype none
// Real quarter-bridge control catalogue. Ten49b operations per native512b word;
// word[511:490]=0, and q2 operations[48:30]=0. No behavioral memory.
// Raw HOST target56+QID, address=globalword*2+half, two256b frames/word.
// Reserve2edges afterfinalframe before nextword. Descriptor base/limit are
// cycle indices, base aligned10, loops1 only. Reserve64*NBANKS+2edges after
// descriptor before launch. Execution is fixed: firstoutput=launchcapture+5,
// bridgecaptures+6; one control/cycle, outputzero outside valid, done withlast.
module ot_hgi_coll_bridge_program #(
 parameter integer NBANKS=2,
 parameter [1:0] QID=2'd0,
 parameter [7:0] TARGET=8'd56+8'(QID),
 parameter integer MUT_DATA=0,MUT_WRAP=0,
 parameter integer WORDS=NBANKS*64,BW=(NBANKS>1?$clog2(NBANKS):1),WW=$clog2(WORDS)
)(
 input wire clk_control,input wire [NBANKS-1:0] clk_mem,input wire rst_n,
 input wire cfg_v,input wire [7:0] cfg_target,input wire [11:0] cfg_addr,
 input wire [255:0] cfg_data,
 input wire desc_v,input wire [11:0] desc_base,input wire [12:0] desc_limit,
 input wire [15:0] desc_loops,input wire launch_v,program_active,
 output reg configured,init_busy,busy,done,fault,
 output reg control_v,output reg [48:0] control,
 output reg [12:0] control_cycle
);
 initial if(NBANKS<1 || NBANKS>12)$fatal(1,"bridgecatalog NBANKS1..12 fits actual13b hostcycle descriptor");
 reg cv,dv,lv;reg [7:0] target_q;reg [11:0] address_q,base_q;
 reg [12:0] limit_q;reg [15:0] loops_q;reg [255:0] data_q;
 always @(posedge clk_control)begin
  target_q<=cfg_target;address_q<=cfg_addr;data_q<=cfg_data;
  base_q<=desc_base;limit_q<=desc_limit;loops_q<=desc_loops;
 end
 reg [511:0] assembly,write_data,current_word,next_word;
 reg [1:0] seen;reg [10:0] selected_word;
 reg [WORDS-1:0] loaded;
 reg [NBANKS-1:0] write_v,read_v;reg [5:0] write_row,read_row;
 reg write_guard;
 wire [NBANKS*512-1:0] bank_data;
 for(genvar b=0;b<NBANKS;b=b+1)begin:g_mem
  ot_hgi_coll_static_program_bank u_bank(.clk(clk_mem[b]),.read_v(read_v[b]),.read_row(read_row),
   .write_v(write_v[b]),.write_row(write_row),.write_data(write_data),.data(bank_data[b*512+:512]));
 end
 wire [511:0] assembled=address_q[0]?{data_q,assembly[255:0]}:{assembly[511:256],data_q};
 reg reserved_bad;
 always @*begin
  reserved_bad=|assembled[511:490];
  if(QID!=0)for(integer i=0;i<10;i=i+1)reserved_bad=reserved_bad | (|assembled[i*49+30+:19]);
 end
 reg checking,check_bad;reg [WW-1:0] scan_word;
 reg [WW-1:0] first_word,last_word,word_index;
 reg [12:0] base,limit,pc;
 reg [3:0] position;
 reg run,prefetch_valid;
 reg rp0,rp1,read_first,first0,first1;
 reg [BW-1:0] read_bank,bank0,bank1;
 reg [511:0] selected_data;
 always @*begin
  selected_data=0;
  for(integer b=0;b<NBANKS;b=b+1)
   if(bank1==b)selected_data=selected_data|bank_data[b*512+:512];
 end
 wire missing_word=(scan_word>=first_word && scan_word<=last_word && !loaded[scan_word]);
 always @(posedge clk_control or negedge rst_n)begin
  if(!rst_n)begin
   cv<=0;dv<=0;lv<=0;configured<=0;init_busy<=0;busy<=0;done<=0;fault<=0;
   control_v<=0;control<=0;control_cycle<=0;seen<=0;loaded<=0;
   write_v<=0;read_v<=0;write_guard<=0;checking<=0;check_bad<=0;scan_word<=0;
   base<=0;limit<=0;first_word<=0;last_word<=0;run<=0;prefetch_valid<=0;
   rp0<=0;rp1<=0;read_first<=0;first0<=0;first1<=0;read_bank<=0;bank0<=0;bank1<=0;
   selected_word<=0;position<=0;pc<=0;word_index<=0;
  end else begin
   cv<=cfg_v;dv<=desc_v;lv<=launch_v;
   write_v<=0;read_v<=0;done<=0;control_v<=0;control<=0;
   rp0<=|read_v;rp1<=rp0;bank0<=read_bank;bank1<=bank0;first0<=read_first;first1<=first0;
   if(write_guard)begin write_guard<=0;init_busy<=0;end
   if(checking)begin
    if(missing_word)check_bad<=1;
    if(scan_word==WORDS-1)begin
     checking<=0;init_busy<=0;
     if(check_bad || missing_word)fault<=1;
     else if(!fault)configured<=1;
    end else scan_word<=scan_word+1'b1;
   end
   if(rp1)begin
    if(first1)begin current_word<=selected_data;run<=1;end
    else begin next_word<=selected_data;prefetch_valid<=1;end
   end
   if(run)begin
    control_v<=1;control_cycle<=pc;
    control<=current_word[position*49+:49] ^ (MUT_DATA?49'b1:49'b0);
    pc<=pc+1'b1;
    if(position==4 && word_index<last_word)begin
     read_v[(word_index+1'b1)>>6]<=1;read_row<=6'(word_index+1'b1);
     read_bank<=BW'((word_index+1'b1)>>6);read_first<=0;
    end
    if(pc==limit-1'b1)begin run<=0;busy<=0;done<=1;end
    else if(position==(MUT_WRAP?8:9))begin
     if(!prefetch_valid)fault<=1;
     current_word<=next_word;prefetch_valid<=0;position<=0;word_index<=word_index+1'b1;
    end else position<=position+1'b1;
   end
   if(cv && target_q==TARGET)begin
    if(program_active || busy || control_v || checking || write_guard || lv || dv || fault ||
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
    if(program_active || busy || control_v || checking || write_guard || seen!=0 || lv || cv || fault ||
       loops_q!=1 || base_q%10!=0 || limit_q<={1'b0,base_q} || limit_q>WORDS*10)fault<=1;
    else begin
     base<={1'b0,base_q};limit<=limit_q;first_word<=WW'(base_q/10);
     last_word<=WW'((limit_q-1'b1)/10);scan_word<=0;check_bad<=0;
     checking<=1;configured<=0;init_busy<=1;
    end
   end
   if(lv && configured)begin
    if(program_active || busy || control_v || checking || write_guard || seen!=0 || cv || dv || fault)fault<=1;
    else begin
     busy<=1;word_index<=first_word;pc<=base;position<=0;prefetch_valid<=0;
     read_v[first_word>>6]<=1;read_row<=6'(first_word);read_bank<=BW'(first_word>>6);read_first<=1;
    end
   end else if(lv && (checking || init_busy))fault<=1;
  end
 end
endmodule
`default_nettype wire
