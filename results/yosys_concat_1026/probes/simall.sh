#!/bin/bash
# runs on host (iverilog); netlists made in docker beforehand
S=ot_qfd_su_kv_static_posted; N=ot_qfd_su_kv_native_posted; cd sim
run(){ name=$1; shift; iverilog -g2012 -o $name "$@" 2>/dev/null >/dev/null || { echo "$name BUILD FAIL"; return; }; echo "$name: $(vvp -n $name | grep LOCKSTEP)"; }
for L in 0 1; do
 run st_rtl_L$L -P tb.LOCAL_CTL=$L ../tb_lock.sv ${S}_orig.sv ../fix/$S.sv
 run st_mut_L$L -P tb.LOCAL_CTL=$L -P tb.MUT_TAG_T=1 ../tb_lock.sv ${S}_orig.sv ../fix/$S.sv
 run st_ysfix_L$L -DNETLIST -P tb.LOCAL_CTL=$L ../tb_lock.sv ${S}_orig.sv ../net/fix_${S}_L$L.v
 run st_ysorig_L$L -DNETLIST -P tb.LOCAL_CTL=$L ../tb_lock.sv ${S}_orig.sv ../net/orig_${S}_L$L.v
done
run na_rtl -DNATIVE ../tb_lock.sv ${N}_orig.sv ../fix/$N.sv
run na_mut -DNATIVE -P tb.MUT_TAG_T=1 ../tb_lock.sv ${N}_orig.sv ../fix/$N.sv
run na_ysfix -DNATIVE -DNETLIST ../tb_lock.sv ${N}_orig.sv ../net/fix_$N.v
run na_ysorig -DNATIVE -DNETLIST ../tb_lock.sv ${N}_orig.sv ../net/orig_$N.v
