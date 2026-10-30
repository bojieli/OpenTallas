Current native norm rescale, actual XF scalar only

Intel1 ot-run2643599-1793375151 PASS: one current VP/VN pair with real SRAM,
genuine3920 input writes,HLOAD/GAIN/NORMR,then actual16-XF rstd40ca3c85. All640
actualpacked128bit output vectors (5120BF16elements) match independent H/pre/
gain arithmetic exactly;0errors833ps. FirstY is17edges after publicVN RSTD
pins,in all80contexts; inputcapture is included. Every8-vector set is observed
within the101-edge local wait. No unmeasured exactlastY date is claimed.
Corrupting only actualrstd to408a3c85 causes640vector mismatches and terminalFAIL.

ExpectedY is a scoreboard only; it never connects to hardware. No goldenrstd
or norm-output image is stimulus. The actual scalar is itself exact against
independent FP32 tree math over actual80 valid-time partials. Inputimage and
actualscalar file hashes link the real source cuts. Nativeoutput is BF16packed
128bits,not the historical padded256bit FP32-container interface.

No global RSTD/GO,NXphysicaltransport,VQ K-profile,retirement/reset/START or full
stage/token qualification is inferred. This proves current component math and
its explicit local pin boundaries,not a booked native programme.
