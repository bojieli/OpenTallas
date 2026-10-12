Attention halves two-level lockstep (physical/hbm_attn_tile_r/half/run_lockh.sh, RTL f55fbf5e1 on claude/el1011-hbm-attn-phys,
ot-epyc4, Verilator 5.050; params -GCG=1 -GLNK=3 -GLNC=1 -GLNR=2 -GLPMID=3 -GLNFR=4 -GLNXP=3 -GXPX=2 -GLLDKR=16):
split halves (lo + hi, closed banks sn544/sn136/ew544/ew136 + quads + glue) vs the one-piece hfd_attn_tile_b.
pos.out: roles 0-5 0 mismatches -> ATTN_LOCKH PASS.  neg.out: mutants 1-6 all FAIL -> ATTN_LOCKH NEG ALL CAUGHT.
