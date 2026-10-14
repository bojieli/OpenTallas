# Transit6: functional PASS, physical UNQUALIFIED

Source: `642f3888818bfe3f4d3b1ed85fbb1698156b2df6`; unchanged archived input on EPYC4 at `/srv/opentallas-scratch/claude/el1013-engc-compose/transit6/src`.
Exact ot-run unit `oth-ubuntu-846009-1791963287`; CTS-stop `oth-ubuntu-846008-1791963287`; corner replay `oth-ubuntu-914233-1791963710`. All terminal exit 0, but CTS exit is not a timing verdict.

Five positive tests PASS with all dumps present and zero element mismatches; all five mutants caught. Separate earlydone negative emits `ENGRAM_C_NEG earlydone FAIL as required`. Isolated window-to-slot-ready mean509.7 cycles / immutable500 =1.0194x; back-to-back355.1 cycles/token. Coherent status16-bit and PB1-to-PB0 transit334-bit registers preserve functional output ordering.

Actual mapped relay counts16 and334. At TT setup150, SINK-to-status294.1ps / status-to-WIN264.0ps; PB1-to-transit217.3ps / transit-to-PB0164.4ps. At FF hold100 the corresponding margins143.5/53.8/75.7/50.2ps. All16 reset flop clocks share exactly the intended hard-child clock net. Normal TT setup stage/child minima401.8/56.5ps; FF hold stage/child minima60.0/59.5ps.

Remaining direct core-to-core setup failures at TT150: PB1-to-IO -140.1ps; WS-to-PB1 -40.8ps; WIN-to-SINK -22.1ps; IO-to-PB1 -4.4ps. Deeper setup210 rows are separately retained. External IO already includes skew in its input/output delay allowance, so applying150 uniformly additionally is conservative and not the final IO signoff budget.

CTS hold repair stalled on488 I2R endpoints at -388ps under the route-corner model. No route or qualification is claimed. Scalar virtual950/837 and hand-balanced spine offsets are diagnostic, not a source-bound phi-minus-R contract. Source reset launch/recovery/removal remains unbound: die owner confirms interim c7 cannot establish native producer/startup wait/pin binding. Parent includes16 reset and350 data flops and therefore requires actual related parent logic delivery proof. Do not use legacy spread/slew-only gate PASS as setup/hold qualification.

Exact original child ODB/SPEF corner measurements are being collected separately with unchanged source slew, all source-port data-delay tags removed and source latency normalized0 only inside the read-only Tcl session. Their binding to exported ETM context must be verified before adopting references. No exception, period relaxation or guessed phase tuning is authorized by these logs.
