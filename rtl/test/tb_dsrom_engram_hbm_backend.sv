`timescale 1ns/1ps
module tb_dsrom_engram_hbm_backend(input wire clk);
    localparam integer PCBASE=2929688;
    reg rst_n=0,iv=0,valid=1;reg [31:0] addr=0;reg [255:0] data=0;
    reg [1919:0] pc_base=0,pc_limit=0;
    wire credit,ready,fault;wire [21823:0] rq;wire [63:0] wd,pr;
    integer cycle=0,credits=8,sent=0,writes=0,completed=0,p,n,row,index,localatom,pc,stack,globalatom,mode=0;
    reg marker=0;reg [575:0] seen=0;reg [340:0] word;
    function automatic integer inverse(input integer p,input integer a);
        integer t,bank;
        begin t=a>>2;bank=(p^t^(t>>5))&31;inverse=(t<<7)|(bank<<2)|(a&3);end
    endfunction
    wire [17791:0] rd;
    wire [63:0] pc_want,pc_held,pc_claim,pc_release,pc_available;
    wire runtime_phase,hq_credit,hr_v;wire [2:0] hr_tag;wire [3:0] hr_idx;wire [255:0] hr_data;
    reg hq_v=0;reg [30:0] hq_atom=0;reg [2:0] hq_tag=0;
    integer runtime_cycles=0,read_sent=0,read_got=0,read_requests=0,read_credits=0,claims=0,releases=0;
    reg [53:0] read_seen=0;
    assign pc_available=~pc_held & ((runtime_cycles>200) ? 64'hffffffffffffffff : 64'hfffffffffffffffe);
    ot_dsrom_engram_hbm_backend #(.EXPECT_SECTORS(576)) dut(
        .ck(clk),.rst_n(rst_n),.aperture_valid(valid),.pc_base(pc_base),.pc_limit(pc_limit),
        .boot_v(iv),.boot_addr(addr),.boot_data(data),.boot_credit(credit),
        .hq_v(hq_v),.hq_atom(hq_atom),.hq_tag(hq_tag),.hq_credit(hq_credit),
        .pc_available(pc_available),.pc_want(pc_want),.pc_held(pc_held),.pc_claim(pc_claim),.pc_release(pc_release),
        .rq(rq),.rd_engram(rd),.wd_boot(runtime_phase ? 64'd0 : wd),
        .hr_v(hr_v),.hr_tag(hr_tag),.hr_idx(hr_idx),.hr_data(hr_data),.ready(ready),.fault(fault),.runtime_phase(runtime_phase));
    genvar st,j;
    generate for(st=0;st<2;st=st+1) begin:g_stack
        wire [31:0] v,we;wire [959:0] a;wire [127:0] len;wire [543:0] tags;wire [8191:0] d;wire [1023:0] strb;wire [31:0] rv;wire [543:0] rt;wire [127:0] rb;wire [8191:0] rdata;
        for(j=0;j<32;j=j+1) begin:g_pc
            assign {d[j*256+:256],strb[j*32+:32],tags[j*17+:17],len[j*4+:4],a[j*30+:30],we[j],v[j]}=rq[(st*32+j)*341+:341];
            assign rd[st*8896+j*256+:256]=rdata[j*256+:256];
            assign rd[st*8896+8192+j*17+:17]=rt[j*17+:17];
            assign rd[st*8896+8736+j*4+:4]=rb[j*4+:4];
            assign rd[st*8896+8864+j]=rv[j];
        end
        ot_hdc_v41x_idx_hbm #(.NPC(32),.AW(30),.TAGW(17),.LENW(4),.BEATW(4),.CLK_PS(833),.MEM_MODE(0),.MEM_WORDS(1024)) phy(
            .clk(clk),.rst_n(rst_n),.req_v(v),.req_rdy(pr[st*32+:32]),.req_addr(a),.req_len(len),.req_tag(tags),
            .req_we(we),.req_wdata(d),.req_wstrb(strb),.wr_done(wd[st*32+:32]),.rsp_v(rv),.rsp_rdy(32'hffffffff),.rsp_tag(rt),.rsp_beat(rb),.rsp_data(rdata));
    end endgenerate
    initial begin
        if($value$plusargs("MODE=%d",mode)) begin end
        for(p=0;p<64;p=p+1) begin pc_base[p*30+:30]=PCBASE;pc_limit[p*30+:30]=PCBASE+9;end
        if(mode==1) pc_limit[0+:30]=PCBASE+8;
    end
    always @(posedge clk) begin
        cycle=cycle+1;rst_n<=cycle>=10;iv<=0;hq_v<=0;
        if(rst_n) begin
            credits=credits+credit-iv;
            if(cycle>=20 && credits>0 && !marker) begin
                iv<=1;
                if(sent<576) begin addr<=32'hc0000000+sent;data<=sent;sent=sent+1;end
                else begin addr<=32'hffffffff;data<={190'd0,2'b11,32'd0,32'd576};marker=1;end
            end
            if((mode==1 || mode==2) && fault) begin $display("ENGRAM_BACKEND NEG mode=%0d caught",mode);$finish;end
            if(mode==2 && cycle==20) begin hq_v<=1;hq_atom<=0;hq_tag<=0;end
            if(mode==0 && fault) $fatal(1,"canonical backend unexpected fault");
            if(cycle>50000) $fatal(1,"canonical boot drain");
            for(p=0;p<64;p=p+1) begin
                if(wd[p]) completed=completed+1;
                word=rq[p*341+:341];
                if(word[0] && word[1]) begin
                    n=word[116:85];row=n/9;index=n%9;
                    pc=(row%2)*32+(row/2)%32;globalatom=inverse(p%32,PCBASE+index);
                    if(!pr[p] || word[1]!=1 || word[35:32]!=1 || n>=576 || seen[n] || p!=pc || word[31:2]!=globalatom) $fatal(1,"canonical boot actual request/count/PC");
                    seen[n]=1;writes=writes+1;
                end
            end
            if(ready && runtime_cycles==0) begin
                if(writes!=576 || completed!=576 || seen!={576{1'b1}}) $fatal(1,"marker before actual write completion");
                for(n=0;n<576;n=n+1) begin
                    row=n/9;index=n%9;stack=row%2;pc=(row/2)%32;globalatom=inverse(pc,PCBASE+index);
                    // This minimum first-row-perPC image has no aliases in
                    // the model's1024-sector backing array; all576 sectors
                    // remain distinct within their two separate stacks.
                    if(stack==0) begin
                        if(g_stack[0].phy.mem[globalatom%1024]!==n) $fatal(1,"SW backing payload mismatch");
                    end else if(g_stack[1].phy.mem[globalatom%1024]!==n) $fatal(1,"SE backing payload mismatch");
                end
            end
            if(ready) begin
                runtime_cycles=runtime_cycles+1;
                if(runtime_cycles>=20 && read_sent<6) begin
                    hq_v<=1;hq_atom<=read_sent*9;hq_tag<=read_sent;read_sent=read_sent+1;
                end
                if(hq_credit) read_credits=read_credits+1;
                for(p=0;p<64;p=p+1) begin
                    if(pc_claim[p]) begin
                        if(!pc_held[p]) $fatal(1,"claim without held row");claims=claims+1;
                    end
                    if(pc_release[p]) begin
                        if(pc_held[p]) $fatal(1,"release before drain");releases=releases+1;
                    end
                    word=rq[p*341+:341];
                    if(word[0] && !word[1]) begin
                        if(runtime_cycles<200) $fatal(1,"request before PC lease grant");
                        if(!pc_held[p] || !pr[p] || word[35:32]<1 || word[35:32]>4) $fatal(1,"runtime request owner/count");
                        read_requests=read_requests+1;
                    end
                end
                if(hr_v) begin
                    if(hr_tag>=6 || hr_idx>=9 || read_seen[hr_tag*9+hr_idx] || hr_data!==hr_tag*9+hr_idx) $fatal(1,"boot/runtime payload or identity mismatch");
                    read_seen[hr_tag*9+hr_idx]=1;read_got=read_got+1;
                end
                if(read_got==54 && runtime_cycles%16==0) begin
                    if(read_requests!=18 || read_credits!=6 || claims!=6 || releases!=6 || pc_held!=0 || read_seen!={54{1'b1}}) $fatal(1,"backend credit/lease completion");
                    $display("ENGRAM_BACKEND PASS boot=576 read_rows=6 read_atoms=54 bursts=18 actual_PHY=1 lease_wait=200 claims=6 releases=6 cycles=%0d",cycle);$finish;
                end
            end
        end
    end
endmodule
