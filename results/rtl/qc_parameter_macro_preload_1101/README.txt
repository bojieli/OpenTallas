QC signed parameter metadata mechanism PASS: pinned openroad/orfs:asap7lock, ot-run2GB/1CPU, epyc2 unit oth-ubuntu-691219-1793547736 exit0.

Actual candidate sources from codex-qc-suc@1a1386281d5 and its signed_restore_1101 TC Liberty models, with SHA identity in manifest.json. Native VMR1509 and CRH998 functional bits match the signed libraries exactly; only their four explicit die-owned FT signal pins are added to each metadata header (1513/1002 total). VDD/VSS are excluded based on the exact LEFs' USE POWER/GROUND, recorded in manifest, rather than inferred as functional spare inputs.

Liberty-only + native deferred RTL + actual .MIF(0) override FAILS: Library interface has no parameter MIF. Reading the exact *_bb.v header eagerly (-lib -overwrite), as the existing native_bb.py ORFS patch already does, PASSes and retains the original master with MIF0 (and VMR MUT0 default). No generic binder/physical generator code change is necessary. EX's nonparameterized preload case is distinct.

These are physical metadata headers, not a functional model or an independent child proof. Adoption requires the exact independently signed child source/parameter identity, an unchanged canonical golden, parent MIF0 enforcement, and actual wiring of the declared physical FT arcs. The test top intentionally exercises only native functional ports, so this count/frontend coupon grants no physical FT closure or route approval. No functional input tieoff was added.

Replay: bash run.sh under ot-run; cases retain exact native module, matching signed Liberty, generated metadata header, both frontend logs and eager JSON. Lib-only failures are expected controls and are preserved.
