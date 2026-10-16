`default_nettype none
// Additive explicit reset leaf: fifteen actual reset FF, no inherited view.
module hbfd_rst_13_candidate(input wire ck,rs,output wire [12:0] rn);
 ot_rst_relay #(.REGIONS(13),.SYNC_STAGES(2),.TREE_STAGES(1)) u_reset
  (.clk(ck),.rst_n_in(rs),.rst_n(rn));
endmodule
// Physical ABI candidate: zero logic in this parent; each real payload leaf
// and the real reset leaf have independent scalar clock entries. Native parent
// routing, insertion compensation, phase/reset delivery remain unqualified.
module hbfd_rly_624_split48_physical_candidate(
 input wire ck_payload0,ck_payload1,ck_payload2,ck_payload3,ck_payload4,ck_payload5,ck_payload6,ck_payload7,ck_payload8,ck_payload9,ck_payload10,ck_payload11,ck_payload12,ck_reset,rs,
 input wire[623:0]i,output wire[623:0]o);
 wire[12:0]rn;
 hbfd_rst_13_candidate reset_leaf(.ck(ck_reset),.rs(rs),.rn(rn));
 hbfd_rly_48_EW payload0(.ck(ck_payload0),.rs(rn[0]),.i(i[0+:48]),.o(o[0+:48]));
 hbfd_rly_48_EW payload1(.ck(ck_payload1),.rs(rn[1]),.i(i[48+:48]),.o(o[48+:48]));
 hbfd_rly_48_EW payload2(.ck(ck_payload2),.rs(rn[2]),.i(i[96+:48]),.o(o[96+:48]));
 hbfd_rly_48_EW payload3(.ck(ck_payload3),.rs(rn[3]),.i(i[144+:48]),.o(o[144+:48]));
 hbfd_rly_48_EW payload4(.ck(ck_payload4),.rs(rn[4]),.i(i[192+:48]),.o(o[192+:48]));
 hbfd_rly_48_EW payload5(.ck(ck_payload5),.rs(rn[5]),.i(i[240+:48]),.o(o[240+:48]));
 hbfd_rly_48_EW payload6(.ck(ck_payload6),.rs(rn[6]),.i(i[288+:48]),.o(o[288+:48]));
 hbfd_rly_48_EW payload7(.ck(ck_payload7),.rs(rn[7]),.i(i[336+:48]),.o(o[336+:48]));
 hbfd_rly_48_EW payload8(.ck(ck_payload8),.rs(rn[8]),.i(i[384+:48]),.o(o[384+:48]));
 hbfd_rly_48_EW payload9(.ck(ck_payload9),.rs(rn[9]),.i(i[432+:48]),.o(o[432+:48]));
 hbfd_rly_48_EW payload10(.ck(ck_payload10),.rs(rn[10]),.i(i[480+:48]),.o(o[480+:48]));
 hbfd_rly_48_EW payload11(.ck(ck_payload11),.rs(rn[11]),.i(i[528+:48]),.o(o[528+:48]));
 hbfd_rly_48_EW payload12(.ck(ck_payload12),.rs(rn[12]),.i(i[576+:48]),.o(o[576+:48]));
endmodule
`default_nettype wire
