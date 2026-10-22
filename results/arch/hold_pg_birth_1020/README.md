# Hold PG bind-before-protection source fix

Own MAIN-based branch codex/pg-protect-birth-1020, base940af3428. Source changes only leaf_inhold.tcl and leaf_iohold.tcl final protection blocks: use existing whole-batch ot_pg_bind_batch_before_protect on actual same hold-name cohort BEFORE existing set_dont_touch. Current ot_pg_standard_bind interface, actual PG rules, net topology, protection flags and constraints unchanged. No unprotect, late repair or waiver.

Concrete current defect: leaf_inhold.tcl4cfb8a2c line100 and leaf_iohold.tcld678a4d6 line105 protected newborn holds without calling binder. Existing nativePGhelperECC2257f cannot act if nevercalled. Frozen FJ3/FJ2 supplies missed448/455 protectedHBcells. CLOCK residual164/165 is a separate stale-consumer issue: frozenclk_net_protect94cc061d differs currente74b6d2c, which alreadybinds before nativeclockprotect. Future recipe must contain BOTH currentclockconsumer and this holdpatch; ROOT also composes independent MC3 outputhold naming52ef34c5d/5a3a675c5/04f675752. No frozenFJkit modified by thisfix.

Actual native tests (OpenROAD26Q3-1510-g6cb3f2b704, ORFSimage requestedlatest, fleetep5):
* Actual originalFJ3 3_2IO ODB + complete originalsource preGPLhooks vs patchedholds/currentnativePGhelper replay: old protected448 and896unboundPGiterms; fixed protected448 andZEROunboundPGiterms. Every12712 actualinstance master, location,orientation,placementstatus,donttouch,sourceflag and nonPGpin/net identity EXACTLYunchanged. Receipt run_positive.py checksallrows; noODBsave needed.
* Nativebatch positive: two unprotectedHBnewborns bind bothactualVDD/VSS before protection.
* Four atomicnative negatives: FIRST target valid newborn, SECOND target unknownPGmaster(VDDX), wrongdomain, protectedunbound, or wrongdomain+protected. Eachrefuses beforeFIRSTcellgetsanyPGconnection; all actualinstance PG/signalpin netidentities,donttouch,placementstatus/sourceflags and globalrules unchanged overENTIREblock. Not a perinstance-only check. Logs batch_*.log and genericbatch_test.tcl.

Reproduction inputs: original frozen FJ3 at ot-epyc5:/srv/opentallas-scratch/claude/ref_gate/hcoll_fj3_r128u-20261020-013704. Sourcecopy and scripts own /srv/opentallas-scratch/claude/codex-pg-protect-birth-1020. run_batch.py uses original2_4PDN; run_positive.py uses original3_2IO. All originalmounts read-only. No originalfiles, nets, regions, masks orPGdomainrules changed. Initialtest path staging refusal is preserved locally beforecompletecohort; nohardwareverdict inferred.

Thisfix closes source-owned holdprotection ordering. It does not claim native CTS internalbirth/analysistransaction coverage, finalclosedPG, FJphysicalresetfanout<=32 or successfulnewdesigngate. ExactbadFJfrozen snapshots remain for regression.
