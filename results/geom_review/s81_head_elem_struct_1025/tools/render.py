# HEAD-ELEM render: routed layout + w_r transport + clock GRT-vs-RCX gap + FF-hold startpoints.
import json, gzip, re, sys, statistics as st, collections
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
geom, d, tag, out = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
g = json.load(gzip.open(geom, 'rt'))
un = lambda s: s.replace('\\', '')
loc = {un(n): (x/1000, y/1000, m) for n, m, x, y in g['comps']}
def ck(fn):
    r = {}
    for ln in open(fn):
        f = ln.rstrip('\n').split('\t')
        if len(f) == 5 and f[3] and f[4]: r[f[0]] = (float(f[3]), float(f[4]))
    return r
R = ck(f'{d}/ck_rcx_FF.tsv'); G = ck(f'{d}/ck_grt_FF.tsv')
import os; hp = [l.rstrip('\n').split('\t') for l in open(f'{d}/hold_pairs2_rcx_FF.tsv' if os.path.exists(f'{d}/hold_pairs2_rcx_FF.tsv') else f'{d}/hold_pairs_rcx_FF.tsv')]
hpG = [l.rstrip('\n').split('\t') for l in open(f'{d}/hold_pairs_grt_FF.tsv')] if __import__('os').path.exists(f'{d}/hold_pairs_grt_FF.tsv') else []
face = {}
for l in open(f'{d}/ot_face_flops.txt'):
    f = l.split('\t'); face[un(f[0])] = (f[1], f[4].strip())
port2ff = {v[1]: k for k, v in face.items()}
common = [k for k in R if k in G]
gap = {k: G[k][0] - R[k][0] for k in common}   # min (early) arrival, FF
S = {}
vals = sorted(gap.values()); n = len(vals)
S['n_sinks'] = n
S['gap_grt_minus_rcx_FF_min_ps'] = dict(min=round(vals[0],2), p1=round(vals[n//100],2), median=round(vals[n//2],2), p99=round(vals[n*99//100],2), max=round(vals[-1],2))
fo = [k for k in common if k in face]
fi = [k for k in common if k not in face]
S['gap_face_flops_median'] = round(st.median(gap[k] for k in fo), 2) if fo else None
S['gap_internal_median'] = round(st.median(gap[k] for k in fi), 2)
S['rcx_FF_early_arrival'] = dict(face_median=round(st.median(R[k][0] for k in fo),2) if fo else None, internal_median=round(st.median(R[k][0] for k in fi),2))
S['grt_FF_early_arrival'] = dict(face_median=round(st.median(G[k][0] for k in fo),2) if fo else None, internal_median=round(st.median(G[k][0] for k in fi),2))
starts = collections.Counter(); ends_port = 0
crit = []
for s, e, sl in hp:
    si = re.sub(r'/[^/]+$', '', s)
    if si == 'clk': si = port2ff.get(e, re.sub(r'/[^/]+$', '', e))
    crit.append((si, e, float(sl)*1e12))
    if '/' not in e and not e.startswith('u_'): ends_port += 1
S['rcx_FF_hold_paths_slack_lt15'] = len(crit); S['to_output_ports'] = ends_port
S['rcx_FF_hold_worst'] = sorted(crit, key=lambda t: t[2])[:5]
# face-flop launch arrival vs fixed 250 vclk
fo_out = [k for k in fo if face[k][0] and k in R]
D = max(max(p[1],p[2]) for p in g['pins'])/1000
fig, ax = plt.subplots(1, 3, figsize=(27, 9))
for a in ax[:2]:
    a.set_aspect('equal'); a.set_xlim(0, D+1); a.set_ylim(0, D+1)
    a.add_patch(Rectangle((0,0),D,D,fill=False,lw=1))
    for n_, (x, y, m) in loc.items():
        if m.startswith('ot_rom'):
            a.add_patch(Rectangle((x,y),125.304,62.952,fc='#d9d2e9',ec='k',lw=1)); a.text(x+3,y+3,n_.split('.')[-1],fontsize=9)
xs = [v[0] for v in loc.values()]; ys = [v[1] for v in loc.values()]
ax[0].scatter(xs, ys, s=0.05, c='#bbbbbb', rasterized=True)
# w_r lanes and t_r->w_r transport lines
cm = plt.get_cmap('tab20')
seg = []
for i in range(256):
    t = loc.get(f'u_m.t_r[{i}]$_DFF_P_'); w = loc.get(f'u_m.w_r[{i}]$_DFF_P_')
    if t and w:
        ax[0].plot([t[0], w[0]], [t[1], w[1]], c=cm((i//16)%20), lw=0.4, alpha=0.7)
        seg.append(abs(t[0]-w[0])+abs(t[1]-w[1]))
if seg:
    seg.sort(); S['t_r_to_w_r_manhattan_um'] = dict(median=round(seg[len(seg)//2],1), p90=round(seg[len(seg)*9//10],1), max=round(seg[-1],1), n_over_100=sum(1 for s in seg if s > 100))
    for l in range(16):
        pts = [loc[f'u_m.w_r[{i}]$_DFF_P_'] for i in range(16*l, 16*l+16) if f'u_m.w_r[{i}]$_DFF_P_' in loc]
        ax[0].text(st.median(p[0] for p in pts), st.median(p[1] for p in pts), f'L{l}', fontsize=10, weight='bold', color=cm(l%20))
for nn, nd in g['nets'].items():
    if nd['clk']:
        for sgm in nd['segs']:
            p = sgm[1:]; ax[1].plot([p[i]/1000 for i in range(0,len(p),2)], [p[i]/1000 for i in range(1,len(p),2)], c='#4a86e8', lw=0.3)
    else:
        for sgm in nd['segs']:
            p = sgm[1:]; ax[0].plot([p[i]/1000 for i in range(0,len(p),2)], [p[i]/1000 for i in range(1,len(p),2)], c='red', lw=2.5)
        ax[0].text(p[0]/1000, p[1]/1000+3, nn+' (M2 139 um, slew 351)', color='red', fontsize=10)
# hold-critical launch flops (RCX FF)
cx = [loc[c[0]][0] for c in crit if c[0] in loc]; cy = [loc[c[0]][1] for c in crit if c[0] in loc]
ax[1].scatter(cx, cy, s=14, c='red', marker='x', label=f'RCX FF hold <15 ps: launch (port) / capture flop ({len(cx)})')
gx = [loc[k][0] for k in common if k in loc]; gy = [loc[k][1] for k in common if k in loc]; gv = [gap[k] for k in common if k in loc]
sc = ax[1].scatter(gx, gy, s=1.5, c=gv, cmap='coolwarm', vmin=-50, vmax=50, rasterized=True)
plt.colorbar(sc, ax=ax[1], fraction=0.04, label='GRT-est minus RCX clock arrival (FF early, ps)')
ax[1].legend(loc='upper right'); ax[0].set_title(f'{tag}: routed 6_final, ROMs, t_r->w_r transport per lane (colour), red = w_r[244] D net')
ax[1].set_title(f'{tag}: clock tree routes, sink GRT-RCX arrival gap, FF-hold launch flops')
ax[2].hist(vals, bins=80, color='#888'); 
if fo: ax[2].hist([gap[k] for k in fo], bins=40, color='red', alpha=0.7, label='face (pin) flops')
ax[2].set_xlabel('GRT-est minus RCX clock arrival per sink, FF min (ps)'); ax[2].legend(); ax[2].set_title('per-pin clock estimate error')
plt.tight_layout(); plt.savefig(out, dpi=110)
print(json.dumps(S, indent=1))
