SOURCE-ONLY RECURSIVE ENDPOINT INVENTORY. NO NATIVE TIMING OR ADOPTION.

Frozen inputs: source_manifest.json, original f543 parent + VM5c0e; BEFORE final station/stream/nativehead changes.
Frontend: Yosys0.68 read_verilog -defer -sv -DSYNTHESIS -DOT_QFD_DV_SAFE_STORAGE <37 exact sources>; hierarchy -check -top qfd_dv_slice2_w_regional_lp; proc; memory_map; opt_clean; write_json.
Frontend unit oth-ubuntu-3290461-1792433002 ep7:19.01s/930.53MB; raw290MB JSON hash in summary.
Auditor final code: cccfc0e1f+7ecbc283d+fdbcaf2ab+7207a40b5+296d575ab. Actual audit unit oth-ubuntu-3328046-1792433766 ep7 exit0.
All18 clockroots represented,2,326,303 preoptimization leafcells/57,916 endpointcells (wordFF widths separately in report),4,258 foreignclock/phase/input-boundary sink records; no unknownleaf/unownedclock issue.
Exactly64 expected parent memory instances match master, declared clockpin, source rootcore, posedge and phase0 after master-specific geometry binding correction5398bf162. Eight additional oldhead TLS memories are separate unqualified nativechild obligations, not included in64 parentpin count.
Eight explicitly open child OUTPUT ports recorded; interior endpoint analysis retained. Missing inputs and partialwidths still reject. Exact constant/outputwirealiases canonicalize parents; independent childinput/rootclock aliases still reject.
No landing/crossing exception is applied. Source clock aliases cannot prove native clockobject ownership, phase/age/setup/hold, TT/FF, pin access, reset405um reach, placement/routing, mappedarea/fanout or finalphysicalsource integration.

Full primitive census also completed separately: ep8 /srv/opentallas-scratch/claude/safe-qw-regional-endpoints-1019-v2/out/netlist.json (2GB), NOT yet analyzed. Original older baseline census PID3135775 ep8 remains live and preserved.
