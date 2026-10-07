`timescale 1ns/1ps
// Actual r21 transport graph only. Cold POR; no warm reset or endpoint credit/protection claim.
module ot_qwen_link_graph_r22 #(parameter integer ENABLE=0) (
 input wire link_por_n,
 input wire [3:0] hub_tx_clk, strip_tx_clk,
 input wire [2111:0] hub_tx_data, strip_tx_data,
 output wire [3:0] hub_rx_clk, strip_rx_clk,
 output wire [2111:0] hub_rx_data, strip_rx_data
);
 wire [527:0] e0_down, e0_up;
 wire [0:0] e0_dclk, e0_uclk;
 wire [527:0] e1_down, e1_up;
 wire [0:0] e1_dclk, e1_uclk;
 wire [527:0] e2_down, e2_up;
 wire [0:0] e2_dclk, e2_uclk;
 wire [527:0] e3_down, e3_up;
 wire [0:0] e3_dclk, e3_uclk;
 wire [527:0] e4_down, e4_up;
 wire [0:0] e4_dclk, e4_uclk;
 wire [527:0] e5_down, e5_up;
 wire [0:0] e5_dclk, e5_uclk;
 wire [527:0] e6_down, e6_up;
 wire [0:0] e6_dclk, e6_uclk;
 wire [527:0] e7_down, e7_up;
 wire [0:0] e7_dclk, e7_uclk;
 wire [527:0] e8_down, e8_up;
 wire [0:0] e8_dclk, e8_uclk;
 wire [527:0] e9_down, e9_up;
 wire [0:0] e9_dclk, e9_uclk;
 wire [527:0] e10_down, e10_up;
 wire [0:0] e10_dclk, e10_uclk;
 wire [527:0] e11_down, e11_up;
 wire [0:0] e11_dclk, e11_uclk;
 wire [527:0] e12_down, e12_up;
 wire [0:0] e12_dclk, e12_uclk;
 wire [527:0] e13_down, e13_up;
 wire [0:0] e13_dclk, e13_uclk;
 wire [527:0] e14_down, e14_up;
 wire [0:0] e14_dclk, e14_uclk;
 wire [527:0] e15_down, e15_up;
 wire [0:0] e15_dclk, e15_uclk;
 wire [527:0] e16_down, e16_up;
 wire [0:0] e16_dclk, e16_uclk;
 wire [527:0] e17_down, e17_up;
 wire [0:0] e17_dclk, e17_uclk;
 wire [527:0] e18_down, e18_up;
 wire [0:0] e18_dclk, e18_uclk;
 wire [527:0] e19_down, e19_up;
 wire [0:0] e19_dclk, e19_uclk;
 wire [527:0] e20_down, e20_up;
 wire [0:0] e20_dclk, e20_uclk;
 wire [527:0] e21_down, e21_up;
 wire [0:0] e21_dclk, e21_uclk;
 wire [527:0] e22_down, e22_up;
 wire [0:0] e22_dclk, e22_uclk;
 wire [527:0] e23_down, e23_up;
 wire [0:0] e23_dclk, e23_uclk;
 wire [527:0] e24_down, e24_up;
 wire [0:0] e24_dclk, e24_uclk;
 wire [527:0] e25_down, e25_up;
 wire [0:0] e25_dclk, e25_uclk;
 wire [527:0] e26_down, e26_up;
 wire [0:0] e26_dclk, e26_uclk;
 wire [527:0] e27_down, e27_up;
 wire [0:0] e27_dclk, e27_uclk;
 wire [527:0] e28_down, e28_up;
 wire [0:0] e28_dclk, e28_uclk;
 wire [527:0] e29_down, e29_up;
 wire [0:0] e29_dclk, e29_uclk;
 wire [527:0] e30_down, e30_up;
 wire [0:0] e30_dclk, e30_uclk;
 wire [527:0] e31_down, e31_up;
 wire [0:0] e31_dclk, e31_uclk;
 wire [527:0] e32_down, e32_up;
 wire [0:0] e32_dclk, e32_uclk;
 wire [527:0] e33_down, e33_up;
 wire [0:0] e33_dclk, e33_uclk;
 wire [527:0] e34_down, e34_up;
 wire [0:0] e34_dclk, e34_uclk;
 wire [527:0] e35_down, e35_up;
 wire [0:0] e35_dclk, e35_uclk;
 wire [527:0] e36_down, e36_up;
 wire [0:0] e36_dclk, e36_uclk;
 wire [527:0] e37_down, e37_up;
 wire [0:0] e37_dclk, e37_uclk;
 wire [527:0] e38_down, e38_up;
 wire [0:0] e38_dclk, e38_uclk;
 assign e38_up=strip_tx_data[1056+:528];
 assign e38_uclk=strip_tx_clk[2];
 assign strip_rx_data[1056+:528]=e38_down;
 assign strip_rx_clk[2]=e38_dclk;
 wire [527:0] e39_down, e39_up;
 wire [0:0] e39_dclk, e39_uclk;
 wire [527:0] e40_down, e40_up;
 wire [0:0] e40_dclk, e40_uclk;
 wire [527:0] e41_down, e41_up;
 wire [0:0] e41_dclk, e41_uclk;
 wire [527:0] e42_down, e42_up;
 wire [0:0] e42_dclk, e42_uclk;
 wire [527:0] e43_down, e43_up;
 wire [0:0] e43_dclk, e43_uclk;
 wire [527:0] e44_down, e44_up;
 wire [0:0] e44_dclk, e44_uclk;
 wire [527:0] e45_down, e45_up;
 wire [0:0] e45_dclk, e45_uclk;
 wire [527:0] e46_down, e46_up;
 wire [0:0] e46_dclk, e46_uclk;
 wire [527:0] e47_down, e47_up;
 wire [0:0] e47_dclk, e47_uclk;
 wire [527:0] e48_down, e48_up;
 wire [0:0] e48_dclk, e48_uclk;
 wire [527:0] e49_down, e49_up;
 wire [0:0] e49_dclk, e49_uclk;
 wire [527:0] e50_down, e50_up;
 wire [0:0] e50_dclk, e50_uclk;
 wire [527:0] e51_down, e51_up;
 wire [0:0] e51_dclk, e51_uclk;
 wire [527:0] e52_down, e52_up;
 wire [0:0] e52_dclk, e52_uclk;
 wire [527:0] e53_down, e53_up;
 wire [0:0] e53_dclk, e53_uclk;
 wire [527:0] e54_down, e54_up;
 wire [0:0] e54_dclk, e54_uclk;
 wire [527:0] e55_down, e55_up;
 wire [0:0] e55_dclk, e55_uclk;
 wire [527:0] e56_down, e56_up;
 wire [0:0] e56_dclk, e56_uclk;
 wire [527:0] e57_down, e57_up;
 wire [0:0] e57_dclk, e57_uclk;
 wire [527:0] e58_down, e58_up;
 wire [0:0] e58_dclk, e58_uclk;
 wire [527:0] e59_down, e59_up;
 wire [0:0] e59_dclk, e59_uclk;
 wire [527:0] e60_down, e60_up;
 wire [0:0] e60_dclk, e60_uclk;
 wire [527:0] e61_down, e61_up;
 wire [0:0] e61_dclk, e61_uclk;
 wire [527:0] e62_down, e62_up;
 wire [0:0] e62_dclk, e62_uclk;
 wire [527:0] e63_down, e63_up;
 wire [0:0] e63_dclk, e63_uclk;
 wire [527:0] e64_down, e64_up;
 wire [0:0] e64_dclk, e64_uclk;
 wire [527:0] e65_down, e65_up;
 wire [0:0] e65_dclk, e65_uclk;
 wire [527:0] e66_down, e66_up;
 wire [0:0] e66_dclk, e66_uclk;
 wire [527:0] e67_down, e67_up;
 wire [0:0] e67_dclk, e67_uclk;
 wire [527:0] e68_down, e68_up;
 wire [0:0] e68_dclk, e68_uclk;
 wire [527:0] e69_down, e69_up;
 wire [0:0] e69_dclk, e69_uclk;
 wire [527:0] e70_down, e70_up;
 wire [0:0] e70_dclk, e70_uclk;
 wire [527:0] e71_down, e71_up;
 wire [0:0] e71_dclk, e71_uclk;
 wire [527:0] e72_down, e72_up;
 wire [0:0] e72_dclk, e72_uclk;
 wire [527:0] e73_down, e73_up;
 wire [0:0] e73_dclk, e73_uclk;
 wire [527:0] e74_down, e74_up;
 wire [0:0] e74_dclk, e74_uclk;
 wire [527:0] e75_down, e75_up;
 wire [0:0] e75_dclk, e75_uclk;
 wire [527:0] e76_down, e76_up;
 wire [0:0] e76_dclk, e76_uclk;
 wire [527:0] e77_down, e77_up;
 wire [0:0] e77_dclk, e77_uclk;
 assign e77_up=strip_tx_data[1584+:528];
 assign e77_uclk=strip_tx_clk[3];
 assign strip_rx_data[1584+:528]=e77_down;
 assign strip_rx_clk[3]=e77_dclk;
 wire [1055:0] e78_down, e78_up;
 wire [1:0] e78_dclk, e78_uclk;
 assign e78_down[0+:528]=hub_tx_data[0+:528];
 assign e78_dclk[0]=hub_tx_clk[0];
 assign hub_rx_data[0+:528]=e78_up[0+:528];
 assign hub_rx_clk[0]=e78_uclk[0];
 assign e78_down[528+:528]=hub_tx_data[528+:528];
 assign e78_dclk[1]=hub_tx_clk[1];
 assign hub_rx_data[528+:528]=e78_up[528+:528];
 assign hub_rx_clk[1]=e78_uclk[1];
 wire [1055:0] e79_down, e79_up;
 wire [1:0] e79_dclk, e79_uclk;
 wire [1055:0] e80_down, e80_up;
 wire [1:0] e80_dclk, e80_uclk;
 wire [1055:0] e81_down, e81_up;
 wire [1:0] e81_dclk, e81_uclk;
 wire [1055:0] e82_down, e82_up;
 wire [1:0] e82_dclk, e82_uclk;
 wire [1055:0] e83_down, e83_up;
 wire [1:0] e83_dclk, e83_uclk;
 wire [1055:0] e84_down, e84_up;
 wire [1:0] e84_dclk, e84_uclk;
 wire [1055:0] e85_down, e85_up;
 wire [1:0] e85_dclk, e85_uclk;
 wire [1055:0] e86_down, e86_up;
 wire [1:0] e86_dclk, e86_uclk;
 wire [1055:0] e87_down, e87_up;
 wire [1:0] e87_dclk, e87_uclk;
 wire [1055:0] e88_down, e88_up;
 wire [1:0] e88_dclk, e88_uclk;
 wire [1055:0] e89_down, e89_up;
 wire [1:0] e89_dclk, e89_uclk;
 wire [1055:0] e90_down, e90_up;
 wire [1:0] e90_dclk, e90_uclk;
 wire [1055:0] e91_down, e91_up;
 wire [1:0] e91_dclk, e91_uclk;
 wire [1055:0] e92_down, e92_up;
 wire [1:0] e92_dclk, e92_uclk;
 wire [1055:0] e93_down, e93_up;
 wire [1:0] e93_dclk, e93_uclk;
 wire [527:0] e94_down, e94_up;
 wire [0:0] e94_dclk, e94_uclk;
 wire [527:0] e95_down, e95_up;
 wire [0:0] e95_dclk, e95_uclk;
 wire [527:0] e96_down, e96_up;
 wire [0:0] e96_dclk, e96_uclk;
 wire [527:0] e97_down, e97_up;
 wire [0:0] e97_dclk, e97_uclk;
 wire [527:0] e98_down, e98_up;
 wire [0:0] e98_dclk, e98_uclk;
 wire [527:0] e99_down, e99_up;
 wire [0:0] e99_dclk, e99_uclk;
 wire [527:0] e100_down, e100_up;
 wire [0:0] e100_dclk, e100_uclk;
 wire [527:0] e101_down, e101_up;
 wire [0:0] e101_dclk, e101_uclk;
 wire [527:0] e102_down, e102_up;
 wire [0:0] e102_dclk, e102_uclk;
 wire [527:0] e103_down, e103_up;
 wire [0:0] e103_dclk, e103_uclk;
 wire [527:0] e104_down, e104_up;
 wire [0:0] e104_dclk, e104_uclk;
 wire [527:0] e105_down, e105_up;
 wire [0:0] e105_dclk, e105_uclk;
 wire [527:0] e106_down, e106_up;
 wire [0:0] e106_dclk, e106_uclk;
 wire [527:0] e107_down, e107_up;
 wire [0:0] e107_dclk, e107_uclk;
 wire [527:0] e108_down, e108_up;
 wire [0:0] e108_dclk, e108_uclk;
 wire [527:0] e109_down, e109_up;
 wire [0:0] e109_dclk, e109_uclk;
 wire [527:0] e110_down, e110_up;
 wire [0:0] e110_dclk, e110_uclk;
 wire [527:0] e111_down, e111_up;
 wire [0:0] e111_dclk, e111_uclk;
 wire [527:0] e112_down, e112_up;
 wire [0:0] e112_dclk, e112_uclk;
 wire [527:0] e113_down, e113_up;
 wire [0:0] e113_dclk, e113_uclk;
 wire [527:0] e114_down, e114_up;
 wire [0:0] e114_dclk, e114_uclk;
 wire [527:0] e115_down, e115_up;
 wire [0:0] e115_dclk, e115_uclk;
 wire [527:0] e116_down, e116_up;
 wire [0:0] e116_dclk, e116_uclk;
 wire [527:0] e117_down, e117_up;
 wire [0:0] e117_dclk, e117_uclk;
 wire [527:0] e118_down, e118_up;
 wire [0:0] e118_dclk, e118_uclk;
 wire [527:0] e119_down, e119_up;
 wire [0:0] e119_dclk, e119_uclk;
 wire [527:0] e120_down, e120_up;
 wire [0:0] e120_dclk, e120_uclk;
 wire [527:0] e121_down, e121_up;
 wire [0:0] e121_dclk, e121_uclk;
 wire [527:0] e122_down, e122_up;
 wire [0:0] e122_dclk, e122_uclk;
 wire [527:0] e123_down, e123_up;
 wire [0:0] e123_dclk, e123_uclk;
 wire [527:0] e124_down, e124_up;
 wire [0:0] e124_dclk, e124_uclk;
 wire [527:0] e125_down, e125_up;
 wire [0:0] e125_dclk, e125_uclk;
 wire [527:0] e126_down, e126_up;
 wire [0:0] e126_dclk, e126_uclk;
 wire [527:0] e127_down, e127_up;
 wire [0:0] e127_dclk, e127_uclk;
 wire [527:0] e128_down, e128_up;
 wire [0:0] e128_dclk, e128_uclk;
 wire [527:0] e129_down, e129_up;
 wire [0:0] e129_dclk, e129_uclk;
 wire [527:0] e130_down, e130_up;
 wire [0:0] e130_dclk, e130_uclk;
 wire [527:0] e131_down, e131_up;
 wire [0:0] e131_dclk, e131_uclk;
 wire [527:0] e132_down, e132_up;
 wire [0:0] e132_dclk, e132_uclk;
 assign e132_up=strip_tx_data[0+:528];
 assign e132_uclk=strip_tx_clk[0];
 assign strip_rx_data[0+:528]=e132_down;
 assign strip_rx_clk[0]=e132_dclk;
 wire [527:0] e133_down, e133_up;
 wire [0:0] e133_dclk, e133_uclk;
 wire [527:0] e134_down, e134_up;
 wire [0:0] e134_dclk, e134_uclk;
 wire [527:0] e135_down, e135_up;
 wire [0:0] e135_dclk, e135_uclk;
 wire [527:0] e136_down, e136_up;
 wire [0:0] e136_dclk, e136_uclk;
 wire [527:0] e137_down, e137_up;
 wire [0:0] e137_dclk, e137_uclk;
 wire [527:0] e138_down, e138_up;
 wire [0:0] e138_dclk, e138_uclk;
 wire [527:0] e139_down, e139_up;
 wire [0:0] e139_dclk, e139_uclk;
 wire [527:0] e140_down, e140_up;
 wire [0:0] e140_dclk, e140_uclk;
 wire [527:0] e141_down, e141_up;
 wire [0:0] e141_dclk, e141_uclk;
 wire [527:0] e142_down, e142_up;
 wire [0:0] e142_dclk, e142_uclk;
 wire [527:0] e143_down, e143_up;
 wire [0:0] e143_dclk, e143_uclk;
 wire [527:0] e144_down, e144_up;
 wire [0:0] e144_dclk, e144_uclk;
 wire [527:0] e145_down, e145_up;
 wire [0:0] e145_dclk, e145_uclk;
 wire [527:0] e146_down, e146_up;
 wire [0:0] e146_dclk, e146_uclk;
 wire [527:0] e147_down, e147_up;
 wire [0:0] e147_dclk, e147_uclk;
 wire [527:0] e148_down, e148_up;
 wire [0:0] e148_dclk, e148_uclk;
 wire [527:0] e149_down, e149_up;
 wire [0:0] e149_dclk, e149_uclk;
 wire [527:0] e150_down, e150_up;
 wire [0:0] e150_dclk, e150_uclk;
 wire [527:0] e151_down, e151_up;
 wire [0:0] e151_dclk, e151_uclk;
 wire [527:0] e152_down, e152_up;
 wire [0:0] e152_dclk, e152_uclk;
 wire [527:0] e153_down, e153_up;
 wire [0:0] e153_dclk, e153_uclk;
 wire [527:0] e154_down, e154_up;
 wire [0:0] e154_dclk, e154_uclk;
 wire [527:0] e155_down, e155_up;
 wire [0:0] e155_dclk, e155_uclk;
 wire [527:0] e156_down, e156_up;
 wire [0:0] e156_dclk, e156_uclk;
 wire [527:0] e157_down, e157_up;
 wire [0:0] e157_dclk, e157_uclk;
 wire [527:0] e158_down, e158_up;
 wire [0:0] e158_dclk, e158_uclk;
 wire [527:0] e159_down, e159_up;
 wire [0:0] e159_dclk, e159_uclk;
 wire [527:0] e160_down, e160_up;
 wire [0:0] e160_dclk, e160_uclk;
 wire [527:0] e161_down, e161_up;
 wire [0:0] e161_dclk, e161_uclk;
 wire [527:0] e162_down, e162_up;
 wire [0:0] e162_dclk, e162_uclk;
 wire [527:0] e163_down, e163_up;
 wire [0:0] e163_dclk, e163_uclk;
 wire [527:0] e164_down, e164_up;
 wire [0:0] e164_dclk, e164_uclk;
 wire [527:0] e165_down, e165_up;
 wire [0:0] e165_dclk, e165_uclk;
 wire [527:0] e166_down, e166_up;
 wire [0:0] e166_dclk, e166_uclk;
 wire [527:0] e167_down, e167_up;
 wire [0:0] e167_dclk, e167_uclk;
 wire [527:0] e168_down, e168_up;
 wire [0:0] e168_dclk, e168_uclk;
 wire [527:0] e169_down, e169_up;
 wire [0:0] e169_dclk, e169_uclk;
 wire [527:0] e170_down, e170_up;
 wire [0:0] e170_dclk, e170_uclk;
 wire [527:0] e171_down, e171_up;
 wire [0:0] e171_dclk, e171_uclk;
 assign e171_up=strip_tx_data[528+:528];
 assign e171_uclk=strip_tx_clk[1];
 assign strip_rx_data[528+:528]=e171_down;
 assign strip_rx_clk[1]=e171_dclk;
 wire [527:0] e172_down, e172_up;
 wire [0:0] e172_dclk, e172_uclk;
 assign e172_down[0+:528]=hub_tx_data[1056+:528];
 assign e172_dclk[0]=hub_tx_clk[2];
 assign hub_rx_data[1056+:528]=e172_up[0+:528];
 assign hub_rx_clk[2]=e172_uclk[0];
 wire [527:0] e173_down, e173_up;
 wire [0:0] e173_dclk, e173_uclk;
 wire [527:0] e174_down, e174_up;
 wire [0:0] e174_dclk, e174_uclk;
 wire [527:0] e175_down, e175_up;
 wire [0:0] e175_dclk, e175_uclk;
 wire [527:0] e176_down, e176_up;
 wire [0:0] e176_dclk, e176_uclk;
 wire [527:0] e177_down, e177_up;
 wire [0:0] e177_dclk, e177_uclk;
 wire [527:0] e178_down, e178_up;
 wire [0:0] e178_dclk, e178_uclk;
 wire [527:0] e179_down, e179_up;
 wire [0:0] e179_dclk, e179_uclk;
 wire [527:0] e180_down, e180_up;
 wire [0:0] e180_dclk, e180_uclk;
 wire [527:0] e181_down, e181_up;
 wire [0:0] e181_dclk, e181_uclk;
 wire [527:0] e182_down, e182_up;
 wire [0:0] e182_dclk, e182_uclk;
 wire [527:0] e183_down, e183_up;
 wire [0:0] e183_dclk, e183_uclk;
 wire [527:0] e184_down, e184_up;
 wire [0:0] e184_dclk, e184_uclk;
 wire [527:0] e185_down, e185_up;
 wire [0:0] e185_dclk, e185_uclk;
 wire [527:0] e186_down, e186_up;
 wire [0:0] e186_dclk, e186_uclk;
 wire [527:0] e187_down, e187_up;
 wire [0:0] e187_dclk, e187_uclk;
 wire [527:0] e188_down, e188_up;
 wire [0:0] e188_dclk, e188_uclk;
 assign e188_down[0+:528]=hub_tx_data[1584+:528];
 assign e188_dclk[0]=hub_tx_clk[3];
 assign hub_rx_data[1584+:528]=e188_up[0+:528];
 assign hub_rx_clk[3]=e188_uclk[0];
 wire [527:0] e189_down, e189_up;
 wire [0:0] e189_dclk, e189_uclk;
 wire [527:0] e190_down, e190_up;
 wire [0:0] e190_dclk, e190_uclk;
 wire [527:0] e191_down, e191_up;
 wire [0:0] e191_dclk, e191_uclk;
 wire [527:0] e192_down, e192_up;
 wire [0:0] e192_dclk, e192_uclk;
 wire [527:0] e193_down, e193_up;
 wire [0:0] e193_dclk, e193_uclk;
 wire [527:0] e194_down, e194_up;
 wire [0:0] e194_dclk, e194_uclk;
 wire [527:0] e195_down, e195_up;
 wire [0:0] e195_dclk, e195_uclk;
 wire [527:0] e196_down, e196_up;
 wire [0:0] e196_dclk, e196_uclk;
 wire [527:0] e197_down, e197_up;
 wire [0:0] e197_dclk, e197_uclk;
 wire [527:0] e198_down, e198_up;
 wire [0:0] e198_dclk, e198_uclk;
 wire [527:0] e199_down, e199_up;
 wire [0:0] e199_dclk, e199_uclk;
 wire [527:0] e200_down, e200_up;
 wire [0:0] e200_dclk, e200_uclk;
 wire [527:0] e201_down, e201_up;
 wire [0:0] e201_dclk, e201_uclk;
 wire [527:0] e202_down, e202_up;
 wire [0:0] e202_dclk, e202_uclk;
 wire [527:0] e203_down, e203_up;
 wire [0:0] e203_dclk, e203_uclk;
 wire [527:0] e204_down, e204_up;
 wire [0:0] e204_dclk, e204_uclk;
 // lv_N_1: lnkv_1_0__r4[0] <-> lnkv_1_1[0]
 ot_qwen_die_link_fwd_full #(.NL(1),.ENABLE(ENABLE)) u_stage_0 (
  .rst_n(link_por_n),
  .fclk_ab_i(e82_dclk[0]), .fclk_ab_o(e83_dclk[0]),
  .fclk_ba_i(e83_uclk[0]), .fclk_ba_o(e82_uclk[0]),
  .a_i(e82_down[0+:528]), .a_o(e82_up[0+:528]),
  .b_i(e83_up[0+:528]), .b_o(e83_down[0+:528]) );
 // lv_N_1: lnkv_1_0__r4[1] <-> lnkv_1_1[1]
 ot_qwen_die_link_fwd_full #(.NL(1),.ENABLE(ENABLE)) u_stage_1 (
  .rst_n(link_por_n),
  .fclk_ab_i(e82_dclk[1]), .fclk_ab_o(e83_dclk[1]),
  .fclk_ba_i(e83_uclk[1]), .fclk_ba_o(e82_uclk[1]),
  .a_i(e82_down[528+:528]), .a_o(e82_up[528+:528]),
  .b_i(e83_up[528+:528]), .b_o(e83_down[528+:528]) );
 // lv_N_2: lnkv_1_1__r3[0] <-> lnkv_1_2[0]
 ot_qwen_die_link_fwd_full #(.NL(1),.ENABLE(ENABLE)) u_stage_2 (
  .rst_n(link_por_n),
  .fclk_ab_i(e86_dclk[0]), .fclk_ab_o(e87_dclk[0]),
  .fclk_ba_i(e87_uclk[0]), .fclk_ba_o(e86_uclk[0]),
  .a_i(e86_down[0+:528]), .a_o(e86_up[0+:528]),
  .b_i(e87_up[0+:528]), .b_o(e87_down[0+:528]) );
 // lv_N_2: lnkv_1_1__r3[1] <-> lnkv_1_2[1]
 ot_qwen_die_link_fwd_full #(.NL(1),.ENABLE(ENABLE)) u_stage_3 (
  .rst_n(link_por_n),
  .fclk_ab_i(e86_dclk[1]), .fclk_ab_o(e87_dclk[1]),
  .fclk_ba_i(e87_uclk[1]), .fclk_ba_o(e86_uclk[1]),
  .a_i(e86_down[528+:528]), .a_o(e86_up[528+:528]),
  .b_i(e87_up[528+:528]), .b_o(e87_down[528+:528]) );
 // lv_N_3: lnkv_1_2__r3[0] <-> lnkv_1_c[0]
 ot_qwen_die_link_fwd_full #(.NL(1),.ENABLE(ENABLE)) u_stage_4 (
  .rst_n(link_por_n),
  .fclk_ab_i(e90_dclk[0]), .fclk_ab_o(e91_dclk[0]),
  .fclk_ba_i(e91_uclk[0]), .fclk_ba_o(e90_uclk[0]),
  .a_i(e90_down[0+:528]), .a_o(e90_up[0+:528]),
  .b_i(e91_up[0+:528]), .b_o(e91_down[0+:528]) );
 // lv_N_3: lnkv_1_2__r3[1] <-> lnkv_1_c[1]
 ot_qwen_die_link_fwd_full #(.NL(1),.ENABLE(ENABLE)) u_stage_5 (
  .rst_n(link_por_n),
  .fclk_ab_i(e90_dclk[1]), .fclk_ab_o(e91_dclk[1]),
  .fclk_ba_i(e91_uclk[1]), .fclk_ba_o(e90_uclk[1]),
  .a_i(e90_down[528+:528]), .a_o(e90_up[528+:528]),
  .b_i(e91_up[528+:528]), .b_o(e91_down[528+:528]) );
 // lc_N: lnkv_1_c__r2[0] <-> lnkh_1W_0[0]
 ot_qwen_die_link_fwd_full #(.NL(1),.ENABLE(ENABLE)) u_stage_6 (
  .rst_n(link_por_n),
  .fclk_ab_i(e93_dclk[0]), .fclk_ab_o(e94_dclk[0]),
  .fclk_ba_i(e94_uclk[0]), .fclk_ba_o(e93_uclk[0]),
  .a_i(e93_down[0+:528]), .a_o(e93_up[0+:528]),
  .b_i(e94_up[0+:528]), .b_o(e94_down[0+:528]) );
 // lc_N: lnkv_1_c__r2[1] <-> lnkh_1E_0[0]
 ot_qwen_die_link_fwd_full #(.NL(1),.ENABLE(ENABLE)) u_stage_7 (
  .rst_n(link_por_n),
  .fclk_ab_i(e93_dclk[1]), .fclk_ab_o(e133_dclk[0]),
  .fclk_ba_i(e133_uclk[0]), .fclk_ba_o(e93_uclk[1]),
  .a_i(e93_down[528+:528]), .a_o(e93_up[528+:528]),
  .b_i(e133_up[0+:528]), .b_o(e133_down[0+:528]) );
 // lh_SW_1: lnkh_0W_0__r7[0] <-> lnkh_0W_1[0]
 ot_qwen_die_link_fwd_full #(.NL(1),.ENABLE(ENABLE)) u_stage_8 (
  .rst_n(link_por_n),
  .fclk_ab_i(e7_dclk[0]), .fclk_ab_o(e8_dclk[0]),
  .fclk_ba_i(e8_uclk[0]), .fclk_ba_o(e7_uclk[0]),
  .a_i(e7_down[0+:528]), .a_o(e7_up[0+:528]),
  .b_i(e8_up[0+:528]), .b_o(e8_down[0+:528]) );
 // lh_SW_2: lnkh_0W_1__r6[0] <-> lnkh_0W_2[0]
 ot_qwen_die_link_fwd_full #(.NL(1),.ENABLE(ENABLE)) u_stage_9 (
  .rst_n(link_por_n),
  .fclk_ab_i(e14_dclk[0]), .fclk_ab_o(e15_dclk[0]),
  .fclk_ba_i(e15_uclk[0]), .fclk_ba_o(e14_uclk[0]),
  .a_i(e14_down[0+:528]), .a_o(e14_up[0+:528]),
  .b_i(e15_up[0+:528]), .b_o(e15_down[0+:528]) );
 // lh_SW_3: lnkh_0W_2__r5[0] <-> lnkh_0W_3[0]
 ot_qwen_die_link_fwd_full #(.NL(1),.ENABLE(ENABLE)) u_stage_10 (
  .rst_n(link_por_n),
  .fclk_ab_i(e20_dclk[0]), .fclk_ab_o(e21_dclk[0]),
  .fclk_ba_i(e21_uclk[0]), .fclk_ba_o(e20_uclk[0]),
  .a_i(e20_down[0+:528]), .a_o(e20_up[0+:528]),
  .b_i(e21_up[0+:528]), .b_o(e21_down[0+:528]) );
 // lh_SW_4: lnkh_0W_3__r5[0] <-> lnkh_0W_4[0]
 ot_qwen_die_link_fwd_full #(.NL(1),.ENABLE(ENABLE)) u_stage_11 (
  .rst_n(link_por_n),
  .fclk_ab_i(e26_dclk[0]), .fclk_ab_o(e27_dclk[0]),
  .fclk_ba_i(e27_uclk[0]), .fclk_ba_o(e26_uclk[0]),
  .a_i(e26_down[0+:528]), .a_o(e26_up[0+:528]),
  .b_i(e27_up[0+:528]), .b_o(e27_down[0+:528]) );
 // lh_SW_5: lnkh_0W_4__r6[0] <-> lnkh_0W_f[0]
 ot_qwen_die_link_fwd_full #(.NL(1),.ENABLE(ENABLE)) u_stage_12 (
  .rst_n(link_por_n),
  .fclk_ab_i(e33_dclk[0]), .fclk_ab_o(e34_dclk[0]),
  .fclk_ba_i(e34_uclk[0]), .fclk_ba_o(e33_uclk[0]),
  .a_i(e33_down[0+:528]), .a_o(e33_up[0+:528]),
  .b_i(e34_up[0+:528]), .b_o(e34_down[0+:528]) );
 // lh_SE_1: lnkh_0E_0__r6[0] <-> lnkh_0E_1[0]
 ot_qwen_die_link_fwd_full #(.NL(1),.ENABLE(ENABLE)) u_stage_13 (
  .rst_n(link_por_n),
  .fclk_ab_i(e45_dclk[0]), .fclk_ab_o(e46_dclk[0]),
  .fclk_ba_i(e46_uclk[0]), .fclk_ba_o(e45_uclk[0]),
  .a_i(e45_down[0+:528]), .a_o(e45_up[0+:528]),
  .b_i(e46_up[0+:528]), .b_o(e46_down[0+:528]) );
 // lh_SE_2: lnkh_0E_1__r6[0] <-> lnkh_0E_2[0]
 ot_qwen_die_link_fwd_full #(.NL(1),.ENABLE(ENABLE)) u_stage_14 (
  .rst_n(link_por_n),
  .fclk_ab_i(e52_dclk[0]), .fclk_ab_o(e53_dclk[0]),
  .fclk_ba_i(e53_uclk[0]), .fclk_ba_o(e52_uclk[0]),
  .a_i(e52_down[0+:528]), .a_o(e52_up[0+:528]),
  .b_i(e53_up[0+:528]), .b_o(e53_down[0+:528]) );
 // lh_SE_3: lnkh_0E_2__r5[0] <-> lnkh_0E_3[0]
 ot_qwen_die_link_fwd_full #(.NL(1),.ENABLE(ENABLE)) u_stage_15 (
  .rst_n(link_por_n),
  .fclk_ab_i(e58_dclk[0]), .fclk_ab_o(e59_dclk[0]),
  .fclk_ba_i(e59_uclk[0]), .fclk_ba_o(e58_uclk[0]),
  .a_i(e58_down[0+:528]), .a_o(e58_up[0+:528]),
  .b_i(e59_up[0+:528]), .b_o(e59_down[0+:528]) );
 // lh_SE_4: lnkh_0E_3__r6[0] <-> lnkh_0E_4[0]
 ot_qwen_die_link_fwd_full #(.NL(1),.ENABLE(ENABLE)) u_stage_16 (
  .rst_n(link_por_n),
  .fclk_ab_i(e65_dclk[0]), .fclk_ab_o(e66_dclk[0]),
  .fclk_ba_i(e66_uclk[0]), .fclk_ba_o(e65_uclk[0]),
  .a_i(e65_down[0+:528]), .a_o(e65_up[0+:528]),
  .b_i(e66_up[0+:528]), .b_o(e66_down[0+:528]) );
 // lh_SE_5: lnkh_0E_4__r5[0] <-> lnkh_0E_f[0]
 ot_qwen_die_link_fwd_full #(.NL(1),.ENABLE(ENABLE)) u_stage_17 (
  .rst_n(link_por_n),
  .fclk_ab_i(e71_dclk[0]), .fclk_ab_o(e72_dclk[0]),
  .fclk_ba_i(e72_uclk[0]), .fclk_ba_o(e71_uclk[0]),
  .a_i(e71_down[0+:528]), .a_o(e71_up[0+:528]),
  .b_i(e72_up[0+:528]), .b_o(e72_down[0+:528]) );
 // lh_NW_1: lnkh_1W_0__r7[0] <-> lnkh_1W_1[0]
 ot_qwen_die_link_fwd_full #(.NL(1),.ENABLE(ENABLE)) u_stage_18 (
  .rst_n(link_por_n),
  .fclk_ab_i(e101_dclk[0]), .fclk_ab_o(e102_dclk[0]),
  .fclk_ba_i(e102_uclk[0]), .fclk_ba_o(e101_uclk[0]),
  .a_i(e101_down[0+:528]), .a_o(e101_up[0+:528]),
  .b_i(e102_up[0+:528]), .b_o(e102_down[0+:528]) );
 // lh_NW_2: lnkh_1W_1__r6[0] <-> lnkh_1W_2[0]
 ot_qwen_die_link_fwd_full #(.NL(1),.ENABLE(ENABLE)) u_stage_19 (
  .rst_n(link_por_n),
  .fclk_ab_i(e108_dclk[0]), .fclk_ab_o(e109_dclk[0]),
  .fclk_ba_i(e109_uclk[0]), .fclk_ba_o(e108_uclk[0]),
  .a_i(e108_down[0+:528]), .a_o(e108_up[0+:528]),
  .b_i(e109_up[0+:528]), .b_o(e109_down[0+:528]) );
 // lh_NW_3: lnkh_1W_2__r5[0] <-> lnkh_1W_3[0]
 ot_qwen_die_link_fwd_full #(.NL(1),.ENABLE(ENABLE)) u_stage_20 (
  .rst_n(link_por_n),
  .fclk_ab_i(e114_dclk[0]), .fclk_ab_o(e115_dclk[0]),
  .fclk_ba_i(e115_uclk[0]), .fclk_ba_o(e114_uclk[0]),
  .a_i(e114_down[0+:528]), .a_o(e114_up[0+:528]),
  .b_i(e115_up[0+:528]), .b_o(e115_down[0+:528]) );
 // lh_NW_4: lnkh_1W_3__r5[0] <-> lnkh_1W_4[0]
 ot_qwen_die_link_fwd_full #(.NL(1),.ENABLE(ENABLE)) u_stage_21 (
  .rst_n(link_por_n),
  .fclk_ab_i(e120_dclk[0]), .fclk_ab_o(e121_dclk[0]),
  .fclk_ba_i(e121_uclk[0]), .fclk_ba_o(e120_uclk[0]),
  .a_i(e120_down[0+:528]), .a_o(e120_up[0+:528]),
  .b_i(e121_up[0+:528]), .b_o(e121_down[0+:528]) );
 // lh_NW_5: lnkh_1W_4__r6[0] <-> lnkh_1W_f[0]
 ot_qwen_die_link_fwd_full #(.NL(1),.ENABLE(ENABLE)) u_stage_22 (
  .rst_n(link_por_n),
  .fclk_ab_i(e127_dclk[0]), .fclk_ab_o(e128_dclk[0]),
  .fclk_ba_i(e128_uclk[0]), .fclk_ba_o(e127_uclk[0]),
  .a_i(e127_down[0+:528]), .a_o(e127_up[0+:528]),
  .b_i(e128_up[0+:528]), .b_o(e128_down[0+:528]) );
 // lh_NE_1: lnkh_1E_0__r6[0] <-> lnkh_1E_1[0]
 ot_qwen_die_link_fwd_full #(.NL(1),.ENABLE(ENABLE)) u_stage_23 (
  .rst_n(link_por_n),
  .fclk_ab_i(e139_dclk[0]), .fclk_ab_o(e140_dclk[0]),
  .fclk_ba_i(e140_uclk[0]), .fclk_ba_o(e139_uclk[0]),
  .a_i(e139_down[0+:528]), .a_o(e139_up[0+:528]),
  .b_i(e140_up[0+:528]), .b_o(e140_down[0+:528]) );
 // lh_NE_2: lnkh_1E_1__r6[0] <-> lnkh_1E_2[0]
 ot_qwen_die_link_fwd_full #(.NL(1),.ENABLE(ENABLE)) u_stage_24 (
  .rst_n(link_por_n),
  .fclk_ab_i(e146_dclk[0]), .fclk_ab_o(e147_dclk[0]),
  .fclk_ba_i(e147_uclk[0]), .fclk_ba_o(e146_uclk[0]),
  .a_i(e146_down[0+:528]), .a_o(e146_up[0+:528]),
  .b_i(e147_up[0+:528]), .b_o(e147_down[0+:528]) );
 // lh_NE_3: lnkh_1E_2__r5[0] <-> lnkh_1E_3[0]
 ot_qwen_die_link_fwd_full #(.NL(1),.ENABLE(ENABLE)) u_stage_25 (
  .rst_n(link_por_n),
  .fclk_ab_i(e152_dclk[0]), .fclk_ab_o(e153_dclk[0]),
  .fclk_ba_i(e153_uclk[0]), .fclk_ba_o(e152_uclk[0]),
  .a_i(e152_down[0+:528]), .a_o(e152_up[0+:528]),
  .b_i(e153_up[0+:528]), .b_o(e153_down[0+:528]) );
 // lh_NE_4: lnkh_1E_3__r6[0] <-> lnkh_1E_4[0]
 ot_qwen_die_link_fwd_full #(.NL(1),.ENABLE(ENABLE)) u_stage_26 (
  .rst_n(link_por_n),
  .fclk_ab_i(e159_dclk[0]), .fclk_ab_o(e160_dclk[0]),
  .fclk_ba_i(e160_uclk[0]), .fclk_ba_o(e159_uclk[0]),
  .a_i(e159_down[0+:528]), .a_o(e159_up[0+:528]),
  .b_i(e160_up[0+:528]), .b_o(e160_down[0+:528]) );
 // lh_NE_5: lnkh_1E_4__r5[0] <-> lnkh_1E_f[0]
 ot_qwen_die_link_fwd_full #(.NL(1),.ENABLE(ENABLE)) u_stage_27 (
  .rst_n(link_por_n),
  .fclk_ab_i(e165_dclk[0]), .fclk_ab_o(e166_dclk[0]),
  .fclk_ba_i(e166_uclk[0]), .fclk_ba_o(e165_uclk[0]),
  .a_i(e165_down[0+:528]), .a_o(e165_up[0+:528]),
  .b_i(e166_up[0+:528]), .b_o(e166_down[0+:528]) );
 // lv_S_1_W: lnkv_0_W_0__r4[0] <-> lnkv_0_W_1[0]
 ot_qwen_die_link_fwd_full #(.NL(1),.ENABLE(ENABLE)) u_stage_28 (
  .rst_n(link_por_n),
  .fclk_ab_i(e176_dclk[0]), .fclk_ab_o(e177_dclk[0]),
  .fclk_ba_i(e177_uclk[0]), .fclk_ba_o(e176_uclk[0]),
  .a_i(e176_down[0+:528]), .a_o(e176_up[0+:528]),
  .b_i(e177_up[0+:528]), .b_o(e177_down[0+:528]) );
 // lv_S_2_W: lnkv_0_W_1__r3[0] <-> lnkv_0_W_2[0]
 ot_qwen_die_link_fwd_full #(.NL(1),.ENABLE(ENABLE)) u_stage_29 (
  .rst_n(link_por_n),
  .fclk_ab_i(e180_dclk[0]), .fclk_ab_o(e181_dclk[0]),
  .fclk_ba_i(e181_uclk[0]), .fclk_ba_o(e180_uclk[0]),
  .a_i(e180_down[0+:528]), .a_o(e180_up[0+:528]),
  .b_i(e181_up[0+:528]), .b_o(e181_down[0+:528]) );
 // lv_S_3_W: lnkv_0_W_2__r3[0] <-> lnkv_0_W_c[0]
 ot_qwen_die_link_fwd_full #(.NL(1),.ENABLE(ENABLE)) u_stage_30 (
  .rst_n(link_por_n),
  .fclk_ab_i(e184_dclk[0]), .fclk_ab_o(e185_dclk[0]),
  .fclk_ba_i(e185_uclk[0]), .fclk_ba_o(e184_uclk[0]),
  .a_i(e184_down[0+:528]), .a_o(e184_up[0+:528]),
  .b_i(e185_up[0+:528]), .b_o(e185_down[0+:528]) );
 // lc_SW: lnkv_0_W_c__r2[0] <-> lnkh_0W_0[0]
 ot_qwen_die_link_fwd_full #(.NL(1),.ENABLE(ENABLE)) u_stage_31 (
  .rst_n(link_por_n),
  .fclk_ab_i(e187_dclk[0]), .fclk_ab_o(e0_dclk[0]),
  .fclk_ba_i(e0_uclk[0]), .fclk_ba_o(e187_uclk[0]),
  .a_i(e187_down[0+:528]), .a_o(e187_up[0+:528]),
  .b_i(e0_up[0+:528]), .b_o(e0_down[0+:528]) );
 // lv_S_1_E: lnkv_0_E_0__r5[0] <-> lnkv_0_E_1[0]
 ot_qwen_die_link_fwd_full #(.NL(1),.ENABLE(ENABLE)) u_stage_32 (
  .rst_n(link_por_n),
  .fclk_ab_i(e193_dclk[0]), .fclk_ab_o(e194_dclk[0]),
  .fclk_ba_i(e194_uclk[0]), .fclk_ba_o(e193_uclk[0]),
  .a_i(e193_down[0+:528]), .a_o(e193_up[0+:528]),
  .b_i(e194_up[0+:528]), .b_o(e194_down[0+:528]) );
 // lv_S_2_E: lnkv_0_E_1__r3[0] <-> lnkv_0_E_2[0]
 ot_qwen_die_link_fwd_full #(.NL(1),.ENABLE(ENABLE)) u_stage_33 (
  .rst_n(link_por_n),
  .fclk_ab_i(e197_dclk[0]), .fclk_ab_o(e198_dclk[0]),
  .fclk_ba_i(e198_uclk[0]), .fclk_ba_o(e197_uclk[0]),
  .a_i(e197_down[0+:528]), .a_o(e197_up[0+:528]),
  .b_i(e198_up[0+:528]), .b_o(e198_down[0+:528]) );
 // lv_S_3_E: lnkv_0_E_2__r3[0] <-> lnkv_0_E_c[0]
 ot_qwen_die_link_fwd_full #(.NL(1),.ENABLE(ENABLE)) u_stage_34 (
  .rst_n(link_por_n),
  .fclk_ab_i(e201_dclk[0]), .fclk_ab_o(e202_dclk[0]),
  .fclk_ba_i(e202_uclk[0]), .fclk_ba_o(e201_uclk[0]),
  .a_i(e201_down[0+:528]), .a_o(e201_up[0+:528]),
  .b_i(e202_up[0+:528]), .b_o(e202_down[0+:528]) );
 // lc_SE: lnkv_0_E_c__r2[0] <-> lnkh_0E_0[0]
 ot_qwen_die_link_fwd_full #(.NL(1),.ENABLE(ENABLE)) u_stage_35 (
  .rst_n(link_por_n),
  .fclk_ab_i(e204_dclk[0]), .fclk_ab_o(e39_dclk[0]),
  .fclk_ba_i(e39_uclk[0]), .fclk_ba_o(e204_uclk[0]),
  .a_i(e204_down[0+:528]), .a_o(e204_up[0+:528]),
  .b_i(e39_up[0+:528]), .b_o(e39_down[0+:528]) );
 // rly_lnkh_0W_0_0: lnkh_0W_0[0] <-> lnkh_0W_0__r1[0]
 ot_qwen_die_link_fwd_full #(.NL(1),.ENABLE(ENABLE)) u_stage_36 (
  .rst_n(link_por_n),
  .fclk_ab_i(e0_dclk[0]), .fclk_ab_o(e1_dclk[0]),
  .fclk_ba_i(e1_uclk[0]), .fclk_ba_o(e0_uclk[0]),
  .a_i(e0_down[0+:528]), .a_o(e0_up[0+:528]),
  .b_i(e1_up[0+:528]), .b_o(e1_down[0+:528]) );
 // rly_lnkh_0W_0_1: lnkh_0W_0__r1[0] <-> lnkh_0W_0__r2[0]
 ot_qwen_die_link_fwd_full #(.NL(1),.ENABLE(ENABLE)) u_stage_37 (
  .rst_n(link_por_n),
  .fclk_ab_i(e1_dclk[0]), .fclk_ab_o(e2_dclk[0]),
  .fclk_ba_i(e2_uclk[0]), .fclk_ba_o(e1_uclk[0]),
  .a_i(e1_down[0+:528]), .a_o(e1_up[0+:528]),
  .b_i(e2_up[0+:528]), .b_o(e2_down[0+:528]) );
 // rly_lnkh_0W_0_2: lnkh_0W_0__r2[0] <-> lnkh_0W_0__r3[0]
 ot_qwen_die_link_fwd_full #(.NL(1),.ENABLE(ENABLE)) u_stage_38 (
  .rst_n(link_por_n),
  .fclk_ab_i(e2_dclk[0]), .fclk_ab_o(e3_dclk[0]),
  .fclk_ba_i(e3_uclk[0]), .fclk_ba_o(e2_uclk[0]),
  .a_i(e2_down[0+:528]), .a_o(e2_up[0+:528]),
  .b_i(e3_up[0+:528]), .b_o(e3_down[0+:528]) );
 // rly_lnkh_0W_0_3: lnkh_0W_0__r3[0] <-> lnkh_0W_0__r4[0]
 ot_qwen_die_link_fwd_full #(.NL(1),.ENABLE(ENABLE)) u_stage_39 (
  .rst_n(link_por_n),
  .fclk_ab_i(e3_dclk[0]), .fclk_ab_o(e4_dclk[0]),
  .fclk_ba_i(e4_uclk[0]), .fclk_ba_o(e3_uclk[0]),
  .a_i(e3_down[0+:528]), .a_o(e3_up[0+:528]),
  .b_i(e4_up[0+:528]), .b_o(e4_down[0+:528]) );
 // rly_lnkh_0W_0_4: lnkh_0W_0__r4[0] <-> lnkh_0W_0__r5[0]
 ot_qwen_die_link_fwd_full #(.NL(1),.ENABLE(ENABLE)) u_stage_40 (
  .rst_n(link_por_n),
  .fclk_ab_i(e4_dclk[0]), .fclk_ab_o(e5_dclk[0]),
  .fclk_ba_i(e5_uclk[0]), .fclk_ba_o(e4_uclk[0]),
  .a_i(e4_down[0+:528]), .a_o(e4_up[0+:528]),
  .b_i(e5_up[0+:528]), .b_o(e5_down[0+:528]) );
 // rly_lnkh_0W_0_5: lnkh_0W_0__r5[0] <-> lnkh_0W_0__r6[0]
 ot_qwen_die_link_fwd_full #(.NL(1),.ENABLE(ENABLE)) u_stage_41 (
  .rst_n(link_por_n),
  .fclk_ab_i(e5_dclk[0]), .fclk_ab_o(e6_dclk[0]),
  .fclk_ba_i(e6_uclk[0]), .fclk_ba_o(e5_uclk[0]),
  .a_i(e5_down[0+:528]), .a_o(e5_up[0+:528]),
  .b_i(e6_up[0+:528]), .b_o(e6_down[0+:528]) );
 // rly_lnkh_0W_0_6: lnkh_0W_0__r6[0] <-> lnkh_0W_0__r7[0]
 ot_qwen_die_link_fwd_full #(.NL(1),.ENABLE(ENABLE)) u_stage_42 (
  .rst_n(link_por_n),
  .fclk_ab_i(e6_dclk[0]), .fclk_ab_o(e7_dclk[0]),
  .fclk_ba_i(e7_uclk[0]), .fclk_ba_o(e6_uclk[0]),
  .a_i(e6_down[0+:528]), .a_o(e6_up[0+:528]),
  .b_i(e7_up[0+:528]), .b_o(e7_down[0+:528]) );
 // rly_lnkh_0W_1_0: lnkh_0W_1[0] <-> lnkh_0W_1__r1[0]
 ot_qwen_die_link_fwd_full #(.NL(1),.ENABLE(ENABLE)) u_stage_43 (
  .rst_n(link_por_n),
  .fclk_ab_i(e8_dclk[0]), .fclk_ab_o(e9_dclk[0]),
  .fclk_ba_i(e9_uclk[0]), .fclk_ba_o(e8_uclk[0]),
  .a_i(e8_down[0+:528]), .a_o(e8_up[0+:528]),
  .b_i(e9_up[0+:528]), .b_o(e9_down[0+:528]) );
 // rly_lnkh_0W_1_1: lnkh_0W_1__r1[0] <-> lnkh_0W_1__r2[0]
 ot_qwen_die_link_fwd_full #(.NL(1),.ENABLE(ENABLE)) u_stage_44 (
  .rst_n(link_por_n),
  .fclk_ab_i(e9_dclk[0]), .fclk_ab_o(e10_dclk[0]),
  .fclk_ba_i(e10_uclk[0]), .fclk_ba_o(e9_uclk[0]),
  .a_i(e9_down[0+:528]), .a_o(e9_up[0+:528]),
  .b_i(e10_up[0+:528]), .b_o(e10_down[0+:528]) );
 // rly_lnkh_0W_1_2: lnkh_0W_1__r2[0] <-> lnkh_0W_1__r3[0]
 ot_qwen_die_link_fwd_full #(.NL(1),.ENABLE(ENABLE)) u_stage_45 (
  .rst_n(link_por_n),
  .fclk_ab_i(e10_dclk[0]), .fclk_ab_o(e11_dclk[0]),
  .fclk_ba_i(e11_uclk[0]), .fclk_ba_o(e10_uclk[0]),
  .a_i(e10_down[0+:528]), .a_o(e10_up[0+:528]),
  .b_i(e11_up[0+:528]), .b_o(e11_down[0+:528]) );
 // rly_lnkh_0W_1_3: lnkh_0W_1__r3[0] <-> lnkh_0W_1__r4[0]
 ot_qwen_die_link_fwd_full #(.NL(1),.ENABLE(ENABLE)) u_stage_46 (
  .rst_n(link_por_n),
  .fclk_ab_i(e11_dclk[0]), .fclk_ab_o(e12_dclk[0]),
  .fclk_ba_i(e12_uclk[0]), .fclk_ba_o(e11_uclk[0]),
  .a_i(e11_down[0+:528]), .a_o(e11_up[0+:528]),
  .b_i(e12_up[0+:528]), .b_o(e12_down[0+:528]) );
 // rly_lnkh_0W_1_4: lnkh_0W_1__r4[0] <-> lnkh_0W_1__r5[0]
 ot_qwen_die_link_fwd_full #(.NL(1),.ENABLE(ENABLE)) u_stage_47 (
  .rst_n(link_por_n),
  .fclk_ab_i(e12_dclk[0]), .fclk_ab_o(e13_dclk[0]),
  .fclk_ba_i(e13_uclk[0]), .fclk_ba_o(e12_uclk[0]),
  .a_i(e12_down[0+:528]), .a_o(e12_up[0+:528]),
  .b_i(e13_up[0+:528]), .b_o(e13_down[0+:528]) );
 // rly_lnkh_0W_1_5: lnkh_0W_1__r5[0] <-> lnkh_0W_1__r6[0]
 ot_qwen_die_link_fwd_full #(.NL(1),.ENABLE(ENABLE)) u_stage_48 (
  .rst_n(link_por_n),
  .fclk_ab_i(e13_dclk[0]), .fclk_ab_o(e14_dclk[0]),
  .fclk_ba_i(e14_uclk[0]), .fclk_ba_o(e13_uclk[0]),
  .a_i(e13_down[0+:528]), .a_o(e13_up[0+:528]),
  .b_i(e14_up[0+:528]), .b_o(e14_down[0+:528]) );
 // rly_lnkh_0W_2_0: lnkh_0W_2[0] <-> lnkh_0W_2__r1[0]
 ot_qwen_die_link_fwd_full #(.NL(1),.ENABLE(ENABLE)) u_stage_49 (
  .rst_n(link_por_n),
  .fclk_ab_i(e15_dclk[0]), .fclk_ab_o(e16_dclk[0]),
  .fclk_ba_i(e16_uclk[0]), .fclk_ba_o(e15_uclk[0]),
  .a_i(e15_down[0+:528]), .a_o(e15_up[0+:528]),
  .b_i(e16_up[0+:528]), .b_o(e16_down[0+:528]) );
 // rly_lnkh_0W_2_1: lnkh_0W_2__r1[0] <-> lnkh_0W_2__r2[0]
 ot_qwen_die_link_fwd_full #(.NL(1),.ENABLE(ENABLE)) u_stage_50 (
  .rst_n(link_por_n),
  .fclk_ab_i(e16_dclk[0]), .fclk_ab_o(e17_dclk[0]),
  .fclk_ba_i(e17_uclk[0]), .fclk_ba_o(e16_uclk[0]),
  .a_i(e16_down[0+:528]), .a_o(e16_up[0+:528]),
  .b_i(e17_up[0+:528]), .b_o(e17_down[0+:528]) );
 // rly_lnkh_0W_2_2: lnkh_0W_2__r2[0] <-> lnkh_0W_2__r3[0]
 ot_qwen_die_link_fwd_full #(.NL(1),.ENABLE(ENABLE)) u_stage_51 (
  .rst_n(link_por_n),
  .fclk_ab_i(e17_dclk[0]), .fclk_ab_o(e18_dclk[0]),
  .fclk_ba_i(e18_uclk[0]), .fclk_ba_o(e17_uclk[0]),
  .a_i(e17_down[0+:528]), .a_o(e17_up[0+:528]),
  .b_i(e18_up[0+:528]), .b_o(e18_down[0+:528]) );
 // rly_lnkh_0W_2_3: lnkh_0W_2__r3[0] <-> lnkh_0W_2__r4[0]
 ot_qwen_die_link_fwd_full #(.NL(1),.ENABLE(ENABLE)) u_stage_52 (
  .rst_n(link_por_n),
  .fclk_ab_i(e18_dclk[0]), .fclk_ab_o(e19_dclk[0]),
  .fclk_ba_i(e19_uclk[0]), .fclk_ba_o(e18_uclk[0]),
  .a_i(e18_down[0+:528]), .a_o(e18_up[0+:528]),
  .b_i(e19_up[0+:528]), .b_o(e19_down[0+:528]) );
 // rly_lnkh_0W_2_4: lnkh_0W_2__r4[0] <-> lnkh_0W_2__r5[0]
 ot_qwen_die_link_fwd_full #(.NL(1),.ENABLE(ENABLE)) u_stage_53 (
  .rst_n(link_por_n),
  .fclk_ab_i(e19_dclk[0]), .fclk_ab_o(e20_dclk[0]),
  .fclk_ba_i(e20_uclk[0]), .fclk_ba_o(e19_uclk[0]),
  .a_i(e19_down[0+:528]), .a_o(e19_up[0+:528]),
  .b_i(e20_up[0+:528]), .b_o(e20_down[0+:528]) );
 // rly_lnkh_0W_3_0: lnkh_0W_3[0] <-> lnkh_0W_3__r1[0]
 ot_qwen_die_link_fwd_full #(.NL(1),.ENABLE(ENABLE)) u_stage_54 (
  .rst_n(link_por_n),
  .fclk_ab_i(e21_dclk[0]), .fclk_ab_o(e22_dclk[0]),
  .fclk_ba_i(e22_uclk[0]), .fclk_ba_o(e21_uclk[0]),
  .a_i(e21_down[0+:528]), .a_o(e21_up[0+:528]),
  .b_i(e22_up[0+:528]), .b_o(e22_down[0+:528]) );
 // rly_lnkh_0W_3_1: lnkh_0W_3__r1[0] <-> lnkh_0W_3__r2[0]
 ot_qwen_die_link_fwd_full #(.NL(1),.ENABLE(ENABLE)) u_stage_55 (
  .rst_n(link_por_n),
  .fclk_ab_i(e22_dclk[0]), .fclk_ab_o(e23_dclk[0]),
  .fclk_ba_i(e23_uclk[0]), .fclk_ba_o(e22_uclk[0]),
  .a_i(e22_down[0+:528]), .a_o(e22_up[0+:528]),
  .b_i(e23_up[0+:528]), .b_o(e23_down[0+:528]) );
 // rly_lnkh_0W_3_2: lnkh_0W_3__r2[0] <-> lnkh_0W_3__r3[0]
 ot_qwen_die_link_fwd_full #(.NL(1),.ENABLE(ENABLE)) u_stage_56 (
  .rst_n(link_por_n),
  .fclk_ab_i(e23_dclk[0]), .fclk_ab_o(e24_dclk[0]),
  .fclk_ba_i(e24_uclk[0]), .fclk_ba_o(e23_uclk[0]),
  .a_i(e23_down[0+:528]), .a_o(e23_up[0+:528]),
  .b_i(e24_up[0+:528]), .b_o(e24_down[0+:528]) );
 // rly_lnkh_0W_3_3: lnkh_0W_3__r3[0] <-> lnkh_0W_3__r4[0]
 ot_qwen_die_link_fwd_full #(.NL(1),.ENABLE(ENABLE)) u_stage_57 (
  .rst_n(link_por_n),
  .fclk_ab_i(e24_dclk[0]), .fclk_ab_o(e25_dclk[0]),
  .fclk_ba_i(e25_uclk[0]), .fclk_ba_o(e24_uclk[0]),
  .a_i(e24_down[0+:528]), .a_o(e24_up[0+:528]),
  .b_i(e25_up[0+:528]), .b_o(e25_down[0+:528]) );
 // rly_lnkh_0W_3_4: lnkh_0W_3__r4[0] <-> lnkh_0W_3__r5[0]
 ot_qwen_die_link_fwd_full #(.NL(1),.ENABLE(ENABLE)) u_stage_58 (
  .rst_n(link_por_n),
  .fclk_ab_i(e25_dclk[0]), .fclk_ab_o(e26_dclk[0]),
  .fclk_ba_i(e26_uclk[0]), .fclk_ba_o(e25_uclk[0]),
  .a_i(e25_down[0+:528]), .a_o(e25_up[0+:528]),
  .b_i(e26_up[0+:528]), .b_o(e26_down[0+:528]) );
 // rly_lnkh_0W_4_0: lnkh_0W_4[0] <-> lnkh_0W_4__r1[0]
 ot_qwen_die_link_fwd_full #(.NL(1),.ENABLE(ENABLE)) u_stage_59 (
  .rst_n(link_por_n),
  .fclk_ab_i(e27_dclk[0]), .fclk_ab_o(e28_dclk[0]),
  .fclk_ba_i(e28_uclk[0]), .fclk_ba_o(e27_uclk[0]),
  .a_i(e27_down[0+:528]), .a_o(e27_up[0+:528]),
  .b_i(e28_up[0+:528]), .b_o(e28_down[0+:528]) );
 // rly_lnkh_0W_4_1: lnkh_0W_4__r1[0] <-> lnkh_0W_4__r2[0]
 ot_qwen_die_link_fwd_full #(.NL(1),.ENABLE(ENABLE)) u_stage_60 (
  .rst_n(link_por_n),
  .fclk_ab_i(e28_dclk[0]), .fclk_ab_o(e29_dclk[0]),
  .fclk_ba_i(e29_uclk[0]), .fclk_ba_o(e28_uclk[0]),
  .a_i(e28_down[0+:528]), .a_o(e28_up[0+:528]),
  .b_i(e29_up[0+:528]), .b_o(e29_down[0+:528]) );
 // rly_lnkh_0W_4_2: lnkh_0W_4__r2[0] <-> lnkh_0W_4__r3[0]
 ot_qwen_die_link_fwd_full #(.NL(1),.ENABLE(ENABLE)) u_stage_61 (
  .rst_n(link_por_n),
  .fclk_ab_i(e29_dclk[0]), .fclk_ab_o(e30_dclk[0]),
  .fclk_ba_i(e30_uclk[0]), .fclk_ba_o(e29_uclk[0]),
  .a_i(e29_down[0+:528]), .a_o(e29_up[0+:528]),
  .b_i(e30_up[0+:528]), .b_o(e30_down[0+:528]) );
 // rly_lnkh_0W_4_3: lnkh_0W_4__r3[0] <-> lnkh_0W_4__r4[0]
 ot_qwen_die_link_fwd_full #(.NL(1),.ENABLE(ENABLE)) u_stage_62 (
  .rst_n(link_por_n),
  .fclk_ab_i(e30_dclk[0]), .fclk_ab_o(e31_dclk[0]),
  .fclk_ba_i(e31_uclk[0]), .fclk_ba_o(e30_uclk[0]),
  .a_i(e30_down[0+:528]), .a_o(e30_up[0+:528]),
  .b_i(e31_up[0+:528]), .b_o(e31_down[0+:528]) );
 // rly_lnkh_0W_4_4: lnkh_0W_4__r4[0] <-> lnkh_0W_4__r5[0]
 ot_qwen_die_link_fwd_full #(.NL(1),.ENABLE(ENABLE)) u_stage_63 (
  .rst_n(link_por_n),
  .fclk_ab_i(e31_dclk[0]), .fclk_ab_o(e32_dclk[0]),
  .fclk_ba_i(e32_uclk[0]), .fclk_ba_o(e31_uclk[0]),
  .a_i(e31_down[0+:528]), .a_o(e31_up[0+:528]),
  .b_i(e32_up[0+:528]), .b_o(e32_down[0+:528]) );
 // rly_lnkh_0W_4_5: lnkh_0W_4__r5[0] <-> lnkh_0W_4__r6[0]
 ot_qwen_die_link_fwd_full #(.NL(1),.ENABLE(ENABLE)) u_stage_64 (
  .rst_n(link_por_n),
  .fclk_ab_i(e32_dclk[0]), .fclk_ab_o(e33_dclk[0]),
  .fclk_ba_i(e33_uclk[0]), .fclk_ba_o(e32_uclk[0]),
  .a_i(e32_down[0+:528]), .a_o(e32_up[0+:528]),
  .b_i(e33_up[0+:528]), .b_o(e33_down[0+:528]) );
 // rly_lnkh_0W_f_0: lnkh_0W_f[0] <-> lnkh_0W_f__r1[0]
 ot_qwen_die_link_fwd_full #(.NL(1),.ENABLE(ENABLE)) u_stage_65 (
  .rst_n(link_por_n),
  .fclk_ab_i(e34_dclk[0]), .fclk_ab_o(e35_dclk[0]),
  .fclk_ba_i(e35_uclk[0]), .fclk_ba_o(e34_uclk[0]),
  .a_i(e34_down[0+:528]), .a_o(e34_up[0+:528]),
  .b_i(e35_up[0+:528]), .b_o(e35_down[0+:528]) );
 // rly_lnkh_0W_f_1: lnkh_0W_f__r1[0] <-> lnkh_0W_f__r2[0]
 ot_qwen_die_link_fwd_full #(.NL(1),.ENABLE(ENABLE)) u_stage_66 (
  .rst_n(link_por_n),
  .fclk_ab_i(e35_dclk[0]), .fclk_ab_o(e36_dclk[0]),
  .fclk_ba_i(e36_uclk[0]), .fclk_ba_o(e35_uclk[0]),
  .a_i(e35_down[0+:528]), .a_o(e35_up[0+:528]),
  .b_i(e36_up[0+:528]), .b_o(e36_down[0+:528]) );
 // rly_lnkh_0W_f_2: lnkh_0W_f__r2[0] <-> lnkh_0W_f__r3[0]
 ot_qwen_die_link_fwd_full #(.NL(1),.ENABLE(ENABLE)) u_stage_67 (
  .rst_n(link_por_n),
  .fclk_ab_i(e36_dclk[0]), .fclk_ab_o(e37_dclk[0]),
  .fclk_ba_i(e37_uclk[0]), .fclk_ba_o(e36_uclk[0]),
  .a_i(e36_down[0+:528]), .a_o(e36_up[0+:528]),
  .b_i(e37_up[0+:528]), .b_o(e37_down[0+:528]) );
 // rly_lnkh_0W_f_3: lnkh_0W_f__r3[0] <-> lnkh_0W_f__r4[0]
 ot_qwen_die_link_fwd_full #(.NL(1),.ENABLE(ENABLE)) u_stage_68 (
  .rst_n(link_por_n),
  .fclk_ab_i(e37_dclk[0]), .fclk_ab_o(e38_dclk[0]),
  .fclk_ba_i(e38_uclk[0]), .fclk_ba_o(e37_uclk[0]),
  .a_i(e37_down[0+:528]), .a_o(e37_up[0+:528]),
  .b_i(e38_up[0+:528]), .b_o(e38_down[0+:528]) );
 // rly_lnkh_0E_0_0: lnkh_0E_0[0] <-> lnkh_0E_0__r1[0]
 ot_qwen_die_link_fwd_full #(.NL(1),.ENABLE(ENABLE)) u_stage_69 (
  .rst_n(link_por_n),
  .fclk_ab_i(e39_dclk[0]), .fclk_ab_o(e40_dclk[0]),
  .fclk_ba_i(e40_uclk[0]), .fclk_ba_o(e39_uclk[0]),
  .a_i(e39_down[0+:528]), .a_o(e39_up[0+:528]),
  .b_i(e40_up[0+:528]), .b_o(e40_down[0+:528]) );
 // rly_lnkh_0E_0_1: lnkh_0E_0__r1[0] <-> lnkh_0E_0__r2[0]
 ot_qwen_die_link_fwd_full #(.NL(1),.ENABLE(ENABLE)) u_stage_70 (
  .rst_n(link_por_n),
  .fclk_ab_i(e40_dclk[0]), .fclk_ab_o(e41_dclk[0]),
  .fclk_ba_i(e41_uclk[0]), .fclk_ba_o(e40_uclk[0]),
  .a_i(e40_down[0+:528]), .a_o(e40_up[0+:528]),
  .b_i(e41_up[0+:528]), .b_o(e41_down[0+:528]) );
 // rly_lnkh_0E_0_2: lnkh_0E_0__r2[0] <-> lnkh_0E_0__r3[0]
 ot_qwen_die_link_fwd_full #(.NL(1),.ENABLE(ENABLE)) u_stage_71 (
  .rst_n(link_por_n),
  .fclk_ab_i(e41_dclk[0]), .fclk_ab_o(e42_dclk[0]),
  .fclk_ba_i(e42_uclk[0]), .fclk_ba_o(e41_uclk[0]),
  .a_i(e41_down[0+:528]), .a_o(e41_up[0+:528]),
  .b_i(e42_up[0+:528]), .b_o(e42_down[0+:528]) );
 // rly_lnkh_0E_0_3: lnkh_0E_0__r3[0] <-> lnkh_0E_0__r4[0]
 ot_qwen_die_link_fwd_full #(.NL(1),.ENABLE(ENABLE)) u_stage_72 (
  .rst_n(link_por_n),
  .fclk_ab_i(e42_dclk[0]), .fclk_ab_o(e43_dclk[0]),
  .fclk_ba_i(e43_uclk[0]), .fclk_ba_o(e42_uclk[0]),
  .a_i(e42_down[0+:528]), .a_o(e42_up[0+:528]),
  .b_i(e43_up[0+:528]), .b_o(e43_down[0+:528]) );
 // rly_lnkh_0E_0_4: lnkh_0E_0__r4[0] <-> lnkh_0E_0__r5[0]
 ot_qwen_die_link_fwd_full #(.NL(1),.ENABLE(ENABLE)) u_stage_73 (
  .rst_n(link_por_n),
  .fclk_ab_i(e43_dclk[0]), .fclk_ab_o(e44_dclk[0]),
  .fclk_ba_i(e44_uclk[0]), .fclk_ba_o(e43_uclk[0]),
  .a_i(e43_down[0+:528]), .a_o(e43_up[0+:528]),
  .b_i(e44_up[0+:528]), .b_o(e44_down[0+:528]) );
 // rly_lnkh_0E_0_5: lnkh_0E_0__r5[0] <-> lnkh_0E_0__r6[0]
 ot_qwen_die_link_fwd_full #(.NL(1),.ENABLE(ENABLE)) u_stage_74 (
  .rst_n(link_por_n),
  .fclk_ab_i(e44_dclk[0]), .fclk_ab_o(e45_dclk[0]),
  .fclk_ba_i(e45_uclk[0]), .fclk_ba_o(e44_uclk[0]),
  .a_i(e44_down[0+:528]), .a_o(e44_up[0+:528]),
  .b_i(e45_up[0+:528]), .b_o(e45_down[0+:528]) );
 // rly_lnkh_0E_1_0: lnkh_0E_1[0] <-> lnkh_0E_1__r1[0]
 ot_qwen_die_link_fwd_full #(.NL(1),.ENABLE(ENABLE)) u_stage_75 (
  .rst_n(link_por_n),
  .fclk_ab_i(e46_dclk[0]), .fclk_ab_o(e47_dclk[0]),
  .fclk_ba_i(e47_uclk[0]), .fclk_ba_o(e46_uclk[0]),
  .a_i(e46_down[0+:528]), .a_o(e46_up[0+:528]),
  .b_i(e47_up[0+:528]), .b_o(e47_down[0+:528]) );
 // rly_lnkh_0E_1_1: lnkh_0E_1__r1[0] <-> lnkh_0E_1__r2[0]
 ot_qwen_die_link_fwd_full #(.NL(1),.ENABLE(ENABLE)) u_stage_76 (
  .rst_n(link_por_n),
  .fclk_ab_i(e47_dclk[0]), .fclk_ab_o(e48_dclk[0]),
  .fclk_ba_i(e48_uclk[0]), .fclk_ba_o(e47_uclk[0]),
  .a_i(e47_down[0+:528]), .a_o(e47_up[0+:528]),
  .b_i(e48_up[0+:528]), .b_o(e48_down[0+:528]) );
 // rly_lnkh_0E_1_2: lnkh_0E_1__r2[0] <-> lnkh_0E_1__r3[0]
 ot_qwen_die_link_fwd_full #(.NL(1),.ENABLE(ENABLE)) u_stage_77 (
  .rst_n(link_por_n),
  .fclk_ab_i(e48_dclk[0]), .fclk_ab_o(e49_dclk[0]),
  .fclk_ba_i(e49_uclk[0]), .fclk_ba_o(e48_uclk[0]),
  .a_i(e48_down[0+:528]), .a_o(e48_up[0+:528]),
  .b_i(e49_up[0+:528]), .b_o(e49_down[0+:528]) );
 // rly_lnkh_0E_1_3: lnkh_0E_1__r3[0] <-> lnkh_0E_1__r4[0]
 ot_qwen_die_link_fwd_full #(.NL(1),.ENABLE(ENABLE)) u_stage_78 (
  .rst_n(link_por_n),
  .fclk_ab_i(e49_dclk[0]), .fclk_ab_o(e50_dclk[0]),
  .fclk_ba_i(e50_uclk[0]), .fclk_ba_o(e49_uclk[0]),
  .a_i(e49_down[0+:528]), .a_o(e49_up[0+:528]),
  .b_i(e50_up[0+:528]), .b_o(e50_down[0+:528]) );
 // rly_lnkh_0E_1_4: lnkh_0E_1__r4[0] <-> lnkh_0E_1__r5[0]
 ot_qwen_die_link_fwd_full #(.NL(1),.ENABLE(ENABLE)) u_stage_79 (
  .rst_n(link_por_n),
  .fclk_ab_i(e50_dclk[0]), .fclk_ab_o(e51_dclk[0]),
  .fclk_ba_i(e51_uclk[0]), .fclk_ba_o(e50_uclk[0]),
  .a_i(e50_down[0+:528]), .a_o(e50_up[0+:528]),
  .b_i(e51_up[0+:528]), .b_o(e51_down[0+:528]) );
 // rly_lnkh_0E_1_5: lnkh_0E_1__r5[0] <-> lnkh_0E_1__r6[0]
 ot_qwen_die_link_fwd_full #(.NL(1),.ENABLE(ENABLE)) u_stage_80 (
  .rst_n(link_por_n),
  .fclk_ab_i(e51_dclk[0]), .fclk_ab_o(e52_dclk[0]),
  .fclk_ba_i(e52_uclk[0]), .fclk_ba_o(e51_uclk[0]),
  .a_i(e51_down[0+:528]), .a_o(e51_up[0+:528]),
  .b_i(e52_up[0+:528]), .b_o(e52_down[0+:528]) );
 // rly_lnkh_0E_2_0: lnkh_0E_2[0] <-> lnkh_0E_2__r1[0]
 ot_qwen_die_link_fwd_full #(.NL(1),.ENABLE(ENABLE)) u_stage_81 (
  .rst_n(link_por_n),
  .fclk_ab_i(e53_dclk[0]), .fclk_ab_o(e54_dclk[0]),
  .fclk_ba_i(e54_uclk[0]), .fclk_ba_o(e53_uclk[0]),
  .a_i(e53_down[0+:528]), .a_o(e53_up[0+:528]),
  .b_i(e54_up[0+:528]), .b_o(e54_down[0+:528]) );
 // rly_lnkh_0E_2_1: lnkh_0E_2__r1[0] <-> lnkh_0E_2__r2[0]
 ot_qwen_die_link_fwd_full #(.NL(1),.ENABLE(ENABLE)) u_stage_82 (
  .rst_n(link_por_n),
  .fclk_ab_i(e54_dclk[0]), .fclk_ab_o(e55_dclk[0]),
  .fclk_ba_i(e55_uclk[0]), .fclk_ba_o(e54_uclk[0]),
  .a_i(e54_down[0+:528]), .a_o(e54_up[0+:528]),
  .b_i(e55_up[0+:528]), .b_o(e55_down[0+:528]) );
 // rly_lnkh_0E_2_2: lnkh_0E_2__r2[0] <-> lnkh_0E_2__r3[0]
 ot_qwen_die_link_fwd_full #(.NL(1),.ENABLE(ENABLE)) u_stage_83 (
  .rst_n(link_por_n),
  .fclk_ab_i(e55_dclk[0]), .fclk_ab_o(e56_dclk[0]),
  .fclk_ba_i(e56_uclk[0]), .fclk_ba_o(e55_uclk[0]),
  .a_i(e55_down[0+:528]), .a_o(e55_up[0+:528]),
  .b_i(e56_up[0+:528]), .b_o(e56_down[0+:528]) );
 // rly_lnkh_0E_2_3: lnkh_0E_2__r3[0] <-> lnkh_0E_2__r4[0]
 ot_qwen_die_link_fwd_full #(.NL(1),.ENABLE(ENABLE)) u_stage_84 (
  .rst_n(link_por_n),
  .fclk_ab_i(e56_dclk[0]), .fclk_ab_o(e57_dclk[0]),
  .fclk_ba_i(e57_uclk[0]), .fclk_ba_o(e56_uclk[0]),
  .a_i(e56_down[0+:528]), .a_o(e56_up[0+:528]),
  .b_i(e57_up[0+:528]), .b_o(e57_down[0+:528]) );
 // rly_lnkh_0E_2_4: lnkh_0E_2__r4[0] <-> lnkh_0E_2__r5[0]
 ot_qwen_die_link_fwd_full #(.NL(1),.ENABLE(ENABLE)) u_stage_85 (
  .rst_n(link_por_n),
  .fclk_ab_i(e57_dclk[0]), .fclk_ab_o(e58_dclk[0]),
  .fclk_ba_i(e58_uclk[0]), .fclk_ba_o(e57_uclk[0]),
  .a_i(e57_down[0+:528]), .a_o(e57_up[0+:528]),
  .b_i(e58_up[0+:528]), .b_o(e58_down[0+:528]) );
 // rly_lnkh_0E_3_0: lnkh_0E_3[0] <-> lnkh_0E_3__r1[0]
 ot_qwen_die_link_fwd_full #(.NL(1),.ENABLE(ENABLE)) u_stage_86 (
  .rst_n(link_por_n),
  .fclk_ab_i(e59_dclk[0]), .fclk_ab_o(e60_dclk[0]),
  .fclk_ba_i(e60_uclk[0]), .fclk_ba_o(e59_uclk[0]),
  .a_i(e59_down[0+:528]), .a_o(e59_up[0+:528]),
  .b_i(e60_up[0+:528]), .b_o(e60_down[0+:528]) );
 // rly_lnkh_0E_3_1: lnkh_0E_3__r1[0] <-> lnkh_0E_3__r2[0]
 ot_qwen_die_link_fwd_full #(.NL(1),.ENABLE(ENABLE)) u_stage_87 (
  .rst_n(link_por_n),
  .fclk_ab_i(e60_dclk[0]), .fclk_ab_o(e61_dclk[0]),
  .fclk_ba_i(e61_uclk[0]), .fclk_ba_o(e60_uclk[0]),
  .a_i(e60_down[0+:528]), .a_o(e60_up[0+:528]),
  .b_i(e61_up[0+:528]), .b_o(e61_down[0+:528]) );
 // rly_lnkh_0E_3_2: lnkh_0E_3__r2[0] <-> lnkh_0E_3__r3[0]
 ot_qwen_die_link_fwd_full #(.NL(1),.ENABLE(ENABLE)) u_stage_88 (
  .rst_n(link_por_n),
  .fclk_ab_i(e61_dclk[0]), .fclk_ab_o(e62_dclk[0]),
  .fclk_ba_i(e62_uclk[0]), .fclk_ba_o(e61_uclk[0]),
  .a_i(e61_down[0+:528]), .a_o(e61_up[0+:528]),
  .b_i(e62_up[0+:528]), .b_o(e62_down[0+:528]) );
 // rly_lnkh_0E_3_3: lnkh_0E_3__r3[0] <-> lnkh_0E_3__r4[0]
 ot_qwen_die_link_fwd_full #(.NL(1),.ENABLE(ENABLE)) u_stage_89 (
  .rst_n(link_por_n),
  .fclk_ab_i(e62_dclk[0]), .fclk_ab_o(e63_dclk[0]),
  .fclk_ba_i(e63_uclk[0]), .fclk_ba_o(e62_uclk[0]),
  .a_i(e62_down[0+:528]), .a_o(e62_up[0+:528]),
  .b_i(e63_up[0+:528]), .b_o(e63_down[0+:528]) );
 // rly_lnkh_0E_3_4: lnkh_0E_3__r4[0] <-> lnkh_0E_3__r5[0]
 ot_qwen_die_link_fwd_full #(.NL(1),.ENABLE(ENABLE)) u_stage_90 (
  .rst_n(link_por_n),
  .fclk_ab_i(e63_dclk[0]), .fclk_ab_o(e64_dclk[0]),
  .fclk_ba_i(e64_uclk[0]), .fclk_ba_o(e63_uclk[0]),
  .a_i(e63_down[0+:528]), .a_o(e63_up[0+:528]),
  .b_i(e64_up[0+:528]), .b_o(e64_down[0+:528]) );
 // rly_lnkh_0E_3_5: lnkh_0E_3__r5[0] <-> lnkh_0E_3__r6[0]
 ot_qwen_die_link_fwd_full #(.NL(1),.ENABLE(ENABLE)) u_stage_91 (
  .rst_n(link_por_n),
  .fclk_ab_i(e64_dclk[0]), .fclk_ab_o(e65_dclk[0]),
  .fclk_ba_i(e65_uclk[0]), .fclk_ba_o(e64_uclk[0]),
  .a_i(e64_down[0+:528]), .a_o(e64_up[0+:528]),
  .b_i(e65_up[0+:528]), .b_o(e65_down[0+:528]) );
 // rly_lnkh_0E_4_0: lnkh_0E_4[0] <-> lnkh_0E_4__r1[0]
 ot_qwen_die_link_fwd_full #(.NL(1),.ENABLE(ENABLE)) u_stage_92 (
  .rst_n(link_por_n),
  .fclk_ab_i(e66_dclk[0]), .fclk_ab_o(e67_dclk[0]),
  .fclk_ba_i(e67_uclk[0]), .fclk_ba_o(e66_uclk[0]),
  .a_i(e66_down[0+:528]), .a_o(e66_up[0+:528]),
  .b_i(e67_up[0+:528]), .b_o(e67_down[0+:528]) );
 // rly_lnkh_0E_4_1: lnkh_0E_4__r1[0] <-> lnkh_0E_4__r2[0]
 ot_qwen_die_link_fwd_full #(.NL(1),.ENABLE(ENABLE)) u_stage_93 (
  .rst_n(link_por_n),
  .fclk_ab_i(e67_dclk[0]), .fclk_ab_o(e68_dclk[0]),
  .fclk_ba_i(e68_uclk[0]), .fclk_ba_o(e67_uclk[0]),
  .a_i(e67_down[0+:528]), .a_o(e67_up[0+:528]),
  .b_i(e68_up[0+:528]), .b_o(e68_down[0+:528]) );
 // rly_lnkh_0E_4_2: lnkh_0E_4__r2[0] <-> lnkh_0E_4__r3[0]
 ot_qwen_die_link_fwd_full #(.NL(1),.ENABLE(ENABLE)) u_stage_94 (
  .rst_n(link_por_n),
  .fclk_ab_i(e68_dclk[0]), .fclk_ab_o(e69_dclk[0]),
  .fclk_ba_i(e69_uclk[0]), .fclk_ba_o(e68_uclk[0]),
  .a_i(e68_down[0+:528]), .a_o(e68_up[0+:528]),
  .b_i(e69_up[0+:528]), .b_o(e69_down[0+:528]) );
 // rly_lnkh_0E_4_3: lnkh_0E_4__r3[0] <-> lnkh_0E_4__r4[0]
 ot_qwen_die_link_fwd_full #(.NL(1),.ENABLE(ENABLE)) u_stage_95 (
  .rst_n(link_por_n),
  .fclk_ab_i(e69_dclk[0]), .fclk_ab_o(e70_dclk[0]),
  .fclk_ba_i(e70_uclk[0]), .fclk_ba_o(e69_uclk[0]),
  .a_i(e69_down[0+:528]), .a_o(e69_up[0+:528]),
  .b_i(e70_up[0+:528]), .b_o(e70_down[0+:528]) );
 // rly_lnkh_0E_4_4: lnkh_0E_4__r4[0] <-> lnkh_0E_4__r5[0]
 ot_qwen_die_link_fwd_full #(.NL(1),.ENABLE(ENABLE)) u_stage_96 (
  .rst_n(link_por_n),
  .fclk_ab_i(e70_dclk[0]), .fclk_ab_o(e71_dclk[0]),
  .fclk_ba_i(e71_uclk[0]), .fclk_ba_o(e70_uclk[0]),
  .a_i(e70_down[0+:528]), .a_o(e70_up[0+:528]),
  .b_i(e71_up[0+:528]), .b_o(e71_down[0+:528]) );
 // rly_lnkh_0E_f_0: lnkh_0E_f[0] <-> lnkh_0E_f__r1[0]
 ot_qwen_die_link_fwd_full #(.NL(1),.ENABLE(ENABLE)) u_stage_97 (
  .rst_n(link_por_n),
  .fclk_ab_i(e72_dclk[0]), .fclk_ab_o(e73_dclk[0]),
  .fclk_ba_i(e73_uclk[0]), .fclk_ba_o(e72_uclk[0]),
  .a_i(e72_down[0+:528]), .a_o(e72_up[0+:528]),
  .b_i(e73_up[0+:528]), .b_o(e73_down[0+:528]) );
 // rly_lnkh_0E_f_1: lnkh_0E_f__r1[0] <-> lnkh_0E_f__r2[0]
 ot_qwen_die_link_fwd_full #(.NL(1),.ENABLE(ENABLE)) u_stage_98 (
  .rst_n(link_por_n),
  .fclk_ab_i(e73_dclk[0]), .fclk_ab_o(e74_dclk[0]),
  .fclk_ba_i(e74_uclk[0]), .fclk_ba_o(e73_uclk[0]),
  .a_i(e73_down[0+:528]), .a_o(e73_up[0+:528]),
  .b_i(e74_up[0+:528]), .b_o(e74_down[0+:528]) );
 // rly_lnkh_0E_f_2: lnkh_0E_f__r2[0] <-> lnkh_0E_f__r3[0]
 ot_qwen_die_link_fwd_full #(.NL(1),.ENABLE(ENABLE)) u_stage_99 (
  .rst_n(link_por_n),
  .fclk_ab_i(e74_dclk[0]), .fclk_ab_o(e75_dclk[0]),
  .fclk_ba_i(e75_uclk[0]), .fclk_ba_o(e74_uclk[0]),
  .a_i(e74_down[0+:528]), .a_o(e74_up[0+:528]),
  .b_i(e75_up[0+:528]), .b_o(e75_down[0+:528]) );
 // rly_lnkh_0E_f_3: lnkh_0E_f__r3[0] <-> lnkh_0E_f__r4[0]
 ot_qwen_die_link_fwd_full #(.NL(1),.ENABLE(ENABLE)) u_stage_100 (
  .rst_n(link_por_n),
  .fclk_ab_i(e75_dclk[0]), .fclk_ab_o(e76_dclk[0]),
  .fclk_ba_i(e76_uclk[0]), .fclk_ba_o(e75_uclk[0]),
  .a_i(e75_down[0+:528]), .a_o(e75_up[0+:528]),
  .b_i(e76_up[0+:528]), .b_o(e76_down[0+:528]) );
 // rly_lnkh_0E_f_4: lnkh_0E_f__r4[0] <-> lnkh_0E_f__r5[0]
 ot_qwen_die_link_fwd_full #(.NL(1),.ENABLE(ENABLE)) u_stage_101 (
  .rst_n(link_por_n),
  .fclk_ab_i(e76_dclk[0]), .fclk_ab_o(e77_dclk[0]),
  .fclk_ba_i(e77_uclk[0]), .fclk_ba_o(e76_uclk[0]),
  .a_i(e76_down[0+:528]), .a_o(e76_up[0+:528]),
  .b_i(e77_up[0+:528]), .b_o(e77_down[0+:528]) );
 // rly_lnkv_1_0_0: lnkv_1_0[0] <-> lnkv_1_0__r1[0]
 ot_qwen_die_link_fwd_full #(.NL(1),.ENABLE(ENABLE)) u_stage_102 (
  .rst_n(link_por_n),
  .fclk_ab_i(e78_dclk[0]), .fclk_ab_o(e79_dclk[0]),
  .fclk_ba_i(e79_uclk[0]), .fclk_ba_o(e78_uclk[0]),
  .a_i(e78_down[0+:528]), .a_o(e78_up[0+:528]),
  .b_i(e79_up[0+:528]), .b_o(e79_down[0+:528]) );
 // rly_lnkv_1_0_0: lnkv_1_0[1] <-> lnkv_1_0__r1[1]
 ot_qwen_die_link_fwd_full #(.NL(1),.ENABLE(ENABLE)) u_stage_103 (
  .rst_n(link_por_n),
  .fclk_ab_i(e78_dclk[1]), .fclk_ab_o(e79_dclk[1]),
  .fclk_ba_i(e79_uclk[1]), .fclk_ba_o(e78_uclk[1]),
  .a_i(e78_down[528+:528]), .a_o(e78_up[528+:528]),
  .b_i(e79_up[528+:528]), .b_o(e79_down[528+:528]) );
 // rly_lnkv_1_0_1: lnkv_1_0__r1[0] <-> lnkv_1_0__r2[0]
 ot_qwen_die_link_fwd_full #(.NL(1),.ENABLE(ENABLE)) u_stage_104 (
  .rst_n(link_por_n),
  .fclk_ab_i(e79_dclk[0]), .fclk_ab_o(e80_dclk[0]),
  .fclk_ba_i(e80_uclk[0]), .fclk_ba_o(e79_uclk[0]),
  .a_i(e79_down[0+:528]), .a_o(e79_up[0+:528]),
  .b_i(e80_up[0+:528]), .b_o(e80_down[0+:528]) );
 // rly_lnkv_1_0_1: lnkv_1_0__r1[1] <-> lnkv_1_0__r2[1]
 ot_qwen_die_link_fwd_full #(.NL(1),.ENABLE(ENABLE)) u_stage_105 (
  .rst_n(link_por_n),
  .fclk_ab_i(e79_dclk[1]), .fclk_ab_o(e80_dclk[1]),
  .fclk_ba_i(e80_uclk[1]), .fclk_ba_o(e79_uclk[1]),
  .a_i(e79_down[528+:528]), .a_o(e79_up[528+:528]),
  .b_i(e80_up[528+:528]), .b_o(e80_down[528+:528]) );
 // rly_lnkv_1_0_2: lnkv_1_0__r2[0] <-> lnkv_1_0__r3[0]
 ot_qwen_die_link_fwd_full #(.NL(1),.ENABLE(ENABLE)) u_stage_106 (
  .rst_n(link_por_n),
  .fclk_ab_i(e80_dclk[0]), .fclk_ab_o(e81_dclk[0]),
  .fclk_ba_i(e81_uclk[0]), .fclk_ba_o(e80_uclk[0]),
  .a_i(e80_down[0+:528]), .a_o(e80_up[0+:528]),
  .b_i(e81_up[0+:528]), .b_o(e81_down[0+:528]) );
 // rly_lnkv_1_0_2: lnkv_1_0__r2[1] <-> lnkv_1_0__r3[1]
 ot_qwen_die_link_fwd_full #(.NL(1),.ENABLE(ENABLE)) u_stage_107 (
  .rst_n(link_por_n),
  .fclk_ab_i(e80_dclk[1]), .fclk_ab_o(e81_dclk[1]),
  .fclk_ba_i(e81_uclk[1]), .fclk_ba_o(e80_uclk[1]),
  .a_i(e80_down[528+:528]), .a_o(e80_up[528+:528]),
  .b_i(e81_up[528+:528]), .b_o(e81_down[528+:528]) );
 // rly_lnkv_1_0_3: lnkv_1_0__r3[0] <-> lnkv_1_0__r4[0]
 ot_qwen_die_link_fwd_full #(.NL(1),.ENABLE(ENABLE)) u_stage_108 (
  .rst_n(link_por_n),
  .fclk_ab_i(e81_dclk[0]), .fclk_ab_o(e82_dclk[0]),
  .fclk_ba_i(e82_uclk[0]), .fclk_ba_o(e81_uclk[0]),
  .a_i(e81_down[0+:528]), .a_o(e81_up[0+:528]),
  .b_i(e82_up[0+:528]), .b_o(e82_down[0+:528]) );
 // rly_lnkv_1_0_3: lnkv_1_0__r3[1] <-> lnkv_1_0__r4[1]
 ot_qwen_die_link_fwd_full #(.NL(1),.ENABLE(ENABLE)) u_stage_109 (
  .rst_n(link_por_n),
  .fclk_ab_i(e81_dclk[1]), .fclk_ab_o(e82_dclk[1]),
  .fclk_ba_i(e82_uclk[1]), .fclk_ba_o(e81_uclk[1]),
  .a_i(e81_down[528+:528]), .a_o(e81_up[528+:528]),
  .b_i(e82_up[528+:528]), .b_o(e82_down[528+:528]) );
 // rly_lnkv_1_1_0: lnkv_1_1[0] <-> lnkv_1_1__r1[0]
 ot_qwen_die_link_fwd_full #(.NL(1),.ENABLE(ENABLE)) u_stage_110 (
  .rst_n(link_por_n),
  .fclk_ab_i(e83_dclk[0]), .fclk_ab_o(e84_dclk[0]),
  .fclk_ba_i(e84_uclk[0]), .fclk_ba_o(e83_uclk[0]),
  .a_i(e83_down[0+:528]), .a_o(e83_up[0+:528]),
  .b_i(e84_up[0+:528]), .b_o(e84_down[0+:528]) );
 // rly_lnkv_1_1_0: lnkv_1_1[1] <-> lnkv_1_1__r1[1]
 ot_qwen_die_link_fwd_full #(.NL(1),.ENABLE(ENABLE)) u_stage_111 (
  .rst_n(link_por_n),
  .fclk_ab_i(e83_dclk[1]), .fclk_ab_o(e84_dclk[1]),
  .fclk_ba_i(e84_uclk[1]), .fclk_ba_o(e83_uclk[1]),
  .a_i(e83_down[528+:528]), .a_o(e83_up[528+:528]),
  .b_i(e84_up[528+:528]), .b_o(e84_down[528+:528]) );
 // rly_lnkv_1_1_1: lnkv_1_1__r1[0] <-> lnkv_1_1__r2[0]
 ot_qwen_die_link_fwd_full #(.NL(1),.ENABLE(ENABLE)) u_stage_112 (
  .rst_n(link_por_n),
  .fclk_ab_i(e84_dclk[0]), .fclk_ab_o(e85_dclk[0]),
  .fclk_ba_i(e85_uclk[0]), .fclk_ba_o(e84_uclk[0]),
  .a_i(e84_down[0+:528]), .a_o(e84_up[0+:528]),
  .b_i(e85_up[0+:528]), .b_o(e85_down[0+:528]) );
 // rly_lnkv_1_1_1: lnkv_1_1__r1[1] <-> lnkv_1_1__r2[1]
 ot_qwen_die_link_fwd_full #(.NL(1),.ENABLE(ENABLE)) u_stage_113 (
  .rst_n(link_por_n),
  .fclk_ab_i(e84_dclk[1]), .fclk_ab_o(e85_dclk[1]),
  .fclk_ba_i(e85_uclk[1]), .fclk_ba_o(e84_uclk[1]),
  .a_i(e84_down[528+:528]), .a_o(e84_up[528+:528]),
  .b_i(e85_up[528+:528]), .b_o(e85_down[528+:528]) );
 // rly_lnkv_1_1_2: lnkv_1_1__r2[0] <-> lnkv_1_1__r3[0]
 ot_qwen_die_link_fwd_full #(.NL(1),.ENABLE(ENABLE)) u_stage_114 (
  .rst_n(link_por_n),
  .fclk_ab_i(e85_dclk[0]), .fclk_ab_o(e86_dclk[0]),
  .fclk_ba_i(e86_uclk[0]), .fclk_ba_o(e85_uclk[0]),
  .a_i(e85_down[0+:528]), .a_o(e85_up[0+:528]),
  .b_i(e86_up[0+:528]), .b_o(e86_down[0+:528]) );
 // rly_lnkv_1_1_2: lnkv_1_1__r2[1] <-> lnkv_1_1__r3[1]
 ot_qwen_die_link_fwd_full #(.NL(1),.ENABLE(ENABLE)) u_stage_115 (
  .rst_n(link_por_n),
  .fclk_ab_i(e85_dclk[1]), .fclk_ab_o(e86_dclk[1]),
  .fclk_ba_i(e86_uclk[1]), .fclk_ba_o(e85_uclk[1]),
  .a_i(e85_down[528+:528]), .a_o(e85_up[528+:528]),
  .b_i(e86_up[528+:528]), .b_o(e86_down[528+:528]) );
 // rly_lnkv_1_2_0: lnkv_1_2[0] <-> lnkv_1_2__r1[0]
 ot_qwen_die_link_fwd_full #(.NL(1),.ENABLE(ENABLE)) u_stage_116 (
  .rst_n(link_por_n),
  .fclk_ab_i(e87_dclk[0]), .fclk_ab_o(e88_dclk[0]),
  .fclk_ba_i(e88_uclk[0]), .fclk_ba_o(e87_uclk[0]),
  .a_i(e87_down[0+:528]), .a_o(e87_up[0+:528]),
  .b_i(e88_up[0+:528]), .b_o(e88_down[0+:528]) );
 // rly_lnkv_1_2_0: lnkv_1_2[1] <-> lnkv_1_2__r1[1]
 ot_qwen_die_link_fwd_full #(.NL(1),.ENABLE(ENABLE)) u_stage_117 (
  .rst_n(link_por_n),
  .fclk_ab_i(e87_dclk[1]), .fclk_ab_o(e88_dclk[1]),
  .fclk_ba_i(e88_uclk[1]), .fclk_ba_o(e87_uclk[1]),
  .a_i(e87_down[528+:528]), .a_o(e87_up[528+:528]),
  .b_i(e88_up[528+:528]), .b_o(e88_down[528+:528]) );
 // rly_lnkv_1_2_1: lnkv_1_2__r1[0] <-> lnkv_1_2__r2[0]
 ot_qwen_die_link_fwd_full #(.NL(1),.ENABLE(ENABLE)) u_stage_118 (
  .rst_n(link_por_n),
  .fclk_ab_i(e88_dclk[0]), .fclk_ab_o(e89_dclk[0]),
  .fclk_ba_i(e89_uclk[0]), .fclk_ba_o(e88_uclk[0]),
  .a_i(e88_down[0+:528]), .a_o(e88_up[0+:528]),
  .b_i(e89_up[0+:528]), .b_o(e89_down[0+:528]) );
 // rly_lnkv_1_2_1: lnkv_1_2__r1[1] <-> lnkv_1_2__r2[1]
 ot_qwen_die_link_fwd_full #(.NL(1),.ENABLE(ENABLE)) u_stage_119 (
  .rst_n(link_por_n),
  .fclk_ab_i(e88_dclk[1]), .fclk_ab_o(e89_dclk[1]),
  .fclk_ba_i(e89_uclk[1]), .fclk_ba_o(e88_uclk[1]),
  .a_i(e88_down[528+:528]), .a_o(e88_up[528+:528]),
  .b_i(e89_up[528+:528]), .b_o(e89_down[528+:528]) );
 // rly_lnkv_1_2_2: lnkv_1_2__r2[0] <-> lnkv_1_2__r3[0]
 ot_qwen_die_link_fwd_full #(.NL(1),.ENABLE(ENABLE)) u_stage_120 (
  .rst_n(link_por_n),
  .fclk_ab_i(e89_dclk[0]), .fclk_ab_o(e90_dclk[0]),
  .fclk_ba_i(e90_uclk[0]), .fclk_ba_o(e89_uclk[0]),
  .a_i(e89_down[0+:528]), .a_o(e89_up[0+:528]),
  .b_i(e90_up[0+:528]), .b_o(e90_down[0+:528]) );
 // rly_lnkv_1_2_2: lnkv_1_2__r2[1] <-> lnkv_1_2__r3[1]
 ot_qwen_die_link_fwd_full #(.NL(1),.ENABLE(ENABLE)) u_stage_121 (
  .rst_n(link_por_n),
  .fclk_ab_i(e89_dclk[1]), .fclk_ab_o(e90_dclk[1]),
  .fclk_ba_i(e90_uclk[1]), .fclk_ba_o(e89_uclk[1]),
  .a_i(e89_down[528+:528]), .a_o(e89_up[528+:528]),
  .b_i(e90_up[528+:528]), .b_o(e90_down[528+:528]) );
 // rly_lnkv_1_c_0: lnkv_1_c[0] <-> lnkv_1_c__r1[0]
 ot_qwen_die_link_fwd_full #(.NL(1),.ENABLE(ENABLE)) u_stage_122 (
  .rst_n(link_por_n),
  .fclk_ab_i(e91_dclk[0]), .fclk_ab_o(e92_dclk[0]),
  .fclk_ba_i(e92_uclk[0]), .fclk_ba_o(e91_uclk[0]),
  .a_i(e91_down[0+:528]), .a_o(e91_up[0+:528]),
  .b_i(e92_up[0+:528]), .b_o(e92_down[0+:528]) );
 // rly_lnkv_1_c_0: lnkv_1_c[1] <-> lnkv_1_c__r1[1]
 ot_qwen_die_link_fwd_full #(.NL(1),.ENABLE(ENABLE)) u_stage_123 (
  .rst_n(link_por_n),
  .fclk_ab_i(e91_dclk[1]), .fclk_ab_o(e92_dclk[1]),
  .fclk_ba_i(e92_uclk[1]), .fclk_ba_o(e91_uclk[1]),
  .a_i(e91_down[528+:528]), .a_o(e91_up[528+:528]),
  .b_i(e92_up[528+:528]), .b_o(e92_down[528+:528]) );
 // rly_lnkv_1_c_1: lnkv_1_c__r1[0] <-> lnkv_1_c__r2[0]
 ot_qwen_die_link_fwd_full #(.NL(1),.ENABLE(ENABLE)) u_stage_124 (
  .rst_n(link_por_n),
  .fclk_ab_i(e92_dclk[0]), .fclk_ab_o(e93_dclk[0]),
  .fclk_ba_i(e93_uclk[0]), .fclk_ba_o(e92_uclk[0]),
  .a_i(e92_down[0+:528]), .a_o(e92_up[0+:528]),
  .b_i(e93_up[0+:528]), .b_o(e93_down[0+:528]) );
 // rly_lnkv_1_c_1: lnkv_1_c__r1[1] <-> lnkv_1_c__r2[1]
 ot_qwen_die_link_fwd_full #(.NL(1),.ENABLE(ENABLE)) u_stage_125 (
  .rst_n(link_por_n),
  .fclk_ab_i(e92_dclk[1]), .fclk_ab_o(e93_dclk[1]),
  .fclk_ba_i(e93_uclk[1]), .fclk_ba_o(e92_uclk[1]),
  .a_i(e92_down[528+:528]), .a_o(e92_up[528+:528]),
  .b_i(e93_up[528+:528]), .b_o(e93_down[528+:528]) );
 // rly_lnkh_1W_0_0: lnkh_1W_0[0] <-> lnkh_1W_0__r1[0]
 ot_qwen_die_link_fwd_full #(.NL(1),.ENABLE(ENABLE)) u_stage_126 (
  .rst_n(link_por_n),
  .fclk_ab_i(e94_dclk[0]), .fclk_ab_o(e95_dclk[0]),
  .fclk_ba_i(e95_uclk[0]), .fclk_ba_o(e94_uclk[0]),
  .a_i(e94_down[0+:528]), .a_o(e94_up[0+:528]),
  .b_i(e95_up[0+:528]), .b_o(e95_down[0+:528]) );
 // rly_lnkh_1W_0_1: lnkh_1W_0__r1[0] <-> lnkh_1W_0__r2[0]
 ot_qwen_die_link_fwd_full #(.NL(1),.ENABLE(ENABLE)) u_stage_127 (
  .rst_n(link_por_n),
  .fclk_ab_i(e95_dclk[0]), .fclk_ab_o(e96_dclk[0]),
  .fclk_ba_i(e96_uclk[0]), .fclk_ba_o(e95_uclk[0]),
  .a_i(e95_down[0+:528]), .a_o(e95_up[0+:528]),
  .b_i(e96_up[0+:528]), .b_o(e96_down[0+:528]) );
 // rly_lnkh_1W_0_2: lnkh_1W_0__r2[0] <-> lnkh_1W_0__r3[0]
 ot_qwen_die_link_fwd_full #(.NL(1),.ENABLE(ENABLE)) u_stage_128 (
  .rst_n(link_por_n),
  .fclk_ab_i(e96_dclk[0]), .fclk_ab_o(e97_dclk[0]),
  .fclk_ba_i(e97_uclk[0]), .fclk_ba_o(e96_uclk[0]),
  .a_i(e96_down[0+:528]), .a_o(e96_up[0+:528]),
  .b_i(e97_up[0+:528]), .b_o(e97_down[0+:528]) );
 // rly_lnkh_1W_0_3: lnkh_1W_0__r3[0] <-> lnkh_1W_0__r4[0]
 ot_qwen_die_link_fwd_full #(.NL(1),.ENABLE(ENABLE)) u_stage_129 (
  .rst_n(link_por_n),
  .fclk_ab_i(e97_dclk[0]), .fclk_ab_o(e98_dclk[0]),
  .fclk_ba_i(e98_uclk[0]), .fclk_ba_o(e97_uclk[0]),
  .a_i(e97_down[0+:528]), .a_o(e97_up[0+:528]),
  .b_i(e98_up[0+:528]), .b_o(e98_down[0+:528]) );
 // rly_lnkh_1W_0_4: lnkh_1W_0__r4[0] <-> lnkh_1W_0__r5[0]
 ot_qwen_die_link_fwd_full #(.NL(1),.ENABLE(ENABLE)) u_stage_130 (
  .rst_n(link_por_n),
  .fclk_ab_i(e98_dclk[0]), .fclk_ab_o(e99_dclk[0]),
  .fclk_ba_i(e99_uclk[0]), .fclk_ba_o(e98_uclk[0]),
  .a_i(e98_down[0+:528]), .a_o(e98_up[0+:528]),
  .b_i(e99_up[0+:528]), .b_o(e99_down[0+:528]) );
 // rly_lnkh_1W_0_5: lnkh_1W_0__r5[0] <-> lnkh_1W_0__r6[0]
 ot_qwen_die_link_fwd_full #(.NL(1),.ENABLE(ENABLE)) u_stage_131 (
  .rst_n(link_por_n),
  .fclk_ab_i(e99_dclk[0]), .fclk_ab_o(e100_dclk[0]),
  .fclk_ba_i(e100_uclk[0]), .fclk_ba_o(e99_uclk[0]),
  .a_i(e99_down[0+:528]), .a_o(e99_up[0+:528]),
  .b_i(e100_up[0+:528]), .b_o(e100_down[0+:528]) );
 // rly_lnkh_1W_0_6: lnkh_1W_0__r6[0] <-> lnkh_1W_0__r7[0]
 ot_qwen_die_link_fwd_full #(.NL(1),.ENABLE(ENABLE)) u_stage_132 (
  .rst_n(link_por_n),
  .fclk_ab_i(e100_dclk[0]), .fclk_ab_o(e101_dclk[0]),
  .fclk_ba_i(e101_uclk[0]), .fclk_ba_o(e100_uclk[0]),
  .a_i(e100_down[0+:528]), .a_o(e100_up[0+:528]),
  .b_i(e101_up[0+:528]), .b_o(e101_down[0+:528]) );
 // rly_lnkh_1W_1_0: lnkh_1W_1[0] <-> lnkh_1W_1__r1[0]
 ot_qwen_die_link_fwd_full #(.NL(1),.ENABLE(ENABLE)) u_stage_133 (
  .rst_n(link_por_n),
  .fclk_ab_i(e102_dclk[0]), .fclk_ab_o(e103_dclk[0]),
  .fclk_ba_i(e103_uclk[0]), .fclk_ba_o(e102_uclk[0]),
  .a_i(e102_down[0+:528]), .a_o(e102_up[0+:528]),
  .b_i(e103_up[0+:528]), .b_o(e103_down[0+:528]) );
 // rly_lnkh_1W_1_1: lnkh_1W_1__r1[0] <-> lnkh_1W_1__r2[0]
 ot_qwen_die_link_fwd_full #(.NL(1),.ENABLE(ENABLE)) u_stage_134 (
  .rst_n(link_por_n),
  .fclk_ab_i(e103_dclk[0]), .fclk_ab_o(e104_dclk[0]),
  .fclk_ba_i(e104_uclk[0]), .fclk_ba_o(e103_uclk[0]),
  .a_i(e103_down[0+:528]), .a_o(e103_up[0+:528]),
  .b_i(e104_up[0+:528]), .b_o(e104_down[0+:528]) );
 // rly_lnkh_1W_1_2: lnkh_1W_1__r2[0] <-> lnkh_1W_1__r3[0]
 ot_qwen_die_link_fwd_full #(.NL(1),.ENABLE(ENABLE)) u_stage_135 (
  .rst_n(link_por_n),
  .fclk_ab_i(e104_dclk[0]), .fclk_ab_o(e105_dclk[0]),
  .fclk_ba_i(e105_uclk[0]), .fclk_ba_o(e104_uclk[0]),
  .a_i(e104_down[0+:528]), .a_o(e104_up[0+:528]),
  .b_i(e105_up[0+:528]), .b_o(e105_down[0+:528]) );
 // rly_lnkh_1W_1_3: lnkh_1W_1__r3[0] <-> lnkh_1W_1__r4[0]
 ot_qwen_die_link_fwd_full #(.NL(1),.ENABLE(ENABLE)) u_stage_136 (
  .rst_n(link_por_n),
  .fclk_ab_i(e105_dclk[0]), .fclk_ab_o(e106_dclk[0]),
  .fclk_ba_i(e106_uclk[0]), .fclk_ba_o(e105_uclk[0]),
  .a_i(e105_down[0+:528]), .a_o(e105_up[0+:528]),
  .b_i(e106_up[0+:528]), .b_o(e106_down[0+:528]) );
 // rly_lnkh_1W_1_4: lnkh_1W_1__r4[0] <-> lnkh_1W_1__r5[0]
 ot_qwen_die_link_fwd_full #(.NL(1),.ENABLE(ENABLE)) u_stage_137 (
  .rst_n(link_por_n),
  .fclk_ab_i(e106_dclk[0]), .fclk_ab_o(e107_dclk[0]),
  .fclk_ba_i(e107_uclk[0]), .fclk_ba_o(e106_uclk[0]),
  .a_i(e106_down[0+:528]), .a_o(e106_up[0+:528]),
  .b_i(e107_up[0+:528]), .b_o(e107_down[0+:528]) );
 // rly_lnkh_1W_1_5: lnkh_1W_1__r5[0] <-> lnkh_1W_1__r6[0]
 ot_qwen_die_link_fwd_full #(.NL(1),.ENABLE(ENABLE)) u_stage_138 (
  .rst_n(link_por_n),
  .fclk_ab_i(e107_dclk[0]), .fclk_ab_o(e108_dclk[0]),
  .fclk_ba_i(e108_uclk[0]), .fclk_ba_o(e107_uclk[0]),
  .a_i(e107_down[0+:528]), .a_o(e107_up[0+:528]),
  .b_i(e108_up[0+:528]), .b_o(e108_down[0+:528]) );
 // rly_lnkh_1W_2_0: lnkh_1W_2[0] <-> lnkh_1W_2__r1[0]
 ot_qwen_die_link_fwd_full #(.NL(1),.ENABLE(ENABLE)) u_stage_139 (
  .rst_n(link_por_n),
  .fclk_ab_i(e109_dclk[0]), .fclk_ab_o(e110_dclk[0]),
  .fclk_ba_i(e110_uclk[0]), .fclk_ba_o(e109_uclk[0]),
  .a_i(e109_down[0+:528]), .a_o(e109_up[0+:528]),
  .b_i(e110_up[0+:528]), .b_o(e110_down[0+:528]) );
 // rly_lnkh_1W_2_1: lnkh_1W_2__r1[0] <-> lnkh_1W_2__r2[0]
 ot_qwen_die_link_fwd_full #(.NL(1),.ENABLE(ENABLE)) u_stage_140 (
  .rst_n(link_por_n),
  .fclk_ab_i(e110_dclk[0]), .fclk_ab_o(e111_dclk[0]),
  .fclk_ba_i(e111_uclk[0]), .fclk_ba_o(e110_uclk[0]),
  .a_i(e110_down[0+:528]), .a_o(e110_up[0+:528]),
  .b_i(e111_up[0+:528]), .b_o(e111_down[0+:528]) );
 // rly_lnkh_1W_2_2: lnkh_1W_2__r2[0] <-> lnkh_1W_2__r3[0]
 ot_qwen_die_link_fwd_full #(.NL(1),.ENABLE(ENABLE)) u_stage_141 (
  .rst_n(link_por_n),
  .fclk_ab_i(e111_dclk[0]), .fclk_ab_o(e112_dclk[0]),
  .fclk_ba_i(e112_uclk[0]), .fclk_ba_o(e111_uclk[0]),
  .a_i(e111_down[0+:528]), .a_o(e111_up[0+:528]),
  .b_i(e112_up[0+:528]), .b_o(e112_down[0+:528]) );
 // rly_lnkh_1W_2_3: lnkh_1W_2__r3[0] <-> lnkh_1W_2__r4[0]
 ot_qwen_die_link_fwd_full #(.NL(1),.ENABLE(ENABLE)) u_stage_142 (
  .rst_n(link_por_n),
  .fclk_ab_i(e112_dclk[0]), .fclk_ab_o(e113_dclk[0]),
  .fclk_ba_i(e113_uclk[0]), .fclk_ba_o(e112_uclk[0]),
  .a_i(e112_down[0+:528]), .a_o(e112_up[0+:528]),
  .b_i(e113_up[0+:528]), .b_o(e113_down[0+:528]) );
 // rly_lnkh_1W_2_4: lnkh_1W_2__r4[0] <-> lnkh_1W_2__r5[0]
 ot_qwen_die_link_fwd_full #(.NL(1),.ENABLE(ENABLE)) u_stage_143 (
  .rst_n(link_por_n),
  .fclk_ab_i(e113_dclk[0]), .fclk_ab_o(e114_dclk[0]),
  .fclk_ba_i(e114_uclk[0]), .fclk_ba_o(e113_uclk[0]),
  .a_i(e113_down[0+:528]), .a_o(e113_up[0+:528]),
  .b_i(e114_up[0+:528]), .b_o(e114_down[0+:528]) );
 // rly_lnkh_1W_3_0: lnkh_1W_3[0] <-> lnkh_1W_3__r1[0]
 ot_qwen_die_link_fwd_full #(.NL(1),.ENABLE(ENABLE)) u_stage_144 (
  .rst_n(link_por_n),
  .fclk_ab_i(e115_dclk[0]), .fclk_ab_o(e116_dclk[0]),
  .fclk_ba_i(e116_uclk[0]), .fclk_ba_o(e115_uclk[0]),
  .a_i(e115_down[0+:528]), .a_o(e115_up[0+:528]),
  .b_i(e116_up[0+:528]), .b_o(e116_down[0+:528]) );
 // rly_lnkh_1W_3_1: lnkh_1W_3__r1[0] <-> lnkh_1W_3__r2[0]
 ot_qwen_die_link_fwd_full #(.NL(1),.ENABLE(ENABLE)) u_stage_145 (
  .rst_n(link_por_n),
  .fclk_ab_i(e116_dclk[0]), .fclk_ab_o(e117_dclk[0]),
  .fclk_ba_i(e117_uclk[0]), .fclk_ba_o(e116_uclk[0]),
  .a_i(e116_down[0+:528]), .a_o(e116_up[0+:528]),
  .b_i(e117_up[0+:528]), .b_o(e117_down[0+:528]) );
 // rly_lnkh_1W_3_2: lnkh_1W_3__r2[0] <-> lnkh_1W_3__r3[0]
 ot_qwen_die_link_fwd_full #(.NL(1),.ENABLE(ENABLE)) u_stage_146 (
  .rst_n(link_por_n),
  .fclk_ab_i(e117_dclk[0]), .fclk_ab_o(e118_dclk[0]),
  .fclk_ba_i(e118_uclk[0]), .fclk_ba_o(e117_uclk[0]),
  .a_i(e117_down[0+:528]), .a_o(e117_up[0+:528]),
  .b_i(e118_up[0+:528]), .b_o(e118_down[0+:528]) );
 // rly_lnkh_1W_3_3: lnkh_1W_3__r3[0] <-> lnkh_1W_3__r4[0]
 ot_qwen_die_link_fwd_full #(.NL(1),.ENABLE(ENABLE)) u_stage_147 (
  .rst_n(link_por_n),
  .fclk_ab_i(e118_dclk[0]), .fclk_ab_o(e119_dclk[0]),
  .fclk_ba_i(e119_uclk[0]), .fclk_ba_o(e118_uclk[0]),
  .a_i(e118_down[0+:528]), .a_o(e118_up[0+:528]),
  .b_i(e119_up[0+:528]), .b_o(e119_down[0+:528]) );
 // rly_lnkh_1W_3_4: lnkh_1W_3__r4[0] <-> lnkh_1W_3__r5[0]
 ot_qwen_die_link_fwd_full #(.NL(1),.ENABLE(ENABLE)) u_stage_148 (
  .rst_n(link_por_n),
  .fclk_ab_i(e119_dclk[0]), .fclk_ab_o(e120_dclk[0]),
  .fclk_ba_i(e120_uclk[0]), .fclk_ba_o(e119_uclk[0]),
  .a_i(e119_down[0+:528]), .a_o(e119_up[0+:528]),
  .b_i(e120_up[0+:528]), .b_o(e120_down[0+:528]) );
 // rly_lnkh_1W_4_0: lnkh_1W_4[0] <-> lnkh_1W_4__r1[0]
 ot_qwen_die_link_fwd_full #(.NL(1),.ENABLE(ENABLE)) u_stage_149 (
  .rst_n(link_por_n),
  .fclk_ab_i(e121_dclk[0]), .fclk_ab_o(e122_dclk[0]),
  .fclk_ba_i(e122_uclk[0]), .fclk_ba_o(e121_uclk[0]),
  .a_i(e121_down[0+:528]), .a_o(e121_up[0+:528]),
  .b_i(e122_up[0+:528]), .b_o(e122_down[0+:528]) );
 // rly_lnkh_1W_4_1: lnkh_1W_4__r1[0] <-> lnkh_1W_4__r2[0]
 ot_qwen_die_link_fwd_full #(.NL(1),.ENABLE(ENABLE)) u_stage_150 (
  .rst_n(link_por_n),
  .fclk_ab_i(e122_dclk[0]), .fclk_ab_o(e123_dclk[0]),
  .fclk_ba_i(e123_uclk[0]), .fclk_ba_o(e122_uclk[0]),
  .a_i(e122_down[0+:528]), .a_o(e122_up[0+:528]),
  .b_i(e123_up[0+:528]), .b_o(e123_down[0+:528]) );
 // rly_lnkh_1W_4_2: lnkh_1W_4__r2[0] <-> lnkh_1W_4__r3[0]
 ot_qwen_die_link_fwd_full #(.NL(1),.ENABLE(ENABLE)) u_stage_151 (
  .rst_n(link_por_n),
  .fclk_ab_i(e123_dclk[0]), .fclk_ab_o(e124_dclk[0]),
  .fclk_ba_i(e124_uclk[0]), .fclk_ba_o(e123_uclk[0]),
  .a_i(e123_down[0+:528]), .a_o(e123_up[0+:528]),
  .b_i(e124_up[0+:528]), .b_o(e124_down[0+:528]) );
 // rly_lnkh_1W_4_3: lnkh_1W_4__r3[0] <-> lnkh_1W_4__r4[0]
 ot_qwen_die_link_fwd_full #(.NL(1),.ENABLE(ENABLE)) u_stage_152 (
  .rst_n(link_por_n),
  .fclk_ab_i(e124_dclk[0]), .fclk_ab_o(e125_dclk[0]),
  .fclk_ba_i(e125_uclk[0]), .fclk_ba_o(e124_uclk[0]),
  .a_i(e124_down[0+:528]), .a_o(e124_up[0+:528]),
  .b_i(e125_up[0+:528]), .b_o(e125_down[0+:528]) );
 // rly_lnkh_1W_4_4: lnkh_1W_4__r4[0] <-> lnkh_1W_4__r5[0]
 ot_qwen_die_link_fwd_full #(.NL(1),.ENABLE(ENABLE)) u_stage_153 (
  .rst_n(link_por_n),
  .fclk_ab_i(e125_dclk[0]), .fclk_ab_o(e126_dclk[0]),
  .fclk_ba_i(e126_uclk[0]), .fclk_ba_o(e125_uclk[0]),
  .a_i(e125_down[0+:528]), .a_o(e125_up[0+:528]),
  .b_i(e126_up[0+:528]), .b_o(e126_down[0+:528]) );
 // rly_lnkh_1W_4_5: lnkh_1W_4__r5[0] <-> lnkh_1W_4__r6[0]
 ot_qwen_die_link_fwd_full #(.NL(1),.ENABLE(ENABLE)) u_stage_154 (
  .rst_n(link_por_n),
  .fclk_ab_i(e126_dclk[0]), .fclk_ab_o(e127_dclk[0]),
  .fclk_ba_i(e127_uclk[0]), .fclk_ba_o(e126_uclk[0]),
  .a_i(e126_down[0+:528]), .a_o(e126_up[0+:528]),
  .b_i(e127_up[0+:528]), .b_o(e127_down[0+:528]) );
 // rly_lnkh_1W_f_0: lnkh_1W_f[0] <-> lnkh_1W_f__r1[0]
 ot_qwen_die_link_fwd_full #(.NL(1),.ENABLE(ENABLE)) u_stage_155 (
  .rst_n(link_por_n),
  .fclk_ab_i(e128_dclk[0]), .fclk_ab_o(e129_dclk[0]),
  .fclk_ba_i(e129_uclk[0]), .fclk_ba_o(e128_uclk[0]),
  .a_i(e128_down[0+:528]), .a_o(e128_up[0+:528]),
  .b_i(e129_up[0+:528]), .b_o(e129_down[0+:528]) );
 // rly_lnkh_1W_f_1: lnkh_1W_f__r1[0] <-> lnkh_1W_f__r2[0]
 ot_qwen_die_link_fwd_full #(.NL(1),.ENABLE(ENABLE)) u_stage_156 (
  .rst_n(link_por_n),
  .fclk_ab_i(e129_dclk[0]), .fclk_ab_o(e130_dclk[0]),
  .fclk_ba_i(e130_uclk[0]), .fclk_ba_o(e129_uclk[0]),
  .a_i(e129_down[0+:528]), .a_o(e129_up[0+:528]),
  .b_i(e130_up[0+:528]), .b_o(e130_down[0+:528]) );
 // rly_lnkh_1W_f_2: lnkh_1W_f__r2[0] <-> lnkh_1W_f__r3[0]
 ot_qwen_die_link_fwd_full #(.NL(1),.ENABLE(ENABLE)) u_stage_157 (
  .rst_n(link_por_n),
  .fclk_ab_i(e130_dclk[0]), .fclk_ab_o(e131_dclk[0]),
  .fclk_ba_i(e131_uclk[0]), .fclk_ba_o(e130_uclk[0]),
  .a_i(e130_down[0+:528]), .a_o(e130_up[0+:528]),
  .b_i(e131_up[0+:528]), .b_o(e131_down[0+:528]) );
 // rly_lnkh_1W_f_3: lnkh_1W_f__r3[0] <-> lnkh_1W_f__r4[0]
 ot_qwen_die_link_fwd_full #(.NL(1),.ENABLE(ENABLE)) u_stage_158 (
  .rst_n(link_por_n),
  .fclk_ab_i(e131_dclk[0]), .fclk_ab_o(e132_dclk[0]),
  .fclk_ba_i(e132_uclk[0]), .fclk_ba_o(e131_uclk[0]),
  .a_i(e131_down[0+:528]), .a_o(e131_up[0+:528]),
  .b_i(e132_up[0+:528]), .b_o(e132_down[0+:528]) );
 // rly_lnkh_1E_0_0: lnkh_1E_0[0] <-> lnkh_1E_0__r1[0]
 ot_qwen_die_link_fwd_full #(.NL(1),.ENABLE(ENABLE)) u_stage_159 (
  .rst_n(link_por_n),
  .fclk_ab_i(e133_dclk[0]), .fclk_ab_o(e134_dclk[0]),
  .fclk_ba_i(e134_uclk[0]), .fclk_ba_o(e133_uclk[0]),
  .a_i(e133_down[0+:528]), .a_o(e133_up[0+:528]),
  .b_i(e134_up[0+:528]), .b_o(e134_down[0+:528]) );
 // rly_lnkh_1E_0_1: lnkh_1E_0__r1[0] <-> lnkh_1E_0__r2[0]
 ot_qwen_die_link_fwd_full #(.NL(1),.ENABLE(ENABLE)) u_stage_160 (
  .rst_n(link_por_n),
  .fclk_ab_i(e134_dclk[0]), .fclk_ab_o(e135_dclk[0]),
  .fclk_ba_i(e135_uclk[0]), .fclk_ba_o(e134_uclk[0]),
  .a_i(e134_down[0+:528]), .a_o(e134_up[0+:528]),
  .b_i(e135_up[0+:528]), .b_o(e135_down[0+:528]) );
 // rly_lnkh_1E_0_2: lnkh_1E_0__r2[0] <-> lnkh_1E_0__r3[0]
 ot_qwen_die_link_fwd_full #(.NL(1),.ENABLE(ENABLE)) u_stage_161 (
  .rst_n(link_por_n),
  .fclk_ab_i(e135_dclk[0]), .fclk_ab_o(e136_dclk[0]),
  .fclk_ba_i(e136_uclk[0]), .fclk_ba_o(e135_uclk[0]),
  .a_i(e135_down[0+:528]), .a_o(e135_up[0+:528]),
  .b_i(e136_up[0+:528]), .b_o(e136_down[0+:528]) );
 // rly_lnkh_1E_0_3: lnkh_1E_0__r3[0] <-> lnkh_1E_0__r4[0]
 ot_qwen_die_link_fwd_full #(.NL(1),.ENABLE(ENABLE)) u_stage_162 (
  .rst_n(link_por_n),
  .fclk_ab_i(e136_dclk[0]), .fclk_ab_o(e137_dclk[0]),
  .fclk_ba_i(e137_uclk[0]), .fclk_ba_o(e136_uclk[0]),
  .a_i(e136_down[0+:528]), .a_o(e136_up[0+:528]),
  .b_i(e137_up[0+:528]), .b_o(e137_down[0+:528]) );
 // rly_lnkh_1E_0_4: lnkh_1E_0__r4[0] <-> lnkh_1E_0__r5[0]
 ot_qwen_die_link_fwd_full #(.NL(1),.ENABLE(ENABLE)) u_stage_163 (
  .rst_n(link_por_n),
  .fclk_ab_i(e137_dclk[0]), .fclk_ab_o(e138_dclk[0]),
  .fclk_ba_i(e138_uclk[0]), .fclk_ba_o(e137_uclk[0]),
  .a_i(e137_down[0+:528]), .a_o(e137_up[0+:528]),
  .b_i(e138_up[0+:528]), .b_o(e138_down[0+:528]) );
 // rly_lnkh_1E_0_5: lnkh_1E_0__r5[0] <-> lnkh_1E_0__r6[0]
 ot_qwen_die_link_fwd_full #(.NL(1),.ENABLE(ENABLE)) u_stage_164 (
  .rst_n(link_por_n),
  .fclk_ab_i(e138_dclk[0]), .fclk_ab_o(e139_dclk[0]),
  .fclk_ba_i(e139_uclk[0]), .fclk_ba_o(e138_uclk[0]),
  .a_i(e138_down[0+:528]), .a_o(e138_up[0+:528]),
  .b_i(e139_up[0+:528]), .b_o(e139_down[0+:528]) );
 // rly_lnkh_1E_1_0: lnkh_1E_1[0] <-> lnkh_1E_1__r1[0]
 ot_qwen_die_link_fwd_full #(.NL(1),.ENABLE(ENABLE)) u_stage_165 (
  .rst_n(link_por_n),
  .fclk_ab_i(e140_dclk[0]), .fclk_ab_o(e141_dclk[0]),
  .fclk_ba_i(e141_uclk[0]), .fclk_ba_o(e140_uclk[0]),
  .a_i(e140_down[0+:528]), .a_o(e140_up[0+:528]),
  .b_i(e141_up[0+:528]), .b_o(e141_down[0+:528]) );
 // rly_lnkh_1E_1_1: lnkh_1E_1__r1[0] <-> lnkh_1E_1__r2[0]
 ot_qwen_die_link_fwd_full #(.NL(1),.ENABLE(ENABLE)) u_stage_166 (
  .rst_n(link_por_n),
  .fclk_ab_i(e141_dclk[0]), .fclk_ab_o(e142_dclk[0]),
  .fclk_ba_i(e142_uclk[0]), .fclk_ba_o(e141_uclk[0]),
  .a_i(e141_down[0+:528]), .a_o(e141_up[0+:528]),
  .b_i(e142_up[0+:528]), .b_o(e142_down[0+:528]) );
 // rly_lnkh_1E_1_2: lnkh_1E_1__r2[0] <-> lnkh_1E_1__r3[0]
 ot_qwen_die_link_fwd_full #(.NL(1),.ENABLE(ENABLE)) u_stage_167 (
  .rst_n(link_por_n),
  .fclk_ab_i(e142_dclk[0]), .fclk_ab_o(e143_dclk[0]),
  .fclk_ba_i(e143_uclk[0]), .fclk_ba_o(e142_uclk[0]),
  .a_i(e142_down[0+:528]), .a_o(e142_up[0+:528]),
  .b_i(e143_up[0+:528]), .b_o(e143_down[0+:528]) );
 // rly_lnkh_1E_1_3: lnkh_1E_1__r3[0] <-> lnkh_1E_1__r4[0]
 ot_qwen_die_link_fwd_full #(.NL(1),.ENABLE(ENABLE)) u_stage_168 (
  .rst_n(link_por_n),
  .fclk_ab_i(e143_dclk[0]), .fclk_ab_o(e144_dclk[0]),
  .fclk_ba_i(e144_uclk[0]), .fclk_ba_o(e143_uclk[0]),
  .a_i(e143_down[0+:528]), .a_o(e143_up[0+:528]),
  .b_i(e144_up[0+:528]), .b_o(e144_down[0+:528]) );
 // rly_lnkh_1E_1_4: lnkh_1E_1__r4[0] <-> lnkh_1E_1__r5[0]
 ot_qwen_die_link_fwd_full #(.NL(1),.ENABLE(ENABLE)) u_stage_169 (
  .rst_n(link_por_n),
  .fclk_ab_i(e144_dclk[0]), .fclk_ab_o(e145_dclk[0]),
  .fclk_ba_i(e145_uclk[0]), .fclk_ba_o(e144_uclk[0]),
  .a_i(e144_down[0+:528]), .a_o(e144_up[0+:528]),
  .b_i(e145_up[0+:528]), .b_o(e145_down[0+:528]) );
 // rly_lnkh_1E_1_5: lnkh_1E_1__r5[0] <-> lnkh_1E_1__r6[0]
 ot_qwen_die_link_fwd_full #(.NL(1),.ENABLE(ENABLE)) u_stage_170 (
  .rst_n(link_por_n),
  .fclk_ab_i(e145_dclk[0]), .fclk_ab_o(e146_dclk[0]),
  .fclk_ba_i(e146_uclk[0]), .fclk_ba_o(e145_uclk[0]),
  .a_i(e145_down[0+:528]), .a_o(e145_up[0+:528]),
  .b_i(e146_up[0+:528]), .b_o(e146_down[0+:528]) );
 // rly_lnkh_1E_2_0: lnkh_1E_2[0] <-> lnkh_1E_2__r1[0]
 ot_qwen_die_link_fwd_full #(.NL(1),.ENABLE(ENABLE)) u_stage_171 (
  .rst_n(link_por_n),
  .fclk_ab_i(e147_dclk[0]), .fclk_ab_o(e148_dclk[0]),
  .fclk_ba_i(e148_uclk[0]), .fclk_ba_o(e147_uclk[0]),
  .a_i(e147_down[0+:528]), .a_o(e147_up[0+:528]),
  .b_i(e148_up[0+:528]), .b_o(e148_down[0+:528]) );
 // rly_lnkh_1E_2_1: lnkh_1E_2__r1[0] <-> lnkh_1E_2__r2[0]
 ot_qwen_die_link_fwd_full #(.NL(1),.ENABLE(ENABLE)) u_stage_172 (
  .rst_n(link_por_n),
  .fclk_ab_i(e148_dclk[0]), .fclk_ab_o(e149_dclk[0]),
  .fclk_ba_i(e149_uclk[0]), .fclk_ba_o(e148_uclk[0]),
  .a_i(e148_down[0+:528]), .a_o(e148_up[0+:528]),
  .b_i(e149_up[0+:528]), .b_o(e149_down[0+:528]) );
 // rly_lnkh_1E_2_2: lnkh_1E_2__r2[0] <-> lnkh_1E_2__r3[0]
 ot_qwen_die_link_fwd_full #(.NL(1),.ENABLE(ENABLE)) u_stage_173 (
  .rst_n(link_por_n),
  .fclk_ab_i(e149_dclk[0]), .fclk_ab_o(e150_dclk[0]),
  .fclk_ba_i(e150_uclk[0]), .fclk_ba_o(e149_uclk[0]),
  .a_i(e149_down[0+:528]), .a_o(e149_up[0+:528]),
  .b_i(e150_up[0+:528]), .b_o(e150_down[0+:528]) );
 // rly_lnkh_1E_2_3: lnkh_1E_2__r3[0] <-> lnkh_1E_2__r4[0]
 ot_qwen_die_link_fwd_full #(.NL(1),.ENABLE(ENABLE)) u_stage_174 (
  .rst_n(link_por_n),
  .fclk_ab_i(e150_dclk[0]), .fclk_ab_o(e151_dclk[0]),
  .fclk_ba_i(e151_uclk[0]), .fclk_ba_o(e150_uclk[0]),
  .a_i(e150_down[0+:528]), .a_o(e150_up[0+:528]),
  .b_i(e151_up[0+:528]), .b_o(e151_down[0+:528]) );
 // rly_lnkh_1E_2_4: lnkh_1E_2__r4[0] <-> lnkh_1E_2__r5[0]
 ot_qwen_die_link_fwd_full #(.NL(1),.ENABLE(ENABLE)) u_stage_175 (
  .rst_n(link_por_n),
  .fclk_ab_i(e151_dclk[0]), .fclk_ab_o(e152_dclk[0]),
  .fclk_ba_i(e152_uclk[0]), .fclk_ba_o(e151_uclk[0]),
  .a_i(e151_down[0+:528]), .a_o(e151_up[0+:528]),
  .b_i(e152_up[0+:528]), .b_o(e152_down[0+:528]) );
 // rly_lnkh_1E_3_0: lnkh_1E_3[0] <-> lnkh_1E_3__r1[0]
 ot_qwen_die_link_fwd_full #(.NL(1),.ENABLE(ENABLE)) u_stage_176 (
  .rst_n(link_por_n),
  .fclk_ab_i(e153_dclk[0]), .fclk_ab_o(e154_dclk[0]),
  .fclk_ba_i(e154_uclk[0]), .fclk_ba_o(e153_uclk[0]),
  .a_i(e153_down[0+:528]), .a_o(e153_up[0+:528]),
  .b_i(e154_up[0+:528]), .b_o(e154_down[0+:528]) );
 // rly_lnkh_1E_3_1: lnkh_1E_3__r1[0] <-> lnkh_1E_3__r2[0]
 ot_qwen_die_link_fwd_full #(.NL(1),.ENABLE(ENABLE)) u_stage_177 (
  .rst_n(link_por_n),
  .fclk_ab_i(e154_dclk[0]), .fclk_ab_o(e155_dclk[0]),
  .fclk_ba_i(e155_uclk[0]), .fclk_ba_o(e154_uclk[0]),
  .a_i(e154_down[0+:528]), .a_o(e154_up[0+:528]),
  .b_i(e155_up[0+:528]), .b_o(e155_down[0+:528]) );
 // rly_lnkh_1E_3_2: lnkh_1E_3__r2[0] <-> lnkh_1E_3__r3[0]
 ot_qwen_die_link_fwd_full #(.NL(1),.ENABLE(ENABLE)) u_stage_178 (
  .rst_n(link_por_n),
  .fclk_ab_i(e155_dclk[0]), .fclk_ab_o(e156_dclk[0]),
  .fclk_ba_i(e156_uclk[0]), .fclk_ba_o(e155_uclk[0]),
  .a_i(e155_down[0+:528]), .a_o(e155_up[0+:528]),
  .b_i(e156_up[0+:528]), .b_o(e156_down[0+:528]) );
 // rly_lnkh_1E_3_3: lnkh_1E_3__r3[0] <-> lnkh_1E_3__r4[0]
 ot_qwen_die_link_fwd_full #(.NL(1),.ENABLE(ENABLE)) u_stage_179 (
  .rst_n(link_por_n),
  .fclk_ab_i(e156_dclk[0]), .fclk_ab_o(e157_dclk[0]),
  .fclk_ba_i(e157_uclk[0]), .fclk_ba_o(e156_uclk[0]),
  .a_i(e156_down[0+:528]), .a_o(e156_up[0+:528]),
  .b_i(e157_up[0+:528]), .b_o(e157_down[0+:528]) );
 // rly_lnkh_1E_3_4: lnkh_1E_3__r4[0] <-> lnkh_1E_3__r5[0]
 ot_qwen_die_link_fwd_full #(.NL(1),.ENABLE(ENABLE)) u_stage_180 (
  .rst_n(link_por_n),
  .fclk_ab_i(e157_dclk[0]), .fclk_ab_o(e158_dclk[0]),
  .fclk_ba_i(e158_uclk[0]), .fclk_ba_o(e157_uclk[0]),
  .a_i(e157_down[0+:528]), .a_o(e157_up[0+:528]),
  .b_i(e158_up[0+:528]), .b_o(e158_down[0+:528]) );
 // rly_lnkh_1E_3_5: lnkh_1E_3__r5[0] <-> lnkh_1E_3__r6[0]
 ot_qwen_die_link_fwd_full #(.NL(1),.ENABLE(ENABLE)) u_stage_181 (
  .rst_n(link_por_n),
  .fclk_ab_i(e158_dclk[0]), .fclk_ab_o(e159_dclk[0]),
  .fclk_ba_i(e159_uclk[0]), .fclk_ba_o(e158_uclk[0]),
  .a_i(e158_down[0+:528]), .a_o(e158_up[0+:528]),
  .b_i(e159_up[0+:528]), .b_o(e159_down[0+:528]) );
 // rly_lnkh_1E_4_0: lnkh_1E_4[0] <-> lnkh_1E_4__r1[0]
 ot_qwen_die_link_fwd_full #(.NL(1),.ENABLE(ENABLE)) u_stage_182 (
  .rst_n(link_por_n),
  .fclk_ab_i(e160_dclk[0]), .fclk_ab_o(e161_dclk[0]),
  .fclk_ba_i(e161_uclk[0]), .fclk_ba_o(e160_uclk[0]),
  .a_i(e160_down[0+:528]), .a_o(e160_up[0+:528]),
  .b_i(e161_up[0+:528]), .b_o(e161_down[0+:528]) );
 // rly_lnkh_1E_4_1: lnkh_1E_4__r1[0] <-> lnkh_1E_4__r2[0]
 ot_qwen_die_link_fwd_full #(.NL(1),.ENABLE(ENABLE)) u_stage_183 (
  .rst_n(link_por_n),
  .fclk_ab_i(e161_dclk[0]), .fclk_ab_o(e162_dclk[0]),
  .fclk_ba_i(e162_uclk[0]), .fclk_ba_o(e161_uclk[0]),
  .a_i(e161_down[0+:528]), .a_o(e161_up[0+:528]),
  .b_i(e162_up[0+:528]), .b_o(e162_down[0+:528]) );
 // rly_lnkh_1E_4_2: lnkh_1E_4__r2[0] <-> lnkh_1E_4__r3[0]
 ot_qwen_die_link_fwd_full #(.NL(1),.ENABLE(ENABLE)) u_stage_184 (
  .rst_n(link_por_n),
  .fclk_ab_i(e162_dclk[0]), .fclk_ab_o(e163_dclk[0]),
  .fclk_ba_i(e163_uclk[0]), .fclk_ba_o(e162_uclk[0]),
  .a_i(e162_down[0+:528]), .a_o(e162_up[0+:528]),
  .b_i(e163_up[0+:528]), .b_o(e163_down[0+:528]) );
 // rly_lnkh_1E_4_3: lnkh_1E_4__r3[0] <-> lnkh_1E_4__r4[0]
 ot_qwen_die_link_fwd_full #(.NL(1),.ENABLE(ENABLE)) u_stage_185 (
  .rst_n(link_por_n),
  .fclk_ab_i(e163_dclk[0]), .fclk_ab_o(e164_dclk[0]),
  .fclk_ba_i(e164_uclk[0]), .fclk_ba_o(e163_uclk[0]),
  .a_i(e163_down[0+:528]), .a_o(e163_up[0+:528]),
  .b_i(e164_up[0+:528]), .b_o(e164_down[0+:528]) );
 // rly_lnkh_1E_4_4: lnkh_1E_4__r4[0] <-> lnkh_1E_4__r5[0]
 ot_qwen_die_link_fwd_full #(.NL(1),.ENABLE(ENABLE)) u_stage_186 (
  .rst_n(link_por_n),
  .fclk_ab_i(e164_dclk[0]), .fclk_ab_o(e165_dclk[0]),
  .fclk_ba_i(e165_uclk[0]), .fclk_ba_o(e164_uclk[0]),
  .a_i(e164_down[0+:528]), .a_o(e164_up[0+:528]),
  .b_i(e165_up[0+:528]), .b_o(e165_down[0+:528]) );
 // rly_lnkh_1E_f_0: lnkh_1E_f[0] <-> lnkh_1E_f__r1[0]
 ot_qwen_die_link_fwd_full #(.NL(1),.ENABLE(ENABLE)) u_stage_187 (
  .rst_n(link_por_n),
  .fclk_ab_i(e166_dclk[0]), .fclk_ab_o(e167_dclk[0]),
  .fclk_ba_i(e167_uclk[0]), .fclk_ba_o(e166_uclk[0]),
  .a_i(e166_down[0+:528]), .a_o(e166_up[0+:528]),
  .b_i(e167_up[0+:528]), .b_o(e167_down[0+:528]) );
 // rly_lnkh_1E_f_1: lnkh_1E_f__r1[0] <-> lnkh_1E_f__r2[0]
 ot_qwen_die_link_fwd_full #(.NL(1),.ENABLE(ENABLE)) u_stage_188 (
  .rst_n(link_por_n),
  .fclk_ab_i(e167_dclk[0]), .fclk_ab_o(e168_dclk[0]),
  .fclk_ba_i(e168_uclk[0]), .fclk_ba_o(e167_uclk[0]),
  .a_i(e167_down[0+:528]), .a_o(e167_up[0+:528]),
  .b_i(e168_up[0+:528]), .b_o(e168_down[0+:528]) );
 // rly_lnkh_1E_f_2: lnkh_1E_f__r2[0] <-> lnkh_1E_f__r3[0]
 ot_qwen_die_link_fwd_full #(.NL(1),.ENABLE(ENABLE)) u_stage_189 (
  .rst_n(link_por_n),
  .fclk_ab_i(e168_dclk[0]), .fclk_ab_o(e169_dclk[0]),
  .fclk_ba_i(e169_uclk[0]), .fclk_ba_o(e168_uclk[0]),
  .a_i(e168_down[0+:528]), .a_o(e168_up[0+:528]),
  .b_i(e169_up[0+:528]), .b_o(e169_down[0+:528]) );
 // rly_lnkh_1E_f_3: lnkh_1E_f__r3[0] <-> lnkh_1E_f__r4[0]
 ot_qwen_die_link_fwd_full #(.NL(1),.ENABLE(ENABLE)) u_stage_190 (
  .rst_n(link_por_n),
  .fclk_ab_i(e169_dclk[0]), .fclk_ab_o(e170_dclk[0]),
  .fclk_ba_i(e170_uclk[0]), .fclk_ba_o(e169_uclk[0]),
  .a_i(e169_down[0+:528]), .a_o(e169_up[0+:528]),
  .b_i(e170_up[0+:528]), .b_o(e170_down[0+:528]) );
 // rly_lnkh_1E_f_4: lnkh_1E_f__r4[0] <-> lnkh_1E_f__r5[0]
 ot_qwen_die_link_fwd_full #(.NL(1),.ENABLE(ENABLE)) u_stage_191 (
  .rst_n(link_por_n),
  .fclk_ab_i(e170_dclk[0]), .fclk_ab_o(e171_dclk[0]),
  .fclk_ba_i(e171_uclk[0]), .fclk_ba_o(e170_uclk[0]),
  .a_i(e170_down[0+:528]), .a_o(e170_up[0+:528]),
  .b_i(e171_up[0+:528]), .b_o(e171_down[0+:528]) );
 // rly_lnkv_0_W_0_0: lnkv_0_W_0[0] <-> lnkv_0_W_0__r1[0]
 ot_qwen_die_link_fwd_full #(.NL(1),.ENABLE(ENABLE)) u_stage_192 (
  .rst_n(link_por_n),
  .fclk_ab_i(e172_dclk[0]), .fclk_ab_o(e173_dclk[0]),
  .fclk_ba_i(e173_uclk[0]), .fclk_ba_o(e172_uclk[0]),
  .a_i(e172_down[0+:528]), .a_o(e172_up[0+:528]),
  .b_i(e173_up[0+:528]), .b_o(e173_down[0+:528]) );
 // rly_lnkv_0_W_0_1: lnkv_0_W_0__r1[0] <-> lnkv_0_W_0__r2[0]
 ot_qwen_die_link_fwd_full #(.NL(1),.ENABLE(ENABLE)) u_stage_193 (
  .rst_n(link_por_n),
  .fclk_ab_i(e173_dclk[0]), .fclk_ab_o(e174_dclk[0]),
  .fclk_ba_i(e174_uclk[0]), .fclk_ba_o(e173_uclk[0]),
  .a_i(e173_down[0+:528]), .a_o(e173_up[0+:528]),
  .b_i(e174_up[0+:528]), .b_o(e174_down[0+:528]) );
 // rly_lnkv_0_W_0_2: lnkv_0_W_0__r2[0] <-> lnkv_0_W_0__r3[0]
 ot_qwen_die_link_fwd_full #(.NL(1),.ENABLE(ENABLE)) u_stage_194 (
  .rst_n(link_por_n),
  .fclk_ab_i(e174_dclk[0]), .fclk_ab_o(e175_dclk[0]),
  .fclk_ba_i(e175_uclk[0]), .fclk_ba_o(e174_uclk[0]),
  .a_i(e174_down[0+:528]), .a_o(e174_up[0+:528]),
  .b_i(e175_up[0+:528]), .b_o(e175_down[0+:528]) );
 // rly_lnkv_0_W_0_3: lnkv_0_W_0__r3[0] <-> lnkv_0_W_0__r4[0]
 ot_qwen_die_link_fwd_full #(.NL(1),.ENABLE(ENABLE)) u_stage_195 (
  .rst_n(link_por_n),
  .fclk_ab_i(e175_dclk[0]), .fclk_ab_o(e176_dclk[0]),
  .fclk_ba_i(e176_uclk[0]), .fclk_ba_o(e175_uclk[0]),
  .a_i(e175_down[0+:528]), .a_o(e175_up[0+:528]),
  .b_i(e176_up[0+:528]), .b_o(e176_down[0+:528]) );
 // rly_lnkv_0_W_1_0: lnkv_0_W_1[0] <-> lnkv_0_W_1__r1[0]
 ot_qwen_die_link_fwd_full #(.NL(1),.ENABLE(ENABLE)) u_stage_196 (
  .rst_n(link_por_n),
  .fclk_ab_i(e177_dclk[0]), .fclk_ab_o(e178_dclk[0]),
  .fclk_ba_i(e178_uclk[0]), .fclk_ba_o(e177_uclk[0]),
  .a_i(e177_down[0+:528]), .a_o(e177_up[0+:528]),
  .b_i(e178_up[0+:528]), .b_o(e178_down[0+:528]) );
 // rly_lnkv_0_W_1_1: lnkv_0_W_1__r1[0] <-> lnkv_0_W_1__r2[0]
 ot_qwen_die_link_fwd_full #(.NL(1),.ENABLE(ENABLE)) u_stage_197 (
  .rst_n(link_por_n),
  .fclk_ab_i(e178_dclk[0]), .fclk_ab_o(e179_dclk[0]),
  .fclk_ba_i(e179_uclk[0]), .fclk_ba_o(e178_uclk[0]),
  .a_i(e178_down[0+:528]), .a_o(e178_up[0+:528]),
  .b_i(e179_up[0+:528]), .b_o(e179_down[0+:528]) );
 // rly_lnkv_0_W_1_2: lnkv_0_W_1__r2[0] <-> lnkv_0_W_1__r3[0]
 ot_qwen_die_link_fwd_full #(.NL(1),.ENABLE(ENABLE)) u_stage_198 (
  .rst_n(link_por_n),
  .fclk_ab_i(e179_dclk[0]), .fclk_ab_o(e180_dclk[0]),
  .fclk_ba_i(e180_uclk[0]), .fclk_ba_o(e179_uclk[0]),
  .a_i(e179_down[0+:528]), .a_o(e179_up[0+:528]),
  .b_i(e180_up[0+:528]), .b_o(e180_down[0+:528]) );
 // rly_lnkv_0_W_2_0: lnkv_0_W_2[0] <-> lnkv_0_W_2__r1[0]
 ot_qwen_die_link_fwd_full #(.NL(1),.ENABLE(ENABLE)) u_stage_199 (
  .rst_n(link_por_n),
  .fclk_ab_i(e181_dclk[0]), .fclk_ab_o(e182_dclk[0]),
  .fclk_ba_i(e182_uclk[0]), .fclk_ba_o(e181_uclk[0]),
  .a_i(e181_down[0+:528]), .a_o(e181_up[0+:528]),
  .b_i(e182_up[0+:528]), .b_o(e182_down[0+:528]) );
 // rly_lnkv_0_W_2_1: lnkv_0_W_2__r1[0] <-> lnkv_0_W_2__r2[0]
 ot_qwen_die_link_fwd_full #(.NL(1),.ENABLE(ENABLE)) u_stage_200 (
  .rst_n(link_por_n),
  .fclk_ab_i(e182_dclk[0]), .fclk_ab_o(e183_dclk[0]),
  .fclk_ba_i(e183_uclk[0]), .fclk_ba_o(e182_uclk[0]),
  .a_i(e182_down[0+:528]), .a_o(e182_up[0+:528]),
  .b_i(e183_up[0+:528]), .b_o(e183_down[0+:528]) );
 // rly_lnkv_0_W_2_2: lnkv_0_W_2__r2[0] <-> lnkv_0_W_2__r3[0]
 ot_qwen_die_link_fwd_full #(.NL(1),.ENABLE(ENABLE)) u_stage_201 (
  .rst_n(link_por_n),
  .fclk_ab_i(e183_dclk[0]), .fclk_ab_o(e184_dclk[0]),
  .fclk_ba_i(e184_uclk[0]), .fclk_ba_o(e183_uclk[0]),
  .a_i(e183_down[0+:528]), .a_o(e183_up[0+:528]),
  .b_i(e184_up[0+:528]), .b_o(e184_down[0+:528]) );
 // rly_lnkv_0_W_c_0: lnkv_0_W_c[0] <-> lnkv_0_W_c__r1[0]
 ot_qwen_die_link_fwd_full #(.NL(1),.ENABLE(ENABLE)) u_stage_202 (
  .rst_n(link_por_n),
  .fclk_ab_i(e185_dclk[0]), .fclk_ab_o(e186_dclk[0]),
  .fclk_ba_i(e186_uclk[0]), .fclk_ba_o(e185_uclk[0]),
  .a_i(e185_down[0+:528]), .a_o(e185_up[0+:528]),
  .b_i(e186_up[0+:528]), .b_o(e186_down[0+:528]) );
 // rly_lnkv_0_W_c_1: lnkv_0_W_c__r1[0] <-> lnkv_0_W_c__r2[0]
 ot_qwen_die_link_fwd_full #(.NL(1),.ENABLE(ENABLE)) u_stage_203 (
  .rst_n(link_por_n),
  .fclk_ab_i(e186_dclk[0]), .fclk_ab_o(e187_dclk[0]),
  .fclk_ba_i(e187_uclk[0]), .fclk_ba_o(e186_uclk[0]),
  .a_i(e186_down[0+:528]), .a_o(e186_up[0+:528]),
  .b_i(e187_up[0+:528]), .b_o(e187_down[0+:528]) );
 // rly_lnkv_0_E_0_0: lnkv_0_E_0[0] <-> lnkv_0_E_0__r1[0]
 ot_qwen_die_link_fwd_full #(.NL(1),.ENABLE(ENABLE)) u_stage_204 (
  .rst_n(link_por_n),
  .fclk_ab_i(e188_dclk[0]), .fclk_ab_o(e189_dclk[0]),
  .fclk_ba_i(e189_uclk[0]), .fclk_ba_o(e188_uclk[0]),
  .a_i(e188_down[0+:528]), .a_o(e188_up[0+:528]),
  .b_i(e189_up[0+:528]), .b_o(e189_down[0+:528]) );
 // rly_lnkv_0_E_0_1: lnkv_0_E_0__r1[0] <-> lnkv_0_E_0__r2[0]
 ot_qwen_die_link_fwd_full #(.NL(1),.ENABLE(ENABLE)) u_stage_205 (
  .rst_n(link_por_n),
  .fclk_ab_i(e189_dclk[0]), .fclk_ab_o(e190_dclk[0]),
  .fclk_ba_i(e190_uclk[0]), .fclk_ba_o(e189_uclk[0]),
  .a_i(e189_down[0+:528]), .a_o(e189_up[0+:528]),
  .b_i(e190_up[0+:528]), .b_o(e190_down[0+:528]) );
 // rly_lnkv_0_E_0_2: lnkv_0_E_0__r2[0] <-> lnkv_0_E_0__r3[0]
 ot_qwen_die_link_fwd_full #(.NL(1),.ENABLE(ENABLE)) u_stage_206 (
  .rst_n(link_por_n),
  .fclk_ab_i(e190_dclk[0]), .fclk_ab_o(e191_dclk[0]),
  .fclk_ba_i(e191_uclk[0]), .fclk_ba_o(e190_uclk[0]),
  .a_i(e190_down[0+:528]), .a_o(e190_up[0+:528]),
  .b_i(e191_up[0+:528]), .b_o(e191_down[0+:528]) );
 // rly_lnkv_0_E_0_3: lnkv_0_E_0__r3[0] <-> lnkv_0_E_0__r4[0]
 ot_qwen_die_link_fwd_full #(.NL(1),.ENABLE(ENABLE)) u_stage_207 (
  .rst_n(link_por_n),
  .fclk_ab_i(e191_dclk[0]), .fclk_ab_o(e192_dclk[0]),
  .fclk_ba_i(e192_uclk[0]), .fclk_ba_o(e191_uclk[0]),
  .a_i(e191_down[0+:528]), .a_o(e191_up[0+:528]),
  .b_i(e192_up[0+:528]), .b_o(e192_down[0+:528]) );
 // rly_lnkv_0_E_0_4: lnkv_0_E_0__r4[0] <-> lnkv_0_E_0__r5[0]
 ot_qwen_die_link_fwd_full #(.NL(1),.ENABLE(ENABLE)) u_stage_208 (
  .rst_n(link_por_n),
  .fclk_ab_i(e192_dclk[0]), .fclk_ab_o(e193_dclk[0]),
  .fclk_ba_i(e193_uclk[0]), .fclk_ba_o(e192_uclk[0]),
  .a_i(e192_down[0+:528]), .a_o(e192_up[0+:528]),
  .b_i(e193_up[0+:528]), .b_o(e193_down[0+:528]) );
 // rly_lnkv_0_E_1_0: lnkv_0_E_1[0] <-> lnkv_0_E_1__r1[0]
 ot_qwen_die_link_fwd_full #(.NL(1),.ENABLE(ENABLE)) u_stage_209 (
  .rst_n(link_por_n),
  .fclk_ab_i(e194_dclk[0]), .fclk_ab_o(e195_dclk[0]),
  .fclk_ba_i(e195_uclk[0]), .fclk_ba_o(e194_uclk[0]),
  .a_i(e194_down[0+:528]), .a_o(e194_up[0+:528]),
  .b_i(e195_up[0+:528]), .b_o(e195_down[0+:528]) );
 // rly_lnkv_0_E_1_1: lnkv_0_E_1__r1[0] <-> lnkv_0_E_1__r2[0]
 ot_qwen_die_link_fwd_full #(.NL(1),.ENABLE(ENABLE)) u_stage_210 (
  .rst_n(link_por_n),
  .fclk_ab_i(e195_dclk[0]), .fclk_ab_o(e196_dclk[0]),
  .fclk_ba_i(e196_uclk[0]), .fclk_ba_o(e195_uclk[0]),
  .a_i(e195_down[0+:528]), .a_o(e195_up[0+:528]),
  .b_i(e196_up[0+:528]), .b_o(e196_down[0+:528]) );
 // rly_lnkv_0_E_1_2: lnkv_0_E_1__r2[0] <-> lnkv_0_E_1__r3[0]
 ot_qwen_die_link_fwd_full #(.NL(1),.ENABLE(ENABLE)) u_stage_211 (
  .rst_n(link_por_n),
  .fclk_ab_i(e196_dclk[0]), .fclk_ab_o(e197_dclk[0]),
  .fclk_ba_i(e197_uclk[0]), .fclk_ba_o(e196_uclk[0]),
  .a_i(e196_down[0+:528]), .a_o(e196_up[0+:528]),
  .b_i(e197_up[0+:528]), .b_o(e197_down[0+:528]) );
 // rly_lnkv_0_E_2_0: lnkv_0_E_2[0] <-> lnkv_0_E_2__r1[0]
 ot_qwen_die_link_fwd_full #(.NL(1),.ENABLE(ENABLE)) u_stage_212 (
  .rst_n(link_por_n),
  .fclk_ab_i(e198_dclk[0]), .fclk_ab_o(e199_dclk[0]),
  .fclk_ba_i(e199_uclk[0]), .fclk_ba_o(e198_uclk[0]),
  .a_i(e198_down[0+:528]), .a_o(e198_up[0+:528]),
  .b_i(e199_up[0+:528]), .b_o(e199_down[0+:528]) );
 // rly_lnkv_0_E_2_1: lnkv_0_E_2__r1[0] <-> lnkv_0_E_2__r2[0]
 ot_qwen_die_link_fwd_full #(.NL(1),.ENABLE(ENABLE)) u_stage_213 (
  .rst_n(link_por_n),
  .fclk_ab_i(e199_dclk[0]), .fclk_ab_o(e200_dclk[0]),
  .fclk_ba_i(e200_uclk[0]), .fclk_ba_o(e199_uclk[0]),
  .a_i(e199_down[0+:528]), .a_o(e199_up[0+:528]),
  .b_i(e200_up[0+:528]), .b_o(e200_down[0+:528]) );
 // rly_lnkv_0_E_2_2: lnkv_0_E_2__r2[0] <-> lnkv_0_E_2__r3[0]
 ot_qwen_die_link_fwd_full #(.NL(1),.ENABLE(ENABLE)) u_stage_214 (
  .rst_n(link_por_n),
  .fclk_ab_i(e200_dclk[0]), .fclk_ab_o(e201_dclk[0]),
  .fclk_ba_i(e201_uclk[0]), .fclk_ba_o(e200_uclk[0]),
  .a_i(e200_down[0+:528]), .a_o(e200_up[0+:528]),
  .b_i(e201_up[0+:528]), .b_o(e201_down[0+:528]) );
 // rly_lnkv_0_E_c_0: lnkv_0_E_c[0] <-> lnkv_0_E_c__r1[0]
 ot_qwen_die_link_fwd_full #(.NL(1),.ENABLE(ENABLE)) u_stage_215 (
  .rst_n(link_por_n),
  .fclk_ab_i(e202_dclk[0]), .fclk_ab_o(e203_dclk[0]),
  .fclk_ba_i(e203_uclk[0]), .fclk_ba_o(e202_uclk[0]),
  .a_i(e202_down[0+:528]), .a_o(e202_up[0+:528]),
  .b_i(e203_up[0+:528]), .b_o(e203_down[0+:528]) );
 // rly_lnkv_0_E_c_1: lnkv_0_E_c__r1[0] <-> lnkv_0_E_c__r2[0]
 ot_qwen_die_link_fwd_full #(.NL(1),.ENABLE(ENABLE)) u_stage_216 (
  .rst_n(link_por_n),
  .fclk_ab_i(e203_dclk[0]), .fclk_ab_o(e204_dclk[0]),
  .fclk_ba_i(e204_uclk[0]), .fclk_ba_o(e203_uclk[0]),
  .a_i(e203_down[0+:528]), .a_o(e203_up[0+:528]),
  .b_i(e204_up[0+:528]), .b_o(e204_down[0+:528]) );
endmodule
