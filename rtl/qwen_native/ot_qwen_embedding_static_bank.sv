`timescale 1ns/1ps
// Static successor. All issue cycles are compiler reservations; fault checks
// never stretch execution. Input at edge E, macro reads at E+1, capture E+3,
// response at E+4. Reserve an idle edge between reads (real two-edge capture).
module ot_qwen_embedding_static_bank #(
    parameter integer BANK_ID = 0,
    parameter integer SCALE = 0
)(
    input wire clk, rst_n, i_v,
    input wire [23:0] i_addr,
    output reg o_v,
    output reg [23:0] o_addr,
    output reg [511:0] o_data,
    output reg fault
);
    reg ce;
    reg [11:0] address;
    reg [3:0] vp;
    reg [23:0] ap[0:3];
    reg [511:0] capture;
    wire [265:0] lo, hi;
    wire bad_address = SCALE ? ((i_addr >= 151936) || ((i_addr >> 16) != BANK_ID))
                                    : ((i_addr >= 9723904) || ((i_addr >> 12) != BANK_ID));
`ifndef SYNTHESIS
    localparam MASK_LO = SCALE ? $sformatf("qembed_scale_b%0d", BANK_ID)
                               : $sformatf("qembed_code_b%0d_c0", BANK_ID);
    localparam MASK_HI = $sformatf("qembed_code_b%0d_c1", BANK_ID);
    string directory, filename;
    integer fd;
    initial begin
        if (!$value$plusargs("OT_ROM_DIR=%s", directory))
            $fatal(1,"static embedding requires +OT_ROM_DIR with resident physical masks");
        filename = {directory,"/",MASK_LO,".viamap.hex"};
        fd=$fopen(filename,"r");
        if (!fd) $fatal(1,"missing embedding mask %s",filename);
        $fclose(fd);
        if (!SCALE) begin
            filename={directory,"/",MASK_HI,".viamap.hex"};
            fd=$fopen(filename,"r");
            if (!fd) $fatal(1,"missing embedding mask %s",filename);
            $fclose(fd);
        end
    end
`endif
    ot_rom_4096x266_m8
`ifndef SYNTHESIS
        #(.INSTANCE(MASK_LO))
`endif
        u_lo(.clk(clk),.ce_in(ce),.addr_in(address),.rd_out(lo));
    generate if (SCALE == 0) begin:g_code
        ot_rom_4096x266_m8
`ifndef SYNTHESIS
            #(.INSTANCE(MASK_HI))
`endif
            u_hi(.clk(clk),.ce_in(ce),.addr_in(address),.rd_out(hi));
    end else begin:g_scale
        assign hi=266'd0;
    end endgenerate
    integer n;
    always @(posedge clk) begin
        address <= SCALE ? i_addr[15:4] : i_addr[11:0];
        ap[0] <= i_addr;
        for(n=1;n<4;n=n+1) ap[n] <= ap[n-1];
        if(vp[2]) capture <= {hi[255:0],lo[255:0]};
        o_addr <= ap[3];
        if(vp[3]) o_data <= SCALE ? {496'd0,capture[ap[3][3:0]*16+:16]} : capture;
    end
    always @(posedge clk or negedge rst_n) begin
        if(!rst_n) begin ce<=0;vp<=0;o_v<=0;fault<=0;end
        else begin
            ce <= i_v;
            vp <= {vp[2:0],i_v};
            o_v <= vp[3];
            if(i_v && (ce || bad_address)) fault<=1;
        end
    end
endmodule
