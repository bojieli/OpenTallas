module source_core_clock #(parameter VM_OWNED_LEASE=1,DEC_LA_PINREG=0)(input clk,rst_n_i,me_mem_ok,vm_me_lease,issue_intent,output vm_me_wanted,effective,engine_clk,pending,take,output[31:0]accepts);
localparam ME_STALL=1,ME_IDLE_GATE=1,DEC_LA_MEIF=1,DEC_LA_ISSUE_FB=1;
localparam S_RUN=2;wire[1:0]st=S_RUN,d_unit=1;wire nx_v=1;
wire me_ready,me_idle,me_go,me_en,me_clk_en;wire[15:0]me_progress;
wire me_ready_pin=1,me_idle_pin=0;wire[15:0]me_progress_pin=0;wire me_go_pin;
wire kv_ok=1,kvd_v=0,su_go=0,su_idle=1;wire[1:0]dst=0;
wire fb_run=issue_intent,fb_is_me=1,fb_cond_me=1,fb_kvg_me=1,fb_wg_me=1,issue=0;
    reg pr_kvok_q, pr_kvdv_q, pr_su_kv, pr_mmo_q;
    always @(posedge clk or negedge rst_n_i)
        if (!rst_n_i) begin pr_kvok_q <= 1'b0; pr_kvdv_q <= 1'b0; pr_su_kv <= 1'b0; pr_mmo_q <= 1'b0; end
        else begin
            pr_kvok_q <= kv_ok; pr_kvdv_q <= kvd_v; pr_mmo_q <= me_mem_ok;
            if (su_go && dst == 2'd2) pr_su_kv <= 1'b1; else if (su_idle) pr_su_kv <= 1'b0;
        end
    wire kv_ok_i = (DEC_LA_PINREG == 0) ? kv_ok :
                   (DEC_LA_PINREG == 2) ? pr_kvok_q : (pr_kvok_q && !pr_kvdv_q && !pr_su_kv);
    wire me_mem_ok_i = (DEC_LA_PINREG == 0) ? me_mem_ok : pr_mmo_q;
    wire me_wake = (st == S_RUN) && nx_v && (d_unit == 2'd1);
    assign vm_me_wanted = !rst_n_i || (((ME_STALL == 0) || me_mem_ok_i) &&
                              ((ME_IDLE_GATE == 0) || !me_idle || me_wake));
    // Reset keeps the native ME reset path enabled; normal acceptance is leased.
    assign me_en = !rst_n_i || (vm_me_wanted &&
                       ((VM_OWNED_LEASE == 0) || vm_me_lease));
    assign me_clk_en = me_en;
    wire me_clk;
    generate if (VM_OWNED_LEASE != 0 || ME_STALL != 0 || ME_IDLE_GATE != 0) begin : g_me_cg
        ot_hdc_cg u_me_cg (.clk(clk), .en(me_en), .gclk(me_clk));
    end else begin : g_me_clk
        assign me_clk = clk;
    end endgenerate
    (* keep *) wire fb_me_go = fb_run && fb_is_me && fb_cond_me && me_ready && me_en && fb_kvg_me && fb_wg_me;
    assign me_go = (DEC_LA_ISSUE_FB != 0) ? fb_me_go : (issue && (d_unit == 2'd1));
    reg me_gop, me_tk_d, me_rdy_q, me_idl_q;
    reg [15:0] me_prg_q;
    always @(posedge clk or negedge rst_n_i)
        if (!rst_n_i) begin me_gop <= 1'b0; me_tk_d <= 1'b0; me_rdy_q <= 1'b0; me_idl_q <= 1'b1; me_prg_q <= 16'd0; end
        else begin
            me_gop <= me_go ? 1'b1 : (me_en ? 1'b0 : me_gop);       // raised until the ME's enabled clock takes it
            me_tk_d <= me_gop && me_en;                              // the acceptance edge
            me_rdy_q <= me_ready_pin; me_idl_q <= me_idle_pin; me_prg_q <= me_progress_pin;
        end
    wire me_ifhold = (DEC_LA_MEIF == 2) ? 1'b0 : (me_gop || me_tk_d);   // 2 = NEGATIVE CONTROL: stale status unmasked
    generate if (DEC_LA_MEIF != 0) begin : g_meif
        assign me_go_pin = me_gop;
        assign me_ready = me_rdy_q && !me_ifhold;
        assign me_idle = me_idl_q && !me_ifhold;
        assign me_progress = me_ifhold ? 16'd0 : me_prg_q;
    end else begin : g_nomeif
        assign me_go_pin = me_go;
        assign me_ready = me_ready_pin;
        assign me_idle = me_idle_pin;
        assign me_progress = me_progress_pin;
    end endgenerate

assign effective=me_en;assign engine_clk=me_clk;assign pending=me_gop;assign take=me_tk_d;
reg[31:0]accepted=0;assign accepts=accepted;
always @(posedge me_clk)if(!rst_n_i)accepted<=0;else if(me_go_pin)accepted<=accepted+1;
endmodule
