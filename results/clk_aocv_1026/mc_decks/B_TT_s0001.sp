* CLK-AOCV MC chain B TT sample 1
.control
pre_osdi /w/osdi/bsimcmg23.osdi
set noaskquit
run
wrdata /w/run/B_TT/s0001.dat v(n1) v(o1) v(n2) v(o2) v(n3) v(o3) v(n4) v(o4) v(n5) v(o5) v(n6) v(o6) v(n7)
quit
.endc
.options klu
.save v(n1) v(o1) v(n2) v(o2) v(n3) v(o3) v(n4) v(o4) v(n5) v(o5) v(n6) v(o6) v(n7)
.temp 25
.include /w/lib/TT/models.sp
.include /w/lib/TT/cells.sp
.subckt MCBUF VSS VDD A Y d0=0 d1=0 d2=0 d3=0 d4=0 d5=0 d6=0 d7=0 d8=0 d9=0 d10=0 d11=0 d12=0 d13=0 d14=0 d15=0 d16=0 d17=0 d18=0 d19=0
*
* VSS VSS
* VDD VDD
* A A
* Y Y
*
*

N0 N_M0_d N_M0_g VSS VSS nmos_rvt L=2e-08 nfin=2 delvtrand={d0}
N1 N_M1_d N_M1_g VSS VSS nmos_rvt L=2e-08 nfin=2 delvtrand={d1}
N2 N_M2_d N_M2_g VSS VSS nmos_rvt L=2e-08 nfin=3 delvtrand={d2}
N3 N_M3_d N_M3_g VSS VSS nmos_rvt L=2e-08 nfin=3 delvtrand={d3}
N4 N_M4_d N_M4_g VSS VSS nmos_rvt L=2e-08 nfin=3 delvtrand={d4}
N5 N_M5_d N_M5_g VSS VSS nmos_rvt L=2e-08 nfin=3 delvtrand={d5}
N6 N_M6_d N_M6_g VSS VSS nmos_rvt L=2e-08 nfin=3 delvtrand={d6}
N7 N_M7_d N_M7_g VSS VSS nmos_rvt L=2e-08 nfin=3 delvtrand={d7}
N8 N_M8_d N_M8_g VSS VSS nmos_rvt L=2e-08 nfin=3 delvtrand={d8}
N9 N_M9_d N_M9_g VSS VSS nmos_rvt L=2e-08 nfin=3 delvtrand={d9}
N10 N_M10_d N_M10_g VDD VDD pmos_rvt L=2e-08 nfin=2 delvtrand={d10}
N11 N_M11_d N_M11_g VDD VDD pmos_rvt L=2e-08 nfin=2 delvtrand={d11}
N12 N_M12_d N_M12_g VDD VDD pmos_rvt L=2e-08 nfin=3 delvtrand={d12}
N13 N_M13_d N_M13_g VDD VDD pmos_rvt L=2e-08 nfin=3 delvtrand={d13}
N14 N_M14_d N_M14_g VDD VDD pmos_rvt L=2e-08 nfin=3 delvtrand={d14}
N15 N_M15_d N_M15_g VDD VDD pmos_rvt L=2e-08 nfin=3 delvtrand={d15}
N16 N_M16_d N_M16_g VDD VDD pmos_rvt L=2e-08 nfin=3 delvtrand={d16}
N17 N_M17_d N_M17_g VDD VDD pmos_rvt L=2e-08 nfin=3 delvtrand={d17}
N18 N_M18_d N_M18_g VDD VDD pmos_rvt L=2e-08 nfin=3 delvtrand={d18}
N19 N_M19_d N_M19_g VDD VDD pmos_rvt L=2e-08 nfin=3 delvtrand={d19}


* .include "BUFx8_ASAP7_75t_R.pex.sp.pxi"

* Start of included file BUFx8_ASAP7_75t_R.pex.sp.pxi
x_PM_BUFx8_ASAP7_75t_R%A vss A N_M0_g N_M10_g N_M1_g N_M11_g N_A_4 N_A_7 N_A_5
+ N_A_1 N_A_3 PM_BUFx8_ASAP7_75t_R%A
x_PM_BUFx8_ASAP7_75t_R%Y vss Y N_M2_d N_M3_d N_M4_d N_M5_d N_M6_d N_M7_d N_M8_d
+ N_M9_d N_M12_d N_M13_d N_M14_d N_M15_d N_M16_d N_M17_d N_M18_d N_M19_d N_Y_32
+ N_Y_5 N_Y_7 N_Y_8 N_Y_29 N_Y_25 N_Y_26 N_Y_27 N_Y_30 N_Y_31 N_Y_28 N_Y_37
+ N_Y_3 N_Y_4 N_Y_6 N_Y_1 N_Y_2 N_Y_35 N_Y_36 PM_BUFx8_ASAP7_75t_R%Y
cc_1 N_Y_32 N_4_21 0.000192005f
cc_2 N_Y_32 N_4_26 0.000179041f
cc_3 N_Y_32 N_4_27 0.000179041f
cc_4 N_Y_32 N_4_29 0.000398305f
cc_5 N_Y_32 N_4_30 0.000398305f
cc_6 N_Y_32 N_4_1 0.00243996f
cc_7 N_Y_5 N_4_1 0.000689687f
cc_8 N_Y_7 N_4_1 0.000689687f
cc_9 N_Y_8 N_4_1 0.000777752f
cc_10 N_Y_29 N_4_17 0.0189792f
cc_11 N_Y_25 N_4_17 0.055442f
cc_12 N_Y_26 N_4_18 0.0655935f
cc_13 N_Y_27 N_4_20 0.0655949f
cc_14 N_Y_32 N_4_22 0.0556147f
cc_15 N_Y_30 N_4_18 0.000830261f
cc_16 N_Y_31 N_4_20 0.000830261f
cc_17 N_Y_28 N_4_23 0.0110494f
cc_18 N_Y_37 N_4_31 0.00165487f
cc_19 N_Y_7 N_4_23 0.00186947f
cc_20 N_Y_8 N_4_23 0.00186947f
cc_21 N_Y_3 N_4_18 0.00193725f
cc_22 N_Y_4 N_4_19 0.00193725f
cc_23 N_Y_5 N_4_20 0.00193725f
cc_24 N_Y_6 N_4_21 0.00193725f
cc_25 N_Y_1 N_4_17 0.00208118f
cc_26 N_Y_2 N_4_17 0.00208118f
cc_27 N_Y_35 N_4_31 0.00312139f
cc_28 N_Y_36 N_4_31 0.00312139f
cc_29 N_Y_3 N_4_31 0.00833279f
cc_30 N_Y_29 N_4_16 0.0353264f
cc_31 N_Y_25 N_4_16 0.0100845f
cc_32 N_Y_27 N_4_1 0.0166249f
cc_33 N_Y_30 N_4_19 0.0647645f
cc_34 N_Y_31 N_4_21 0.0646887f
cc_35 N_Y_28 N_4_22 0.0182322f
cc_36 N_Y_32 N_4_23 0.047593f
x_PM_BUFx8_ASAP7_75t_R%4 vss N_M2_g N_M12_g N_M3_g N_M13_g N_M4_g N_M14_g
+ N_M5_g N_M15_g N_M6_g N_M16_g N_M7_g N_M17_g N_M8_g N_M18_g N_M9_g N_M19_g
+ N_M0_d N_M1_d N_M10_d N_M11_d N_4_31 N_4_1 N_4_27 N_4_26 N_4_28 N_4_25 N_4_24
+ N_4_10 N_4_11 N_4_29 N_4_30 N_4_16 N_4_21 N_4_17 N_4_18 N_4_20 N_4_22 N_4_23
+ N_4_19 PM_BUFx8_ASAP7_75t_R%4
cc_37 N_4_31 N_A_4 0.000337228f
cc_38 N_4_1 N_A_4 0.00045905f
cc_39 N_4_27 N_A_4 0.000507552f
cc_40 N_4_26 N_A_4 0.000559311f
cc_41 N_4_28 N_A_4 0.000611665f
cc_42 N_4_25 N_A_4 0.00851398f
cc_43 N_4_24 N_A_4 0.0218707f
cc_44 N_4_10 N_A_4 0.000951278f
cc_45 N_4_11 N_A_4 0.000951278f
cc_46 N_4_27 N_A_7 0.00107764f
cc_47 N_4_26 N_A_5 0.0010786f
cc_48 N_4_29 A 0.00111293f
cc_49 N_4_30 A 0.00111293f
cc_50 N_4_28 A 0.00224747f
cc_51 N_4_25 N_A_1 0.00249729f
cc_52 N_4_25 N_A_3 0.0135786f
cc_53 N_4_24 N_A_3 0.0187506f
cc_54 N_4_16 N_A_4 0.0318696f


* End of included file BUFx8_ASAP7_75t_R.pex.sp.pxi
.ends
Vdd vdd 0 0.7
Vss vss 0 0
Vin in 0 PWL(0 0 100p 0 140p 0.7)
Xp1 vss vdd in p1 BUFx8_ASAP7_75t_R
Xp2 vss vdd p1 n1 BUFx8_ASAP7_75t_R
X1 vss vdd n1 o1 MCBUF d0=2.755696e-02 d1=2.188705e-02 d2=-2.529539e-02 d3=-3.577244e-02 d4=-1.876037e-03 d5=1.405747e-02 d6=-2.704208e-03 d7=-2.690909e-02 d8=-9.155835e-03 d9=2.647683e-02 d10=-3.120712e-02 d11=2.368534e-02 d12=9.650748e-03 d13=8.881733e-03 d14=1.414702e-02 d15=-1.008103e-02 d16=-2.176530e-03 d17=3.325332e-02 d18=-7.112608e-03 d19=-7.734635e-03
Cw1_0a o1 0 0.8200f
Rw1_0 o1 w1_0 190.000
Cw1_0b w1_0 0 0.8200f
Cw1_1a w1_0 0 0.8200f
Rw1_1 w1_0 w1_1 190.000
Cw1_1b w1_1 0 0.8200f
Cw1_2a w1_1 0 0.8200f
Rw1_2 w1_1 w1_2 190.000
Cw1_2b w1_2 0 0.8200f
Cw1_3a w1_2 0 0.8200f
Rw1_3 w1_2 n2 190.000
Cw1_3b n2 0 0.8200f
Xs1_0 vss vdd n2 sib1_0 BUFx8_ASAP7_75t_R
Xs1_1 vss vdd n2 sib1_1 BUFx8_ASAP7_75t_R
Xs1_2 vss vdd n2 sib1_2 BUFx8_ASAP7_75t_R
X2 vss vdd n2 o2 MCBUF d0=-3.165341e-02 d1=-1.057865e-02 d2=1.364833e-02 d3=2.306095e-02 d4=1.197550e-02 d5=1.168211e-02 d6=1.081120e-02 d7=6.230501e-03 d8=1.858217e-02 d9=-2.585156e-03 d10=2.423972e-02 d11=-1.458893e-03 d12=-2.922580e-02 d13=-2.342369e-02 d14=-3.465905e-03 d15=-8.276609e-03 d16=-2.215964e-02 d17=-1.388472e-02 d18=3.447591e-03 d19=7.471985e-03
Cw2_0a o2 0 0.8200f
Rw2_0 o2 w2_0 190.000
Cw2_0b w2_0 0 0.8200f
Cw2_1a w2_0 0 0.8200f
Rw2_1 w2_0 w2_1 190.000
Cw2_1b w2_1 0 0.8200f
Cw2_2a w2_1 0 0.8200f
Rw2_2 w2_1 w2_2 190.000
Cw2_2b w2_2 0 0.8200f
Cw2_3a w2_2 0 0.8200f
Rw2_3 w2_2 n3 190.000
Cw2_3b n3 0 0.8200f
Xs2_0 vss vdd n3 sib2_0 BUFx8_ASAP7_75t_R
Xs2_1 vss vdd n3 sib2_1 BUFx8_ASAP7_75t_R
Xs2_2 vss vdd n3 sib2_2 BUFx8_ASAP7_75t_R
X3 vss vdd n3 o3 MCBUF d0=1.916419e-02 d1=-1.921388e-02 d2=7.000010e-03 d3=1.900698e-02 d4=6.554741e-03 d5=3.235528e-02 d6=-8.577496e-03 d7=-2.587592e-05 d8=3.317326e-03 d9=-7.270435e-03 d10=-1.031315e-03 d11=5.285582e-03 d12=-5.502601e-04 d13=-9.055934e-03 d14=-8.044960e-03 d15=-1.313843e-03 d16=-2.784739e-02 d17=3.440212e-03 d18=-1.984828e-02 d19=-4.417040e-03
Cw3_0a o3 0 0.8200f
Rw3_0 o3 w3_0 190.000
Cw3_0b w3_0 0 0.8200f
Cw3_1a w3_0 0 0.8200f
Rw3_1 w3_0 w3_1 190.000
Cw3_1b w3_1 0 0.8200f
Cw3_2a w3_1 0 0.8200f
Rw3_2 w3_1 w3_2 190.000
Cw3_2b w3_2 0 0.8200f
Cw3_3a w3_2 0 0.8200f
Rw3_3 w3_2 n4 190.000
Cw3_3b n4 0 0.8200f
Xs3_0 vss vdd n4 sib3_0 BUFx8_ASAP7_75t_R
Xs3_1 vss vdd n4 sib3_1 BUFx8_ASAP7_75t_R
Xs3_2 vss vdd n4 sib3_2 BUFx8_ASAP7_75t_R
X4 vss vdd n4 o4 MCBUF d0=-2.411409e-02 d1=2.299184e-03 d2=-6.799892e-03 d3=-4.649149e-03 d4=-1.337338e-02 d5=2.159658e-03 d6=2.895300e-02 d7=-3.265286e-02 d8=9.380261e-03 d9=4.160985e-03 d10=-8.478157e-03 d11=-2.816897e-02 d12=2.861829e-02 d13=3.452126e-03 d14=1.816449e-02 d15=-6.677605e-03 d16=-1.377103e-02 d17=1.959668e-02 d18=1.338913e-02 d19=-5.385397e-03
Cw4_0a o4 0 0.8200f
Rw4_0 o4 w4_0 190.000
Cw4_0b w4_0 0 0.8200f
Cw4_1a w4_0 0 0.8200f
Rw4_1 w4_0 w4_1 190.000
Cw4_1b w4_1 0 0.8200f
Cw4_2a w4_1 0 0.8200f
Rw4_2 w4_1 w4_2 190.000
Cw4_2b w4_2 0 0.8200f
Cw4_3a w4_2 0 0.8200f
Rw4_3 w4_2 n5 190.000
Cw4_3b n5 0 0.8200f
Xs4_0 vss vdd n5 sib4_0 BUFx8_ASAP7_75t_R
Xs4_1 vss vdd n5 sib4_1 BUFx8_ASAP7_75t_R
Xs4_2 vss vdd n5 sib4_2 BUFx8_ASAP7_75t_R
X5 vss vdd n5 o5 MCBUF d0=-4.715186e-03 d1=1.383282e-02 d2=-1.436641e-02 d3=-1.499703e-02 d4=-6.974695e-04 d5=1.826772e-02 d6=1.559079e-02 d7=3.462213e-03 d8=2.436404e-02 d9=-2.626958e-03 d10=-1.077593e-02 d11=5.189717e-02 d12=-8.834882e-03 d13=1.091825e-02 d14=1.012194e-02 d15=2.271855e-03 d16=4.199118e-03 d17=1.266290e-02 d18=1.009694e-02 d19=-1.035642e-02
Cw5_0a o5 0 0.8200f
Rw5_0 o5 w5_0 190.000
Cw5_0b w5_0 0 0.8200f
Cw5_1a w5_0 0 0.8200f
Rw5_1 w5_0 w5_1 190.000
Cw5_1b w5_1 0 0.8200f
Cw5_2a w5_1 0 0.8200f
Rw5_2 w5_1 w5_2 190.000
Cw5_2b w5_2 0 0.8200f
Cw5_3a w5_2 0 0.8200f
Rw5_3 w5_2 n6 190.000
Cw5_3b n6 0 0.8200f
Xs5_0 vss vdd n6 sib5_0 BUFx8_ASAP7_75t_R
Xs5_1 vss vdd n6 sib5_1 BUFx8_ASAP7_75t_R
Xs5_2 vss vdd n6 sib5_2 BUFx8_ASAP7_75t_R
X6 vss vdd n6 o6 MCBUF d0=2.704093e-04 d1=3.075366e-02 d2=1.328458e-02 d3=-7.617378e-03 d4=1.287447e-03 d5=-1.765092e-02 d6=-2.302709e-02 d7=-9.303930e-03 d8=2.902976e-02 d9=-1.100878e-02 d10=-4.330822e-02 d11=-2.219904e-03 d12=-1.213866e-02 d13=1.351491e-02 d14=2.245590e-02 d15=-5.769312e-03 d16=2.352771e-03 d17=-1.585898e-02 d18=2.189873e-02 d19=-1.289691e-02
Cw6_0a o6 0 0.8200f
Rw6_0 o6 w6_0 190.000
Cw6_0b w6_0 0 0.8200f
Cw6_1a w6_0 0 0.8200f
Rw6_1 w6_0 w6_1 190.000
Cw6_1b w6_1 0 0.8200f
Cw6_2a w6_1 0 0.8200f
Rw6_2 w6_1 w6_2 190.000
Cw6_2b w6_2 0 0.8200f
Cw6_3a w6_2 0 0.8200f
Rw6_3 w6_2 n7 190.000
Cw6_3b n7 0 0.8200f
Xs6_0 vss vdd n7 sib6_0 BUFx8_ASAP7_75t_R
Xs6_1 vss vdd n7 sib6_1 BUFx8_ASAP7_75t_R
Xs6_2 vss vdd n7 sib6_2 BUFx8_ASAP7_75t_R
Xend vss vdd n7 oend BUFx8_ASAP7_75t_R
.tran 1p 760p 0 1p
.end
