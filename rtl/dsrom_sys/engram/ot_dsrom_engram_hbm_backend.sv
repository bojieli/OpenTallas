`timescale 1ns/1ps
// Canonical class11 bootstrap -> row read service. Controller rq is a CLIENT
// face: production SW sharing must supply real pc_available grants and route
// only Engram-owned rd back here. Boot owns the controllers exclusively before
// admission. No KV/controller ownership mux or deployed aperture is invented.
module ot_dsrom_engram_hbm_backend #(parameter integer EXPECT_SECTORS=1)(
    input wire ck,rst_n,input wire aperture_valid,
    input wire [1919:0] pc_base,pc_limit,
    input wire boot_v,input wire [31:0] boot_addr,input wire [255:0] boot_data,output wire boot_credit,
    input wire hq_v,input wire [30:0] hq_atom,input wire [2:0] hq_tag,output reg hq_credit,
    input wire [63:0] pc_available,output wire [63:0] pc_want,pc_held,pc_claim,pc_release,
    output wire [21823:0] rq,input wire [17791:0] rd_engram,input wire [63:0] wd_boot,
    output reg hr_v,output reg [2:0] hr_tag,output reg [3:0] hr_idx,output reg [255:0] hr_data,
    output wire ready,fault,output wire runtime_phase
);
    wire [21823:0] boot_rq,read_rq;
    wire boot_ready,boot_fault,read_fault,read_hr_v,read_credit;
    wire [2:0] read_hr_tag;wire [3:0] read_hr_idx;wire [255:0] read_hr_data;
    reg protocol_fault;
    reg [339:0] out_fields;reg [63:0] out_v;
    assign runtime_phase=boot_ready;
    assign fault=boot_fault|read_fault|protocol_fault;
    assign ready=boot_ready&&!fault;
    ot_dsrom_engram_boot_path #(.ROWSTRIPE(1),.CANONICAL(1),.APERTURE(1),.EXPECT_SECTORS(EXPECT_SECTORS)) u_boot(
        .ck(ck),.rst_n(rst_n),.aperture_valid(aperture_valid),.pc_base(pc_base),.pc_limit(pc_limit),
        .i_v(boot_v),.i_addr(boot_addr),.i_d(boot_data),.i_cred(boot_credit),.rq(boot_rq),.wd(wd_boot),.ready(boot_ready),.fault(boot_fault));
    ot_dsrom_engram_rowstripe_service #(.CANONICAL(1),.APERTURE(1),.USE_LEASE(1)) u_read(
        .ck(ck),.rst_n(rst_n&&boot_ready),.aperture_valid(aperture_valid),.pc_base(pc_base),.pc_limit(pc_limit),
        .pc_available(pc_available),.pc_want(pc_want),.pc_held(pc_held),.pc_claim(pc_claim),.pc_release(pc_release),
        .hq_v(hq_v),.hq_atom(hq_atom),.hq_tag(hq_tag),.hq_cred(read_credit),.rq(read_rq),.rd(rd_engram),
        .hr_v(read_hr_v),.hr_tag(read_hr_tag),.hr_idx(read_hr_idx),.hr_d(read_hr_data),.fault(read_fault));
    genvar p;
    generate for(p=0;p<64;p=p+1) begin:g_rq
        assign rq[p*341+:341]={out_fields,out_v[p]};
    end endgenerate
    integer j;
    always @(posedge ck or negedge rst_n) begin
        if(!rst_n) begin protocol_fault<=0;out_v<=0;out_fields<=0;hq_credit<=0;hr_v<=0;hr_tag<=0;hr_idx<=0;hr_data<=0;end
        else begin
            if(hq_v && !boot_ready) protocol_fault<=1;
            hq_credit<=read_credit&&!fault;
            hr_v<=read_hr_v&&!fault;
            hr_tag<=read_hr_tag;hr_idx<=read_hr_idx;hr_data<=read_hr_data;
            out_fields<=boot_ready ? read_rq[340:1] : boot_rq[340:1];
            for(j=0;j<64;j=j+1) out_v[j]<=!fault && (boot_ready ? read_rq[j*341] : boot_rq[j*341]);
        end
    end
endmodule
