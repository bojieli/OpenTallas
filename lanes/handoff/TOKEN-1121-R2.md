# TOKEN-1121-R2 handoff (2026-11-21, STAND-DOWN)

Goal: HEAD r16 transport/token bench PASS on a completed die top.

## Done
- Completed r16 top built with the standard path (l48hp1/rp18 assemble.py procedure):
  head_publish_wrappers.py (plan p5 1a7d319a9ba6, bound RTL) -> head_start_sources.complete_top(+ rp18 start_stages).
  epyc10 /srv/opentallas-scratch2/claude/token-1121-r2/{published,completed,assemble.py,tr4.sh}.
- main @b1bb664d56f: complete_top accepts the non-ANSI gen.py top; head_transport_depth drives `*__clk` START-stage taps; test_head_start_sources.py.
- attempt4 (oth-ubuntu-2679423-1795271101): FAIL 211/329 (was 317), start_i 0, lep_fault_i 1.

## Root cause (measured)
- r16 sidecar count_aligned (K straps) bound to the NF15b START tree: st: regions hash 3a52427e1ba3, 1488 virtual stages
  (re-bound on kit tree c1cefe64), unchanged NF15b..NF15f. All existing providers (l48*/rp18) realise the l48 tree
  a32fd99c90ea (1251 stages). Per-partition START depth differs -8..+9 stages.
- Predicted START offset delta explains the bench: 116/118 passing lanes predict 0; 166/204 measured failures equal prediction mod ring depth.
- r16 plan landing_network.start_tree.uses == rp18 verbatim (provider contract never updated since NF6).
- No provider was ever emitted for the NF tree. Its inputs (fable-die-head nf15b_bind/bind.json, base/head/fdh_st13/ca4, node_cell proof) are deleted on all hosts.
- r16 die clock (r13r e5c13, kit_tree 564220a7) is not the c1cefe64 tree the START plan was bound on.

## Needed (owner: HEAD die-clock / START lane)
1. count_align_plan --start-tree clock + die_sta_related proof on the r16 die clock; count_align_bind (rebind15b.py recipe on epyc7 fable-die-head) -> new sidecar K + plan start_tree.uses.
2. start_stage_emit.py emit BIND PROOF --ctree DIR -> start_stages.json/.sv.
3. Rerun: assemble.py + tr4.sh with the new provider (same dir).
