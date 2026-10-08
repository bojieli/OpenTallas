def bridge_lines(d,flush):
    return f'''
wire [63:0] kvw{d}=(bs{d}==2)?(64'h1<<((ns{d}-1)%64)):64'd0;
wire [63:0] kvw_input{d}=kvw{d};
wire drain{d},brfault{d},rv{d},wv{d};wire[23:0] rs{d},ws{d};wire[255:0] wd{d};
reg response{d}=0;reg[255:0] memory{d}=0,rd{d}=0;integer writes{d}=0;
wire mrdy{d}=!STALL || cycle%5!=0;
wire mwdy{d}=!STALL || cycle%7!=0;
wire[23:0] addr{d}=24'd4096+(ns{d}-1);
ot_hdc_qwen_kv_vector_bridge #(.SW(64),.AW(24),.FIFO_BEATS(16),.MAX_KV_OP_ELEMS(64),.V0_ELEMENT(4096)) br{d}(
.clk(clk),.rst_n(rst_n),.core_we(kvw{d}),.core_addr({{64{{addr{d}}}}}),.core_data({{64{{32'h3f800000}}}}),.drained(drain{d}),
.fl_v(1'b0),.fl_word_addr(24'd0),.fl_word_data(128'd0),.flush({flush}),
.mem_r_v(rv{d}),.mem_r_ready(mrdy{d}),.mem_r_sector(rs{d}),.mem_r_resp_v(response{d}),.mem_r_resp_data(rd{d}),
.mem_w_v(wv{d}),.mem_w_ready(mwdy{d}),.mem_w_sector(ws{d}),.mem_w_data(wd{d}),.fault(brfault{d}));
always @(posedge clk) begin
 if(!rst_n) begin response{d}<=0;memory{d}<=0;rd{d}<=0;writes{d}<=0;end
 else begin
 response{d}<=rv{d}&&mrdy{d};if(rv{d}&&mrdy{d}) begin if(rs{d}!=128) $fatal(1,"read sector");rd{d}<=memory{d};end
 if(wv{d}&&mwdy{d}) begin if(ws{d}!=128) $fatal(1,"write sector");memory{d}<=wd{d};writes{d}<=writes{d}+1;end
 if(brfault{d}) $fatal(1,"bridge fault");
 end
end
'''.splitlines()
