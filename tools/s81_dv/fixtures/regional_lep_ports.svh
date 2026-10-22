// Source commit: f6f2fcc48
// Full source SHA256: 980c3c70832cdc01024d4649616d3a3dc76e7a510c8b2e64801e2e0b4ec29f9d
// Exact module declaration excerpt, used only for the port-clock contract test.
`timescale 1ns/1ps
`default_nettype none
// S81-LEPAB regional successor. Three explicit same-frequency roots; every
// C<->A/B bus is a fixed D4/K2 landing, not an asynchronous FIFO. New master:
// never bind a legacy lep_mu_ab view onto this module. See committed MODEL.json.
module ot_s81sl_lep_mu_ab_regional #(
    parameter integer DT = 512, parameter integer DR = 12, parameter integer CRED = 12, parameter integer SRAM = 1,
    parameter integer NB = 80, parameter integer RX_SRAM = 1, parameter integer IN_PIPE = 1, parameter integer NATIVE32 = 1
) (
    input  wire            clk,
    input  wire            clk_a,
    input  wire            clk_b,
    input  wire            rst_n,
    input  wire [1103:0]   ro,
    output wire [1103:0]   ri,
    output wire            lo0_v, input wire lo0_r, output wire [552:0] lo0_d,
    output wire            lo1_v, input wire lo1_r, output wire [552:0] lo1_d,
    input  wire            li0_v, output wire li0_r, input wire [552:0] li0_d,
    input  wire            li1_v, output wire li1_r, input wire [552:0] li1_d,
    output wire [1:0]      rxv,
    input  wire            sl_f,
    input  wire [2:0]      l0_f,
    input  wire [2:0]      l1_f,
    input  wire [33:0]     mu_c,
    output wire [31:0]     mu_rt,
    output wire            ml_wv,
    output wire [1103:0]   ml_wd,
    input  wire            ml_rv,
    input  wire [1103:0]   ml_rd,
    input  wire            ml_f,
    output wire            lo2_v, input wire lo2_r, output wire [552:0] lo2_d,
    output wire            lo3_v, input wire lo3_r, output wire [552:0] lo3_d,
    input  wire            li2_v, output wire li2_r, input wire [552:0] li2_d,
    input  wire            li3_v, output wire li3_r, input wire [552:0] li3_d,
    output wire [1:0]      rxvb,
    input  wire [2:0]      l2_f,
    input  wire [2:0]      l3_f,
    output wire            fault
);
