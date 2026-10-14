# Actual row-hierarchy placed timing

The frozen row-hierarchy source is a5bc70a71, with the existing common-pin repair context and known first-CTS IO-boundary omission retained. This experiment is not native-qualified. Actual four-domain nominal phase-compensated diagnostics use placement-estimated RC, real 4_1_cts.odb and each corner's independently measured raw boundary R. They preserve833.333/1111.110667ps periods and60/25ps uncertainties. No crossing exception is added.

| Pair | SS setup ps | FF hold ps |
|---|---:|---:|
| core to core | 26.565805 | 10.972442 |
| serial to serial | 466.039551 | 9.188657 |
| core to serial | -8.175030 | 22.126551 |
| serial to core | 40.336483 | -4.474568 |

The retained row controllers/local reset drivers repair both former same-domain bottlenecks. The remaining forward setup path is wp_pub to wp_r through four hold buffers and a native-polarity inverter(12.17ps SS). The reverse hold path is r_st to the complemented r_st_w_n sample, a direct native QN-to-D wire with no combinational cell. Its internal serial launch clock arrives21.77ps before the serial boundary mean; the capture arrives5.23ps before the core mean. The source-bound gate's positive TT setup51.12/hold16.82 therefore cannot establish compensated closure. The separate boundary-order repair34948a0cf and any further native-polarity change require fresh physical evidence; no old receipt may be promoted.
