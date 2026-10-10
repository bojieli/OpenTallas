# mtp-hbm 2026-10-08: ot_gpu_scratch_service_m (CAP2) in a 410 x 410 um frame: the two 1024x256 banks stacked at the
# centre, >= 60 um from every pin edge (fp-lint macro_edge: the auto placer put bank 1 2.2 um off the S pin face)
place_macro -macro_name {g_bank\[0\].u_sram} -location {117.612 120.96} -orientation R0
place_macro -macro_name {g_bank\[1\].u_sram} -location {117.612 216.0} -orientation R0
