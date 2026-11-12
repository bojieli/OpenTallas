"""clear x-intervals of a type at a given y band (hard cores + 2 um halo). usage: PLAN TYPE Y0 Y1 [Y0 Y1 ...]"""
import json, sys
t = json.load(open(sys.argv[1]))['partition_types'][sys.argv[2]]; W, H = t['outline_um']
R = [(h['origin_um'][0] - 2, h['origin_um'][1] - 2, h['origin_um'][0] + h['outline_um'][0] + 2, h['origin_um'][1] + h['outline_um'][1] + 2) for h in t['hard_cores']]
a = sys.argv[3:]
for y0, y1 in zip(map(float, a[::2]), map(float, a[1::2])):
    bl = sorted((r[0], r[2]) for r in R if r[1] < y1 and r[3] > y0)
    free = []; x = 0.0
    for l, h in bl:
        if l > x: free.append((round(x, 1), round(l, 1)))
        x = max(x, h)
    if x < W: free.append((round(x, 1), round(W, 1)))
    print(sys.argv[2], 'outline', W, H, 'y', y0, y1, 'free', [f for f in free if f[1] - f[0] >= 4])
