# Selected bind178 PORTFIX providers

These two files are byte-identical to the integrated source commit 4460aee667
and the actual frozen bind178 source set. They restore the existing emitted
top's fault-ring and index routing ABI when selected explicitly by a manifest.

The main-tree seqhost mux predates the ring input/output ports. The index file
retains all other common module bodies byte-for-byte; only bk_sel_vmtx differs,
with its two private vmux6/loop_lane3 helpers added. This is an existing source
cohort, not a guessed port adapter. Original masters, flags, pipelines and reset
behavior remain as recorded in the source. Default RTL selection is unchanged.

Original qualification definitions are e2cdb60865 (PORTFIX-FLT owner decision4)
and 4460aee667, with run_fault_ring_bench.sh (base plus six controls) and
run_bk_sel_fault.sh (base plus two controls). This recovery claims source
identity and ABI closure only; it does not rerun or extend those qualifications,
qualify timed reset/START, or transfer any physical view.
