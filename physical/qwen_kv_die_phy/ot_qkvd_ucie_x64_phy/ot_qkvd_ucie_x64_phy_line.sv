`timescale 1ns/1ps
// FUNCTIONAL LINE VIEW of the ot_qkvd_ucie_x64_phy hard macro for bound-die verify / simulation (TOK-SCHED 10-25).
// The KV plan declares the macro's die line pins as bump ports (kv3_sys_c ucie_rom bump_ports link_v/link_flit/far_v/
// far_flit, prepare_native_mission.py), so the bound sys_c binds them; the physical abstract (_bb.v / LEF) keeps only the
// FDI pins (codex 49f8568805 projects the line proxies onto the physical FDI for kits).  This view exposes the line pins
// and is the existing simulation model (LAT 5 / UP 16, the qfd_link_slots.sv behaviour); never synthesised.
module ot_qkvd_ucie_x64_phy #(parameter integer PW = 583) (
    input  wire          clk,
    input  wire          rst_n,
    output wire          tx_up,
    input  wire          tx_v,
    input  wire [PW-1:0] tx_flit,
    output wire          rx_v,
    output wire [PW-1:0] rx_flit,
    output wire          link_v,
    output wire [PW-1:0] link_flit,
    input  wire          far_v,
    input  wire [PW-1:0] far_flit
);
    ot_qkvd_ucie_x64_phy_model #(.LAT(5), .UP(16), .FW(PW)) u_m (.clk(clk), .rst_n(rst_n), .tx_up(tx_up), .tx_v(tx_v),
        .tx_flit(tx_flit), .rx_v(rx_v), .rx_flit(rx_flit), .link_v(link_v), .link_flit(link_flit), .far_v(far_v),
        .far_flit(far_flit));
endmodule
