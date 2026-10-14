from pathlib import Path
import hashlib,json
root=Path(__file__).resolve().parents[2]
src=root/'rtl/v41rom/ot_v41_rom_elem_qx_pq_w10.sv';wrapper=root/'rtl/v41rom/ot_v41_rom_elem_q_qxpq_w10.sv'
out=root/'rtl/dsrom_sys/s81_ctrl/q_startup_candidate';out.mkdir(exist_ok=True)
s=src.read_text().replace('ot_v41_rom_elem_qx_pq_w10','ot_s81_qx_pq_startup_core').replace('ot_s81_q_lane_pair_native','ot_s81_q_lane_pair_startup_native')
s=s.replace('output wire         fault\n','output wire         fault,\n    output wire [1+5*NB:0] startup_rst_ack,\n    output wire startup_local_ready\n',1)
needle='    wire cg_en_g;'
inject='''    // Source-only distinct master: witnesses sample each actual reset/clock group.
    // Raw epoch clears witnesses even if a forwarded reset remains stale high.
    wire startup_keepalive;
    (* keep, dont_touch = "true" *) reg [1+5*NB:0] startup_s1, startup_s2;
    always @(posedge clk or negedge rst_n_pin) begin
        if (!rst_n_pin) begin startup_s1 <= '0; startup_s2 <= '0; end
        else begin startup_s1 <= startup_rst_ack; startup_s2 <= startup_s1; end
    end
`ifdef S81_Q_STARTUP_OMIT_LAST
    assign startup_local_ready = &{startup_s2[1+5*NB],startup_s2[5*NB-1:0]};
`else
    assign startup_local_ready = &startup_s2;
`endif
    assign startup_keepalive = !rst_n_pin || !startup_local_ready;
    ot_s81_q_reset_witness u_ack_raw (.clk(clk), .epoch_n(rst_n_pin), .local_n(rst_n), .ack(startup_rst_ack[0]));
    ot_s81_q_reset_witness u_ack_bx (.clk(gclk_bx), .epoch_n(rst_n_pin), .local_n(rst_n), .ack(startup_rst_ack[1]));
'''
assert needle in s;s=s.replace(needle,inject+needle,1)
s=s.replace('.en(cg_en_g), .gclk(gclk)', '.en(cg_en_g || startup_keepalive), .gclk(gclk)')
s=s.replace('.en(zc), .gclk(gclk_bx)', '.en(zc || startup_keepalive), .gclk(gclk_bx)')
s=s.replace('.en(native_en), .gclk(gclk_ma)', '.en(native_en || startup_keepalive), .gclk(gclk_ma)')
s=s.replace('.en(zc), .gclk(gclk_mb)', '.en(zc || startup_keepalive), .gclk(gclk_mb)')
needle='    if (QZ != 0) begin : g_mz'
inject='''    ot_s81_q_reset_witness u_ack_ma (.clk(gclk_ma), .epoch_n(rst_n_pin), .local_n(rst_m), .ack(startup_rst_ack[2+5*mb]));
    ot_s81_q_reset_witness u_ack_mc (.clk(gclk_mb), .epoch_n(rst_n_pin), .local_n(rst_mc), .ack(startup_rst_ack[3+5*mb]));
    ot_s81_q_reset_witness u_ack_mp (.clk(gclk_mb), .epoch_n(rst_n_pin), .local_n(rst_mp), .ack(startup_rst_ack[4+5*mb]));
    ot_s81_q_reset_witness u_ack_mt (.clk(gclk_mb), .epoch_n(rst_n_pin), .local_n(rst_mt), .ack(startup_rst_ack[5+5*mb]));
    ot_s81_q_reset_witness u_ack_m (.clk(gclk_mb), .epoch_n(rst_n_pin), .local_n(rst_m), .ack(startup_rst_ack[6+5*mb]));
'''
assert needle in s;s=s.replace(needle,inject+needle,1)
s+='''\nmodule ot_s81_q_reset_witness(input wire clk,epoch_n,local_n,output wire ack);
    (* keep, dont_touch = "true" *) reg [1:0] live;
    always @(posedge clk or negedge epoch_n or negedge local_n)
        if (!epoch_n || !local_n) live <= 2'b00;
        else live <= {live[0],1'b1};
    assign ack=live[1];
endmodule
'''
(out/'ot_s81_qx_pq_startup_core.sv').write_text(s)
w=wrapper.read_text().replace('ot_v41_rom_elem_q_qxpq_w10','ot_s81_q_elem_startup_native').replace('ot_v41_rom_elem_qx_pq_w10','ot_s81_qx_pq_startup_core')
w=w.replace('parameter integer QCG = 0','parameter integer QCG = 1',1)
w=w.replace('output wire         fault\n','output wire         fault,\n    output wire [1+5*NB:0] startup_rst_ack,\n    output wire startup_local_ready\n',1)
w=w.replace('.busy(busy), .fault(fault));','.busy(busy), .fault(fault), .startup_rst_ack(startup_rst_ack), .startup_local_ready(startup_local_ready));',1)
(out/'ot_s81_q_elem_startup_native.sv').write_text(w)
(out/'source_request.json').write_text(json.dumps({'historical_source_sha256':{str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [src,wrapper]},'distinct_new_masters':['ot_s81_q_elem_startup_native','ot_s81_qx_pq_startup_core'],'raw_epoch_port':'rst_n','actual_reset_witness_groups':['raw_rst_n','bx_rst_n','each_half_ma_rst_m','each_half_mb_rst_mc','each_half_mb_rst_mp','each_half_mb_rst_mt','each_half_mb_rst_m'],'ack_count_NB2':12,'witness_and_sync_added_FF_NB2':48,'keepalive':'actual individually synchronized reset/clock witnesses, no counter','operation_epochs_added':0,'physical_admission':False,'numerical_proof':'PENDING','source_clock_phase':None,'new_pin_views':None},indent=2)+'\n')
print('GENERATED_DISTINCT_STARTUP_VARIANT')
