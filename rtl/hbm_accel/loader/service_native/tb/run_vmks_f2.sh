#!/bin/bash
# HBM-HARD-2-KSH proof of f2: run_f2.sh SRC OUT [JOBS]  (verilator v5.032 container)
S=$1;O=$2;J=${3:-6};mkdir -p $O
cat > $O/one.sh <<'X'
#!/bin/bash
n=$1;e=$2;g=$3;pa=$4;O=/o;S=/s
DEP="$S/tb_hbm_svc_vmks_forms.sv $S/ot_hbm_svc_vmks_f2.sv $S/ot_hbm_svc_vmks_forms.sv $S/ot_hbm_svc_vm_kshare_splitstrap.sv $S/ot_hbm_svc_pc_ctrl_leaf.sv $S/ot_hbm_svc_async_fifo.sv $S/ot_hbm_svc_ring_h9b_ff.sv $S/ot_reset_sync.sv"
verilator --binary --timing -j 2 -O1 -Wno-fatal -Wno-lint -Wno-style --top-module tb_hbm_svc_vmks_forms --Mdir $O/obj-$n -o sim $g $DEP > $O/$n.build.log 2>&1 || { echo "$n BUILD FAIL";exit 0; }
timeout 3000 $O/obj-$n/sim $pa > $O/$n.log 2>&1
l=$(grep -E '^(PASS|FAIL)' $O/$n.log|tail -1)
case "$e:$l" in PASS:PASS*|FAIL:FAIL*) v=OK;; *) v=UNEXPECTED;; esac
echo "$v $n expect=$e : $l"; rm -rf $O/obj-$n
X
run(){ while [ "$(jobs -r|wc -l)" -ge "$J" ];do wait -n;done
 docker run --rm --entrypoint bash --cpus=2 --memory=8g -v $S:/s:ro -v $O:/o verilator/verilator:v5.032 /o/one.sh "$1" "$2" "$3" "$4" >> $O/summary.log 2>&1 & }
T="-GCHECK=2"
run eq1 PASS "$T" "+WINDOWS=24 +SEED=1"
run eq2 PASS "$T" "+WINDOWS=24 +SEED=2"
run fast PASS "$T" "+WINDOWS=24 +SEED=3 +HBM_HALF=350 +STR_HALF=600"
run slow PASS "$T" "+WINDOWS=24 +SEED=4 +HBM_HALF=600 +STR_HALF=350"
run slowstr PASS "$T" "+WINDOWS=24 +SEED=8 +HBM_HALF=300 +STR_HALF=1500"
run wb PASS "$T" "+WINDOWS=1500 +SEED=7 +WBONLY=1 +GN=200"
run burst PASS "$T" "+WINDOWS=500 +SEED=9 +WBONLY=2 +GN=200"
run far PASS "$T" "+WINDOWS=150 +SEED=10 +WBONLY=3 +GN=200 +FARSLOW=1 +WAITT=2"
run badtag PASS "$T" "+WINDOWS=24 +SEED=1 +BADTAG=1"
run mid PASS "$T" "+WINDOWS=24 +SEED=11 +MIDRST=5"
run midwb PASS "$T" "+WINDOWS=300 +SEED=12 +WBONLY=1 +GN=200 +MIDRST=40"
for m in 1 2 4 5 6 7 8 10 17 19 20 21;do run m$m FAIL "$T -GMUT=$m" "+WINDOWS=24 +SEED=1";done
run m11 FAIL "$T -GMUT=11" "+WINDOWS=1500 +SEED=6 +WBONLY=1 +GN=200"
run m18wb FAIL "$T -GMUT=18" "+WINDOWS=1500 +SEED=6 +WBONLY=1 +GN=200"
run m17wb FAIL "$T -GMUT=17" "+WINDOWS=1500 +SEED=6 +WBONLY=1 +GN=200"
run m23 FAIL "$T -GMUT=23" "+WINDOWS=150 +SEED=10 +WBONLY=3 +GN=200 +FARSLOW=1 +WAITT=2"
run m24 FAIL "$T -GMUT=24" "+WINDOWS=24 +SEED=1 +BADTAG=1"
run m9 FAIL "$T -GMUT=9" "+WINDOWS=24 +SEED=8 +HBM_HALF=300 +STR_HALF=1500"
run vmb PASS "$T" "+WINDOWS=24 +SEED=1 +VMBURST=1"
run vmb2 PASS "$T" "+WINDOWS=24 +SEED=2 +VMBURST=1 +HBM_HALF=350 +STR_HALF=600"
run m12vm FAIL "$T -GMUT=12" "+WINDOWS=24 +SEED=1 +VMBURST=1"
run m3far FAIL "$T -GMUT=3" "+WINDOWS=48 +SEED=1 +FARSLOW=1"
run m3far2 FAIL "$T -GMUT=3" "+WINDOWS=48 +SEED=2 +FARSLOW=1"
run far2 PASS "$T" "+WINDOWS=48 +SEED=1 +FARSLOW=1"
run m25 FAIL "$T -GMUT=25" "+WINDOWS=1500 +SEED=6 +WBONLY=1 +GN=200"
run m22 FAIL "$T -GMUT=22" "+WINDOWS=24 +SEED=11 +MIDRST=2 +MIDEVERY=1"
run midev PASS "$T" "+WINDOWS=24 +SEED=11 +MIDRST=2 +MIDEVERY=1"
run m22wb FAIL "$T -GMUT=22" "+WINDOWS=300 +SEED=12 +WBONLY=1 +GN=200 +MIDRST=40 +MIDEVERY=1"
run midevw PASS "$T" "+WINDOWS=300 +SEED=12 +WBONLY=1 +GN=200 +MIDRST=40 +MIDEVERY=1"
run far3 PASS "$T" "+WINDOWS=150 +SEED=13 +WBONLY=3 +GN=200 +FARSLOW=1 +WAITT=2"
run m23b FAIL "$T -GMUT=23" "+WINDOWS=150 +SEED=13 +WBONLY=3 +GN=200 +FARSLOW=1 +WAITT=2"
wait
echo ALLDONE >> $O/summary.log
