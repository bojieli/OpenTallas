L=/srv/opentallas-scratch/claude/s81-rtlgap-idx-1021
cd $L
case $1 in
rstfix_tt) bash run_idx72.sh $L/out rstfix_tt kit_tt var/rstfix_tt.sv tb_idx72.sv tb_extra.f 16  "pass_small|+N=4096 +B=13 +T0=400 +P=3"  "pass_gs|+GATHER=1 +N=256 +T0=1500 +P=3"  "pass_g2048|+GATHER=1 +N=2048 +T0=1500 +P=4"  "pass_g2048s2|+GATHER=1 +N=2048 +T0=1500 +P=4 +SEED=2"  "closed_g2048p3|+GATHER=1 +N=2048 +T0=1500 +P=3"  "pass_open6|+N=4096 +B=13 +T0=400 +P=3 +OPEN=6"  "pass_l2|+N=43691 +B=13 +T0=400 +P=3"  "pass_l2s2|+N=43691 +B=13 +T0=400 +P=3 +SEED=2"  "pass_l20|+N=87382 +B=13 +T0=400 +P=3"  "closed_late|+N=4096 +B=13 +T0=60 +P=3"  "closed_glate|+GATHER=1 +N=2048 +T0=60 +P=4"  "fail_slothit|+N=4096 +B=13 +T0=400 +P=3 +SLOTHIT=1"  "x_l2t0600|+N=43691 +B=13 +T0=600 +P=3"  "x_t0s300|+N=4096 +B=13 +T0=300 +P=3"  "x_t0s500|+N=4096 +B=13 +T0=500 +P=3"  "x_gt0s2000|+GATHER=1 +N=2048 +T0=2000 +P=4" ;;
rstfix_ff) bash run_idx72.sh $L/out rstfix_ff kit_ff var/rstfix_ff.sv tb_idx72.sv tb_extra.f 8  "pass_small|+N=4096 +B=13 +T0=400 +P=3" "pass_l2|+N=43691 +B=13 +T0=400 +P=3"  "pass_g2048|+GATHER=1 +N=2048 +T0=1500 +P=4" "closed_late|+N=4096 +B=13 +T0=60 +P=3" "x_l2t0600|+N=43691 +B=13 +T0=600 +P=3" ;;
asis_tt) bash run_idx72.sh $L/out asis_tt kit_tt var/asis_tt.sv tb_idx72.sv tb_extra.f 4  "fail_asis_small|+N=4096 +B=13 +T0=400 +P=3" "fail_asis_l2|+N=43691 +B=13 +T0=600 +P=3" ;;
m1_tt) bash run_idx72.sh $L/out m1_tt kit_tt var/m1_tt.sv tb_idx72.sv tb_extra.f 4  "fail_m1_small|+N=4096 +B=13 +T0=400 +P=3" "fail_m1_l2|+N=43691 +B=13 +T0=600 +P=3" ;;
esac
