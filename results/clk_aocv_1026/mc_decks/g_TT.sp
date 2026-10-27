* process-only global corner: TT card at TT supply/temperature
.control
pre_osdi /w/osdi/bsimcmg23.osdi
set noaskquit
run
quit
.endc
.options klu
.temp 25
.include /w/lib/TT/models.sp
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
