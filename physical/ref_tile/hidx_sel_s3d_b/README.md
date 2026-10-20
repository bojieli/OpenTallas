# hidx_sel_s3d_b -- FAN32 ctl tile ot_hidx_s3_ctl of the landed IDX selector cluster (HBM-IDX6, 10-20)
Successor of hidx_sel_s3c_b: census FAIL 2 (d_go 61 loads, reset leaf 115) and util 16%/10%. Now d_go is 4 kept copies
(one per quadrant tie register), the reset relay has 6 regional leaves, the dead !rc_n term of thr_n is dropped; ports,
timing and arithmetic unchanged (lockstep equivalence vs ot_hidx_s3_ctl_ref, rtl/test/hbm_idx_static/run_s3_equiv.sh).
Outline 32.4 x 27.0 um from the s3c synthesis area 306 um2 (gate: std 298 um2, util ~47-48%); pin ranges scaled per face
(<= 4.7 pins/um).
## Gate (--cts, da849b068): PASS 0 fail 0 warn; native32 census PASS max 30; TT/FF pin-flop spread ~5 ps; setup WNS
~+70 ps, hold WNS ~+50 ps; 466 flops, depth 547 ps.
## SAFE-DESIGN checklist
1 Pins PASS (cw_r/k_r/a_ret/a_qf pin flops, registered outputs, 2-stage reset landing); 2 Reach PASS (29 um tile);
3 Fanout PASS (census max 30); 4 Depth PASS (547 ps); 5 Storage PASS (no arrays); 6 Floorplan PASS (util 47-48%,
square-ish, no macros); 7 Clock PASS (one root, spread ~5 ps); 8 Schedule PASS (static, unchanged calendar).
