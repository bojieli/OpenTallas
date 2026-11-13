GUNIT gf4 programme correction

The compare-register form shifts IDs by two clocks. The weight-feedback path traverses the bf core again, so weights shift by four clocks. The inherited claim that RW_GAP stays 101 fails the full GU bench (five errors at the weight rows). lower_gu now derives RT_LAT and RW_GAP from the selected recipe define set; gf2 remains 62/60 and101, gf3 becomes63/61 and102, gf4 becomes64/62 and103.

The actual GU minimum integration vehicle passes three jobs,1655 incomingHP/SC beats,15CTL rows per side,50roots and2rsqrt operations with no fault. Late and wrong programme controls fail35 and34 checks. The original failed gf3/gf4 logs remain outside this committed result directory. Physical gf4 signoff is still in progress; no view adoption is made by this change.
