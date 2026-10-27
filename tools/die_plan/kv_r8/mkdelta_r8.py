# D-KV-CLK-R8: band partitions (outside the driven mesh rows) take die clock entries on their array-facing edge(s).
import json,sys
src,dst=sys.argv[1:3]; p=json.load(open(src)); INSET=21.6
spec={"kv3_hroot":"S","kv3_hub_C":"SN","kv3_hub_Ei":"SN","kv3_hub_Eo":"SN","kv3_hub_Wi":"SN","kv3_hub_Wo":"SN",
      "kv3_io_cor":"S","kv3_io_cor_v1":"S","kv3_io_ft":"S","kv3_io_ft_v1":"S","kv3_sys_SD":"S","kv3_sys_SD_v1":"S","kv3_sys_c":"S"}
for t,f in spec.items():
    h=p["partition_types"][t]["outline_um"][1]
    p["partition_types"][t].setdefault("clock",{})["tap_edge_y_um"]=[v for v in ([INSET] if "S" in f else [])+([round(h-INSET,3)] if "N" in f else [])]
p.setdefault("plan_deltas",[]).append({"id":"D-KV-CLK-R8","note":"CLOCK-KV-R8 option (a): band clock entries on the array-facing edge, inset %.2f um (type frame; orientations map S to the array side)"%INSET,"types":spec})
json.dump(p,open(dst,"w"),indent=1); print("types",len(spec))
