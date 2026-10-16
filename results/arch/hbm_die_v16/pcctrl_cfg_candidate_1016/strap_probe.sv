module pcctrl_strap_probe;
initial begin
begin : ctl_NE_p00
localparam integer P=0,PHASE=0;
localparam integer RP=(PHASE+P*118/32)%118;
localparam integer RELOAD=118+RP+((RP+118+P)%2);
$display("STRAP ctl_NE_p00 %0d %0d", P, RELOAD);
end
begin : ctl_NE_p01
localparam integer P=1,PHASE=0;
localparam integer RP=(PHASE+P*118/32)%118;
localparam integer RELOAD=118+RP+((RP+118+P)%2);
$display("STRAP ctl_NE_p01 %0d %0d", P, RELOAD);
end
begin : ctl_NE_p02
localparam integer P=2,PHASE=0;
localparam integer RP=(PHASE+P*118/32)%118;
localparam integer RELOAD=118+RP+((RP+118+P)%2);
$display("STRAP ctl_NE_p02 %0d %0d", P, RELOAD);
end
begin : ctl_NE_p03
localparam integer P=3,PHASE=0;
localparam integer RP=(PHASE+P*118/32)%118;
localparam integer RELOAD=118+RP+((RP+118+P)%2);
$display("STRAP ctl_NE_p03 %0d %0d", P, RELOAD);
end
begin : ctl_NE_p04
localparam integer P=4,PHASE=0;
localparam integer RP=(PHASE+P*118/32)%118;
localparam integer RELOAD=118+RP+((RP+118+P)%2);
$display("STRAP ctl_NE_p04 %0d %0d", P, RELOAD);
end
begin : ctl_NE_p05
localparam integer P=5,PHASE=0;
localparam integer RP=(PHASE+P*118/32)%118;
localparam integer RELOAD=118+RP+((RP+118+P)%2);
$display("STRAP ctl_NE_p05 %0d %0d", P, RELOAD);
end
begin : ctl_NE_p06
localparam integer P=6,PHASE=0;
localparam integer RP=(PHASE+P*118/32)%118;
localparam integer RELOAD=118+RP+((RP+118+P)%2);
$display("STRAP ctl_NE_p06 %0d %0d", P, RELOAD);
end
begin : ctl_NE_p07
localparam integer P=7,PHASE=0;
localparam integer RP=(PHASE+P*118/32)%118;
localparam integer RELOAD=118+RP+((RP+118+P)%2);
$display("STRAP ctl_NE_p07 %0d %0d", P, RELOAD);
end
begin : ctl_NE_p08
localparam integer P=8,PHASE=0;
localparam integer RP=(PHASE+P*118/32)%118;
localparam integer RELOAD=118+RP+((RP+118+P)%2);
$display("STRAP ctl_NE_p08 %0d %0d", P, RELOAD);
end
begin : ctl_NE_p09
localparam integer P=9,PHASE=0;
localparam integer RP=(PHASE+P*118/32)%118;
localparam integer RELOAD=118+RP+((RP+118+P)%2);
$display("STRAP ctl_NE_p09 %0d %0d", P, RELOAD);
end
begin : ctl_NE_p10
localparam integer P=10,PHASE=0;
localparam integer RP=(PHASE+P*118/32)%118;
localparam integer RELOAD=118+RP+((RP+118+P)%2);
$display("STRAP ctl_NE_p10 %0d %0d", P, RELOAD);
end
begin : ctl_NE_p11
localparam integer P=11,PHASE=0;
localparam integer RP=(PHASE+P*118/32)%118;
localparam integer RELOAD=118+RP+((RP+118+P)%2);
$display("STRAP ctl_NE_p11 %0d %0d", P, RELOAD);
end
begin : ctl_NE_p12
localparam integer P=12,PHASE=0;
localparam integer RP=(PHASE+P*118/32)%118;
localparam integer RELOAD=118+RP+((RP+118+P)%2);
$display("STRAP ctl_NE_p12 %0d %0d", P, RELOAD);
end
begin : ctl_NE_p13
localparam integer P=13,PHASE=0;
localparam integer RP=(PHASE+P*118/32)%118;
localparam integer RELOAD=118+RP+((RP+118+P)%2);
$display("STRAP ctl_NE_p13 %0d %0d", P, RELOAD);
end
begin : ctl_NE_p14
localparam integer P=14,PHASE=0;
localparam integer RP=(PHASE+P*118/32)%118;
localparam integer RELOAD=118+RP+((RP+118+P)%2);
$display("STRAP ctl_NE_p14 %0d %0d", P, RELOAD);
end
begin : ctl_NE_p15
localparam integer P=15,PHASE=0;
localparam integer RP=(PHASE+P*118/32)%118;
localparam integer RELOAD=118+RP+((RP+118+P)%2);
$display("STRAP ctl_NE_p15 %0d %0d", P, RELOAD);
end
begin : ctl_NE_p16
localparam integer P=16,PHASE=0;
localparam integer RP=(PHASE+P*118/32)%118;
localparam integer RELOAD=118+RP+((RP+118+P)%2);
$display("STRAP ctl_NE_p16 %0d %0d", P, RELOAD);
end
begin : ctl_NE_p17
localparam integer P=17,PHASE=0;
localparam integer RP=(PHASE+P*118/32)%118;
localparam integer RELOAD=118+RP+((RP+118+P)%2);
$display("STRAP ctl_NE_p17 %0d %0d", P, RELOAD);
end
begin : ctl_NE_p18
localparam integer P=18,PHASE=0;
localparam integer RP=(PHASE+P*118/32)%118;
localparam integer RELOAD=118+RP+((RP+118+P)%2);
$display("STRAP ctl_NE_p18 %0d %0d", P, RELOAD);
end
begin : ctl_NE_p19
localparam integer P=19,PHASE=0;
localparam integer RP=(PHASE+P*118/32)%118;
localparam integer RELOAD=118+RP+((RP+118+P)%2);
$display("STRAP ctl_NE_p19 %0d %0d", P, RELOAD);
end
begin : ctl_NE_p20
localparam integer P=20,PHASE=0;
localparam integer RP=(PHASE+P*118/32)%118;
localparam integer RELOAD=118+RP+((RP+118+P)%2);
$display("STRAP ctl_NE_p20 %0d %0d", P, RELOAD);
end
begin : ctl_NE_p21
localparam integer P=21,PHASE=0;
localparam integer RP=(PHASE+P*118/32)%118;
localparam integer RELOAD=118+RP+((RP+118+P)%2);
$display("STRAP ctl_NE_p21 %0d %0d", P, RELOAD);
end
begin : ctl_NE_p22
localparam integer P=22,PHASE=0;
localparam integer RP=(PHASE+P*118/32)%118;
localparam integer RELOAD=118+RP+((RP+118+P)%2);
$display("STRAP ctl_NE_p22 %0d %0d", P, RELOAD);
end
begin : ctl_NE_p23
localparam integer P=23,PHASE=0;
localparam integer RP=(PHASE+P*118/32)%118;
localparam integer RELOAD=118+RP+((RP+118+P)%2);
$display("STRAP ctl_NE_p23 %0d %0d", P, RELOAD);
end
begin : ctl_NE_p24
localparam integer P=24,PHASE=0;
localparam integer RP=(PHASE+P*118/32)%118;
localparam integer RELOAD=118+RP+((RP+118+P)%2);
$display("STRAP ctl_NE_p24 %0d %0d", P, RELOAD);
end
begin : ctl_NE_p25
localparam integer P=25,PHASE=0;
localparam integer RP=(PHASE+P*118/32)%118;
localparam integer RELOAD=118+RP+((RP+118+P)%2);
$display("STRAP ctl_NE_p25 %0d %0d", P, RELOAD);
end
begin : ctl_NE_p26
localparam integer P=26,PHASE=0;
localparam integer RP=(PHASE+P*118/32)%118;
localparam integer RELOAD=118+RP+((RP+118+P)%2);
$display("STRAP ctl_NE_p26 %0d %0d", P, RELOAD);
end
begin : ctl_NE_p27
localparam integer P=27,PHASE=0;
localparam integer RP=(PHASE+P*118/32)%118;
localparam integer RELOAD=118+RP+((RP+118+P)%2);
$display("STRAP ctl_NE_p27 %0d %0d", P, RELOAD);
end
begin : ctl_NE_p28
localparam integer P=28,PHASE=0;
localparam integer RP=(PHASE+P*118/32)%118;
localparam integer RELOAD=118+RP+((RP+118+P)%2);
$display("STRAP ctl_NE_p28 %0d %0d", P, RELOAD);
end
begin : ctl_NE_p29
localparam integer P=29,PHASE=0;
localparam integer RP=(PHASE+P*118/32)%118;
localparam integer RELOAD=118+RP+((RP+118+P)%2);
$display("STRAP ctl_NE_p29 %0d %0d", P, RELOAD);
end
begin : ctl_NE_p30
localparam integer P=30,PHASE=0;
localparam integer RP=(PHASE+P*118/32)%118;
localparam integer RELOAD=118+RP+((RP+118+P)%2);
$display("STRAP ctl_NE_p30 %0d %0d", P, RELOAD);
end
begin : ctl_NE_p31
localparam integer P=31,PHASE=0;
localparam integer RP=(PHASE+P*118/32)%118;
localparam integer RELOAD=118+RP+((RP+118+P)%2);
$display("STRAP ctl_NE_p31 %0d %0d", P, RELOAD);
end
begin : ctl_NW_p00
localparam integer P=0,PHASE=0;
localparam integer RP=(PHASE+P*118/32)%118;
localparam integer RELOAD=118+RP+((RP+118+P)%2);
$display("STRAP ctl_NW_p00 %0d %0d", P, RELOAD);
end
begin : ctl_NW_p01
localparam integer P=1,PHASE=0;
localparam integer RP=(PHASE+P*118/32)%118;
localparam integer RELOAD=118+RP+((RP+118+P)%2);
$display("STRAP ctl_NW_p01 %0d %0d", P, RELOAD);
end
begin : ctl_NW_p02
localparam integer P=2,PHASE=0;
localparam integer RP=(PHASE+P*118/32)%118;
localparam integer RELOAD=118+RP+((RP+118+P)%2);
$display("STRAP ctl_NW_p02 %0d %0d", P, RELOAD);
end
begin : ctl_NW_p03
localparam integer P=3,PHASE=0;
localparam integer RP=(PHASE+P*118/32)%118;
localparam integer RELOAD=118+RP+((RP+118+P)%2);
$display("STRAP ctl_NW_p03 %0d %0d", P, RELOAD);
end
begin : ctl_NW_p04
localparam integer P=4,PHASE=0;
localparam integer RP=(PHASE+P*118/32)%118;
localparam integer RELOAD=118+RP+((RP+118+P)%2);
$display("STRAP ctl_NW_p04 %0d %0d", P, RELOAD);
end
begin : ctl_NW_p05
localparam integer P=5,PHASE=0;
localparam integer RP=(PHASE+P*118/32)%118;
localparam integer RELOAD=118+RP+((RP+118+P)%2);
$display("STRAP ctl_NW_p05 %0d %0d", P, RELOAD);
end
begin : ctl_NW_p06
localparam integer P=6,PHASE=0;
localparam integer RP=(PHASE+P*118/32)%118;
localparam integer RELOAD=118+RP+((RP+118+P)%2);
$display("STRAP ctl_NW_p06 %0d %0d", P, RELOAD);
end
begin : ctl_NW_p07
localparam integer P=7,PHASE=0;
localparam integer RP=(PHASE+P*118/32)%118;
localparam integer RELOAD=118+RP+((RP+118+P)%2);
$display("STRAP ctl_NW_p07 %0d %0d", P, RELOAD);
end
begin : ctl_NW_p08
localparam integer P=8,PHASE=0;
localparam integer RP=(PHASE+P*118/32)%118;
localparam integer RELOAD=118+RP+((RP+118+P)%2);
$display("STRAP ctl_NW_p08 %0d %0d", P, RELOAD);
end
begin : ctl_NW_p09
localparam integer P=9,PHASE=0;
localparam integer RP=(PHASE+P*118/32)%118;
localparam integer RELOAD=118+RP+((RP+118+P)%2);
$display("STRAP ctl_NW_p09 %0d %0d", P, RELOAD);
end
begin : ctl_NW_p10
localparam integer P=10,PHASE=0;
localparam integer RP=(PHASE+P*118/32)%118;
localparam integer RELOAD=118+RP+((RP+118+P)%2);
$display("STRAP ctl_NW_p10 %0d %0d", P, RELOAD);
end
begin : ctl_NW_p11
localparam integer P=11,PHASE=0;
localparam integer RP=(PHASE+P*118/32)%118;
localparam integer RELOAD=118+RP+((RP+118+P)%2);
$display("STRAP ctl_NW_p11 %0d %0d", P, RELOAD);
end
begin : ctl_NW_p12
localparam integer P=12,PHASE=0;
localparam integer RP=(PHASE+P*118/32)%118;
localparam integer RELOAD=118+RP+((RP+118+P)%2);
$display("STRAP ctl_NW_p12 %0d %0d", P, RELOAD);
end
begin : ctl_NW_p13
localparam integer P=13,PHASE=0;
localparam integer RP=(PHASE+P*118/32)%118;
localparam integer RELOAD=118+RP+((RP+118+P)%2);
$display("STRAP ctl_NW_p13 %0d %0d", P, RELOAD);
end
begin : ctl_NW_p14
localparam integer P=14,PHASE=0;
localparam integer RP=(PHASE+P*118/32)%118;
localparam integer RELOAD=118+RP+((RP+118+P)%2);
$display("STRAP ctl_NW_p14 %0d %0d", P, RELOAD);
end
begin : ctl_NW_p15
localparam integer P=15,PHASE=0;
localparam integer RP=(PHASE+P*118/32)%118;
localparam integer RELOAD=118+RP+((RP+118+P)%2);
$display("STRAP ctl_NW_p15 %0d %0d", P, RELOAD);
end
begin : ctl_NW_p16
localparam integer P=16,PHASE=0;
localparam integer RP=(PHASE+P*118/32)%118;
localparam integer RELOAD=118+RP+((RP+118+P)%2);
$display("STRAP ctl_NW_p16 %0d %0d", P, RELOAD);
end
begin : ctl_NW_p17
localparam integer P=17,PHASE=0;
localparam integer RP=(PHASE+P*118/32)%118;
localparam integer RELOAD=118+RP+((RP+118+P)%2);
$display("STRAP ctl_NW_p17 %0d %0d", P, RELOAD);
end
begin : ctl_NW_p18
localparam integer P=18,PHASE=0;
localparam integer RP=(PHASE+P*118/32)%118;
localparam integer RELOAD=118+RP+((RP+118+P)%2);
$display("STRAP ctl_NW_p18 %0d %0d", P, RELOAD);
end
begin : ctl_NW_p19
localparam integer P=19,PHASE=0;
localparam integer RP=(PHASE+P*118/32)%118;
localparam integer RELOAD=118+RP+((RP+118+P)%2);
$display("STRAP ctl_NW_p19 %0d %0d", P, RELOAD);
end
begin : ctl_NW_p20
localparam integer P=20,PHASE=0;
localparam integer RP=(PHASE+P*118/32)%118;
localparam integer RELOAD=118+RP+((RP+118+P)%2);
$display("STRAP ctl_NW_p20 %0d %0d", P, RELOAD);
end
begin : ctl_NW_p21
localparam integer P=21,PHASE=0;
localparam integer RP=(PHASE+P*118/32)%118;
localparam integer RELOAD=118+RP+((RP+118+P)%2);
$display("STRAP ctl_NW_p21 %0d %0d", P, RELOAD);
end
begin : ctl_NW_p22
localparam integer P=22,PHASE=0;
localparam integer RP=(PHASE+P*118/32)%118;
localparam integer RELOAD=118+RP+((RP+118+P)%2);
$display("STRAP ctl_NW_p22 %0d %0d", P, RELOAD);
end
begin : ctl_NW_p23
localparam integer P=23,PHASE=0;
localparam integer RP=(PHASE+P*118/32)%118;
localparam integer RELOAD=118+RP+((RP+118+P)%2);
$display("STRAP ctl_NW_p23 %0d %0d", P, RELOAD);
end
begin : ctl_NW_p24
localparam integer P=24,PHASE=0;
localparam integer RP=(PHASE+P*118/32)%118;
localparam integer RELOAD=118+RP+((RP+118+P)%2);
$display("STRAP ctl_NW_p24 %0d %0d", P, RELOAD);
end
begin : ctl_NW_p25
localparam integer P=25,PHASE=0;
localparam integer RP=(PHASE+P*118/32)%118;
localparam integer RELOAD=118+RP+((RP+118+P)%2);
$display("STRAP ctl_NW_p25 %0d %0d", P, RELOAD);
end
begin : ctl_NW_p26
localparam integer P=26,PHASE=0;
localparam integer RP=(PHASE+P*118/32)%118;
localparam integer RELOAD=118+RP+((RP+118+P)%2);
$display("STRAP ctl_NW_p26 %0d %0d", P, RELOAD);
end
begin : ctl_NW_p27
localparam integer P=27,PHASE=0;
localparam integer RP=(PHASE+P*118/32)%118;
localparam integer RELOAD=118+RP+((RP+118+P)%2);
$display("STRAP ctl_NW_p27 %0d %0d", P, RELOAD);
end
begin : ctl_NW_p28
localparam integer P=28,PHASE=0;
localparam integer RP=(PHASE+P*118/32)%118;
localparam integer RELOAD=118+RP+((RP+118+P)%2);
$display("STRAP ctl_NW_p28 %0d %0d", P, RELOAD);
end
begin : ctl_NW_p29
localparam integer P=29,PHASE=0;
localparam integer RP=(PHASE+P*118/32)%118;
localparam integer RELOAD=118+RP+((RP+118+P)%2);
$display("STRAP ctl_NW_p29 %0d %0d", P, RELOAD);
end
begin : ctl_NW_p30
localparam integer P=30,PHASE=0;
localparam integer RP=(PHASE+P*118/32)%118;
localparam integer RELOAD=118+RP+((RP+118+P)%2);
$display("STRAP ctl_NW_p30 %0d %0d", P, RELOAD);
end
begin : ctl_NW_p31
localparam integer P=31,PHASE=0;
localparam integer RP=(PHASE+P*118/32)%118;
localparam integer RELOAD=118+RP+((RP+118+P)%2);
$display("STRAP ctl_NW_p31 %0d %0d", P, RELOAD);
end
begin : ctl_SE_p00
localparam integer P=0,PHASE=0;
localparam integer RP=(PHASE+P*118/32)%118;
localparam integer RELOAD=118+RP+((RP+118+P)%2);
$display("STRAP ctl_SE_p00 %0d %0d", P, RELOAD);
end
begin : ctl_SE_p01
localparam integer P=1,PHASE=0;
localparam integer RP=(PHASE+P*118/32)%118;
localparam integer RELOAD=118+RP+((RP+118+P)%2);
$display("STRAP ctl_SE_p01 %0d %0d", P, RELOAD);
end
begin : ctl_SE_p02
localparam integer P=2,PHASE=0;
localparam integer RP=(PHASE+P*118/32)%118;
localparam integer RELOAD=118+RP+((RP+118+P)%2);
$display("STRAP ctl_SE_p02 %0d %0d", P, RELOAD);
end
begin : ctl_SE_p03
localparam integer P=3,PHASE=0;
localparam integer RP=(PHASE+P*118/32)%118;
localparam integer RELOAD=118+RP+((RP+118+P)%2);
$display("STRAP ctl_SE_p03 %0d %0d", P, RELOAD);
end
begin : ctl_SE_p04
localparam integer P=4,PHASE=0;
localparam integer RP=(PHASE+P*118/32)%118;
localparam integer RELOAD=118+RP+((RP+118+P)%2);
$display("STRAP ctl_SE_p04 %0d %0d", P, RELOAD);
end
begin : ctl_SE_p05
localparam integer P=5,PHASE=0;
localparam integer RP=(PHASE+P*118/32)%118;
localparam integer RELOAD=118+RP+((RP+118+P)%2);
$display("STRAP ctl_SE_p05 %0d %0d", P, RELOAD);
end
begin : ctl_SE_p06
localparam integer P=6,PHASE=0;
localparam integer RP=(PHASE+P*118/32)%118;
localparam integer RELOAD=118+RP+((RP+118+P)%2);
$display("STRAP ctl_SE_p06 %0d %0d", P, RELOAD);
end
begin : ctl_SE_p07
localparam integer P=7,PHASE=0;
localparam integer RP=(PHASE+P*118/32)%118;
localparam integer RELOAD=118+RP+((RP+118+P)%2);
$display("STRAP ctl_SE_p07 %0d %0d", P, RELOAD);
end
begin : ctl_SE_p08
localparam integer P=8,PHASE=0;
localparam integer RP=(PHASE+P*118/32)%118;
localparam integer RELOAD=118+RP+((RP+118+P)%2);
$display("STRAP ctl_SE_p08 %0d %0d", P, RELOAD);
end
begin : ctl_SE_p09
localparam integer P=9,PHASE=0;
localparam integer RP=(PHASE+P*118/32)%118;
localparam integer RELOAD=118+RP+((RP+118+P)%2);
$display("STRAP ctl_SE_p09 %0d %0d", P, RELOAD);
end
begin : ctl_SE_p10
localparam integer P=10,PHASE=0;
localparam integer RP=(PHASE+P*118/32)%118;
localparam integer RELOAD=118+RP+((RP+118+P)%2);
$display("STRAP ctl_SE_p10 %0d %0d", P, RELOAD);
end
begin : ctl_SE_p11
localparam integer P=11,PHASE=0;
localparam integer RP=(PHASE+P*118/32)%118;
localparam integer RELOAD=118+RP+((RP+118+P)%2);
$display("STRAP ctl_SE_p11 %0d %0d", P, RELOAD);
end
begin : ctl_SE_p12
localparam integer P=12,PHASE=0;
localparam integer RP=(PHASE+P*118/32)%118;
localparam integer RELOAD=118+RP+((RP+118+P)%2);
$display("STRAP ctl_SE_p12 %0d %0d", P, RELOAD);
end
begin : ctl_SE_p13
localparam integer P=13,PHASE=0;
localparam integer RP=(PHASE+P*118/32)%118;
localparam integer RELOAD=118+RP+((RP+118+P)%2);
$display("STRAP ctl_SE_p13 %0d %0d", P, RELOAD);
end
begin : ctl_SE_p14
localparam integer P=14,PHASE=0;
localparam integer RP=(PHASE+P*118/32)%118;
localparam integer RELOAD=118+RP+((RP+118+P)%2);
$display("STRAP ctl_SE_p14 %0d %0d", P, RELOAD);
end
begin : ctl_SE_p15
localparam integer P=15,PHASE=0;
localparam integer RP=(PHASE+P*118/32)%118;
localparam integer RELOAD=118+RP+((RP+118+P)%2);
$display("STRAP ctl_SE_p15 %0d %0d", P, RELOAD);
end
begin : ctl_SE_p16
localparam integer P=16,PHASE=0;
localparam integer RP=(PHASE+P*118/32)%118;
localparam integer RELOAD=118+RP+((RP+118+P)%2);
$display("STRAP ctl_SE_p16 %0d %0d", P, RELOAD);
end
begin : ctl_SE_p17
localparam integer P=17,PHASE=0;
localparam integer RP=(PHASE+P*118/32)%118;
localparam integer RELOAD=118+RP+((RP+118+P)%2);
$display("STRAP ctl_SE_p17 %0d %0d", P, RELOAD);
end
begin : ctl_SE_p18
localparam integer P=18,PHASE=0;
localparam integer RP=(PHASE+P*118/32)%118;
localparam integer RELOAD=118+RP+((RP+118+P)%2);
$display("STRAP ctl_SE_p18 %0d %0d", P, RELOAD);
end
begin : ctl_SE_p19
localparam integer P=19,PHASE=0;
localparam integer RP=(PHASE+P*118/32)%118;
localparam integer RELOAD=118+RP+((RP+118+P)%2);
$display("STRAP ctl_SE_p19 %0d %0d", P, RELOAD);
end
begin : ctl_SE_p20
localparam integer P=20,PHASE=0;
localparam integer RP=(PHASE+P*118/32)%118;
localparam integer RELOAD=118+RP+((RP+118+P)%2);
$display("STRAP ctl_SE_p20 %0d %0d", P, RELOAD);
end
begin : ctl_SE_p21
localparam integer P=21,PHASE=0;
localparam integer RP=(PHASE+P*118/32)%118;
localparam integer RELOAD=118+RP+((RP+118+P)%2);
$display("STRAP ctl_SE_p21 %0d %0d", P, RELOAD);
end
begin : ctl_SE_p22
localparam integer P=22,PHASE=0;
localparam integer RP=(PHASE+P*118/32)%118;
localparam integer RELOAD=118+RP+((RP+118+P)%2);
$display("STRAP ctl_SE_p22 %0d %0d", P, RELOAD);
end
begin : ctl_SE_p23
localparam integer P=23,PHASE=0;
localparam integer RP=(PHASE+P*118/32)%118;
localparam integer RELOAD=118+RP+((RP+118+P)%2);
$display("STRAP ctl_SE_p23 %0d %0d", P, RELOAD);
end
begin : ctl_SE_p24
localparam integer P=24,PHASE=0;
localparam integer RP=(PHASE+P*118/32)%118;
localparam integer RELOAD=118+RP+((RP+118+P)%2);
$display("STRAP ctl_SE_p24 %0d %0d", P, RELOAD);
end
begin : ctl_SE_p25
localparam integer P=25,PHASE=0;
localparam integer RP=(PHASE+P*118/32)%118;
localparam integer RELOAD=118+RP+((RP+118+P)%2);
$display("STRAP ctl_SE_p25 %0d %0d", P, RELOAD);
end
begin : ctl_SE_p26
localparam integer P=26,PHASE=0;
localparam integer RP=(PHASE+P*118/32)%118;
localparam integer RELOAD=118+RP+((RP+118+P)%2);
$display("STRAP ctl_SE_p26 %0d %0d", P, RELOAD);
end
begin : ctl_SE_p27
localparam integer P=27,PHASE=0;
localparam integer RP=(PHASE+P*118/32)%118;
localparam integer RELOAD=118+RP+((RP+118+P)%2);
$display("STRAP ctl_SE_p27 %0d %0d", P, RELOAD);
end
begin : ctl_SE_p28
localparam integer P=28,PHASE=0;
localparam integer RP=(PHASE+P*118/32)%118;
localparam integer RELOAD=118+RP+((RP+118+P)%2);
$display("STRAP ctl_SE_p28 %0d %0d", P, RELOAD);
end
begin : ctl_SE_p29
localparam integer P=29,PHASE=0;
localparam integer RP=(PHASE+P*118/32)%118;
localparam integer RELOAD=118+RP+((RP+118+P)%2);
$display("STRAP ctl_SE_p29 %0d %0d", P, RELOAD);
end
begin : ctl_SE_p30
localparam integer P=30,PHASE=0;
localparam integer RP=(PHASE+P*118/32)%118;
localparam integer RELOAD=118+RP+((RP+118+P)%2);
$display("STRAP ctl_SE_p30 %0d %0d", P, RELOAD);
end
begin : ctl_SE_p31
localparam integer P=31,PHASE=0;
localparam integer RP=(PHASE+P*118/32)%118;
localparam integer RELOAD=118+RP+((RP+118+P)%2);
$display("STRAP ctl_SE_p31 %0d %0d", P, RELOAD);
end
begin : ctl_SW_p00
localparam integer P=0,PHASE=0;
localparam integer RP=(PHASE+P*118/32)%118;
localparam integer RELOAD=118+RP+((RP+118+P)%2);
$display("STRAP ctl_SW_p00 %0d %0d", P, RELOAD);
end
begin : ctl_SW_p01
localparam integer P=1,PHASE=0;
localparam integer RP=(PHASE+P*118/32)%118;
localparam integer RELOAD=118+RP+((RP+118+P)%2);
$display("STRAP ctl_SW_p01 %0d %0d", P, RELOAD);
end
begin : ctl_SW_p02
localparam integer P=2,PHASE=0;
localparam integer RP=(PHASE+P*118/32)%118;
localparam integer RELOAD=118+RP+((RP+118+P)%2);
$display("STRAP ctl_SW_p02 %0d %0d", P, RELOAD);
end
begin : ctl_SW_p03
localparam integer P=3,PHASE=0;
localparam integer RP=(PHASE+P*118/32)%118;
localparam integer RELOAD=118+RP+((RP+118+P)%2);
$display("STRAP ctl_SW_p03 %0d %0d", P, RELOAD);
end
begin : ctl_SW_p04
localparam integer P=4,PHASE=0;
localparam integer RP=(PHASE+P*118/32)%118;
localparam integer RELOAD=118+RP+((RP+118+P)%2);
$display("STRAP ctl_SW_p04 %0d %0d", P, RELOAD);
end
begin : ctl_SW_p05
localparam integer P=5,PHASE=0;
localparam integer RP=(PHASE+P*118/32)%118;
localparam integer RELOAD=118+RP+((RP+118+P)%2);
$display("STRAP ctl_SW_p05 %0d %0d", P, RELOAD);
end
begin : ctl_SW_p06
localparam integer P=6,PHASE=0;
localparam integer RP=(PHASE+P*118/32)%118;
localparam integer RELOAD=118+RP+((RP+118+P)%2);
$display("STRAP ctl_SW_p06 %0d %0d", P, RELOAD);
end
begin : ctl_SW_p07
localparam integer P=7,PHASE=0;
localparam integer RP=(PHASE+P*118/32)%118;
localparam integer RELOAD=118+RP+((RP+118+P)%2);
$display("STRAP ctl_SW_p07 %0d %0d", P, RELOAD);
end
begin : ctl_SW_p08
localparam integer P=8,PHASE=0;
localparam integer RP=(PHASE+P*118/32)%118;
localparam integer RELOAD=118+RP+((RP+118+P)%2);
$display("STRAP ctl_SW_p08 %0d %0d", P, RELOAD);
end
begin : ctl_SW_p09
localparam integer P=9,PHASE=0;
localparam integer RP=(PHASE+P*118/32)%118;
localparam integer RELOAD=118+RP+((RP+118+P)%2);
$display("STRAP ctl_SW_p09 %0d %0d", P, RELOAD);
end
begin : ctl_SW_p10
localparam integer P=10,PHASE=0;
localparam integer RP=(PHASE+P*118/32)%118;
localparam integer RELOAD=118+RP+((RP+118+P)%2);
$display("STRAP ctl_SW_p10 %0d %0d", P, RELOAD);
end
begin : ctl_SW_p11
localparam integer P=11,PHASE=0;
localparam integer RP=(PHASE+P*118/32)%118;
localparam integer RELOAD=118+RP+((RP+118+P)%2);
$display("STRAP ctl_SW_p11 %0d %0d", P, RELOAD);
end
begin : ctl_SW_p12
localparam integer P=12,PHASE=0;
localparam integer RP=(PHASE+P*118/32)%118;
localparam integer RELOAD=118+RP+((RP+118+P)%2);
$display("STRAP ctl_SW_p12 %0d %0d", P, RELOAD);
end
begin : ctl_SW_p13
localparam integer P=13,PHASE=0;
localparam integer RP=(PHASE+P*118/32)%118;
localparam integer RELOAD=118+RP+((RP+118+P)%2);
$display("STRAP ctl_SW_p13 %0d %0d", P, RELOAD);
end
begin : ctl_SW_p14
localparam integer P=14,PHASE=0;
localparam integer RP=(PHASE+P*118/32)%118;
localparam integer RELOAD=118+RP+((RP+118+P)%2);
$display("STRAP ctl_SW_p14 %0d %0d", P, RELOAD);
end
begin : ctl_SW_p15
localparam integer P=15,PHASE=0;
localparam integer RP=(PHASE+P*118/32)%118;
localparam integer RELOAD=118+RP+((RP+118+P)%2);
$display("STRAP ctl_SW_p15 %0d %0d", P, RELOAD);
end
begin : ctl_SW_p16
localparam integer P=16,PHASE=0;
localparam integer RP=(PHASE+P*118/32)%118;
localparam integer RELOAD=118+RP+((RP+118+P)%2);
$display("STRAP ctl_SW_p16 %0d %0d", P, RELOAD);
end
begin : ctl_SW_p17
localparam integer P=17,PHASE=0;
localparam integer RP=(PHASE+P*118/32)%118;
localparam integer RELOAD=118+RP+((RP+118+P)%2);
$display("STRAP ctl_SW_p17 %0d %0d", P, RELOAD);
end
begin : ctl_SW_p18
localparam integer P=18,PHASE=0;
localparam integer RP=(PHASE+P*118/32)%118;
localparam integer RELOAD=118+RP+((RP+118+P)%2);
$display("STRAP ctl_SW_p18 %0d %0d", P, RELOAD);
end
begin : ctl_SW_p19
localparam integer P=19,PHASE=0;
localparam integer RP=(PHASE+P*118/32)%118;
localparam integer RELOAD=118+RP+((RP+118+P)%2);
$display("STRAP ctl_SW_p19 %0d %0d", P, RELOAD);
end
begin : ctl_SW_p20
localparam integer P=20,PHASE=0;
localparam integer RP=(PHASE+P*118/32)%118;
localparam integer RELOAD=118+RP+((RP+118+P)%2);
$display("STRAP ctl_SW_p20 %0d %0d", P, RELOAD);
end
begin : ctl_SW_p21
localparam integer P=21,PHASE=0;
localparam integer RP=(PHASE+P*118/32)%118;
localparam integer RELOAD=118+RP+((RP+118+P)%2);
$display("STRAP ctl_SW_p21 %0d %0d", P, RELOAD);
end
begin : ctl_SW_p22
localparam integer P=22,PHASE=0;
localparam integer RP=(PHASE+P*118/32)%118;
localparam integer RELOAD=118+RP+((RP+118+P)%2);
$display("STRAP ctl_SW_p22 %0d %0d", P, RELOAD);
end
begin : ctl_SW_p23
localparam integer P=23,PHASE=0;
localparam integer RP=(PHASE+P*118/32)%118;
localparam integer RELOAD=118+RP+((RP+118+P)%2);
$display("STRAP ctl_SW_p23 %0d %0d", P, RELOAD);
end
begin : ctl_SW_p24
localparam integer P=24,PHASE=0;
localparam integer RP=(PHASE+P*118/32)%118;
localparam integer RELOAD=118+RP+((RP+118+P)%2);
$display("STRAP ctl_SW_p24 %0d %0d", P, RELOAD);
end
begin : ctl_SW_p25
localparam integer P=25,PHASE=0;
localparam integer RP=(PHASE+P*118/32)%118;
localparam integer RELOAD=118+RP+((RP+118+P)%2);
$display("STRAP ctl_SW_p25 %0d %0d", P, RELOAD);
end
begin : ctl_SW_p26
localparam integer P=26,PHASE=0;
localparam integer RP=(PHASE+P*118/32)%118;
localparam integer RELOAD=118+RP+((RP+118+P)%2);
$display("STRAP ctl_SW_p26 %0d %0d", P, RELOAD);
end
begin : ctl_SW_p27
localparam integer P=27,PHASE=0;
localparam integer RP=(PHASE+P*118/32)%118;
localparam integer RELOAD=118+RP+((RP+118+P)%2);
$display("STRAP ctl_SW_p27 %0d %0d", P, RELOAD);
end
begin : ctl_SW_p28
localparam integer P=28,PHASE=0;
localparam integer RP=(PHASE+P*118/32)%118;
localparam integer RELOAD=118+RP+((RP+118+P)%2);
$display("STRAP ctl_SW_p28 %0d %0d", P, RELOAD);
end
begin : ctl_SW_p29
localparam integer P=29,PHASE=0;
localparam integer RP=(PHASE+P*118/32)%118;
localparam integer RELOAD=118+RP+((RP+118+P)%2);
$display("STRAP ctl_SW_p29 %0d %0d", P, RELOAD);
end
begin : ctl_SW_p30
localparam integer P=30,PHASE=0;
localparam integer RP=(PHASE+P*118/32)%118;
localparam integer RELOAD=118+RP+((RP+118+P)%2);
$display("STRAP ctl_SW_p30 %0d %0d", P, RELOAD);
end
begin : ctl_SW_p31
localparam integer P=31,PHASE=0;
localparam integer RP=(PHASE+P*118/32)%118;
localparam integer RELOAD=118+RP+((RP+118+P)%2);
$display("STRAP ctl_SW_p31 %0d %0d", P, RELOAD);
end
$finish;
end
endmodule
