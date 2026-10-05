`timescale 1ps/1ps
// Verification only. Generated original/candidate dependencies; CUT379 means LAT8.
// 833 ps stream clock; no physical timing claim. Default-zero two-state unreset
// payload initialization is identical on both sides; do not change RTL resets.
module field_chain_case #(parameter integer NCH=16);
    reg clk=0, rst_n=1, v=0, first=0, last=0, term_f=0;
    reg [$clog2(NCH)-1:0] slot=0;
    reg [31:0] term=0;
    reg [7:0] tag=0;
    wire ro,co,rf,cf,r_fault,c_fault;
    wire [31:0] rs,cs;
    wire [7:0] rt,ct;
    ref_ot_v41_chain2 #(.NCH(NCH),.TW(8),.CUT(379)) ref_dut
      (.clk(clk),.rst_n(rst_n),.v(v),.slot(slot),.first(first),.last(last),
       .term(term),.term_f(term_f),.tag(tag),.ov(ro),.osum(rs),.of(rf),.otag(rt),.fault(r_fault));
    cand_ot_v41_chain2 #(.NCH(NCH),.TW(8),.CUT(379)) cand_dut
      (.clk(clk),.rst_n(rst_n),.v(v),.slot(slot),.first(first),.last(last),
       .term(term),.term_f(term_f),.tag(tag),.ov(co),.osum(cs),.of(cf),.otag(ct),.fault(c_fault));
    integer cycles=0, emitted=0, fwd8=0, fwd9=0, wr=0, rd=0;
    reg [7:0] expected_tag[0:1023];
    reg negative_phase=0;
    task compare_all;
      if ({ro,rs,rf,rt,r_fault} !== {co,cs,cf,ct,c_fault})
        $fatal(1,"chain%0d mismatch cycle=%0d",NCH,cycles);
    endtask
    task tick;
      compare_all();
      #416; clk=1; #1; compare_all();
      if (rst_n) begin
        if (v && last && !negative_phase) begin expected_tag[wr]=tag; wr=wr+1; end
        if (ro && !negative_phase) begin
          if (rd>=wr || rt!==expected_tag[rd]) $fatal(1,"chain tag/order");
          rd=rd+1; emitted=emitted+1;
        end
        if (v && ref_dut.fwd5) fwd8=fwd8+1;
        if (v && ref_dut.fwd6) fwd9=fwd9+1;
        if (!negative_phase && r_fault) $fatal(1,"legal chain schedule fault");
      end
      #416; clk=0; cycles=cycles+1; compare_all();
    endtask
    task gap(input integer n);
      v=0; repeat(n) tick();
    endtask
    task reset_now;
      v=0; rst_n=0; #1; compare_all();
      if (ro || r_fault) $fatal(1,"chain asynchronous reset control");
      repeat(2) tick(); rst_n=1; wr=0;rd=0; negative_phase=0;
    endtask
    function [31:0] value(input integer i);
      case(i%10)
        0:value=32'h3f800000; 1:value=32'hbf800000; 2:value=32'h33800000;
        3:value=32'h00800000; 4:value=32'h00000001; 5:value=32'h80000000;
        6:value=32'h7f7fffff; 7:value=32'h7f800000; 8:value=32'h7fc00001;
        default:value=32'h3f800001;
      endcase
    endfunction
    integer round_i,s,g,before_outputs;
    initial begin
      reset_now();
      // Eight golden chunk terms, all physical slots; scheduled idle cycles.
      for(round_i=0;round_i<8;round_i=round_i+1) begin
        for(s=0;s<NCH;s=s+1) begin
          v=1;slot=s;first=(round_i==0);last=(round_i==7);
          term=value(round_i+s);term_f=(s==1 && round_i==3);tag=8'h80+s;tick();
        end
        gap(3);
      end
      gap(64);
      if (emitted!=NCH || rd!=wr) $fatal(1,"chain chunk drain/count");
      // Exercise recurrence boundaries exactly 8 and 9, without changing LAT.
      for(g=8;g<=9;g=g+1) begin
        for(round_i=0;round_i<8;round_i=round_i+1) begin
          v=1;slot=0;first=(round_i==0);last=(round_i==7);
          term=value(round_i);term_f=0;tag=g;tick();gap(g-1);
        end
        gap(64);
      end
      if(fwd8==0 || fwd9==0 || emitted!=NCH+2) $fatal(1,"chain forwarding coverage");
      // Reset with a last term and tags still in flight; it cancels valid only.
      v=1;slot=2;first=1;last=1;tag=8'hff;tick();gap(2);reset_now();gap(64);
      if(rd!=wr) $fatal(1,"chain reset left output");
      // Isolated illegal short recurrence must produce sticky hazard, then clear.
      negative_phase=1;v=1;slot=0;first=1;last=0;tick();first=0;tick();gap(20);
      if(!r_fault) $fatal(1,"chain hazard negative not reached");
      reset_now();gap(64);
      $display("PASS chain%0d cycles=%0d outputs=%0d forward8=%0d forward9=%0d",NCH,cycles,emitted,fwd8,fwd9);
      $finish;
    end
endmodule
module tb_chain16; field_chain_case #(.NCH(16)) u(); endmodule
module tb_chain8; field_chain_case #(.NCH(8)) u(); endmodule

module tb_tree16;
    reg clk=0,rst_n=1,in_v=0,in_final=0,in_err=0;
    reg [3:0] in_tree=0;
    reg [2:0] in_pos=0;
    reg [31:0] in_val=0;
    wire ro,co,re,ce,rf,cf;
    wire [3:0] rt,ct;
    wire [2:0] rp,cp;
    wire [31:0] rv,cv;
    ref_ot_v41_segtree2 #(.NT(16),.LV(5),.QD(8),.EARLY(1),.CUT(379)) ref_dut
      (.clk(clk),.rst_n(rst_n),.in_v(in_v),.in_tree(in_tree),.in_pos(in_pos),
       .in_val(in_val),.in_final(in_final),.in_err(in_err),.ov(ro),.otree(rt),.opos(rp),.oval(rv),.oerr(re),.fault(rf));
    cand_ot_v41_segtree2 #(.NT(16),.LV(5),.QD(8),.EARLY(1),.CUT(379)) cand_dut
      (.clk(clk),.rst_n(rst_n),.in_v(in_v),.in_tree(in_tree),.in_pos(in_pos),
       .in_val(in_val),.in_final(in_final),.in_err(in_err),.ov(co),.otree(ct),.opos(cp),.oval(cv),.oerr(ce),.fault(cf));
    integer cycles=0,outputs=0,pairs=0,promotions=0,earlies=0,peak_q=0;
    reg negative_phase=0, scoreboard=0;
    reg [15:0] seen=0;
    task compare_all;
      if({ro,rt,rp,rv,re,rf} !== {co,ct,cp,cv,ce,cf}) $fatal(1,"tree mismatch cycle=%0d",cycles);
    endtask
    task tick;
      compare_all();
      if(rst_n) begin
        if(ref_dut.pair) pairs=pairs+1;
        if(ref_dut.promote) promotions=promotions+1;
        if(ref_dut.early) earlies=earlies+1;
      end
      #416;clk=1;#1;compare_all();
      if(rst_n) begin
        if(ref_dut.qc>peak_q) peak_q=ref_dut.qc;
        if(!negative_phase && rf) $fatal(1,"legal tree traffic fault");
        if(ro && scoreboard) begin
          if(seen[rt] || rp!==(rt%8)) $fatal(1,"tree identity/position duplicate");
          seen[rt]=1; outputs=outputs+1;
        end
      end
      #416;clk=0;cycles=cycles+1;compare_all();
    endtask
    task gap(input integer n); in_v=0;repeat(n) tick(); endtask
    task reset_now;
      in_v=0;rst_n=0;#1;compare_all();
      if(ro || re || rf) $fatal(1,"tree asynchronous reset control");
      repeat(2) tick();rst_n=1;negative_phase=0;scoreboard=0;seen=0;
    endtask
    integer t,n,j;
    initial begin
      reset_now();scoreboard=1;
      // Odd leaf counts force padding/promotions; every tree-id and position.
      for(t=0;t<16;t=t+1) begin
        n=(t%2==0)?3:5;
        for(j=0;j<n;j=j+1) begin
          in_v=1;in_tree=t;in_pos=t%8;in_final=(j==n-1);in_err=(t==3 && j==0);
          case(j%4)
            0:in_val=32'h3f800001;1:in_val=32'hbf800000;
            2:in_val=32'h33800000;default:in_val=32'h00800000;
          endcase
          tick();gap(31);
        end
        gap(128);
      end
      if(outputs!=16 || seen!=16'hffff || pairs==0 || promotions==0) $fatal(1,"tree padding coverage");
      scoreboard=0;
      // Early single final, bypassing padding when no held/inflight above it.
      in_v=1;in_tree=15;in_final=1;in_pos=7;tick();gap(128);
      if(earlies==0) $fatal(1,"early path not reached");
      // Deliberate queue pressure; no ready port exists. Stop at first overflow.
      reset_now();negative_phase=1;
      for(j=0;j<256 && !rf;j=j+1) begin
        in_v=1;in_tree=j%16;in_pos=j%8;in_final=0;in_err=0;in_val=32'h3f800000;tick();
      end
      if(!rf || peak_q<8) $fatal(1,"queue pressure negative not reached");
      reset_now();gap(128);
      // Reset with held values, queue entries and adder operations in flight.
      for(j=0;j<8;j=j+1) begin
        in_v=1;in_tree=0;in_final=(j==7);tick();
      end
      reset_now();gap(128);
      if(ro || rf) $fatal(1,"tree reset drain");
      $display("PASS tree16 cycles=%0d outputs=%0d pairs=%0d promotions=%0d early=%0d peak_queue=%0d",cycles,outputs,pairs,promotions,earlies,peak_q);
      $finish;
    end
endmodule

module tb_bf16;
    reg clk=0,rst_n=1,v=0,first=0,last=0,final_i=0;
    reg [255:0] w=0,x=0;
    reg [2:0] slot=0;
    reg [6:0] tree=0;
    wire ro,co,rfinal,cfinal,re,ce,rf,cf;
    wire [31:0] rv,cv;
    wire [6:0] rt,ct;
    ref_ot_v41_bf16_lanes2 #(.NCHB(8),.TRW(7),.CUT(379)) ref_dut
      (.clk(clk),.rst_n(rst_n),.v(v),.w(w),.x(x),.slot(slot),.first(first),.last(last),
       .tree(tree),.final_i(final_i),.ov(ro),.oval(rv),.otree(rt),.ofinal(rfinal),.oerr(re),.fault(rf));
    cand_ot_v41_bf16_lanes2 #(.NCHB(8),.TRW(7),.CUT(379)) cand_dut
      (.clk(clk),.rst_n(rst_n),.v(v),.w(w),.x(x),.slot(slot),.first(first),.last(last),
       .tree(tree),.final_i(final_i),.ov(co),.oval(cv),.otree(ct),.ofinal(cfinal),.oerr(ce),.fault(cf));
    integer cycles=0,outputs=0,wr=0,rd=0,error_outputs=0,finite_outputs=0;
    reg [7:0] expected[0:255];
    task compare_all;
      if({ro,rv,rt,rfinal,re,rf} !== {co,cv,ct,cfinal,ce,cf}) $fatal(1,"BF16 mismatch cycle=%0d",cycles);
    endtask
    task tick;
      compare_all();#416;clk=1;#1;compare_all();
      if(rst_n) begin
        if(v && last) begin expected[wr]={tree,final_i};wr=wr+1;end
        if(ro) begin
          if(rd>=wr || {rt,rfinal}!==expected[rd]) $fatal(1,"BF16 tree/final/order");
          rd=rd+1;outputs=outputs+1;if(re) error_outputs=error_outputs+1;else finite_outputs=finite_outputs+1;
        end
        if(rf) $fatal(1,"BF16 legal slot schedule fault");
      end
      #416;clk=0;cycles=cycles+1;compare_all();
    endtask
    task gap(input integer n);v=0;repeat(n) tick();endtask
    task reset_now;
      v=0;rst_n=0;#1;compare_all();
      if(ro || rf) $fatal(1,"BF16 asynchronous reset control");
      repeat(2) tick();rst_n=1;wr=0;rd=0;
    endtask
    function [15:0] value(input integer i);
      case(i%12)
        0:value=16'h3f80;1:value=16'hbf80;2:value=16'h0001;
        3:value=16'h0080;4:value=16'h8000;5:value=16'h7f7f;
        6:value=16'h7f80;7:value=16'h7fc1;8:value=16'h3f81;
        9:value=16'h3f00;10:value=16'h3380;default:value=16'h0000;
      endcase
    endfunction
    integer batch,r,s,l,reset_gap;
    initial begin
      reset_now();
      // All 16 physical lanes, 8 slots, chunk8 then the four rounding tree levels.
      // Mix zero/subnormal/ties/cancellation/overflow/Inf/NaN and high TG bits.
      for(batch=0;batch<3;batch=batch+1) begin
        for(r=0;r<8;r=r+1) begin
          for(s=0;s<8;s=s+1) begin
            v=1;slot=s;first=(r==0);last=(r==7);tree=7'h60+batch*8+s;final_i=s[0];
            for(l=0;l<16;l=l+1) begin
              if(batch==0) begin
                w[16*l+:16]=(l%2)?16'h3f81:16'hbf80;
                x[16*l+:16]=(r%2)?16'h3f00:16'h3f80;
              end else begin
                w[16*l+:16]=value(l+r+batch);x[16*l+:16]=value(2*l+s+r);
              end
            end
            tick();
          end
          gap(batch); // 8/9/10-cycle recurrence, observable bubble propagation.
        end
        gap(128);
      end
      if(outputs!=24 || wr!=rd || error_outputs==0 || finite_outputs!=8) $fatal(1,"BF16 drain/error coverage");
      // Cancel queued product, chain and reduction valid/tag activity by reset.
      for(reset_gap=5;reset_gap<=38;reset_gap=reset_gap+11) begin
        v=1;slot=0;first=1;last=1;tick();gap(reset_gap);reset_now();gap(128);
      end
      if(wr!=rd) $fatal(1,"BF16 reset stale output");
      $display("PASS bf16 cycles=%0d outputs=%0d error_outputs=%0d finite_outputs=%0d",cycles,outputs,error_outputs,finite_outputs);
      $finish;
    end
endmodule
