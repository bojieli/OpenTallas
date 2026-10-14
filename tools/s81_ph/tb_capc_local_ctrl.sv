`timescale 1ps/1fs
module tb_capc_local_ctrl;
    bit wclk=0, rclk=0, wrst=0, rrst=0, wv=0, rrdy=0;
    logic [102:0] wd='0;
    integer phase=0, wc=0, rc=0, mm=0;
    initial begin
        wclk=0; #1; wclk=1;
        forever #416.6665 wclk=~wclk;
    end
    initial begin
        if (!$value$plusargs("PHASE=%d",phase)) phase=0;
        rclk=0; #(1+phase*277.77766675); rclk=1;
        forever #555.5553335 rclk=~rclk;
    end
    always @(negedge wclk) begin
        wc=wc+1;
        wrst <= wc>7 && wc%257<210;
        wv <= $urandom_range(0,3)!=0;
        wd <= {32'($urandom),32'($urandom),32'($urandom),7'(wc)};
    end
    always @(negedge rclk) begin
        rc=rc+1;
        rrst <= rc>11 && rc%193<151;
        rrdy <= $urandom_range(0,3)!=0;
    end
    for (genvar cfg=0;cfg<2;cfg++) begin:g_cfg
        localparam integer W=cfg==0?103:64, DEPTH=cfg==0?4:2, LAG=cfg==0?1:0;
        wire old_wr,new_wr,old_rv,new_rv,old_wl,new_wl,old_rl,new_rl;
        wire [W-1:0] old_data,new_data;
        wire def_wr,def_rv,def_wl,def_rl;
        wire [W-1:0] def_data;
        ot_ratio_cdc_fifo_orig #(.W(W),.DEPTH(DEPTH),.LAG(LAG)) old_fifo
          (.wclk(wclk),.wrst_n(wrst),.w_v(wv),.w_rdy(old_wr),.w_d(wd[W-1:0]),
           .rclk(rclk),.rrst_n(rrst),.r_v(old_rv),.r_rdy(rrdy),.r_d(old_data),.w_live(old_wl),.r_live(old_rl));
        ot_ratio_cdc_fifo #(.W(W),.DEPTH(DEPTH),.LAG(LAG),.LOCAL_CTRL(1)) new_fifo
          (.wclk(wclk),.wrst_n(wrst),.w_v(wv),.w_rdy(new_wr),.w_d(wd[W-1:0]),
           .rclk(rclk),.rrst_n(rrst),.r_v(new_rv),.r_rdy(rrdy),.r_d(new_data),.w_live(new_wl),.r_live(new_rl));
        ot_ratio_cdc_fifo #(.W(W),.DEPTH(DEPTH),.LAG(LAG)) default_fifo
          (.wclk(wclk),.wrst_n(wrst),.w_v(wv),.w_rdy(def_wr),.w_d(wd[W-1:0]),
           .rclk(rclk),.rrst_n(rrst),.r_v(def_rv),.r_rdy(rrdy),.r_d(def_data),.w_live(def_wl),.r_live(def_rl));
        always @(posedge wclk) begin
            #0.002;
            if(wc>12 && ({old_wr,old_wl} !== {new_wr,new_wl} || {old_wr,old_wl} !== {def_wr,def_wl})) begin
                mm++; if(mm<5)$display("CTRL_MISMATCH phase=%0d cfg=%0d wcycle=%0d",phase,cfg,wc);
            end
        end
        always @(posedge rclk) begin
            #0.002;
            if(rc>12 && ({old_rv,old_rl,old_data} !== {new_rv,new_rl,new_data} || {old_rv,old_rl,old_data} !== {def_rv,def_rl,def_data})) begin
                mm++; if(mm<5)$display("CTRL_MISMATCH phase=%0d cfg=%0d rcycle=%0d",phase,cfg,rc);
            end
        end
    end
    initial begin
        #5000000;
        $display("SS_CTRL_EQ %s phase=%0d w_edges=%0d r_edges=%0d mismatches=%0d",mm==0?"PASS":"FAIL",phase,wc,rc,mm);
        $finish;
    end
endmodule
