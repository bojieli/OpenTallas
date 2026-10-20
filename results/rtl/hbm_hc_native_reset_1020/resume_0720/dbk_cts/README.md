# DBK l1 placed CTS diagnostic, not final GRT qualification

Original gate: ep7 hv16_dbk_cpl_l1-20261020-065825, source320e14b1b, exact actual image16470cea. Original4_1_cts.odb mounted read-only and SHA unchanged after audit. Full source→capture displacement through all combinational gates and transparent buffers: 8117 captured pins, maximum383.616um, zero>405. DFFs and hard-child BLOCKs are sequential cuts. All14 unreached pins have one actual TIEHI/TIELO driver (recorded individually).

Raw PG FAIL21296 of97710 checked contacts. Every unbound terminal ordinary/unprotected/nonfixed. Existing canonical global_connect in memory clears all; protected unbound0, post-bind failure0. Raw failure preserved; the ODB was never written, no protection cleared, no PG repair applied to running gate.

This establishes only CTS planning geometry and the type of PG debt. GRT final ODB and actual final PG/source/native checks remain required before any review approval or submit.
