# face_chain_place.tcl per-port depth (stations mcast --pin-stages 2; run with OT_FC_STAGES=0): stage 0 midway between
# the meso readout and the pin, the pin register AT the tap pin (mcast_r5 337a5afcb: pin-stages 2 left the pin register
# 10 buffer levels from t0, SS -41).  Every other port depth 0 = untouched: a (input: fwd + meso, two loads), b (forwarded
# RC flop already at its face), rst.
set fc_ps(t0) 2
set fc_ps(t1) 2
set fc_psi(a) 0
set fc_ps(b) 0
