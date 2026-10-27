S=ot_qfd_su_kv_static_posted; N=ot_qfd_su_kv_native_posted; mkdir -p net
for v in orig fix; do
 for L in 0 1; do bash ysnet.sh $v/$S.sv $S "ENABLE=1 HEADS=1 LOCAL_CTL=$L" net/${v}_${S}_L$L.v & done
 bash ysnet.sh $v/$N.sv $N "ENABLE=1 HEADS=1" net/${v}_$N.v &
done; wait
