#!/bin/bash
# HBM-CORES-B q3bc CF2: formal proof that the restart kill is unreachable (P1 comb on the reject chain, P2 one-step), with mutant control M4 (must be SAT/fail).
cd /srv/opentallas-scratch2/claude/hbm-cores-b/q3bc_sf
D=/srv/opentallas-scratch2/claude/hbm-cores-b/q3bc_sf
for i in $(seq 1 400); do grep -q '^DONE' cf2/run.log && ! pgrep -u ubuntu -f '^/bin/bash ./cf2_run.sh' >/dev/null && break; sleep 30; done
IMG=${IMG:-openroad/orfs:latest}
for N in CF2 M4; do
 sed -E 's/^  wire _hcbr_p([12]) =/  (* keep *) wire _hcbr_p\1 =/' cf2/gate_$N.sv > cf2/pv_$N.sv
 cat > cf2/prove_$N.ys <<EOY
read_liberty -lib /q/eq/ot_sram_1r1w_256x256_m2_r2c2_tt.lib
read_liberty -lib /q/eq/ot_sram_1rw_256x64_m4_r2c2_tt.lib
read_slang --compat=vcs --ignore-assertions --top ot_hfd_coll_q3_body_ctl_g --single-unit -DSYNTHESIS -DOT_Q3CTL_TGTQ1 -DOT_Q3CTL_PREACC -DOT_Q3CTL_OFF4_RT -DOT_Q3CTL_CFG_CASE /q/cf2/pv_$N.sv /q/rtl/ot_hfd_coll_q3_body_ctl.sv /q/rtl/ot_bodyctl_off32_split_d.sv /q/rtl/ot_bodyctl_cfg_case.sv --blackboxed-module ot_sram_1r1w_256x256_m2_r2c2 --blackboxed-module ot_sram_1rw_256x64_m4_r2c2
proc; flatten; opt_clean; async2sync; delete t:ot_sram_*
sat -set-init-zero -tempinduct -maxsteps 8 -prove _hcbr_p1 0 -prove _hcbr_p2 0 ot_hfd_coll_q3_body_ctl_g
EOY
 docker run --rm --name hcb-q3bc-prove-$N --memory=32g --memory-swap=32g --cpus=4 -v $D:/q -w /q $IMG bash -c "export PATH=\$PATH:/OpenROAD-flow-scripts/tools/install/yosys/bin; timeout 7200 yosys -l /q/cf2/prove_$N.log /q/cf2/prove_$N.ys >/dev/null 2>&1; echo rc=\$? > /q/cf2/prove_$N.rc"
 echo "$N $(cat cf2/prove_$N.rc)"; grep -E "SUCCESS|FAIL|Proof|proved|not proved|ERROR" cf2/prove_$N.log | tail -n 5 | cut -c1-120
done
echo PROVE_DONE
