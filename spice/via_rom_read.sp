* Generic via-programmed NOR ROM read path -- topology validation only.
* This netlist is intentionally not tied to a foundry PDK. The selected cell
* differs from the unprogrammed cell only in whether the drain is connected to
* the precharged bitline, matching late via-layer personalization.

.title OpenTallas via-programmed ROM topology
.param VDDVAL=1.20
.param LCH=0.13u
.param WREAD=1.00u
.param WPRE=2.00u
.param CBL=80f

VDD vdd 0 {VDDVAL}
* PRE_N low from 0-2 ns charges bitlines, then high isolates them.
VPRE pre_n 0 PULSE(0 {VDDVAL} 2n 40p 40p 8n 20n)
* Selected wordline rises after precharge. Masked wordline remains low.
VWL wordline 0 PULSE(0 {VDDVAL} 2.10n 40p 40p 7.9n 20n)
VWL_MASKED wordline_masked 0 0

.model NREAD NMOS LEVEL=1 VTO=0.38 KP=220u LAMBDA=0.05 GAMMA=0.30 PHI=0.70
.model PPRE  PMOS LEVEL=1 VTO=-0.40 KP=90u LAMBDA=0.05 GAMMA=0.35 PHI=0.70

* Three identical precharge devices and representative bitline capacitances.
MPRE_PRESENT bl_present pre_n vdd vdd PPRE W={WPRE} L={LCH}
MPRE_ABSENT  bl_absent  pre_n vdd vdd PPRE W={WPRE} L={LCH}
MPRE_MASKED  bl_masked  pre_n vdd vdd PPRE W={WPRE} L={LCH}
CBL_PRESENT bl_present 0 {CBL}
CBL_ABSENT  bl_absent  0 {CBL}
CBL_MASKED  bl_masked  0 {CBL}

* Programmed bit: drain via is present and the selected wordline discharges BL.
MCELL_PRESENT bl_present wordline 0 0 NREAD W={WREAD} L={LCH}

* Unprogrammed bit: transistor/diffusion is shared, but the drain via to BL is
* absent. The floating diffusion is retained to model its parasitic load.
MCELL_ABSENT floating_drain wordline 0 0 NREAD W={WREAD} L={LCH}
CFLOAT floating_drain 0 2f

* Programmed but unselected expert: the wordline mask suppresses discharge.
MCELL_MASKED bl_masked wordline_masked 0 0 NREAD W={WREAD} L={LCH}

* Minimal static sense inverters. They demonstrate polarity and resolved levels;
* a real design requires offset/noise Monte Carlo and a clocked sense amplifier.
MSP_PRESENT sense_present bl_present vdd vdd PPRE W=1u L={LCH}
MSN_PRESENT sense_present bl_present 0 0 NREAD W=0.5u L={LCH}
MSP_ABSENT sense_absent bl_absent vdd vdd PPRE W=1u L={LCH}
MSN_ABSENT sense_absent bl_absent 0 0 NREAD W=0.5u L={LCH}
MSP_MASKED sense_masked bl_masked vdd vdd PPRE W=1u L={LCH}
MSN_MASKED sense_masked bl_masked 0 0 NREAD W=0.5u L={LCH}

.tran 2p 8n
.measure tran v_present FIND v(bl_present) AT=4n
.measure tran v_absent FIND v(bl_absent) AT=4n
.measure tran v_masked FIND v(bl_masked) AT=4n
.measure tran sense_present_v FIND v(sense_present) AT=4n
.measure tran sense_absent_v FIND v(sense_absent) AT=4n
.measure tran read_margin PARAM='v_absent-v_present'
.measure tran discharge_delay TRIG v(wordline) VAL='VDDVAL/2' RISE=1 TARG v(bl_present) VAL='VDDVAL/2' FALL=1
.measure tran read_energy INTEG par('-v(vdd)*i(VDD)') FROM=0n TO=4n

.end
