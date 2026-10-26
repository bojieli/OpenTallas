"""TOKj-HBM: trace the COLL kq write lanes hcollgl_SW.vm_kq_* -> hcollks_SW_p* (b_kq) -> VM bank (vm_kq) in die.v and
price them with d4g_bank_latency.Graph.lane_latency (same model as coll_transport)."""
import json, re, sys
from pathlib import Path
W = Path('/home/ubuntu/wt/tokj-hbm-tools/tools')
sys.path.insert(0, str(W)); sys.path.insert(0, str(W / 'hbm_die_v16'))
from hbm_layer_vehicle import coll_transport as CT
import d4g_bank_latency as L
contract, die_v = sys.argv[1], sys.argv[2]
G = L.Graph.__new__(L.Graph); G.I = json.loads(Path(contract).read_text())['instances']
# all instances
inst, cur, buf = {}, None, []
for line in open(die_v):
    if cur is None:
        m = re.match(r"\s*(\w+)\s*(?:#\(.*?\))?\s+(\w+)\s*\(\s*$", line)
        if m: cur, buf = m.groups(), []
    elif re.match(r"\s*\);", line):
        inst[cur[1]] = (cur[0], dict(re.findall(r"\.(\w+)\((.*?)\)\s*,?\s*$", "".join(buf), re.M))); cur = None
    else: buf.append(line)
out = {}
for name, (mod, ports) in inst.items():
    if CT.RELAY.match(name): continue
    for p, expr in ports.items():
        if 'hcollgl_SW__vm_kq' not in expr and 'hcollks_SW' not in expr and not CT.HOP.search(expr): continue
        try: hops, root = CT.trace(inst, name, p)
        except Exception as e: continue
        if 'hcollgl_SW__vm_kq' in root or 'hcollks_SW_p' in root:
            lat, notes = G.lane_latency(hops)
            out[f'{name}.{p}'] = dict(module=mod, latency_edges=lat, wrappers=len(hops), root=root[:120], notes=notes)
for k, v in sorted(out.items()): print(k, v['module'], v['latency_edges'], v['wrappers'], v['root'][:70], v['notes'][:2] if v['notes'] else '')
json.dump(out, open(sys.argv[3], 'w'), indent=1)
