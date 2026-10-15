`timescale 1ns/1ps
`default_nettype none
// Host-only configuration overlay before the real ot_hgi_loader_cp AXI port.
// C/D CP and E MTP addresses pass through. F00 selects {PC10,quadrant2};
// F04 appends one of eight32b programme pieces (low first), then emits cfg_we;
// F08 sets {limit11,base10}, F0c sets loops16 for the selected quadrant.
// The REAL existing loader->CP LCP[71] doorbell launches all four programmes.
// No host request participates in per-cycle on-chip execution.
module ot_vms_calendar_host_static (
    input wire clk,rst_n,
    input wire s_awvalid,output wire s_awready,input wire [11:0] s_awaddr,
    input wire s_wvalid,output wire s_wready,input wire [31:0] s_wdata,input wire [3:0] s_wstrb,
    output wire s_bvalid,input wire s_bready,
    input wire s_arvalid,output wire s_arready,input wire [11:0] s_araddr,
    output wire s_rvalid,input wire s_rready,output wire [31:0] s_rdata,
    output wire c_awvalid,input wire c_awready,output wire [11:0] c_awaddr,
    output wire c_wvalid,input wire c_wready,output wire [31:0] c_wdata,output wire [3:0] c_wstrb,
    input wire c_bvalid,output wire c_bready,
    output wire c_arvalid,input wire c_arready,output wire [11:0] c_araddr,
    input wire c_rvalid,output wire c_rready,input wire [31:0] c_rdata,
    input wire lcp_doorbell,
    input wire [3:0] program_active,program_done,program_fault,
    output reg [3:0] cfg_we,
    output reg [39:0] cfg_addr,
    output reg [1023:0] cfg_data,
    output reg [3:0] start_v,
    output reg [39:0] start_base,
    output reg [43:0] start_limit,
    output reg [63:0] start_loops,
    // F20/F24/F28/F2c configure independently hardened engine programmes.
    // Their local target collars consume this registered broadcast frame.
    output reg ext_cfg_v,
    output reg [7:0] ext_target,
    output reg [11:0] ext_cfg_addr,
    output reg [255:0] ext_cfg_data,
    output reg ext_desc_v,
    output reg [11:0] ext_base,
    output reg [12:0] ext_limit,
    output reg [15:0] ext_loops,
    output reg ext_launch_v,
    output reg fault
);
    wire local_w=s_awaddr[11:8]==4'hf;
    wire local_r=s_araddr[11:8]==4'hf;
    reg bv,rv;
    reg [31:0] rdata;
    wire wt=local_w && s_awvalid && s_wvalid && !bv;
    wire rt=local_r && s_arvalid && !rv;
    assign s_awready=local_w?wt:c_awready;
    assign s_wready=local_w?wt:c_wready;
    assign c_awvalid=s_awvalid && !local_w;assign c_awaddr=s_awaddr;
    assign c_wvalid=s_wvalid && !local_w;assign c_wdata=s_wdata;assign c_wstrb=s_wstrb;
    assign s_bvalid=bv|c_bvalid;assign c_bready=s_bready && !bv;
    assign c_arvalid=s_arvalid && !local_r;assign c_araddr=s_araddr;
    assign s_arready=local_r?rt:c_arready;
    assign s_rvalid=rv|c_rvalid;assign s_rdata=rv?rdata:c_rdata;
    assign c_rready=s_rready && !rv;
    reg [1:0] selected;
    reg [9:0] program_pc;
    reg [2:0] piece;
    reg [223:0] assembly;
    reg [3:0] descriptor_valid;
    reg [39:0] bases;
    reg [43:0] limits;
    reg [63:0] loops;
    reg [7:0] engine_target;
    reg [11:0] engine_pc,engine_base;
    reg [12:0] engine_limit;
    reg [2:0] engine_piece;
    reg [223:0] engine_assembly;
    reg engine_range_valid;
    always @(posedge clk or negedge rst_n)
        if(!rst_n)begin
            bv<=0;rv<=0;rdata<=0;selected<=0;program_pc<=0;piece<=0;
            cfg_we<=0;start_v<=0;descriptor_valid<=0;fault<=0;
            ext_cfg_v<=0;ext_desc_v<=0;ext_launch_v<=0;
            engine_target<=0;engine_pc<=0;engine_piece<=0;engine_range_valid<=0;
        end else begin
            cfg_we<=0;start_v<=0;
            ext_cfg_v<=0;ext_desc_v<=0;ext_launch_v<=0;
            if(bv && s_bready)bv<=0;
            if(rv && s_rready)rv<=0;
            if(wt)begin
                bv<=1;
                if(s_wstrb!=4'hf || (|program_active))fault<=1;
                else case(s_awaddr[7:0])
                    8'h00:begin
                        if(piece!=0)fault<=1;
                        else begin selected<=s_wdata[1:0];program_pc<=s_wdata[11:2];end
                    end
                    8'h04:begin
                        if(piece<7)assembly[piece*32+:32]<=s_wdata;
                        piece<=piece+1;
                        if(piece==7)begin
                            cfg_we[selected]<=1;
                            cfg_addr[selected*10+:10]<=program_pc;
                            cfg_data[selected*256+:256]<={s_wdata,assembly[223:0]};
                            program_pc<=program_pc+1;
                        end
                    end
                    8'h08:begin bases[selected*10+:10]<=s_wdata[9:0];limits[selected*11+:11]<=s_wdata[20:10];descriptor_valid[selected]<=0;end
                    8'h0c:begin
                        if(s_wdata[15:0]==0 || limits[selected*11+:11]<={1'b0,bases[selected*10+:10]} || limits[selected*11+:11]>11'd1024)fault<=1;
                        else begin loops[selected*16+:16]<=s_wdata[15:0];descriptor_valid[selected]<=1;end
                    end
                    8'h20:begin
                        if(engine_piece!=0 || s_wdata[7:0]<16)fault<=1;
                        else begin engine_target<=s_wdata[7:0];engine_pc<=s_wdata[19:8];engine_range_valid<=0;end
                    end
                    8'h24:begin
                        if(engine_target<16)fault<=1;
                        else begin
                            if(engine_piece<7)engine_assembly[engine_piece*32+:32]<=s_wdata;
                            engine_piece<=engine_piece+1;
                            if(engine_piece==7)begin
                                ext_cfg_v<=1;ext_target<=engine_target;
                                ext_cfg_addr<=engine_pc;ext_cfg_data<={s_wdata,engine_assembly[223:0]};
                                engine_pc<=engine_pc+1;
                            end
                        end
                    end
                    8'h28:begin engine_base<=s_wdata[11:0];engine_limit<=s_wdata[24:12];engine_range_valid<=1;end
                    8'h2c:begin
                        if(!engine_range_valid || engine_target<16 || s_wdata[15:0]==0 ||
                           engine_limit<={1'b0,engine_base} || engine_limit>13'd4096)fault<=1;
                        else begin
                            ext_desc_v<=1;ext_target<=engine_target;ext_base<=engine_base;
                            ext_limit<=engine_limit;ext_loops<=s_wdata[15:0];
                        end
                    end
                    default:fault<=1;
                endcase
            end
            if(rt)begin
                rv<=1;
                rdata<={15'd0,fault,descriptor_valid,program_fault,program_done,program_active};
            end
            if(lcp_doorbell)begin
                if(descriptor_valid!=4'hf || (|program_active) || (|program_fault) || fault || piece!=0 || engine_piece!=0 || wt)fault<=1;
                else begin
                    start_v<=4'hf;start_base<=bases;start_limit<=limits;start_loops<=loops;
                    ext_launch_v<=1;
                end
            end
        end
endmodule
`default_nettype wire
