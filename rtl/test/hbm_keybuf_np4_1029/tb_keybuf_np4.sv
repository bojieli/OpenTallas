`timescale 1ps/1fs
module tb_keybuf_np4;
 parameter integer MUT=0;
 localparam integer NP=4,W=NP*1099,DW=NP*1088;
 reg clk=0;always #416.5 clk=~clk;
 reg rst_n=0,clear=0,live_v=0,pre_v=0,replay_v=0;
 reg[2:0]pbase=0;
 reg[7:0]live_index=0,pre_index=0,replay_index=0;
 reg[W-1:0]key_in=0;
 wire[W-1:0]gold,raw;
 wire gf,df;
 wire[2:0]mutbase=(MUT==1)?(pbase^3'b100):pbase;
 wire[7:0]mutpre=(MUT==3&&pre_v)?pre_index+8'd1:pre_index;
 wire[W-1:0]mutinput=(MUT==2&&live_v)?(key_in^(W'(1)<<(2*1099+1098))):key_in;
 ot_hnx_idxn_keybuf #(.NP(NP),.RS(0)) golden(.clk(clk),.rst_n(rst_n),.clear(clear),.pbase(pbase),
  .live_v(live_v),.live_index(live_index),.key_in(key_in),.pre_v(pre_v),.pre_index(pre_index),
  .replay_v(replay_v),.replay_index(replay_index),.key_out(gold),.fault(gf));
 ot_hnx_idxn_keybuf_sliced_np4 #(.NP(NP),.RS(0)) candidate(.clk(clk),.rst_n(rst_n),.clear(clear),.pbase(mutbase),
  .live_v(live_v),.live_index(live_index),.key_in(mutinput),.pre_v(pre_v),.pre_index(mutpre),
  .replay_v(replay_v),.replay_index(replay_index),.key_out(raw),.fault(df));
 reg[DW-1:0]memory[0:255];reg[DW-1:0]read_data=0;
 reg[W-1:0]want;integer epoch=0,cycles=0,checks=0,replays=0,writes=0,negative_cases=0;
 function automatic[W-1:0]word(input integer addr,input integer salt);
  reg[W-1:0]v;reg[31:0]x;integer p,j;
  begin
   v=0;
   for(p=0;p<NP;p=p+1)begin
    x=32'h9e3779b9^(32'(addr)*32'h01010101)^(32'(salt)*32'hA5F13D97)^(32'(p)*32'h7135B92D);
    for(j=0;j<1088;j=j+32)begin
     x=x^(x<<13);x=x^(x>>17);x=x^(x<<5);
     v[p*1099+11+j+:32]=x;
    end
    v[p*1099+:11]=11'((salt*173+addr*13+p*709)^11'h155);
   end
   word=v;
  end
 endfunction
 task automatic step(input bit cl,input bit lv,input integer li,input bit pv,input integer pi,input bit rv,input integer ri,input bit expect_fault);
  integer p;reg[9:0]tag;
  begin
   @(negedge clk);
   clear=cl;live_v=lv;live_index=8'(li);pre_v=pv;pre_index=8'(pi);replay_v=rv;replay_index=8'(ri);
   key_in=word(li,epoch*4096+cycles);
   #1;
   want=key_in;
   if(rv)for(p=0;p<NP;p=p+1)begin
    tag=10'((int'(pbase)+p)*128+ri);
    want[p*1099+:1099]={read_data[p*1088+:1088],tag,1'b1};
   end
   // Sample before the SRAM read edge, exactly where the scorer samples the
   // replay. This also checks simultaneous PRE(next)/REPLAY(current).
   if(raw!==gold)$fatal(1,"LOCKSTEP_DATA MUT=%0d cycle=%0d pbase=%0d replay=%0d",MUT,cycles,pbase,rv);
   if(gold!==want)$fatal(1,"REFERENCE_DATA cycle=%0d pbase=%0d replay=%0d",cycles,pbase,rv);
   checks=checks+2;
   @(posedge clk);
   // The actual macro is read-before-write for a same-address collision.
   if(pv)read_data=memory[8'(pi)];
   if(lv)begin
    for(p=0;p<NP;p=p+1)memory[8'(li)][p*1088+:1088]=key_in[p*1099+11+:1088];
    writes=writes+1;
   end
   #1;
   if(df!==gf)$fatal(1,"LOCKSTEP_FAULT MUT=%0d cycle=%0d golden=%b candidate=%b",MUT,cycles,gf,df);
   if(gf!==expect_fault)$fatal(1,"FAULT_EXPECT cycle=%0d want=%b got=%b",cycles,expect_fault,gf);
   checks=checks+2;cycles=cycles+1;if(rv)replays=replays+1;
  end
 endtask
 task automatic warm_reset;
  begin
   @(negedge clk);clear=0;live_v=0;pre_v=0;replay_v=0;rst_n=0;
   @(posedge clk);#1;
   if(gf!==0||df!==0)$fatal(1,"RESET_FAULT");
   @(negedge clk);rst_n=1;
  end
 endtask
 integer a,b,h;
 initial begin
  for(a=0;a<256;a=a+1)memory[a]=0;
  warm_reset();
  for(h=0;h<2;h=h+1)begin
   pbase=3'(h*4);epoch=epoch+1;
   step(1,0,0,0,0,0,0,0);
   for(a=0;a<=170;a=a+1)step(0,1,a,0,0,0,0,0);
   // First replay scans the complete legal address range, including127/128
   // tag carry and170, with a PRE exactly one edge before each replay.
   for(a=0;a<=170;a=a+1)begin step(0,0,0,1,a,0,0,0);step(0,0,0,0,0,1,a,0);end
   // Overwrite each beat while PRE reads that SAME address. Replay must observe
   // the old payload (actual macro's read-before-write), then the new payload.
   for(a=0;a<=170;a=a+1)begin
    step(0,1,a,1,a,0,0,0);step(0,0,0,0,0,1,a,0);
    step(0,0,0,1,a,0,0,0);step(0,0,0,0,0,1,a,0);
   end
   // Saturated replay: simultaneous PRE(next) and REPLAY(current).
   step(0,0,0,1,0,0,0,0);
   for(a=0;a<170;a=a+1)step(0,0,0,1,a+1,1,a,0);
   step(0,0,0,0,0,1,170,0);
   // Reverse address order defeats a constant/previous-address response.
   for(a=170;a>=0;a=a-1)begin step(0,0,0,1,a,0,0,0);step(0,0,0,0,0,1,a,0);end
   warm_reset();
   // Physical SRAM retains data, while control validity resets.
   step(0,0,0,1,170,0,0,1);negative_cases=negative_cases+1;
   step(0,0,0,0,0,1,170,1);
   warm_reset();step(0,0,0,0,0,1,0,1);negative_cases=negative_cases+1;
   warm_reset();step(0,1,171,0,0,0,0,1);negative_cases=negative_cases+1;
   warm_reset();step(0,1,255,0,0,0,0,1);negative_cases=negative_cases+1;
   warm_reset();step(0,0,0,1,171,0,0,1);negative_cases=negative_cases+1;
   step(0,0,0,0,0,1,171,1);
   warm_reset();step(0,1,0,0,0,0,0,0);step(0,1,1,0,0,0,0,0);
   step(0,0,0,1,0,0,0,0);step(0,0,0,0,0,1,1,1);negative_cases=negative_cases+1;
   warm_reset();step(0,1,0,0,0,0,0,0);step(0,0,0,1,0,0,0,0);
   step(0,1,1,0,0,1,0,1);negative_cases=negative_cases+1;
   warm_reset();step(1,1,0,0,0,0,0,0);step(0,0,0,1,0,0,0,1);negative_cases=negative_cases+1;
   warm_reset();
  end
  $display("NP4_PASS MUT=%0d checks=%0d cycles=%0d full_payload_bits=%0d writes=%0d replays=%0d negative_cases=%0d pbase=0,4 period_ps=833 SRAM=ACTUAL",MUT,checks,cycles,W,writes,replays,negative_cases);
  $finish;
 end
endmodule
