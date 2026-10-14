# Source-bound placed SS classification

Actual gate snapshot manifest c96481bf5f427ce5cdf1189b11331b01ad4297b6521c73c3c86bbc35fa49258f matches commit ef848b8be and current daemon overlays. RTL prototype is a8620c02e. Measurement uses actual 4_1_cts.odb and placement-estimated parasitics, not routed SPEF; hashes retained. Both clocks are nominal 833.333/1111.110667 ps, source phase minus each actual corner boundary mean, setup60/hold25 uncertainties. No new exceptions.

| Domain pair | SS setup ps | FF hold ps |
|---|---:|---:|
| core to core | -35.964565 | 10.461632 |
| serial to serial | 275.483185 | 10.991598 |
| core to serial | -10.581105 | 23.275299 |
| serial to core | 45.132854 | 0.063796 |

Actual232 bank_n flops retained. Serial read decode fanout is repaired in this placed experiment. Core worst path launches shared synthesized rs_n in row4 and reaches row7 hold-memory write mux through seven buffers and enable logic. Forward crossing now launches u_s.mem[0][22] and reaches u_s.sh[0][22] through four hold buffers and an inverter. Reverse FF margin0.064ps is positive but fragile and requires actual routed context. The prototype is NOT SS/native qualified and no physical successor has been submitted.
