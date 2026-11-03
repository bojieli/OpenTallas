#!/bin/bash
# XCHECK-1: generate + run link probes in ORFS docker (mem cap 4g). args: none. run from xcheck-1 dir.
set -u
X=/home/ubuntu/scratch-root/claude/xcheck-1; W=$X/wt; O=$X/link; mkdir -p $O
lib(){ (cd $W && git ls-files "*/$1_$2.lib" | head -1); }
for m in ot_pdie_serdes ot_hbm3e_phy_v41x_aw30_e8p5 ot_hbm3e_phy_rc_e8p5 ot_qfd_serdes_112g_x12_phy_s597 ot_qfd_ucie_x64_phy ot_qkvd_ucie_x64_phy qfd_ucie_six_five ot_ucie_pma_txm ot_ucie_pma_rxm; do
  t=$(lib $m tt); f=$(lib $m ff); [ -z "$t" ] && { echo "NOLIB $m"; continue; }
  mkdir -p $O/$m; cp $W/$t $O/$m/m_tt.lib; cp $W/$f $O/$m/m_ff.lib; (cd $O/$m && python3 -I $X/xchk_link.py $O $m m_tt.lib m_ff.lib) >/dev/null || { echo "GENFAIL $m"; continue; }
  for c in tt ff; do
    docker run --rm --memory 4g -v $W:/w:ro -v $O/$m:/r -w /r openroad/orfs:asap7lock \
      /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/sta -no_init -exit sta_$c.tcl > $O/$m/sta_$c.log 2>&1
    grep -E '^XCHK|VIOLAT|min_period|Error' $O/$m/sta_$c.log | head -12
  done
done
