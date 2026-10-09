# MD-2 storage and whole-row schedule progress

The historical dense maps occupy 1680 pairs/side, but fragment 1344 paired-row
streams per side. They do not establish an executable field schedule.

The opt-in whole-row fallback uses all 1792 pairs per existing die, 112 more than
the dense byte budget (+6.67%), with no additional dies. Rotate the expert's
superrow region by `(superrow + expert*32) mod128`. Every region stores107520
words in14pairs; maximum pair occupancy8160/8192. `rowpack.json.gz` enumerates
466944 unique expert superrows over both sides, retaining each full-K row on one
pair. `rowpack_checks.json` checks complete coverage, no collisions and no row
fragmentation. `rowpack_generator_v1.py` pins the exact schedule generator source
that produced this map; current tool differs by a corrected golden bench-driver
comparator and comment only. Failed unsplit-interface and bench-driver evidence
is retained separately.

NCH16 requires at most2 full-K GU segments/pair or3 W2 segments/pair in a phase.
The generator emits up to3 GU and2 W2 subphases per expert (1908 resident
subphases over both sides); it does not inherit DP1-EP5's measured latency.
`microbench.json` measures the same minimum two-pair/one-region W17/W10 numerical
vehicle with released full-K operands: packed GU375 phase cycles, spread GU318
(+57cycles =47.5ns at1.2GHz), and W2fullK2304 six rows exact. These are component
measurements, not composed step timing. This is the generic numerical vehicle,
not qualification of the production Q-element or physical signoff.

`rowpack_image_pair0.json` records actual PP configurations and the hash of the
complete A/rank0/pair0 binary image. `generated_image_bench.json` loads that
binary and its first emitted configuration into the RTL: all4 GU outputs match
released-checkpoint golden values at fullK5120, fault0,375 phase cycles. The
minimum bench establishes this image/config mechanism. The full schedule, all
ranks/expert identities and production-Qelement context still require their
appropriate gates. None of these records marks MD-2 adopted.

Reproduce storage/schedule/image work with tools/dsrom_mtp_p2.py,
tools/dsrom_mtp_p2_rowpack.py, tools/dsrom_mtp_p2_rowpack_image.py,
tools/dsrom_mtp_p2_microbench.py and tools/dsrom_mtp_p2_image_bench.py. The pair
binary is address-major, two272-bit banks,34bytes each, little endian. Five
replicas share each side/rank image.

Next obligations: primary/head physical packing (97headers assigned only),
production-Qelement full-region timing/exactness, descriptor/config capacity,
region/VM integration, model step composition, and physical qualification.
Build/sim artifacts are preserved at /tmp/dsrom-mtp-p2-rowpack-20261009 and
/tmp/dsrom-mtp-p2-microbench-20261009. After the new owner directive, further
builds and simulations must run remotely through measured admission.
