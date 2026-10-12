# ORFS SYNTH_CANONICALIZE_TCL hook (hbm-forks 2026-10-09): keep every ot_svc_vpipe stage register as its own cell.
# opt_merge otherwise merges stages of different chains whose inputs are equal (svc PS SE_s3: the four c_sg tag chains
# fed by one source, and c_sg3_0's first valid stage with c_sd16_0's, became one register placed for ONE chain; the
# other chain's output then ran ~920 um unregistered to its face pin, routed TT -498 ps).  The wire-stage fence places
# each chain's stages on its own line, so each needs its own registers.
yosys proc
yosys setattr -set keep 1 {*ot_svc_vpipe/t:$dff} {*ot_svc_vpipe/t:$adff} {ot_svs_rdyp/t:$adff} {*ot_svs_rdyp/t:$adff}
