"""remap_asbuilt.py IN OUT KVB_DIR CELLS_DIR MAP_FILE: the lost binder2-1023 scratch paths of a KV asbuilt recipe ->
the reconstructed kv_bound dir (KVB_DIR: die_bound.v, kv_hard_models.sv, bound_netlist.json), ASAP7 cell models, map."""
import json, sys
src, dst, kvb, cells, mapf = sys.argv[1:6]
t = open(src).read()
t = t.replace('/home/ubuntu/scratch/binder2-1023/kv_bound', kvb).replace('/home/ubuntu/scratch/binder2-1023/asap7_cells', cells)
d = json.loads(t)
d['map_file'] = mapf
left = [s for s in json.dumps(d).split('"') if '/home/ubuntu/scratch' in s]
assert not left, left
json.dump(d, open(dst, 'w'), indent=1)
print('remapped', dst)
