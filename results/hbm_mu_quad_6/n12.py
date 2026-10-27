import json, sys
d = json.load(open(sys.argv[1])); T = d["partition_types"]
cnt = {}
for p in d["partitions"]: cnt[p["type"]] = cnt.get(p["type"], 0) + 1
print("N1 bank strips: type W H ft_slots ft_bits max_ft_per_face_bits hard_bbox_x hard_top_y fill")
for tn in ["q_b000","q_b001","q_b002","q_b003","q_b010","q_b011","q_b012","q_b013"]:
    t = T[tn]; W, H = t["outline_um"]; fs = t.get("ft_slots", [])
    bits = sum(f.get("width", 0) for f in fs)
    hc = t["hard_cores"]; xs = [c["origin_um"][0] + c["outline_um"][0] for c in hc]; ys = [c["origin_um"][1] + c["outline_um"][1] for c in hc]
    ha = sum(c["outline_um"][0] * c["outline_um"][1] for c in hc)
    nsf = {}
    for f in fs:
        nsf[f.get("in_face", "?") + f.get("out_face", "?")] = nsf.get(f.get("in_face", "?") + f.get("out_face", "?"), 0) + f.get("width", 0)
    print(f"  {tn} n={cnt.get(tn)} {W:.2f}x{H:.0f} ft {len(fs)} bits {bits} by faces {nsf} xmax {max(xs):.0f} ytop {max(ys):.0f} fill {ha/(W*H):.2f} -> NS bits/um of width {nsf.get('SN',0)+nsf.get('NS',0)} / {W:.0f} = {(nsf.get('SN',0)+nsf.get('NS',0))/W:.1f}")
print("N2 ft/placeholder partitions:")
for tn in ["q_mca","q_mcb","q_spu0","q_spu1","q_spt1","q_spt2","q_spb1","vsN1","vsN2","vsN4","vsN5","vsN6"]:
    if tn not in T: print("  missing", tn); continue
    t = T[tn]; W, H = t["outline_um"]
    print(f"  {tn} n={cnt.get(tn)} {W:.0f}x{H:.0f} = {W*H/1e6:.2f} mm2 each, cells {t.get('cells')} contents {[(c['inst'], c.get('cells')) for c in t.get('contents', [])][:3]} ft {len(t.get('ft_slots', []))} buses {len(t.get('buses', []))}")
