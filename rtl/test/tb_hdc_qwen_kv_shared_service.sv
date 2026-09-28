`timescale 1ns/1ps
// Exact read-after-write across the existing FP8 sector bridge, page adapter,
// and the same finite-credit PC arbiter used by the four-stack service.
module tb_hdc_qwen_kv_shared_service;
    localparam PCS=128, NC=6, AW=32, TAGW=25, CTAGW=32, PTAGW=35;
    localparam KV_CLIENT=5, PC=1, BASE=139054720;
    localparam CAW=NC*AW, CTW=NC*CTAGW, CDW=NC*256;
    localparam PAW=PCS*CTAGW, PDW=PCS*256;
    reg clk=0, rst_n=0;
    always #5 clk=~clk;
    reg log_req_v=0, log_req_we=0;
    reg [23:0] log_req_addr=0;
    reg [3:0] log_req_len=1;
    reg [TAGW-1:0] log_req_tag=25'h12345;
    reg [127:0] log_req_data={16{8'haa}};
    wire log_req_ready;
    wire [PCS-1:0] log_rsp_v;
    reg [PCS-1:0] log_rsp_ready='1;
    wire [PCS*TAGW-1:0] log_rsp_tag;
    wire [PCS*3-1:0] log_rsp_beat;
    wire [PCS*128-1:0] log_rsp_data;
    wire bridge_req_v, bridge_req_we, bridge_req_rdy, bridge_fault;
    wire [23:0] bridge_req_sector;
    wire [3:0] bridge_req_len;
    wire [TAGW-1:0] bridge_req_tag;
    wire [255:0] bridge_req_data;
    wire [PCS-1:0] bridge_rsp_v, bridge_rsp_rdy;
    wire [PCS*TAGW-1:0] bridge_rsp_tag;
    wire [PCS*256-1:0] bridge_rsp_data;
    wire [PCS-1:0] pc_req_v, pc_req_we, pc_rsp_rdy;
    wire [PCS*AW-1:0] pc_req_addr;
    wire [PCS*CTAGW-1:0] pc_req_tag;
    wire [PCS*256-1:0] pc_req_data;
    wire [PCS-1:0] pc_req_rdy, pc_rsp_v, pc_wr_done_v;
    wire [PCS*CTAGW-1:0] pc_rsp_tag, pc_wr_done_tag;
    wire [PCS*256-1:0] pc_rsp_data;
    wire adapter_fault;
    ot_hdc_qwen_hbm_sector_bridge #(.AW(24),.NPC(PCS),.TAGW(TAGW)) u_bridge (
        .clk(clk),.rst_n(rst_n),.log_req_v(log_req_v),.log_req_ready(log_req_ready),
        .log_req_we(log_req_we),.log_req_addr(log_req_addr),.log_req_len(log_req_len),
        .log_req_tag(log_req_tag),.log_req_data(log_req_data),
        .log_rsp_v(log_rsp_v),.log_rsp_ready(log_rsp_ready),
        .log_rsp_tag(log_rsp_tag),.log_rsp_beat(log_rsp_beat),.log_rsp_data(log_rsp_data),
        .phys_req_v(bridge_req_v),.phys_req_ready(bridge_req_rdy),
        .phys_req_we(bridge_req_we),.phys_req_sector(bridge_req_sector),
        .phys_req_len(bridge_req_len),.phys_req_tag(bridge_req_tag),
        .phys_req_data(bridge_req_data),.phys_rsp_v(bridge_rsp_v),
        .phys_rsp_ready(bridge_rsp_rdy),.phys_rsp_tag(bridge_rsp_tag),
        .phys_rsp_beat({PCS*3{1'b0}}),.phys_rsp_data(bridge_rsp_data),.fault(bridge_fault));
    ot_hdc_qwen_kv_pc_adapter u_adapter (
        .clk(clk),.rst_n(rst_n),.page_valid(1'b1),.kv_base_sector(AW'(BASE)),
        .bridge_req_v(bridge_req_v),.bridge_req_rdy(bridge_req_rdy),
        .bridge_req_we(bridge_req_we),.bridge_req_sector(bridge_req_sector),
        .bridge_req_tag(bridge_req_tag),.bridge_req_data(bridge_req_data),
        .bridge_rsp_v(bridge_rsp_v),.bridge_rsp_rdy(bridge_rsp_rdy),
        .bridge_rsp_tag(bridge_rsp_tag),.bridge_rsp_data(bridge_rsp_data),
        .pc_req_v(pc_req_v),.pc_req_rdy(pc_req_rdy),.pc_req_we(pc_req_we),
        .pc_req_addr(pc_req_addr),.pc_req_tag(pc_req_tag),.pc_req_data(pc_req_data),
        .pc_rsp_v(pc_rsp_v),.pc_rsp_rdy(pc_rsp_rdy),.pc_rsp_tag(pc_rsp_tag),
        .pc_rsp_data(pc_rsp_data),.pc_wr_done_v(pc_wr_done_v),
        .pc_wr_done_tag(pc_wr_done_tag),.fault(adapter_fault));
    wire [NC-1:0] c_req_v, c_req_we, c_rsp_rdy;
    wire [NC*AW-1:0] c_req_addr;
    wire [NC*CTAGW-1:0] c_req_tag;
    wire [NC*256-1:0] c_req_data;
    wire [NC-1:0] c_req_rdy, c_rsp_v, c_wr_done_v;
    wire [NC*CTAGW-1:0] c_rsp_tag, c_wr_done_tag;
    wire [NC*256-1:0] c_rsp_data;
    wire p_req_v,p_req_we,p_rsp_rdy,svc_fault;
    reg p_rsp_v=0,p_wr_done_v=0;
    wire [AW-1:0] p_req_addr;
    wire [PTAGW-1:0] p_req_tag;
    wire [255:0] p_req_data;
    reg [PTAGW-1:0] p_rsp_tag=0,p_wr_done_tag=0;
    reg [255:0] p_rsp_data=0;
    ot_hdc_qwen_pc_service #(.NC(NC),.AW(AW),.CTAGW(CTAGW)) u_service (
        .clk(clk),.rst_n(rst_n),.c_req_v(c_req_v),.c_req_rdy(c_req_rdy),
        .c_req_we(c_req_we),.c_req_addr(c_req_addr),.c_req_tag(c_req_tag),
        .c_req_data(c_req_data),.c_rsp_v(c_rsp_v),.c_rsp_rdy(c_rsp_rdy),
        .c_rsp_tag(c_rsp_tag),.c_rsp_data(c_rsp_data),
        .c_wr_done_v(c_wr_done_v),.c_wr_done_tag(c_wr_done_tag),
        .p_req_v(p_req_v),.p_req_rdy(1'b1),.p_req_we(p_req_we),
        .p_req_addr(p_req_addr),.p_req_tag(p_req_tag),.p_req_data(p_req_data),
        .p_rsp_v(p_rsp_v),.p_rsp_rdy(p_rsp_rdy),.p_rsp_tag(p_rsp_tag),
        .p_rsp_data(p_rsp_data),.p_wr_done_v(p_wr_done_v),
        .p_wr_done_tag(p_wr_done_tag),.fault(svc_fault));
    assign c_req_v=(NC'(pc_req_v[PC]) << KV_CLIENT);
    assign c_req_we=(NC'(pc_req_we[PC]) << KV_CLIENT);
    assign c_req_addr=(CAW'(pc_req_addr[PC*AW +: AW]) << (KV_CLIENT*AW));
    assign c_req_tag=(CTW'(pc_req_tag[PC*CTAGW +: CTAGW]) << (KV_CLIENT*CTAGW));
    assign c_req_data=(CDW'(pc_req_data[PC*256 +: 256]) << (KV_CLIENT*256));
    assign pc_req_rdy=(PCS'(c_req_rdy[KV_CLIENT]) << PC);
    assign c_rsp_rdy=(NC'(pc_rsp_rdy[PC]) << KV_CLIENT);
    assign pc_rsp_v=(PCS'(c_rsp_v[KV_CLIENT]) << PC);
    assign pc_rsp_tag=(PAW'(c_rsp_tag[KV_CLIENT*CTAGW +: CTAGW]) << (PC*CTAGW));
    assign pc_rsp_data=(PDW'(c_rsp_data[KV_CLIENT*256 +: 256]) << (PC*256));
    assign pc_wr_done_v=(PCS'(c_wr_done_v[KV_CLIENT]) << PC);
    assign pc_wr_done_tag=(PAW'(c_wr_done_tag[KV_CLIENT*CTAGW +: CTAGW]) << (PC*CTAGW));
    reg [255:0] mem={{16{8'h44}},{16{8'h33}}};
    reg [255:0] pending_write;
    reg [PTAGW-1:0] pending_tag;
    integer write_delay=0, accepted_writes=0, accepted_reads=0, cycles=0;
    always @(posedge clk) if (rst_n) begin
        cycles<=cycles+1;
        p_rsp_v<=0; p_wr_done_v<=0;
        if (p_req_v) begin
            if (p_req_addr!==BASE+1) $fatal(1,"wrong shared PC address got=%0d want=%0d",p_req_addr,BASE+1);
            if (p_req_we) begin
                if (write_delay!=0) $fatal(1,"duplicate write while pending");
                pending_write<=p_req_data; pending_tag<=p_req_tag;
                write_delay<=5; accepted_writes<=accepted_writes+1;
            end else begin
                p_rsp_v<=1; p_rsp_tag<=p_req_tag; p_rsp_data<=mem;
                accepted_reads<=accepted_reads+1;
            end
        end
        if (write_delay>1) write_delay<=write_delay-1;
        if (write_delay==1) begin
            mem<=pending_write; p_wr_done_v<=1;
            p_wr_done_tag<=pending_tag; write_delay<=0;
        end
        if (svc_fault || adapter_fault || bridge_fault) $fatal(1,"shared KV fault");
        if (cycles>100) $fatal(1,"shared KV test timeout");
    end
    task automatic request(input bit we);
        @(negedge clk);
        wait(log_req_ready);
        log_req_v=1; log_req_we=we; log_req_addr=2;
        @(negedge clk); log_req_v=0;
    endtask
    initial begin
        repeat(3) @(negedge clk); rst_n=1;
        request(1);
        wait(log_req_ready);
        request(0);
        wait(log_rsp_v[0]);
        #1;
        if (log_rsp_data[0 +: 128] !== {16{8'haa}} ||
            mem[255:128] !== {16{8'h44}} ||
            accepted_writes!=1 || accepted_reads!=2)
            $fatal(1,"shared read-after-write byte or transaction mismatch");
        $display("PASS Qwen shared KV RMW read-after-write, one write and two reads");
        $finish;
    end
endmodule
