# IDXTX R3 existing production proof

Logic104b065c5 (laterreceipt-onlyHEAD07c51b4cd), exactverifiedL20S5e97dfd5c8c813d5374479508ee78b72d3232e9803c2051f6d871a637bf444ad; TREE4fdbaf13ac73d998ae3f5566ef3cb46628559a19b6a69f5c6dc6a3aecdd66032. Properfreshunitoth-ubuntu-4003840-1792622504 onot-epyc9 returned0. Existingactual6dieSRAMDIEM1/TXS1k3 productionwrapper bench PASSzero mismatch/fault, exactoriginalspansdie1edges17963..19406/1431beats,die2edges19564..20987/1424beats. Build833.384s/19.4GBallocation.

This qualifiesobservedproductiontimingofsame-edge R3consumerpartition, not native/physical. ExistingMUT1/2/3 startedonlyafterthisPASS usingbyteidenticalthreefilefixtures inindependentoutputcases. MUT4remainsunexercisedbyexistingfull-maskk3. NativeMAIN/FBmustfollowterminalcausals, noadoptionyet.

Connected scope: this existing DIEM bench instantiates dsdv_bk_sel_vmtx (VMUX + baseline dsdv_bk_sel + the changed dsdv_idx_tx_n32). It proves the real TX path and VMUX integration at that existing selector boundary. It does not instantiate the separately qualified cb73 PlanA regional parent; composing that parent, new control profile, all regional clock/reset ports, landed crossings, and actual TX/VMUX bodies remains open as recorded in ASSEMBLY_MODEL.md. No full PlanA+TX closure or inherited old 640-edge calendar is claimed.
