#!/usr/bin/env python3
"""DIE-KV-69 11-04 qkd_hr_core_peer RE-FORM (OWNER two strikes): source form on the unchanged member RTL.
 (1) u_root_mux binds qkd_host_peer_root_mux_pl2 (KV-PEER5 r5 10-19, all directions registered, class9 transport).
 (2) one no-reset stage (+1 edge) on the rank-codec status faces (same list as peer_rr r5 codec input stage).
usage: peer_rf.py CORE_SV_IN CORE_SV_OUT
"""
import re, sys
STATUS = ["service_ready", "native_ready", "service_epoch", "drained", "context_owned", "links_drained",
          "link_reset_seen", "retrained", "program_ready", "program_epoch", "program_digest"]
t = open(sys.argv[1]).read()
n = t.count("qkd_host_peer_root_mux u_root_mux (")
assert n == 1
t = t.replace("qkd_host_peer_root_mux u_root_mux (", "qkd_host_peer_root_mux_pl2 u_root_mux (")
i = t.index("qkd_host_peer_rank_codec u_peer_codec (")
j = t.index(");", i)
inst = t[i:j]
decl, seq = [], []
for s in STATUS:
    p = "u_peer_codec__" + s
    m = re.search(r"input\s+wire\s+\[(\d+):0\]\s+" + p + r"\s*;", t)
    assert m, p
    w = int(m.group(1)) + 1
    q = "rf_st__" + s
    decl.append(f"    (* keep = 1 *) reg [{w-1}:0] {q};")
    seq.append(f"    always @(posedge ck) {q} <= {p};")
    inst, k = re.subn(r"\b" + p + r"\b", q, inst)
    assert k >= 1, (p, k)
t = t[:i] + "\n".join(decl + seq) + "\n    " + inst + t[j:]
open(sys.argv[2], "w").write(t)
print("stages", len(STATUS))
