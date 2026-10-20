module tb_ctl_repair3;
reg ck=0; always #5 ck=~ck;
integer cycle,j,failures=0,compares=0; integer mutate;
reg rst_ref; always @(posedge ck) rst_ref <= rst_n;
reg [0:0] rst_n;
reg [115:0] cmd_q;
reg [1037:0] chd_q;
reg [0:0] r_v;
reg [7:0] r_idx;
reg [0:0] r_last;
reg [511:0] r_d;
reg [0:0] l9o_v;
reg [0:0] stn_fault;
reg [7:0] vm_we;
reg [191:0] vm_waddr;
reg [255:0] vm_wdata;
reg [7:0] kv_we;
reg [191:0] kv_waddr;
reg [255:0] kv_wdata;
reg [0:0] su_nr;
reg [0:0] su_idle;
reg [0:0] su_fault;
reg [15:0] su_prog;
reg [15:0] su_rows;
reg [0:0] vm_fault;
reg [0:0] red_we;
reg [23:0] red_addr;
reg [31:0] red_data;
reg [0:0] sc_w1_we;
reg [23:0] sc_w1_addr;
reg [31:0] sc_w1_data;
reg [0:0] tok_v;
reg [23:0] tok_idx;
reg [0:0] tok_own;
reg [31:0] tok_val;
reg [1:0] tok_user;
reg [0:0] sc_busy;
reg [0:0] sc_fault;
reg [0:0] stm_fault;
reg [0:0] tld_fault;
reg [0:0] hd_fault;
reg [0:0] pc_bad;
wire [3:0] sid_ref, sid_dut, sid_mut;
wire [28:0] stn_cfg_ref, stn_cfg_dut, stn_cfg_mut;
wire [100:0] sc_cfg_ref, sc_cfg_dut, sc_cfg_mut;
wire [30:0] stm_cfg_ref, stm_cfg_dut, stm_cfg_mut;
wire [9:0] su_cmd_ref, su_cmd_dut, su_cmd_mut;
wire [0:0] am_v_ref, am_v_dut, am_v_mut;
wire [23:0] am_idx_ref, am_idx_dut, am_idx_mut;
wire [31:0] am_val_ref, am_val_dut, am_val_mut;
wire [1:0] am_u_ref, am_u_dut, am_u_mut;
wire [0:0] w16_we_ref, w16_we_dut, w16_we_mut;
wire [23:0] w16_addr_ref, w16_addr_dut, w16_addr_mut;
wire [511:0] w16_data_ref, w16_data_dut, w16_data_mut;
wire [0:0] w1_we_ref, w1_we_dut, w1_we_mut;
wire [23:0] w1_addr_ref, w1_addr_dut, w1_addr_mut;
wire [31:0] w1_data_ref, w1_data_dut, w1_data_mut;
wire [1094:0] own_ch_ref, own_ch_dut, own_ch_mut;
wire [9:0] ag_own_ref, ag_own_dut, ag_own_mut;
wire [106:0] st_ref, st_dut, st_mut;
wire [49:0] cc_o_ref, cc_o_dut, cc_o_mut;
qfd_dv_s5_ctl u_ref(.ck(ck),.rst_n(rst_ref),.cmd_q(cmd_q),.chd_q(chd_q),.r_v(r_v),.r_idx(r_idx),.r_last(r_last),.r_d(r_d),.l9o_v(l9o_v),.stn_fault(stn_fault),.vm_we(vm_we),.vm_waddr(vm_waddr),.vm_wdata(vm_wdata),.kv_we(kv_we),.kv_waddr(kv_waddr),.kv_wdata(kv_wdata),.su_nr(su_nr),.su_idle(su_idle),.su_fault(su_fault),.su_prog(su_prog),.su_rows(su_rows),.vm_fault(vm_fault),.red_we(red_we),.red_addr(red_addr),.red_data(red_data),.sc_w1_we(sc_w1_we),.sc_w1_addr(sc_w1_addr),.sc_w1_data(sc_w1_data),.tok_v(tok_v),.tok_idx(tok_idx),.tok_own(tok_own),.tok_val(tok_val),.tok_user(tok_user),.sc_busy(sc_busy),.sc_fault(sc_fault),.stm_fault(stm_fault),.tld_fault(tld_fault),.hd_fault(hd_fault),.pc_bad(pc_bad),.sid(sid_ref),.stn_cfg(stn_cfg_ref),.sc_cfg(sc_cfg_ref),.stm_cfg(stm_cfg_ref),.su_cmd(su_cmd_ref),.am_v(am_v_ref),.am_idx(am_idx_ref),.am_val(am_val_ref),.am_u(am_u_ref),.w16_we(w16_we_ref),.w16_addr(w16_addr_ref),.w16_data(w16_data_ref),.w1_we(w1_we_ref),.w1_addr(w1_addr_ref),.w1_data(w1_data_ref),.own_ch(own_ch_ref),.ag_own(ag_own_ref),.st(st_ref),.cc_o(cc_o_ref));
qfd_dv_s5_ctl_repair3 u_dut(.ck(ck),.rst_n(rst_n),.cmd_q(cmd_q),.chd_q(chd_q),.r_v(r_v),.r_idx(r_idx),.r_last(r_last),.r_d(r_d),.l9o_v(l9o_v),.stn_fault(stn_fault),.vm_we(vm_we),.vm_waddr(vm_waddr),.vm_wdata(vm_wdata),.kv_we(kv_we),.kv_waddr(kv_waddr),.kv_wdata(kv_wdata),.su_nr(su_nr),.su_idle(su_idle),.su_fault(su_fault),.su_prog(su_prog),.su_rows(su_rows),.vm_fault(vm_fault),.red_we(red_we),.red_addr(red_addr),.red_data(red_data),.sc_w1_we(sc_w1_we),.sc_w1_addr(sc_w1_addr),.sc_w1_data(sc_w1_data),.tok_v(tok_v),.tok_idx(tok_idx),.tok_own(tok_own),.tok_val(tok_val),.tok_user(tok_user),.sc_busy(sc_busy),.sc_fault(sc_fault),.stm_fault(stm_fault),.tld_fault(tld_fault),.hd_fault(hd_fault),.pc_bad(pc_bad),.sid(sid_dut),.stn_cfg(stn_cfg_dut),.sc_cfg(sc_cfg_dut),.stm_cfg(stm_cfg_dut),.su_cmd(su_cmd_dut),.am_v(am_v_dut),.am_idx(am_idx_dut),.am_val(am_val_dut),.am_u(am_u_dut),.w16_we(w16_we_dut),.w16_addr(w16_addr_dut),.w16_data(w16_data_dut),.w1_we(w1_we_dut),.w1_addr(w1_addr_dut),.w1_data(w1_data_dut),.own_ch(own_ch_dut),.ag_own(ag_own_dut),.st(st_dut),.cc_o(cc_o_dut));
qfd_dv_s5_ctl_repair3_mut11 u_mut(.ck(ck),.rst_n(rst_n),.cmd_q(cmd_q),.chd_q(chd_q),.r_v(r_v),.r_idx(r_idx),.r_last(r_last),.r_d(r_d),.l9o_v(l9o_v),.stn_fault(stn_fault),.vm_we(vm_we),.vm_waddr(vm_waddr),.vm_wdata(vm_wdata),.kv_we(kv_we),.kv_waddr(kv_waddr),.kv_wdata(kv_wdata),.su_nr(su_nr),.su_idle(su_idle),.su_fault(su_fault),.su_prog(su_prog),.su_rows(su_rows),.vm_fault(vm_fault),.red_we(red_we),.red_addr(red_addr),.red_data(red_data),.sc_w1_we(sc_w1_we),.sc_w1_addr(sc_w1_addr),.sc_w1_data(sc_w1_data),.tok_v(tok_v),.tok_idx(tok_idx),.tok_own(tok_own),.tok_val(tok_val),.tok_user(tok_user),.sc_busy(sc_busy),.sc_fault(sc_fault),.stm_fault(stm_fault),.tld_fault(tld_fault),.hd_fault(hd_fault),.pc_bad(pc_bad),.sid(sid_mut),.stn_cfg(stn_cfg_mut),.sc_cfg(sc_cfg_mut),.stm_cfg(stm_cfg_mut),.su_cmd(su_cmd_mut),.am_v(am_v_mut),.am_idx(am_idx_mut),.am_val(am_val_mut),.am_u(am_u_mut),.w16_we(w16_we_mut),.w16_addr(w16_addr_mut),.w16_data(w16_data_mut),.w1_we(w1_we_mut),.w1_addr(w1_addr_mut),.w1_data(w1_data_mut),.own_ch(own_ch_mut),.ag_own(ag_own_mut),.st(st_mut),.cc_o(cc_o_mut));
initial begin
mutate=$test$plusargs("mutate");
rst_n=0;
for(cycle=0;cycle<8000;cycle=cycle+1) begin
@(negedge ck);
cmd_q[0 +: 32]=$urandom;
cmd_q[32 +: 32]=$urandom;
cmd_q[64 +: 32]=$urandom;
cmd_q[96 +: 20]=$urandom;
chd_q[0 +: 32]=$urandom;
chd_q[32 +: 32]=$urandom;
chd_q[64 +: 32]=$urandom;
chd_q[96 +: 32]=$urandom;
chd_q[128 +: 32]=$urandom;
chd_q[160 +: 32]=$urandom;
chd_q[192 +: 32]=$urandom;
chd_q[224 +: 32]=$urandom;
chd_q[256 +: 32]=$urandom;
chd_q[288 +: 32]=$urandom;
chd_q[320 +: 32]=$urandom;
chd_q[352 +: 32]=$urandom;
chd_q[384 +: 32]=$urandom;
chd_q[416 +: 32]=$urandom;
chd_q[448 +: 32]=$urandom;
chd_q[480 +: 32]=$urandom;
chd_q[512 +: 32]=$urandom;
chd_q[544 +: 32]=$urandom;
chd_q[576 +: 32]=$urandom;
chd_q[608 +: 32]=$urandom;
chd_q[640 +: 32]=$urandom;
chd_q[672 +: 32]=$urandom;
chd_q[704 +: 32]=$urandom;
chd_q[736 +: 32]=$urandom;
chd_q[768 +: 32]=$urandom;
chd_q[800 +: 32]=$urandom;
chd_q[832 +: 32]=$urandom;
chd_q[864 +: 32]=$urandom;
chd_q[896 +: 32]=$urandom;
chd_q[928 +: 32]=$urandom;
chd_q[960 +: 32]=$urandom;
chd_q[992 +: 32]=$urandom;
chd_q[1024 +: 14]=$urandom;
r_v[0 +: 1]=$urandom;
r_idx[0 +: 8]=$urandom;
r_last[0 +: 1]=$urandom;
r_d[0 +: 32]=$urandom;
r_d[32 +: 32]=$urandom;
r_d[64 +: 32]=$urandom;
r_d[96 +: 32]=$urandom;
r_d[128 +: 32]=$urandom;
r_d[160 +: 32]=$urandom;
r_d[192 +: 32]=$urandom;
r_d[224 +: 32]=$urandom;
r_d[256 +: 32]=$urandom;
r_d[288 +: 32]=$urandom;
r_d[320 +: 32]=$urandom;
r_d[352 +: 32]=$urandom;
r_d[384 +: 32]=$urandom;
r_d[416 +: 32]=$urandom;
r_d[448 +: 32]=$urandom;
r_d[480 +: 32]=$urandom;
l9o_v[0 +: 1]=$urandom;
stn_fault[0 +: 1]=$urandom;
vm_we[0 +: 8]=$urandom;
vm_waddr[0 +: 32]=$urandom;
vm_waddr[32 +: 32]=$urandom;
vm_waddr[64 +: 32]=$urandom;
vm_waddr[96 +: 32]=$urandom;
vm_waddr[128 +: 32]=$urandom;
vm_waddr[160 +: 32]=$urandom;
vm_wdata[0 +: 32]=$urandom;
vm_wdata[32 +: 32]=$urandom;
vm_wdata[64 +: 32]=$urandom;
vm_wdata[96 +: 32]=$urandom;
vm_wdata[128 +: 32]=$urandom;
vm_wdata[160 +: 32]=$urandom;
vm_wdata[192 +: 32]=$urandom;
vm_wdata[224 +: 32]=$urandom;
kv_we[0 +: 8]=$urandom;
kv_waddr[0 +: 32]=$urandom;
kv_waddr[32 +: 32]=$urandom;
kv_waddr[64 +: 32]=$urandom;
kv_waddr[96 +: 32]=$urandom;
kv_waddr[128 +: 32]=$urandom;
kv_waddr[160 +: 32]=$urandom;
kv_wdata[0 +: 32]=$urandom;
kv_wdata[32 +: 32]=$urandom;
kv_wdata[64 +: 32]=$urandom;
kv_wdata[96 +: 32]=$urandom;
kv_wdata[128 +: 32]=$urandom;
kv_wdata[160 +: 32]=$urandom;
kv_wdata[192 +: 32]=$urandom;
kv_wdata[224 +: 32]=$urandom;
su_nr[0 +: 1]=$urandom;
su_idle[0 +: 1]=$urandom;
su_fault[0 +: 1]=$urandom;
su_prog[0 +: 16]=$urandom;
su_rows[0 +: 16]=$urandom;
vm_fault[0 +: 1]=$urandom;
red_we[0 +: 1]=$urandom;
red_addr[0 +: 24]=$urandom;
red_data[0 +: 32]=$urandom;
sc_w1_we[0 +: 1]=$urandom;
sc_w1_addr[0 +: 24]=$urandom;
sc_w1_data[0 +: 32]=$urandom;
tok_v[0 +: 1]=$urandom;
tok_idx[0 +: 24]=$urandom;
tok_own[0 +: 1]=$urandom;
tok_val[0 +: 32]=$urandom;
tok_user[0 +: 2]=$urandom;
sc_busy[0 +: 1]=$urandom;
sc_fault[0 +: 1]=$urandom;
stm_fault[0 +: 1]=$urandom;
tld_fault[0 +: 1]=$urandom;
hd_fault[0 +: 1]=$urandom;
pc_bad[0 +: 1]=$urandom;
rst_n=(cycle>=8)&&!(cycle>=1700&&cycle<1708)&&!(cycle>=4300&&cycle<4308);
@(posedge ck); #1;
if(cycle>16) begin
compares=compares+1; if(sid_ref !== (mutate ? sid_mut : sid_dut)) begin failures=failures+1; if(failures<5)$display("CTL_REPAIR_MISMATCH sid cycle=%0d",cycle);end
compares=compares+1; if(stn_cfg_ref !== (mutate ? stn_cfg_mut : stn_cfg_dut)) begin failures=failures+1; if(failures<5)$display("CTL_REPAIR_MISMATCH stn_cfg cycle=%0d",cycle);end
compares=compares+1; if(sc_cfg_ref !== (mutate ? sc_cfg_mut : sc_cfg_dut)) begin failures=failures+1; if(failures<5)$display("CTL_REPAIR_MISMATCH sc_cfg cycle=%0d",cycle);end
compares=compares+1; if(stm_cfg_ref !== (mutate ? stm_cfg_mut : stm_cfg_dut)) begin failures=failures+1; if(failures<5)$display("CTL_REPAIR_MISMATCH stm_cfg cycle=%0d",cycle);end
compares=compares+1; if(su_cmd_ref !== (mutate ? su_cmd_mut : su_cmd_dut)) begin failures=failures+1; if(failures<5)$display("CTL_REPAIR_MISMATCH su_cmd cycle=%0d",cycle);end
compares=compares+1; if(am_v_ref !== (mutate ? am_v_mut : am_v_dut)) begin failures=failures+1; if(failures<5)$display("CTL_REPAIR_MISMATCH am_v cycle=%0d",cycle);end
compares=compares+1; if(am_idx_ref !== (mutate ? am_idx_mut : am_idx_dut)) begin failures=failures+1; if(failures<5)$display("CTL_REPAIR_MISMATCH am_idx cycle=%0d",cycle);end
compares=compares+1; if(am_val_ref !== (mutate ? am_val_mut : am_val_dut)) begin failures=failures+1; if(failures<5)$display("CTL_REPAIR_MISMATCH am_val cycle=%0d",cycle);end
compares=compares+1; if(am_u_ref !== (mutate ? am_u_mut : am_u_dut)) begin failures=failures+1; if(failures<5)$display("CTL_REPAIR_MISMATCH am_u cycle=%0d",cycle);end
compares=compares+1; if(w16_we_ref !== (mutate ? w16_we_mut : w16_we_dut)) begin failures=failures+1; if(failures<5)$display("CTL_REPAIR_MISMATCH w16_we cycle=%0d",cycle);end
compares=compares+1; if(w16_addr_ref !== (mutate ? w16_addr_mut : w16_addr_dut)) begin failures=failures+1; if(failures<5)$display("CTL_REPAIR_MISMATCH w16_addr cycle=%0d",cycle);end
compares=compares+1; if(w16_data_ref !== (mutate ? w16_data_mut : w16_data_dut)) begin failures=failures+1; if(failures<5)$display("CTL_REPAIR_MISMATCH w16_data cycle=%0d",cycle);end
compares=compares+1; if(w1_we_ref !== (mutate ? w1_we_mut : w1_we_dut)) begin failures=failures+1; if(failures<5)$display("CTL_REPAIR_MISMATCH w1_we cycle=%0d",cycle);end
compares=compares+1; if(w1_addr_ref !== (mutate ? w1_addr_mut : w1_addr_dut)) begin failures=failures+1; if(failures<5)$display("CTL_REPAIR_MISMATCH w1_addr cycle=%0d",cycle);end
compares=compares+1; if(w1_data_ref !== (mutate ? w1_data_mut : w1_data_dut)) begin failures=failures+1; if(failures<5)$display("CTL_REPAIR_MISMATCH w1_data cycle=%0d",cycle);end
compares=compares+1; if(own_ch_ref !== (mutate ? own_ch_mut : own_ch_dut)) begin failures=failures+1; if(failures<5)$display("CTL_REPAIR_MISMATCH own_ch cycle=%0d",cycle);end
compares=compares+1; if(ag_own_ref !== (mutate ? ag_own_mut : ag_own_dut)) begin failures=failures+1; if(failures<5)$display("CTL_REPAIR_MISMATCH ag_own cycle=%0d",cycle);end
compares=compares+1; if(st_ref !== (mutate ? st_mut : st_dut)) begin failures=failures+1; if(failures<5)$display("CTL_REPAIR_MISMATCH st cycle=%0d",cycle);end
compares=compares+1; if(cc_o_ref !== (mutate ? cc_o_mut : cc_o_dut)) begin failures=failures+1; if(failures<5)$display("CTL_REPAIR_MISMATCH cc_o cycle=%0d",cycle);end
end
end
if(failures) begin $display("CTL_REPAIR_EQ FAIL mismatches=%0d compares=%0d",failures,compares);$finish;end
else begin $display("CTL_REPAIR_EQ PASS compares=%0d cycles=%0d",compares,cycle);$finish;end
end
endmodule
