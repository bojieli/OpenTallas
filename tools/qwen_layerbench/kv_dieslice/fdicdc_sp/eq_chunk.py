#!/usr/bin/env python3
"""KV-TYPES-3 11-07 strict equiv of ot_fdi_phy_cdc SEL_PIPE 1, SEL_CHUNK GOLD vs GATE (register duplication).

python3 eq_chunk.py W GOLD_CHUNK GATE_CHUNK OUT.ys [GATE_DEFINES]; run OUT.ys in the ORFS image with /wt = worktree.
Select copies of both sides are merged by opt_merge (sound: identical next-state cells), every storage bit of the gate
is renamed to its gold key (bit g -> g_c[g/GOLD].smem[e][g%GOLD]), then equiv_simple + equiv_induct prove all
outputs and registers.  Controls: GATE_DEFINES -DOT_SP_MUT_WSEL / -DOT_SP_MUT_RSEL must FAIL."""
import sys
W=int(sys.argv[1]); GC=int(sys.argv[2]); TC=int(sys.argv[3]); D=8
def prep(sc, tag, dfn=''):
    return f"""design -reset
read_verilog -sv -DSYNTHESIS {dfn} /wt/rtl/lib/ot_reset_sync.sv /wt/rtl/lib/ot_async_fifo.sv /wt/rtl/physical/ot_fdi_phy_cdc.sv
chparam -set W {W} -set DEPTH {D} -set SEL_PIPE 1 -set SEL_CHUNK {sc} ot_fdi_phy_cdc
hierarchy -check -top ot_fdi_phy_cdc
proc; setattr -mod -unset keep_hierarchy; flatten; opt_clean; memory -nomap; memory_map; opt -fast
setattr -unset keep
setattr -mod -unset keep
opt_merge -share_all; opt_clean
splitnets w:*smem*
"""
out=[]
out.append(prep(GC,'gold')+"rename ot_fdi_phy_cdc gold\ndesign -save G\n")
out.append(prep(TC,'gate',sys.argv[5] if len(sys.argv)>5 else '')+"cd ot_fdi_phy_cdc\n")
# rename gate bits to gold names via a temp prefix
for f in ('u_rx','u_tx'):
    for g in range(W):
        j,b=divmod(g,TC); k,c=divmod(g,GC)
        for e in range(D):
            out.append(f"rename {f}.g_sp.g_c[{j}].smem[{e}][{b}] OTTMP.{f}.{k}.{e}.{c}\n")
for f in ('u_rx','u_tx'):
    for g in range(W):
        k,c=divmod(g,GC)
        for e in range(D):
            out.append(f"rename OTTMP.{f}.{k}.{e}.{c} {f}.g_sp.g_c[{k}].smem[{e}][{c}]\n")
out.append("""cd ..
rename ot_fdi_phy_cdc gate
design -copy-from G -as gold gold
async2sync
equiv_make gold gate eq
hierarchy -top eq
equiv_simple -seq 3
equiv_induct -seq 3
equiv_status -assert
""")
open(sys.argv[4],'w').write(''.join(out))
