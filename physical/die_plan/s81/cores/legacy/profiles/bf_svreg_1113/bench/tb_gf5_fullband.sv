module tb_gf5_fullband;
    timeunit 1ps; timeprecision 1fs;
    reg clk=0, rst_n=0;
    always #416.5 clk=~clk;
    reg [5:0] sa_r=0,sb_r=0;
    reg [223:0] sa_d=0,sb_d=0;
    reg [13:0] we=0;
    reg c_go=0,c_fw=0,c_l=0;
    reg [2:0] c_bn=0; reg [4:0] c_lvn=0;
    reg re=0;reg [3:0] ra=0;
    reg [1:0] bw_e=0;reg [3:0] bw_a=0;reg [255:0] bw_d=0;
    reg g_go=0;reg [5:0] g_hit=0;reg [41:0] g_a=0;
    wire gv,gf,gl,gg,gflt,nv,nf,nl,ng,nflt;wire [244:0] gd,nd;
    gold_dsdv_gunit_l1f u_gold(
      .clk(clk),.rst_n(rst_n),.sa_r(sa_r),.sa_d(sa_d),.sb_r(sb_r),.sb_d(sb_d),.we(we),
      .c_go(c_go),.c_fw(c_fw),.c_l(c_l),.c_bn(c_bn),.c_lvn(c_lvn),
      .re(re),.ra(ra),.bw_e(bw_e),.bw_a(bw_a),.bw_d(bw_d),
      .g_go(g_go),.g_hit(g_hit),.g_a(g_a),
      .o_v(gv),.o_f(gf),.o_l(gl),.o_g(gg),.o_d(gd),.o_flt(gflt));
    dsdv_gunit_l1f u_dut(
      .clk(clk),.rst_n(rst_n),.sa_r(sa_r),.sa_d(sa_d),.sb_r(sb_r),.sb_d(sb_d),.we(we),
      .c_go(c_go),.c_fw(c_fw),.c_l(c_l),.c_bn(c_bn),.c_lvn(c_lvn),
      .re(re),.ra(ra),.bw_e(bw_e),.bw_a(bw_a),.bw_d(bw_d),
      .g_go(g_go),.g_hit(g_hit),.g_a(g_a),
      .o_v(nv),.o_f(nf),.o_l(nl),.o_g(ng),.o_d(nd),.o_flt(nflt));

    reg [539:0] svprev=0;
    reg [1314:0] aprev=0;
    reg [249:0] prev=0;
    reg [511:0] biasprev=0;
    reg [47:0] vfprev=0;reg [2:0] sfprev=0;
    integer age=0,cyc=0,bad=0,checks=0,selects=0,gathers=0,acmp=0,forwards=0,biaschanges=0,biasrw=0;
    task automatic mismatch(input string kind);
      begin bad=bad+1;if(bad<=8)$display("GF5 MISMATCH kind=%s cycle=%0d",kind,cyc);end
    endtask
    always @(posedge clk) begin
      cyc=cyc+1;
      if(!rst_n) age=0;else age=age+1;
      #1;
      if(age>24) begin
        checks=checks+1;
        if({u_dut.sv_hi,u_dut.sv_lo,u_dut.ctl_hi,u_dut.ctl_lo}!==svprev) mismatch("SV_CTL");
        if({nv,nf,nl}!==prev[249:247]) mismatch("SELECT_FLAGS");
        if(ng!==gg) mismatch("GATHER_VALID");
        if(u_dut.sf0!==sfprev)mismatch("A_FLAGS");
        if({u_dut.vf_hi,u_dut.vf_lo}!==vfprev)mismatch("A_ERROR_VALID");
        if(nv) begin selects=selects+1;if(nd!==prev[244:0])mismatch("SELECT_DATA");end
        if(ng) begin gathers=gathers+1;if(nd!==gd)mismatch("GATHER_DATA");end
        if(nflt||gflt)mismatch("FAULT_ON_LEGAL_STREAM");
        if(aprev[1314])begin
          acmp=acmp+1;
          if({u_dut.s1b,u_dut.s1a,u_dut.s0b,u_dut.s0a}!==aprev[1311:0])mismatch("A_RECORDS");
        end
        if((|u_gold.u_f.whf)&&(|u_gold.u_f.cfwc))forwards=forwards+1;
        if(u_gold.u_alo.u_a.bwe&&u_gold.u_alo.u_a.rdq)biasrw=biasrw+1;
        if({u_gold.u_ahi.u_a.s_bias,u_gold.u_alo.u_a.s_bias}!==biasprev)biaschanges=biaschanges+1;
      end
      vfprev={u_gold.vf_hi,u_gold.vf_lo};sfprev=u_gold.sf0;
      svprev={u_gold.sv_hi,u_gold.sv_lo,u_gold.ctl_hi,u_gold.ctl_lo};
      aprev={u_gold.sf0[0],2'b00,u_gold.s1b,u_gold.s1a,u_gold.s0b,u_gold.s0a};
      prev={gv,gf,gl,gg,gflt,gd};
      biasprev={u_gold.u_ahi.u_a.s_bias,u_gold.u_alo.u_a.s_bias};
    end

    task automatic tick;begin @(negedge clk);end endtask
    task automatic quiet;
      begin we=0;c_go=0;c_fw=0;c_l=0;g_go=0;g_hit=0;re=0;bw_e=0;end
    endtask
    integer epoch,row,lane,j,burst,beat,seed=11;
    reg [31:0] rng=32'h13579bdf;
    function automatic [31:0] finite_word(input integer salt);
      reg [31:0] x;
      begin x=32'(salt)*32'h45d9f3b;finite_word=32'h3f000000|(x&32'h007fffff);end
    endfunction
    initial begin
      if($value$plusargs("SEED=%d",seed))rng=32'(seed);
      for(epoch=0;epoch<3;epoch=epoch+1)begin
        quiet;rst_n=0;repeat(8)tick;rst_n=1;repeat(28)tick;
        // Real bias SRAM writes; both halves see different, changing lane/row patterns.
        for(row=0;row<16;row=row+1)begin
          bw_e=3;bw_a=4'(row);
          for(lane=0;lane<8;lane=lane+1)
            bw_d[32*lane+:32]=32'h3e800000+32'((row*8+(lane^row))*524288);
          tick;
        end
        bw_e=0;repeat(5)tick;
        // Initialise all SC address rows through actual registered write/forward decoders.
        for(row=0;row<64;row=row+1)begin
          we=14'h3fff;sa_r=6'(row);sb_r=6'(row);
          for(j=0;j<7;j=j+1)begin
            sa_d[32*j+:32]=finite_word(row*7+j+epoch*997+seed);
            sb_d[32*j+:32]=sa_d[32*j+:32];
          end
          tick;
        end
        quiet;repeat(8)tick;
        // Consecutive select beats, changing SRAM rows and lane-valid masks.
        // Sparse SC writes while c_fw is active exercise real same-edge forwarding.
        for(burst=0;burst<8;burst=burst+1)begin
          for(beat=0;beat<7;beat=beat+1)begin
            c_go=1;c_fw=(beat==0);c_l=(beat==6);c_bn=3'(beat);
            c_lvn=5'(1+((burst+epoch*7)%16));
            re=1;ra=4'((beat+1+burst)&15);
            bw_e=(beat==3 && (burst%2)==0)?3:0;bw_a=ra;
            for(lane=0;lane<8;lane=lane+1)bw_d[32*lane+:32]=finite_word(burst*113+lane+epoch*17);
            we=(beat==0)?14'h3fff:14'b0;sa_r=6'(burst%3);sb_r=sa_r;
            for(j=0;j<7;j=j+1)begin
              sa_d[32*j+:32]=finite_word(burst*29+beat*7+j+epoch*577+seed);
              sb_d[32*j+:32]=sa_d[32*j+:32];
            end
            tick;
          end
          quiet;repeat(3)tick;
        end
        quiet;repeat(48)tick;
        for(row=0;row<6;row=row+1)begin
          g_go=1;g_hit=6'h3f;
          for(j=0;j<6;j=j+1)g_a[7*j+:7]=7'((row*19+j*13+epoch)%112);
          tick;
        end
        quiet;repeat(40)tick;
      end
      if(checks<400||selects<80||gathers<12||acmp<80||forwards==0||biaschanges<20||biasrw==0)begin
        bad=bad+1;$display("GF5 COVERAGE_FAIL");
      end
      $display("GF5_FULLBAND checks=%0d select=%0d gather=%0d Achecks=%0d forwards=%0d biaschanges=%0d biasrw=%0d mismatches=%0d",
                checks,selects,gathers,acmp,forwards,biaschanges,biasrw,bad);
      if(bad==0)$display("GF5_FULLBAND PASS");else $display("GF5_FULLBAND FAIL");
      $finish;
    end
endmodule
