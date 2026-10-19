C199 free-clock successor: mapped diagnostic only

Exact original d6d1730cb gate source/config plus the opt-in tile-clock overlay e51975a97 completed canonical ORFS synthesis. Functional receipt55812b482 preserves124422 output/metadata cycles exactly. No physical gate has been launched.

The mapped ODB has246622 instances,51965 flops,2 actual ROMs and48767.797um² total master area. Raw Yosys hierarchy area52653.440um² includes logic subsequently removed by OpenROAD eliminate_dead_logic; use the ODB result for this census. Clock input51967 loads includes the flops and two ROM clock pins. No latch or ICG master remains in the mapped master inventory. Every nonconstant/nonclock >32-load net is a reset output. Sixteen tile synchronizers drive102 loads each; other reset outputs drive552,136,38,42 and285. These are explicit unresolved SAFE blockers.

The source intentionally enables idle clocks and preserves valid data edges. Its power cost remains unmeasured. A physical experiment requires a source-pinned reset partition, actual placement/fill and clock plan, PNG/checklist review and new native TT/FF proof. No old padded result qualifies the successor.

An initial census launch omitted --dir and failed before reading any database on epyc8 (exit127). The corrected unpinned --dir launch selected epyc7, unit oth-ubuntu-3223189-1792431188, exit0. No original gate snapshot was edited.
