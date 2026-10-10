`timescale 1ns/1ps
module tb_hgi_dma_wide_landing_lane #(parameter integer TEST_MUT=0,D=256);
 reg clk=0;always #0.4165 clk=~clk;reg rst_n=0,in_v=0,out_r=0;
 reg[17:0]in_sec=0;reg[255:0]in_data=0;wire out_v,credit,fault;wire[17:0]out_sec;wire[255:0]out_data;
 ot_hgi_dma_wide_landing_lane #(.ENABLE(1),.DEPTH(D),.MUT(TEST_MUT)) dut(.*);
 wire ov_off,cr_off,f_off;
 ot_hgi_dma_wide_landing_lane #(.DEPTH(D)) off(.clk(clk),.rst_n(rst_n),.in_v(in_v),.in_sec(in_sec),.in_data(in_data),.out_v(ov_off),.out_r(out_r),.credit(cr_off),.fault(f_off));
 function automatic[17:0]sector(input integer seq);
  sector=18'(seq*71)^18'h25ab1;
 endfunction
 function automatic[255:0]data(input integer seq);
  integer w;begin for(w=0;w<8;w=w+1)data[w*32+:32]=(32'h9e3779b9*(seq+1))^(32'h85ebca6b*(w+1));end
 endfunction
 integer sent=0,got=0,credits=D,returned=0,cycle=0,goal=0,run=0,maxrun=0,min_credit=99999,min_out=99999;
 reg read_return_edge;integer arrival[0:8191];reg stream_enable=0,hold=0;integer reject_mode=0;reg[17:0]heldsec;reg[255:0]helddata;
 always @(negedge clk)if(rst_n&&stream_enable)begin
  in_v=sent<goal&&(reject_mode||credits>0);
  in_sec=sector(sent);in_data=data(sent);
 end
 always @(posedge clk)if(rst_n)begin
  cycle=cycle+1;read_return_edge=(|dut.brd)&&!(|dut.bue)&&!(|dut.bfault);
  if(in_v)begin
   if(!reject_mode&&credits<=0)$fatal(1,"SOURCE_OVER_CREDIT");
   credits=credits-1;arrival[sent]=cycle;sent=sent+1;
  end
  if(credit)begin
   if(reject_mode&&reject_mode!=3)$fatal(1,"FAILURE_FAKE_CREDIT");
   if(returned>=sent)$fatal(1,"DUPLICATE_CREDIT");
   if(cycle-arrival[returned]<12)$fatal(1,"EARLY_CREDIT elapsed%0d",cycle-arrival[returned]);
   if(cycle-arrival[returned]<min_credit)min_credit=cycle-arrival[returned];
   credits=credits+1;returned=returned+1;
  end
  if(hold&&!fault&&(out_v!==1||out_sec!==heldsec||out_data!==helddata))$fatal(1,"OUTPUT_HOLD");
  if(out_v&&out_r)begin
   if(out_sec!==sector(got)||out_data!==data(got))$fatal(1,"LANDING_EXACT seq%0d",got);
   if(cycle-arrival[got]<min_out)min_out=cycle-arrival[got];got=got+1;run=run+1;if(run>maxrun)maxrun=run;
  end else run=0;
  hold=out_v&&!out_r;heldsec=out_sec;helddata=out_data;
  // A read is legal only after the matching write ACK was observed and published.
  if(TEST_MUT==2&&dut.ra&&!dut.published[dut.ri])$fatal(1,"UNPUBLISHED_READ");
  #0.05;
  if(credit&&!read_return_edge)$fatal(1,"EARLY_CREDIT_ACTUAL_CAPTURE");
  if({ov_off,cr_off,f_off}!==3'd0)$fatal(1,"DEFAULT_OFF");
  if(^({out_v,out_sec,out_data,credit,fault})===1'bx)$fatal(1,"OUTPUT_X");
  if(fault&&!reject_mode)$fatal(1,"UNEXPECTED_FAULT sent%0d got%0d credits%0d",sent,got,credits);
 end
 task reset_case;
 begin
  @(negedge clk);stream_enable=0;in_v=0;rst_n=0;hold=0;out_r=0;
  repeat(4)@(negedge clk);sent=0;got=0;credits=D;returned=0;cycle=0;run=0;maxrun=0;goal=0;min_credit=99999;min_out=99999;rst_n=1;
 end endtask
 initial begin
  reset_case;
  // Exactly DEPTH initial beats offered with no ready, while consumer stalls far past pipeline depth.
  goal=D;stream_enable=1;repeat(D+80)@(negedge clk);
  if(sent!=D||got!=0||returned>9||credits>D||fault)$fatal(1,"FULL_CREDIT_WINDOW");
  stream_enable=0;in_v=0;out_r=1;
  repeat(D+80)@(negedge clk);
  if(got!=D||returned!=D||credits!=D)$fatal(1,"WINDOW_DROP got%0d credits%0d",got,returned);
  // Four full FIFO wraps; output and source both continuous when credits permit.
  goal=D*5;stream_enable=1;
  repeat(D*4+160)@(negedge clk);
  if(sent!=goal||got!=goal||returned!=goal||credits!=D)$fatal(1,"WRAP_DROP sent%0d got%0d ret%0d",sent,got,returned);
  if(maxrun<D*3)$fatal(1,"LANDING_NOT_II1 run%0d",maxrun);
  $display("LANDING_DATA_PASS depth%0d sent%0d got%0d ret%0d II1_run%0d min_credit_elapsed%0d min_out_elapsed%0d actual4SRAM",D,sent,got,returned,maxrun,min_credit,min_out);
  // Single error in actual committed payload must be corrected before credit and downstream capture.
  stream_enable=0;in_v=0;reset_case;goal=1;stream_enable=1;out_r=1;
  wait(sent==1);wait(dut.bwd[0]);@(negedge clk);stream_enable=0;in_v=0;
  dut.phase[0].u_bank.mem.u_payload.arr[0]=dut.phase[0].u_bank.mem.u_payload.arr[0]^516'd1;
  repeat(35)@(negedge clk);
  if(fault||got!=1||returned!=1||credits!=D)$fatal(1,"CORRECTED_CAPTURE_FAILED");
  // Double error in actual committed payload macro before prefetch; no credit or publication.
  reject_mode=1;reset_case;goal=1;stream_enable=1;
  wait(sent==1);wait(dut.bwd[0]);@(negedge clk);stream_enable=0;in_v=0;
  // First bank's row0 parity payload data bits0/1 occupy interleaved physical columns0/2.
  dut.phase[0].u_bank.mem.u_payload.arr[0]=dut.phase[0].u_bank.mem.u_payload.arr[0]^516'd5;
  repeat(30)@(negedge clk);
  if(!fault||credit||out_v||returned!=0)$fatal(1,"UE_NOT_CLOSED");
  // Metadata complementrail corruption before publication.
  reset_case;goal=1;stream_enable=1;
  wait(sent==1);@(negedge clk);stream_enable=0;in_v=0;
  dut.meta_n[0]=dut.meta_n[0]^18'd1;
  repeat(20)@(negedge clk);
  if(!fault||credit||out_v||returned!=0)$fatal(1,"METADATA_NOT_CLOSED");
  // Overflow: bypass producer credits deliberately; expect sticky fault, never silently drop.
  reject_mode=3;reset_case;goal=D+32;stream_enable=1;
  repeat(D+64)@(negedge clk);stream_enable=0;in_v=0;
  if(!fault||credit||out_v)$fatal(1,"OVERFLOW_NOT_CLOSED");
  $display("LANDING_PASS finitecredit actualcapture UE metadatarail overflow defaultOFF noX");$finish;
 end
endmodule
