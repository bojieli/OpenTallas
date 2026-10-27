# S81 C18 core progress

Pipelined gunit_l1c (R17 sort8 CPS2, already approved/proved; +1 cycle priced in R17) now has a fresh named-sink tree: 4,887 sinks, family menu selected 2,2,2,8 standard wire, 146 cells / nine stages including the existing deterministic three-stage BUFx16f entry trunk. Native plan model TT241.42/window13.11, FF186.21/window16.72; calibrated prediction252.55/189.49 is UNCHECKED until build. Max leaf spread24.8um, no missing/duplicate sink, unequal stage, PG-clearance, reach or displacement failure. No manually tuned clock ECO.

The first uncalibrated menu pass found the six-stage structure but lacked the optional uf_phys module through sparse checkout. The successor adds that existing module and existing trunk calibration; its final checks PASS. The source code and family search rule are unchanged.

Image dsdv_gunit_l1c_r13.png VIEWED: long narrow outline; clock enters at centre, branches into four local driver groups next to the dense west pin strip and interior logic clusters. First-level legs27-38um, second35.6-45.9um, local leaves1.6-35.6um. Short uncrowded paths, no macro walls, every named sink assigned. PASS-COND for one GRT trial; actual placed congestion, clock access, setup and FF hold remain gates. Fresh dsdv_gunit_l1c_c18 static check-kit PASS.

Frozen-view FF202.5 collection: actual old qbank_N137.99TT/11.84FF SIGNED. Actual old rstg334.50/-28.63(68EP), payload536328.55/-26.17(540EP), VQ8.35/-4.64(32EP) NOT SIGNED. These retime results do not certify current plan interfaces. Thirteen old S81 ETM boundary views: ten pass FF202.5; hrow-10.28(485EP), VQ-3.83(14EP), NNfd-0.02(1EP) fail. ETM-only results never replace signoff.py or routed pair timing. The predecessor ETM runs failed because OpenROAD had no technology; corrected read-only runs use standalone STA with explicit FF input-driver liberty and ps conversion. Original logs/verdicts retained.

VQ physical floorplan.png and paths.png VIEWED: south SRAM has clear west/east access and no south signals; dense upper logic and border pin strip; failing path is a very short local west-input capture/removal path, not a long-wire or clock geometry failure. FF202.5 reduces the previous own-SDC launch reference; this exposes rst_n removal-4.64 and y19 capture-3.83ps. A data/reset hold-only repair is plausible, with unchanged clock/cycles and a fresh exact gate; current VQ master-slice rekit remains required for release.

xrt3 old missing lec.json root cause is a measured 24GiB cgroup OOM of Python at03:51:44 (PID2213377), not a design counterexample; old gold Yosys finished at10.06GB. A 64GB read-only-AIG diagnostic successor runs in codex-s81-core-1027/xrt3_lec; originals retained.

l0r c17 proof EQUIVALENT15691/15691; its long preplacement -41.8ps loop was stock ORFS setup repair, not hold. It progressed to global placement; no clock insertion result yet and no inherited job killed.
