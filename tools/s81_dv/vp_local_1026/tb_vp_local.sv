`timescale 1ps/1ps
module tb_vp_local;
  reg clk=0; always begin #416 clk=1; #417 clk=0; end
  reg rst_n=0,c_v=0,sw_v=0;
  reg [159:0] c_d=0; reg [9:0] sw_a=0; reg [7:0] sw_m=0; reg [255:0] sw_d=0;
  integer cyc=0,bad=0,i,j,k,r,mut=0,nw=49,stray=0;
  reg [143:0] wexp[0:48]; integer pin_at[0:48],commit_at[0:48],ncommit[0:48],cpin[0:2];
  integer hw_n=0,wl_n=0,lo_n=0,hw_last=-1,wl_last=-1,lo_last=-1;
  reg [15:0] cargs[0:2];
  wire lo_v,hw_v,hw_hf,wl_v,f_vp;
  wire [255:0] lo_d,hw_d,wl_d; wire [2:0] hw_j,wl_i;
  ot_s81sl_vp #(.ML(7),.AL(6),.HPL(33),.CS_HI_D(0),.CS_HI_GS(0),.CS_HO_D(0),.CS_HO_GS(0),.CS_H_G(4),.HQX(0)) u_vp(
    .clk(clk),.rst_n(rst_n),.c_v(c_v),.c_d(c_d),.sw_v(sw_v),.sw_a(sw_a),.sw_m(sw_m),.sw_d(sw_d),
    .cw_v(2'd0),.cw_a(24'd0),.cw_d(64'd0),.lo_v(lo_v),.lo_d(lo_d),
    .x_rv(1'b0),.x_ra(10'd0),.x_wv(1'b0),.x_wa(10'd0),.x_wm(8'd0),.x_wd(256'd0),
    .hw_v(hw_v),.hw_j(hw_j),.hw_hf(hw_hf),.hw_d(hw_d),.hq_v(1'b0),.hq_d(256'd0),
    .wl_v(wl_v),.wl_i(wl_i),.wl_d(wl_d),.fault(f_vp));
    // ---------------------------------------------------------------- expected leaf-store rows (image; unwritten = 0)
    function automatic [127:0] row_exp(input integer row);
        integer q; begin
            row_exp = 128'd0;
            for (q = 0; q < nw; q = q + 1) if (wexp[q][143:128] == row) row_exp = wexp[q][127:0];
        end
    endfunction
    function automatic integer row_idx(input integer row);
        integer q; begin
            row_idx = -1;
            for (q = 0; q < nw; q = q + 1) if (wexp[q][143:128] == row) row_idx = q;
        end
    endfunction

    // ---------------------------------------------------------------- monitors (sample at the posedge, as rdpair_leaf4)
    always @(posedge clk) begin
        cyc = cyc + 1;
        if (rst_n) begin
            for (k = 0; k < 2; k = k + 1)
                if ((k == 0 && u_vp.u_b0.w_ce_in) || (k == 1 && u_vp.u_b1.w_ce_in)) begin
                    r = 2 * ((k == 0) ? u_vp.u_b0.w_addr_in : u_vp.u_b1.w_addr_in) + k;
                    j = row_idx(r);
                    if (j < 0) begin stray = stray + 1; $display("STRAY commit row %0d cyc %0d", r, cyc); end
                    else begin
                        commit_at[j] = cyc; ncommit[j] = ncommit[j] + 1;
                        if (((k == 0) ? u_vp.u_b0.w_mask_in : u_vp.u_b1.w_mask_in) !== {128{1'b1}} ||
                            ((k == 0) ? u_vp.u_b0.wd_in : u_vp.u_b1.wd_in) !== wexp[j][127:0]) begin
                            bad = bad + 1; $display("COMMIT DATA MISMATCH row %0d", r);
                        end
                    end
                end
            #2;
            if (hw_v) begin
                hw_n = hw_n + 1; hw_last = cyc; r = cargs[0] + 2 * (2 * hw_j + hw_hf);
                if (hw_d !== {row_exp(r + 1), row_exp(r)}) begin bad = bad + 1; $display("HLOAD DATA MISMATCH rows %0d/%0d", r, r + 1); end
            end
            if (wl_v) begin
                wl_n = wl_n + 1; wl_last = cyc; r = cargs[1] + 2 * wl_i;
                if (wl_d !== {row_exp(r + 1), row_exp(r)}) begin bad = bad + 1; $display("GAIN DATA MISMATCH rows %0d/%0d", r, r + 1); end
            end
            if (lo_v) begin
                lo_n = lo_n + 1; lo_last = cyc; r = cargs[2];
                if (lo_d[127:0] !== row_exp(r)) begin bad = bad + 1; $display("RDOUT DATA MISMATCH rows %0d/%0d", r, r + 1); end
            end
        end
    end
    task tick(input integer n); repeat (n) begin @(posedge clk); #5; end endtask
    task write_row(input integer idx);
      begin
        sw_v=1; sw_a=wexp[idx][137:128]; sw_m=8'h0f;
        sw_d={128'd0,wexp[idx][127:0]};
        if(mut && idx==13) sw_d[5]=~sw_d[5];
        pin_at[idx]=cyc;
        tick(1); sw_v=0; tick(1);
      end
    endtask
    task command(input integer idx,input integer opcode,input integer addr,input integer n);
      begin
        c_v=1; c_d=0; c_d[3:0]=opcode; c_d[13:4]=addr; c_d[31:24]=n;
        cpin[idx]=cyc; tick(1); c_v=0;
      end
    endtask
  initial begin
    void'($value$plusargs("MUT=%d",mut));
    $readmemh("expect.memh",wexp); cargs[0]=0;cargs[1]=64;cargs[2]=1008;
    for(i=0;i<49;i=i+1)begin pin_at[i]=-1;commit_at[i]=-1;ncommit[i]=0;end
    tick(20);rst_n=1;tick(20);
    for(i=0;i<49;i=i+1)write_row(i);
    tick(8);command(0,3,0,0);tick(45);command(1,1,64,0);tick(30);command(2,6,1008,1);tick(30);
    for(i=0;i<49;i=i+1)begin
      if(ncommit[i]!=1)bad=bad+1;
      $display("AGE COMMIT row=%0d event=%0d commit=%0d age=%0d",wexp[i][143:128],pin_at[i],commit_at[i],commit_at[i]-pin_at[i]);
    end
    if(hw_n!=16||wl_n!=8||lo_n!=1||stray||f_vp)bad=bad+1;
    $display("AGE HLOAD event=%0d last=%0d age=%0d",cpin[0],hw_last,hw_last-cpin[0]);
    $display("AGE GAIN event=%0d last=%0d age=%0d",cpin[1],wl_last,wl_last-cpin[1]);
    $display("AGE RDOUT event=%0d last=%0d age=%0d",cpin[2],lo_last,lo_last-cpin[2]);
    $display("VP_LOCAL counts commits49 hw=%0d wl=%0d lo=%0d fault=%b bad=%0d mutant=%0d",hw_n,wl_n,lo_n,f_vp,bad,mut);
    if(bad)$fatal(1,"VP_LOCAL FAIL");$display("VP_LOCAL PASS");$finish;
  end
  initial begin tick(500);$fatal(1,"VP_LOCAL finite limit");end
endmodule
