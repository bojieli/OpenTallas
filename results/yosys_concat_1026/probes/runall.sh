S=ot_qfd_su_kv_static_posted; N=ot_qfd_su_kv_native_posted
for p in 'ENABLE=1 HEADS=1 LOCAL_CTL=0' 'ENABLE=1 HEADS=1 LOCAL_CTL=1' 'ENABLE=1 HEADS=1 LOCAL_CTL=1 MUT_TAG=1'; do
 bash eqv.sh . slang orig/$S.sv slang fix/$S.sv $S "$p" &
 bash eqv.sh . slang orig/$S.sv verilog fix/$S.sv $S "$p" &
 bash eqv.sh . slang orig/$S.sv verilog orig/$S.sv $S "$p" &
done
for p in 'ENABLE=1 HEADS=1' 'ENABLE=1 HEADS=2' 'ENABLE=1 HEADS=1 MUT_TAG=1'; do
 bash eqv.sh . slang orig/$N.sv slang fix/$N.sv $N "$p" &
 bash eqv.sh . slang orig/$N.sv verilog fix/$N.sv $N "$p" &
 bash eqv.sh . slang orig/$N.sv verilog orig/$N.sv $N "$p" &
done
bash eqv.sh . slang orig/$S.sv slang fix/$S.sv $S 'ENABLE=1 HEADS=1 LOCAL_CTL=1' 'ENABLE=1 HEADS=1 LOCAL_CTL=1 MUT_TAG=1' &
bash eqv.sh . slang orig/$N.sv slang fix/$N.sv $N 'ENABLE=1 HEADS=1' 'ENABLE=1 HEADS=1 MUT_TAG=1' &
wait
