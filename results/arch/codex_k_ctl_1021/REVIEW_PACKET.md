# CTL c32d exact gate review / source contract

Gate source61e127f40, own submit branch codex/k-ctl-close-1021. Coordinator personally viewed exact floorplan+density and approved geometry64645a5c69db60a3a1a3fe1ffdb09ba82ba6d5eaf9edc8bfde714a92e4bfedad. Native32 PASS, GRT0 M2max21.25%, TT/FF clock pin spread42.1/38.0ps. Placement setup-136.6ps / hold34.6ps is diagnostic, route decides. Six64x128 SRAMs are in two columns/three rows, continuous cells/broad channels, pin-bound fill11%, outline345.6x561.6. The pre-gate README's storage count2 is stale; snapshot remains immutable and actual geometry/review records6.

First submit refused source binding because I appended post-gate notes to README and updated spec job metadata. Restored both gate-consumed files exactly to staged contents; current committed witness paths and branch/reroute metadata belong only in submitted job.json, and new facts are here outside the frozen kit. No gate/source waiver or duplicate physical gate.

Physical input pin registers add1 edge on every data input; physical output pin registers add1 edge on outputs EXCEPT o_hroot_*, which have member RTL launch flops. Reset rst_n/por_n2stage face landing. The die's wires-only CTL/EDGES0 source is incompatible until it carries the exact gate-generated wrapper and updated compiler edge ledger; never alias the view. Slot grows86.4um inY.
