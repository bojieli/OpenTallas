`timescale 1ns/1ps
module tb_hgi_coll_bridge_program;
 parameter integer NBANKS=2,QID=0,MUT_DATA=0,MUT_WRAP=0;
 localparam WORDS=NBANKS*64,CAPACITY=WORDS*10;
 reg clk=0,rst_n=0;always #0.5 clk=~clk;
 reg cv=0,dv=0,lv=0,active=0;reg [7:0] target=8'(56+QID);
 reg [11:0] addr=0,base=0;reg [12:0] limit=13'(CAPACITY);reg [15:0] loops=1;
 reg [255:0] data=0;
 wire configured,init_busy,busy,done,fault,control_v;wire [48:0] control;wire [12:0] pc;
 ot_hgi_coll_bridge_program #(.NBANKS(NBANKS),.QID(2'(QID)),.MUT_DATA(MUT_DATA),.MUT_WRAP(MUT_WRAP)) dut(
  .clk_control(clk),.clk_mem({NBANKS{clk}}),.rst_n(rst_n),.cfg_v(cv),.cfg_target(target),.cfg_addr(addr),.cfg_data(data),
  .desc_v(dv),.desc_base(base),.desc_limit(limit),.desc_loops(loops),.launch_v(lv),.program_active(active),
  .configured(configured),.init_busy(init_busy),.busy(busy),.done(done),.fault(fault),
  .control_v(control_v),.control(control),.control_cycle(pc));
 reg [511:0] image[0:WORDS-1];bit use_image=0;string image_path;integer image_length=0;
 integer cycle=0;always @(posedge clk)cycle<=cycle+1;
 function automatic [48:0] operation(input integer p);
  reg [48:0] d;
  if(use_image)return image[p/10][(p%10)*49+:49];
  d=(49'h1ac4072fd3e99 ^ (49'(p)*49'h139b4712f35));
  return QID==0?d:{19'b0,d[29:0]};
 endfunction
 function automatic [511:0] word_(input integer w);
  reg [511:0] d;if(use_image)return image[w];d=0;
  for(integer i=0;i<10;i=i+1)d[i*49+:49]=operation(w*10+i);
  return d;
 endfunction
 task frame(input integer w,input integer half);
  reg [511:0] d;d=word_(w);
  @(negedge clk);cv=1;addr=12'(w*2+half);data=d[half*256+:256];
 endtask
 task idle(input integer edges);
  @(negedge clk);cv=0;dv=0;lv=0;repeat(edges-1)@(negedge clk);
 endtask
 task word_program(input integer w);
  frame(w,w%2);frame(w,1-w%2);idle(2);
 endtask
 task descriptor;
  @(negedge clk);cv=0;dv=1;idle(WORDS+2);
 endtask
 task execute;
  integer start_edge,checked,first,last;
  @(negedge clk);lv=1;start_edge=cycle+1;idle(1);checked=0;first=-1;last=-1;
  repeat(limit-base+8)begin
   @(posedge clk);#0.01;
   if(fault)$fatal(1,"unexpected programme fault pc%0d",pc);
   if(control_v)begin
    if(first<0)first=cycle;else if(cycle!=last+1)$fatal(1,"control publication gap");last=cycle;
    if(pc!=base+checked || control!==operation(base+checked))$fatal(1,"CONTROL mismatch index%0d got%h expected%h",pc,control,operation(base+checked));
    if(done!==(checked==limit-base-1))$fatal(1,"done notonexactlast control");
    checked++;
   end else if(control!==49'b0)$fatal(1,"nonzero idlecontrol");
  end
  if(first-start_edge!=5 || checked!=limit-base)$fatal(1,"first/count got%0d/%0d",first-start_edge,checked);
  $display("BRIDGE_PROGRAM EXEC PASS banks=%0d qid=%0d base=%0d limit=%0d count=%0d first_edges=5",NBANKS,QID,base,limit,checked);
 endtask
 integer scenario=0;
 initial begin
  if($value$plusargs("fault=%d",scenario))begin end
  if($value$plusargs("image=%s",image_path))begin use_image=1;$readmemh(image_path,image);end
  if($value$plusargs("length=%d",image_length))limit=13'(image_length);
  repeat(4)@(negedge clk);rst_n=1;
  if(scenario!=0)begin
   case(scenario)
    1:begin frame(0,0);frame(0,0);end
    2:begin frame(0,0);frame(1,1);end
    3:frame(WORDS,0);
    4:begin frame(0,0);frame(0,1);data[255]=1;end
    5:begin frame(0,1);frame(0,0);if(QID!=0)data[30]=1;else data[255]=1;frame(0,1);data[255]=1;end
    6:begin active=1;frame(0,0);end
    7:begin loops=2;descriptor();end
    8:begin base=1;descriptor();end
    9:descriptor();
    10:begin word_program(0);@(negedge clk);dv=1;idle(2);@(negedge clk);lv=1;end
    11:begin word_program(0);frame(0,0);end
    12:begin
     word_program(0);limit=10;descriptor();@(negedge clk);lv=1;idle(3);
     if(!busy)$fatal(1,"actual native programme notbusy");frame(1,0);
    end
    13:begin limit=CAPACITY+1;descriptor();end
    14:begin frame(0,0);descriptor();end
    15:begin frame(0,0);@(negedge clk);cv=0;lv=1;end
    16:begin frame(0,0);frame(0,1);frame(1,0);end
    17:begin limit=0;descriptor();end
    default:$fatal(1,"badscenario");
   endcase
   idle(8);if(!fault)$fatal(1,"missing faultscenario%0d",scenario);
   $display("BRIDGE_PROGRAM FAULT PASS scenario=%0d",scenario);$finish;
  end
  target=8'(60+QID);frame(WORDS,0);idle(3);target=8'(56+QID);
  for(integer w=0;w<WORDS;w=w+1)word_program(w);
  descriptor();if(!configured)$fatal(1,"notconfigured afterfixedvalidation");execute();
  if(NBANKS>1 && limit>640)begin base=640;descriptor();execute();end
  $display("BRIDGE_PROGRAM PASS actual_macro_count=%0d capacity=%0d exact_control_bits=49",NBANKS,CAPACITY);$finish;
 end
endmodule
