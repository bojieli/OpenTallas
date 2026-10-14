`timescale 1ns/1ps
// Distinct native59 actual helper mechanism fixture; not a production ring or allocator proof.
module tb_qwen_native8_identity59;
  parameter integer MUT=0;
  reg clk=0,rst_n=0,start=0;
  always #0.5 clk=~clk;
  reg [17:0] token=151935,pos=8191;
  wire done,fault,core_start,desc_re,vm_re,vm_we,cv,cl,cm;
  wire [5:0] desc_addr;
  wire [7:0] vm_addr,vm_wa;
  wire [511:0] cd,vm_wd;
  wire [58:0] ct; reg [58:0] rt=0; reg [15:0] epoch=16'd17;reg [5:0] stage=6'd1;
  reg [63:0] desc_q=0; reg sweep_mode=0; integer sweep_token=0,sweep_bad=0,sweep_wait=0;
  reg [511:0] vm_q=0,rd=0;
  reg core_done=0,cr=0,rv=0,rl=0;
  ot_qwen_tp_seq_w12_vrl_native59 #(.N(8),.NW(18),.RB(3),.CRED(32),.VRL(1)) dut (
    .clk(clk),.rst_n(rst_n),.rst_nw(rst_n),.start(start),.token(token),.pos(pos),
    .tag_epoch(epoch),.tag_stage(stage),.r_tag(rt),.done(done),.fault(fault),.core_start(core_start),.core_done(core_done),
    .core_next_token(18'd0),.core_next_val(32'd0),.core_fault(1'b0),
    .desc_re(desc_re),.desc_addr(desc_addr),.desc_q(desc_q),
    .vm_re(vm_re),.vm_raddr(vm_addr),.vm_rq(vm_q),.vm_we(vm_we),.vm_waddr(vm_wa),.vm_wdata(vm_wd),
    .c_valid(cv),.c_ready(cr),.c_data(cd),.c_last(cl),.c_mode(cm),.c_tag(ct),
    .r_valid(rv),.r_data(rd),.r_last(rl),.r_rank(3'd0),.r_err(1'b0));
  always @(posedge clk) begin
    core_done<=core_start;
    if(desc_re) desc_q<=(sweep_mode||desc_addr!=0)?0:(64'd1|(64'd128<<10));
    if(vm_re) vm_q<={{504{1'b0}},vm_addr};
  end
  integer sent=0,acked=0,received=0,writes=0,stall=0,cyc=0,bad=0,frames=0,full_events=0;
  reg send_sample,ack_sample,receive_sample;
  task frame(input integer frame_id);
    begin
      sent=0;acked=0;received=0;writes=0;stall=0;cyc=0;
      @(negedge clk);start=1;
      @(negedge clk);start=0;
      while((!done||cyc<10)&&cyc<4000&&!(fault&&MUT>=1&&MUT<=5))begin
        cr=0;rv=0;rl=0;
        if(sent==32&&acked==0&&stall<128)begin
          stall=stall+1;
          if(stall==128)full_events=full_events+1;
          if(cv)bad=bad+1;
        end else if(stall>=128&&sent>acked&&(cyc%3==0))cr=1;

        if(sent==128&&received<128)begin
          rv=1;rd=512'(received);rl=(received==127);
          rt={epoch,stage,token,pos[12:0],6'd0};
          if(MUT>=1&&MUT<=5)rt=rt^(59'd1<<((MUT==1)?43:(MUT==2)?37:(MUT==3)?35:(MUT==4)?14:0));
        end
        send_sample=cv;ack_sample=cr;receive_sample=rv;
        if(cv)begin
          if(cd!==512'(sent)||cl!=(sent==127)||cm!=0)bad=bad+1;
          sent=sent+1;
        end
        if(cr)acked=acked+1;
        if(rv)received=received+1;
        @(posedge clk);#0.1;
        if(dut.c_cred>32)bad=bad+1;
        if(vm_we)begin if(vm_wa!=writes||vm_wd!==512'(writes))bad=bad+1;writes=writes+1;end
        @(negedge clk);cyc=cyc+1;
      end
      rv=0;rl=0;
      // Accepted posts have actual staged ACK obligations independent of result_done.
      while(acked<sent)begin cr=1;acked=acked+1;@(negedge clk);end
      cr=0;@(negedge clk);
      if(MUT>=1&&MUT<=5)begin
        if(!fault||writes!=0||dut.rx_k!=0)bad=bad+1;
      end else if(sent!=128||received!=128||writes!=128||stall!=128||fault||!done||dut.c_cred!=32)bad=bad+1;
      frames=frames+1;
      $display("FRAME id=%0d sent=%0d acked=%0d received=%0d writes=%0d depleted_edges=%0d cycles=%0d credit=%0d faults=%0d",frame_id,sent,acked,received,writes,stall,cyc,dut.c_cred,fault);
    end
  endtask
  initial begin
    #0.1;rst_n=1;#0.1;rst_n=0;
    repeat(4)@(negedge clk);rst_n=1;
    if(MUT<=5)begin
      frame(0);
      if(MUT==0)begin
        token=65537;pos=7935;stage=2;frame(1);
        rst_n=0;repeat(4)@(negedge clk);rst_n=1;token=1;pos=8191;epoch=18;stage=37;frame(2);
        sweep_mode=1;
        for(sweep_token=0;sweep_token<151936;sweep_token=sweep_token+1)begin
          @(negedge clk);token=18'(sweep_token);pos=(sweep_token%2)?8191:7935;stage=6'(sweep_token%38);epoch=16'd19;start=1;
          @(negedge clk);start=0;
          if(ct!=={epoch,stage,token,pos[12:0],6'd0})sweep_bad=sweep_bad+1;
          sweep_wait=0;
          while(!done&&sweep_wait<100)begin @(negedge clk);sweep_wait=sweep_wait+1;end
          if(!done||fault)sweep_bad=sweep_bad+1;
        end
        if(sweep_bad!=0)bad=bad+sweep_bad;
        $display("VOCAB_NATIVE59 actual_start_captures=%0d stage_count=38 positions=8191,7935 bad=%0d",sweep_token,sweep_bad);
      end
    end else if(MUT==6)begin
      rt=59'd0;rv=1;@(negedge clk);rv=0;
      if(!fault||vm_we||dut.rx_k!=0)bad=bad+1;
    end else if(MUT==7)begin
      cr=1;@(negedge clk);cr=0;
      if(!fault||dut.c_cred!=32)bad=bad+1;
    end
    if(bad!=0)$fatal(1,"NATIVE59 bad=%0d mutant=%0d",bad,MUT);
    $display("PASS NATIVE59 mutant=%0d frames=%0d full_windows=%0d fault=%0d writes=%0d",MUT,frames,full_events,fault,writes);
    $finish;
  end
endmodule
