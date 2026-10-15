Actual SRAM collective component proof (2026-10-15)
=================================================

The native VM owner's pinned flat source snapshot instantiates all 128 real
512x128 SRAM functional models. One VM supplies rank0's records through its
L12 collective read service; four actual TP4 endpoints, CRC pipelines and FMT1
gearboxes exchange the records. All four rank results land in that VM through
sources44..47. Independent SU read requests then verify every landed row.
Other ranks receive declared external producer stimuli at their chip boundary.
No precomputed value is injected inside the VM or transport hierarchy.

Stage exact source_manifest.json inputs in a flat directory. Add plan.mem and
beats.mem from this directory and the two run_vm_sram_*_flat.sh scripts from
 tools/s81_static_collective (rename them run.sh/run_mutant.sh). Use ot-run with
8 GB and eight threads; invoke each script from the flat directory. The exact
bench is tools/s81_static_collective/tb_s81_static_fmt1_vm_sram.sv. The source
manifest includes the VM owner's snapshot because the service conversion was
still awaiting its publication commit when this component ran.

Base PASS is 28 records/rank,112 native SRAM readback rows,1792 exact FP32 values,
zero endpoint/VM fault. The physical VM landing-write mutant corrupts only rows
>=4096, preserving initial source reads and all transport pin checks; it fails
the unchanged native SRAM readback check. This proves that check observes the
actual memory destination. The earlier bench quiescence failure remains as
history: a registered PHY beat needs its assigned receive slot after TX stops.

This is component evidence. Actual FIELD production sources, complete compiler
calendar, static HC/channel/slab integration and die physical qualification
remain open; it is not native chip execution or timing qualification.
