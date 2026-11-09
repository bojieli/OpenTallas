# Per-PE load locality candidate

Measured compact RXS vB placed TT: global WNS -75.51 ps / TNS -4447.44 ps, ld2[2][3] to BM2 group3 PE18 theta. BM arithmetic-source subset +109.55 ps. Thus keep 30 one-cycle RiBM steps and NBM=3; no calendar change.

Candidate OT_S81_KP4_BM_PE_LOCAL gives each of 46 PEs its own existing-cycle ld2/gamma/discrepancy/k copies (NG=46 instead of8). A PE's selector then serves two 10-bit operands and its local state, instead of up to6 PEs. This adds 38*3*(10+10+6+1)=3078 control bits, approximately950 um2 at measured FF sizes; estimated total core area increases around5%. Same 216 square pilot remains modelable near40% core fill, subject to actual synthesis count. Same reset and next-state equations; no new edge. Source opt-in only; not active in any existing kit.

Required before PLACE: equivalence under repeated30-cycle reload, warm resets and random syndromes; deliberate wrong-copy negative control; actual synth/RAW guard and pin/clock review. Actual placed timing must establish that load fanout was reduced and syndrome Sl broadcasts did not become new critical paths. No CTS approval implied.
