import sys
t = open(sys.argv[1]).read()
def inst(t, head, add):
    i = t.index(head); j = t.index(");\n", i)
    return t[:j] + ", " + add + t[j:]
assert t.count("\n  qkd_host_root_admission #(") == 1
t = t.replace("\n  qkd_host_root_admission #(", "\n  qkd_host_root_admission_obsx #(", 1)
t = inst(t, "\n  qkd_d2d_cal_seq_pin_bc4 #(", ".adm_done(n_ks_obs_dcal[0]), .cal_ready(n_ks_obs_dcal[1]), .running(n_ks_obs_dcal[2]), .layer(n_ks_obs_dlay[5:0])")
assert t.count(") d2d_kv (") == 1
t = inst(t, ") d2d_kv (", ".recovery_cycles(n_ks_obs_rcy[31:0])")
t = inst(t, "\n  qkd_host_root_admission_obsx #(", ".obs_dcal_adm_done(n_ks_obs_dcal[0]), .obs_dcal_cal_ready(n_ks_obs_dcal[1]), .obs_dcal_running(n_ks_obs_dcal[2]), .obs_dcal_layer(n_ks_obs_dlay[5:0]), .obs_d2d_recovery_cycles(n_ks_obs_rcy[31:0])")
k = t.index("  wire [1:0] n_dcal_cfg;\n")
t = t[:k] + "  wire [2:0] n_ks_obs_dcal;\n  wire [5:0] n_ks_obs_dlay;\n  wire [31:0] n_ks_obs_rcy;\n" + t[k:]
open(sys.argv[2], "w").write(t)
print("patched b")
