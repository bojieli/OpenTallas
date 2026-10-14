`timescale 1ns/1ps
module tb_qwen_tp8_kv_sector_adapter #(parameter integer MAP_MUT=0);
    reg clk=0;always #5 clk=~clk;
    reg rst_n=0,rv=0,kind=0;reg[15:0]epoch=16'h53;reg[5:0]layer=0;reg[17:0]pos=0;
    reg[1023:0]data=0;wire ready,fault;wire[1163:0]cmd;
    wire[15:0]ce;wire[5:0]cl;wire[17:0]cp;wire ck;
    reg[3:0]av=0,ak=0;reg[63:0]ae=0;reg[23:0]al=0;reg[71:0]ap=0;
    wire[31:0]issued,committed;
    ot_qwen_tp8_kv_sector_adapter #(.MAP_MUT(MAP_MUT)) dut(.clk(clk),.rst_n(rst_n),
      .row_v(rv),.row_ready(ready),.row_kind(kind),.row_epoch(epoch),.row_layer(layer),.row_pos(pos),.row_data(data),
      .commands(cmd),.command_epoch(ce),.command_layer(cl),.command_pos(cp),.command_kind(ck),
      .ack_v(av),.ack_kind(ak),.ack_epoch(ae),.ack_layer(al),.ack_pos(ap),
      .fault(fault),.sectors_issued(issued),.sectors_committed(committed));
    integer cy=0,nwritten=0, errors=0,which=0,neg=0;
    reg pending[0:3];integer due[0:3];reg[255:0]saved_data[0:3];reg[35:0]saved_key[0:3];
    reg[15:0]saved_epoch[0:3];reg[5:0]saved_layer[0:3];reg[17:0]saved_pos[0:3];reg saved_kind[0:3];
    reg[35:0]backing_key[0:63];reg[255:0]backing_data[0:63];
    function automatic[35:0] key(input integer l,t,v,q);
      reg[1:0]s;reg[4:0]pc,b,c;reg[18:0]r;
      begin s=(t>>7)&3;pc=8*q+(t&7);b=(v<<4)|(((t>>6)&1)<<2)|((t>>3)&3);
        c=(((t>>9)&15)<<1)|((t>>5)&1);r=64+l;key={s,pc,b,r,c};end
    endfunction
    always @(negedge clk)begin
      av=0;
      for(integer q=0;q<4;q++)if(pending[q]&&due[q]<=cy)begin
        av[q]=1;ak[q]=saved_kind[q];ae[16*q+:16]=saved_epoch[q];al[6*q+:6]=saved_layer[q];ap[18*q+:18]=saved_pos[q];
        if(neg==1&&which==2&&q==3)ae[16*q+:16]=saved_epoch[q]+1;
      end
    end
    always @(posedge clk)begin
      cy=cy+1;
      for(integer q=0;q<4;q++)if(av[q])begin
        // ACTUAL backing write from captured mapped output. ACK occurs on
        // this write edge; expected data is used only later by the checker.
        backing_key[nwritten]=saved_key[q];backing_data[nwritten]=saved_data[q];nwritten=nwritten+1;pending[q]=0;
      end
      for(integer s=0;s<4;s++)if(cmd[291*s])begin
        integer q;reg[290:0]packet;q=cmd[291*s+4+:2];packet=cmd[291*s+:291];
        if(pending[q])$fatal(1,"SECTOR_FAIL occupied quarter seat");
        pending[q]=1;due[q]=cy+4+q*3+(which==2&&q==3?59:0);
        saved_data[q]=packet[35+:256];saved_key[q]={2'(s),packet[1+:5],packet[6+:5],packet[16+:19],packet[11+:5]};
        saved_epoch[q]=ce;saved_layer[q]=cl;saved_pos[q]=cp;saved_kind[q]=ck;
      end
    end
    task tick;@(posedge clk);#1;endtask
    task publish(input integer l,t,v);
      integer before_n,ix;reg[255:0]wanted;reg found;
      begin
        while(!ready)tick();layer=l;pos=t;kind=v;epoch=epoch+1;which=which+1;
        for(integer d=0;d<128;d++)data[8*d+:8]=8'(d*3+v*17+which*11);
        before_n=nwritten;rv=1;tick();rv=0;
        // Stimulus includes explicit bounded downstream delays, including a
        // 59-edge final-quarter hold. This is an assertion on those supplied
        // service opportunities, never a production latency measurement.
        repeat(120)tick();
        if(neg==1&&which==2)begin
          if(!fault||ready)$fatal(1,"SECTOR_FAIL stale epoch released row");
          $display("SECTOR_ACK_REJECT_PASS actual write plus stale tagged ACK refused");$finish;
        end
        if(fault||!ready||nwritten!=before_n+4)$fatal(1,"SECTOR_FAIL four mapped write completions");
        for(integer q=0;q<4;q++)begin
          found=0;wanted=data[256*q+:256];
          for(ix=before_n;ix<nwritten;ix++)if(backing_key[ix]==key(l,t,v,q))begin
            found=1;if(backing_data[ix]!=wanted)errors=errors+1;
          end
          if(!found)errors=errors+1;
        end
      end
    endtask
    initial begin
      for(integer q=0;q<4;q++)pending[q]=0;
      if($value$plusargs("NEG=%d",neg))begin end
      repeat(4)tick();rst_n=1;repeat(4)tick();
      publish(0,0,0);publish(0,255,1);publish(17,8191,0);publish(35,8191,1);
      if(errors)$fatal(1,"SECTOR_DATA_FAIL independently addressed mapped quarters errors=%0d",errors);
      if(issued!=16||committed!=16)$fatal(1,"SECTOR_FAIL exact issued/committed count");
      $display("SECTOR_PASS 16 actual32B mapped writes,512 useful bytes, no fullrow replicas");$finish;
    end
endmodule
