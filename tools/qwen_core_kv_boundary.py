"""Exact-epoch banked KV history and one-edge flush boundary; default off."""
def apply(text):
    marker='    parameter integer DEC_LA = 0'
    assert text.count(marker)==1
    text=text.replace(marker,'    parameter integer DEC_LA_KV_BANK = 0,\n'+marker,1)
    marker='    reg pr_kvwe_qq;'
    assert text.count(marker)==1
    text=text.replace(marker,marker+'''
    localparam integer PR_KV_BANKS=SW/8;
    reg [PR_KV_BANKS-1:0] pr_kv_any_q;
    reg pr_kv_idle_q;
    genvar prkb;
    generate for(prkb=0;prkb<PR_KV_BANKS;prkb=prkb+1) begin:g_kv_any
        always @(posedge clk or negedge rst_n)
            if(!rst_n) pr_kv_any_q[prkb]<=1'b0;
            else pr_kv_any_q[prkb]<=|kv_we[prkb*8 +: 8];
    end endgenerate
    always @(posedge clk or negedge rst_n)
        if(!rst_n) pr_kv_idle_q<=1'b0; else pr_kv_idle_q<=su_idle;
    wire pr_kv_any = (DEC_LA_KV_BANK!=0) ? (|pr_kv_any_q) : (|pr_kvwe_q);
''',1)
    old="pr_kvwe_qq <= |pr_kvwe_q;";assert text.count(old)==1;text=text.replace(old,'pr_kvwe_qq <= pr_kv_any;',1)
    old='(pr_kvd_q && !(|pr_kvwe_q) && !pr_kvwe_qq)';assert text.count(old)==1;text=text.replace(old,'(pr_kvd_q && !pr_kv_any && !pr_kvwe_qq)',1)
    old='    assign kv_write_flush = su_idle && !(|kv_we);';assert text.count(old)==1
    text=text.replace(old,"    assign kv_write_flush = (DEC_LA_KV_BANK!=0) ? (pr_kv_idle_q && !(|pr_kv_any_q)) : (su_idle && !(|kv_we));",1)
    return text
