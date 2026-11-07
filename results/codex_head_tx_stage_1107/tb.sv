`timescale 1ns/1ps
module tb;
    parameter integer CHMUT = 0;
    reg clk=0, rst_n=0, tx_v=0;
    reg [511:0] tx_d=0;
    wire rv,rf,bv,bf,nv,nf;
    wire [543:0] rd,bd,nd;
    ot_s81_kp4_enc_la_ref #(.LA(2),.FF(1)) old_i
      (.clk(clk),.rst_n(rst_n),.tx_v(tx_v),.tx_d(tx_d),.p_v(rv),.p_d(rd),.fault(rf));
    ot_s81_kp4_enc_la #(.LA(2),.FF(1)) default_i
      (.clk(clk),.rst_n(rst_n),.tx_v(tx_v),.tx_d(tx_d),.p_v(bv),.p_d(bd),.fault(bf));
    ot_s81_kp4_enc_la #(.LA(2),.FF(1),.CH_STAGE(1),.CH_MUT(CHMUT)) new_i
      (.clk(clk),.rst_n(rst_n),.tx_v(tx_v),.tx_d(tx_d),.p_v(nv),.p_d(nd),.fault(nf));
    always #1 clk=~clk;
    reg old_v=0,old_f=0;
    reg [543:0] old_d=0;
    integer cyc=0,off_bad=0,new_bad=0,words=0,valid_cycles=0,seed=11,dummy,reset_at=3600;
    initial begin
      if($value$plusargs("RESET_AT=%d",reset_at))begin end
      dummy=$urandom(seed);
      for(cyc=0;cyc<6400;cyc=cyc+1) begin
        @(negedge clk);
        rst_n=(cyc>=4 && !(cyc>=reset_at && cyc<reset_at+8));
        tx_v=(cyc>=12 && !(cyc>=reset_at && cyc<reset_at+20) && cyc!=500 && cyc!=1100 && cyc!=4200);
        for(integer b=0;b<16;b=b+1)tx_d[32*b+:32]=$urandom;
        @(posedge clk);#0.1;
        if(cyc>12) begin
          if(bv !== rv || bf !== rf || (rv && bd !== rd)) begin
            off_bad++;
            if(off_bad<5)$display("DEFAULT_DIFF cyc=%0d valid=%b/%b fault=%b/%b",cyc,bv,rv,bf,rf);
          end
          if(nv !== old_v || nf !== old_f || (old_v && nd !== old_d)) begin
            new_bad++;
            if(new_bad<7)$display("STAGE_DIFF cyc=%0d valid=%b/%b fault=%b/%b data_xor=%h",cyc,nv,old_v,nf,old_f,nd^old_d);
          end
          if(old_v)words++;
          if(nv)valid_cycles++;
        end
        old_d=rd;old_v=rv;old_f=rf;
      end
      $display("TX_CH_STAGE CHMUT=%0d RESET_AT=%0d default_diffs=%0d stage_diffs=%0d compared_words=%0d new_valid=%0d %s",CHMUT,reset_at,off_bad,new_bad,words,valid_cycles,(off_bad==0 && new_bad==0 && words>6000)?"PASS":"FAIL");
      if(off_bad || new_bad || words<=6000)$fatal(1,"TX stage equivalence failed");
      $finish;
    end
endmodule
