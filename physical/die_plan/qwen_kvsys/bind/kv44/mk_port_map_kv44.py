#!/usr/bin/env python3
"""KV-BIND 10-24: bind.py asbuilt.rewires.port_map / port_names translate GEN die-port names (host.chf0, ...) to RTL port
slices per RTL MODULE name.  kv44 substitutes the host leaf qkd_host_root_admission_obsx -> qkd_host_root_admission_obsx_bo1
(KV-R2; same ports + output d2d_boot_begin), so the reconstructed bound_netlist.json gets an alias master entry carrying the
same die-port bundles under the variant module name (data only; no tool change).
    mk_port_map_kv44.py ../inputs/kv_bound_rtl6/bound_netlist.json port_map_kv44.json"""
import copy, json, sys
d = json.load(open(sys.argv[1]))
src = d['masters']['qkd_host_rt']
assert src['module'] == 'qkd_host_root_admission_obsx', src['module']
a = copy.deepcopy(src)
a.update(module='qkd_host_root_admission_obsx_bo1', kv44_alias_of='qkd_host_rt (qkd_host_root_admission_obsx)')
d['masters']['qkd_host_rt__kv44_bo1'] = a
d['kv44_note'] = 'alias master qkd_host_rt__kv44_bo1 added by kv44/mk_port_map_kv44.py (substitute_inst host -> obsx_bo1)'
json.dump(d, open(sys.argv[2], 'w'), indent=1)
print('wrote', sys.argv[2])
