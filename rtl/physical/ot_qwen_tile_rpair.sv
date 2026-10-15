`timescale 1ns/1ps
// q13 r5 leaf 1 (2026-10-13): the hardened ROM pair-row leaf of the Qwen ROM die tile (hardened once, 5 a tile, one per
// code bank row): the row's two ot_rom_4096x266_m8 macros (column 0 / column 1) + ot_qwen_rpair_logic at the tile-die
// parameters (PWB 256, ROM_CAP2 1, ROM_CAPX 2).  Parameter-free top (the parent instantiates it by this fixed name).
// The leaf owns the ROM clock: macro clock pins hang on the leaf's own short tree.  Seam: flop -> flop on both sides
// ({ce_d, any_d, ad_d} from the parent's relay pre-stage; r_q = the row's relay register).
module ot_qwen_tile_rpair
`ifndef SYNTHESIS
    #(parameter integer ROM_TILE=-1, parameter integer ROM_BANK=-1)
`endif
(
    input  wire          clk,
    input  wire          rst_n,
    input  wire          ce_d,
    input  wire          any_d,
    input  wire [11:0]   ad_d,
    output wire [1023:0] r_q
);
`ifndef SYNTHESIS
    string image_dir, image_file;
    integer image_fd, col;
    initial begin
        if ($value$plusargs("OT_ROM_DIR=%s",image_dir)) begin
            if (ROM_TILE<0 || ROM_TILE>=768 || ROM_BANK<0 || ROM_BANK>=5)
                $fatal(1,"native rpair mask requires constant ROM_TILE[0..767]/ROM_BANK[0..4]");
            for(col=0;col<2;col=col+1) begin
                image_file=$sformatf("%s/qtile_t%0d_b%0d_c%0d.viamap.hex",image_dir,ROM_TILE,ROM_BANK,col);
                image_fd=$fopen(image_file,"r");
                if(image_fd==0) $fatal(1,"missing native tile ROM mask %s",image_file);
                $fclose(image_fd);
            end
        end else if(ROM_TILE>=0) $fatal(1,"bound native tile ROM requires +OT_ROM_DIR");
    end
`endif
    wire [25:0]  req_m;
    wire [265:0] rd0, rd1;
    ot_qwen_rpair_logic #(.PWB(256), .ROM_CAP2(1), .ROM_CAPX(2), .ROM_MUT(0), .MUT3(0), .MUT5(0)) u_lg (
        .clk(clk), .rst_n(rst_n), .ce_d(ce_d), .any_d(any_d), .ad_d(ad_d), .req_m(req_m),
        .rd({rd1[255:0], rd0[255:0]}), .r_q(r_q));
    ot_rom_4096x266_m8
`ifndef SYNTHESIS
        #(.INSTANCE(ROM_TILE<0 ? "" : $sformatf("qtile_t%0d_b%0d_c0",ROM_TILE,ROM_BANK)))
`endif
        u_rom0 (.clk(clk), .ce_in(req_m[12]), .addr_in(req_m[11:0]), .rd_out(rd0));
    ot_rom_4096x266_m8
`ifndef SYNTHESIS
        #(.INSTANCE(ROM_TILE<0 ? "" : $sformatf("qtile_t%0d_b%0d_c1",ROM_TILE,ROM_BANK)))
`endif
        u_rom1 (.clk(clk), .ce_in(req_m[25]), .addr_in(req_m[24:13]), .rd_out(rd1));
endmodule
