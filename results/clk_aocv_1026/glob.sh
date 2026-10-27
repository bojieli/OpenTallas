set -e
N=/srv/opentallas-scratch2/claude/infra-r3-1026/ngspice; M=/srv/opentallas-scratch2/claude/clk-aocv-1026/mc
mkdir -p $M/lib/SS $M/glob
docker run --rm --memory 2g -v $N:/n:ro -v $M:/w ot-ngspice:r3 python3 -I /n/scripts/mkcells.py /n/dl/stdcell/asap7sc7p5t_28/CDL/xAct3D_extracted/asap7sc7p5t_28_R.sp /n/dl/asap7pdk/asap7_pdk_r1p7/models/hspice/7nm_SS.pm /w/lib/SS BUFx24_ASAP7_75t_R BUFx8_ASAP7_75t_R
for P in TT SS FF; do
cat > $M/glob/g_$P.sp <<SP
* process-only global corner: $P card at TT supply/temperature
.control
pre_osdi /w/osdi/bsimcmg23.osdi
set noaskquit
run
quit
.endc
.options klu
.temp 25
.include /w/lib/$P/models.sp
.include /w/lib/TT/cells.sp
Vdd vdd 0 0.7
Vss vss 0 0
Vin a 0 PWL(0 0 100p 0 150p 0.7)
X1 vss vdd a y1 BUFx24_ASAP7_75t_R
Cl1 y1 0 184.32f
X2 vss vdd a y2 BUFx8_ASAP7_75t_R
Cl2 y2 0 20f
.meas tran d24 TRIG v(a) VAL=0.35 RISE=1 TARG v(y1) VAL=0.35 RISE=1
.meas tran d8 TRIG v(a) VAL=0.35 RISE=1 TARG v(y2) VAL=0.35 RISE=1
.tran 0.1p 500p 0 0.5p
.end
SP
docker run --rm --memory 2g -v $M:/w -w /w/glob ot-ngspice:r3 sh -c "ngspice -b g_$P.sp 2>&1 | grep -E '^d(24|8) '" | sed "s/^/$P /"
done
