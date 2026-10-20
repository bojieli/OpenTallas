# Integrated PC5 source checks

Production candidate e5d857ff5 combines committed fork A40ae6185f, B ab71a2a3c, C40a8bb253 sectionwise, then adds bounded scheduler release decision leaves,192 hgo copies,32 scheduler reset copies and8 landed-reset copies per clock. No additional schedule edge. Generator check reports UP TO DATE.

Actual Verilator5.050, seed1,20000edges: scheduler360000checks PASS; PC528046checks PASS; PC_H491757checks PASS. Payload bits pc__er[258:1] and pc__her[258:1] compare only at their own reference valid bit0; valid/fault/credit bits remain unconditionally compared. Empty FIFO payload is undefined in both source contracts. Health mutant4 and landed fault input mutant5 FAIL with committed witnesses. Scheduler mutant1 is insensitive under this random stimulus and PASSES; it is excluded by the existing sr6+ manifest. Tag read is instead checked by tq mutant1 and ctrl mutant1 (must rerun integrated final source before admission).

Separate full CDC minimum component:44608checks,27473 valid down words,20923 valid upstream words PASS. Upstream bank-permutation mutant3 FAILS exactly20923 checks; down-bank mutant1 and no-prefetch mutant2 FAIL. All source files use full production widths/depths. The added upstream mutant uses the existing OT_KVPC_CDC_UP_MUT source switch. This is direct evidence that valid-qualified payload comparison detects a causal corruption; no payload waiver while valid.

Mapped integrated native census is still pending. These checks do not qualify a layout or submit. Previous source omissions failed closed before actual synthesis and are infrastructure failures, not native results.
