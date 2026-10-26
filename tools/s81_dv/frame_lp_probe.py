#!/usr/bin/env python3
"""AD-S81-FRAME 10-18: landed-region LOOP anatomy of the _l4 frames (col_h9_l4 / col_h10_l4) under lp.py.
Regions = the 3-region min-cut plan of frame_regions.py (regions.json cuts, c26l placement); reset source = the frame's
column reset n257 (crs4 .rs -> 326 child reset pins), lk static.  lp.py plan() (offsets mode) refuses: the frame is ONE
strongly connected component (station x chain forward + e0/e1/nf/si feedback, return tree fu/fd both ways), so every
landing is a COMPILER RE-SCHEDULE (+E+1 edges on every crossing, calendar re-derived), not a transparent offset.
Writes results/arch/s81_dv_1016/frame_l4_cluster/loop_anatomy_<master>.json.   frame_lp_probe.py col_h9|col_h10
Pure netlist arithmetic (no sim)."""
import sys, json, collections, importlib.util
from pathlib import Path as _P
W=str(_P(__file__).resolve().parents[2])
sys.path.insert(0, W+'/tools/s81_dv'); sys.path.insert(0, W+'/tools/landed_parent')
import frame_regions as FR, lp
from pathlib import Path
master=sys.argv[1]
r, cut, H = FR.frame(master, Path(W+'/rtl/dsrom_sys/s81_dv/frame_l4'))
# re-derive yc per inst (frame() keeps it local): patch by recomputing
import re, gzip, statistics
FW=FR.FW
fn, mod, slots, nq, nbf = FW.CLASSES[master]
text = gzip.decompress((FW.SRC / fn).read_bytes()).decode()
_, insts = FW.parse_column(text, mod)
cl = json.loads(gzip.decompress((FW.SRC / 'c26l_sel_clusters.json.gz').read_bytes()))
cluster = next(c for c in cl['clusters'] if c['master'] == mod)
names, _ = FW.local_names(cluster['children'], insts)
box = {c['instance']: c['box_um'] for c in cluster['children']}
pos = {names[i['name']]: box[i['name']] for i in insts if i['name'] in box}
s = open(W+f'/rtl/dsrom_sys/s81_dv/frame_l4/{master}_l4.sv').read()
body = s[s.index(');') + 2:]
inst_re = re.compile(r"^    ([a-z]\w*)\s*(?:#\((?:[^()]|\([^()]*\))*\))?\s*(u_\w+)\s*\((.*?)\);\s*$", re.M | re.S)
nets, kids = collections.defaultdict(set), {}
for m in inst_re.finditer(body):
    mst, inst, conns = m.groups(); kids[inst]=mst
    for pin, expr in re.findall(r"\.(\w+)\s*\(((?:[^()]|\([^()]*\))*)\)", conns):
        if pin in FR.CLOCK_PINS: continue
        for n in re.findall(r"\b(n\d+|(?:x|xo|ret|xk|xok|lk)\[\d+\]|rst_n)", expr): nets[n].add(inst)
yc = {k: v[1] + v[3] / 2 for k, v in pos.items() if k in kids}
nb = collections.defaultdict(set)
for ks in nets.values():
    if len(ks) < 40:
        for a in ks: nb[a] |= ks - {a}
for _ in range(6):
    for k in kids:
        if k not in yc:
            ys = [yc[o] for o in nb[k] if o in yc]
            if ys: yc[k] = statistics.mean(ys)
cuts = json.load(open(W+'/results/arch/s81_dv_1016/frame_l4_cluster/regions.json'))['masters'][master]['plan']['cuts_um']
def reg(y): return 'r%d' % sum(y > c for c in cuts)
regions = collections.defaultdict(list)
for k in kids: regions[reg(yc[k])].append(k)
ch = ['rtl/dsrom_sys/s81_die_bind/dsfd_bf_col.sv', 'rtl/dsrom_sys/s81_die_bind/dsfd_bf_front_roots.sv', 'rtl/dsrom_sys/s81_dv/frame/dsfd_rly_frame_exact.sv', 'rtl/dsrom_sys/s81_dv/land/dsfd_cfifo_crs4.sv', 'rtl/dsrom_sys/s81_fill2/gen19b/dsfd_qbank_N.sv', 'rtl/dsrom_sys/s81_fill2/gen19b/dsfd_qbank_S.sv', 'rtl/dsrom_sys/s81_glue/dsfd_rly_masters.sv', 'rtl/dsrom_sys/s81_glue/dsfd_rly_masters_266ew.sv', 'rtl/dsrom_sys/s81_glue/dsfd_rly_masters_536.sv', 'rtl/dsrom_sys/s81_glue/dsfd_rly_masters_c26l.sv', 'rtl/dsrom_sys/s81_glue/dsfd_rly_masters_dv276.sv', 'rtl/dsrom_sys/s81_glue/dsfd_rly_masters_gen18.sv', 'rtl/dsrom_sys/s81_glue/dsfd_rly_masters_v16.sv', 'rtl/dsrom_sys/s81_glue/test/actual_rly1_reference.sv', 'rtl/dsrom_sys/s81_static_net/gen/dsfd_node_LLd.sv', 'rtl/dsrom_sys/s81_static_net/gen/dsfd_node_LLfd.sv', 'rtl/dsrom_sys/s81_static_net/gen/dsfd_node_LLfu.sv', 'rtl/dsrom_sys/s81_static_net/gen/dsfd_node_NNfd.sv', 'rtl/dsrom_sys/s81_static_net/gen/dsfd_node_NNfu.sv', 'rtl/dsrom_sys/s81_static_net/gen/dsfd_rstg.sv', 'rtl/dsrom_sys/s81_static_net/ot_s81_sstn_base566.sv', 'rtl/dsrom_sys/s81_static_net/ot_s81_sstn_payload536.sv', 'rtl/experimental/w5_context/tb_w5_cfg_context.sv', 'rtl/v41die/ot_s81_cfg7_seq.sv', 'rtl/v41die/ot_s81_cfg7_seq_bfp.sv', 'rtl/v41rom/ot_v41_rom_elem_q_qxpq_w10.sv']
ch = [f for f in ch if '/test/' not in f and 'experimental' not in f] + ['physical/asap7_memory_macros_v2/ot_rom_4096x72_m8/ot_rom_4096x72_m8_bb.v']
hdr_end = s.index(');')
decl = re.findall(r'^\s*(input|output) wire (\[[^\]]*\] )?(\w+);\s*$', s[hdr_end:hdr_end+3000], re.M)
pre = s[:s.index('(clk')]
ansi = pre + '(' + ', '.join(f'{d} wire {r or ""}{n}' for d, r, n in decl) + ');' + re.sub(r'^\s*(input|output) wire (\[[^\]]*\] )?\w+;\s*$', '', s[hdr_end+2:], flags=re.M)
open(f'/tmp/{master}_l4_ansi.sv','w').write(ansi)
spec = dict(top=f'{master}_l4', sources=[f'/tmp/{master}_l4_ansi.sv'], child_sources=ch,
            clock_ports=['clk','cr','cr_s'], clock_pins=['ck','clk','cr','cr_s','xk'], reset_port=sys.argv[2] if len(sys.argv)>2 else 'n257',
            reset_pins=['rs','rst_n','rst'], static=['lk'],
            regions=[dict(name=n, insts=sorted(v)) for n, v in sorted(regions.items())])
lp.ROOT = Path(W)
P = lp.Parent(spec)
print({k: len(v) for k, v in sorted(regions.items())}, 'crs4 in', P.region.get('u_cf'), 'rstg', {i: P.region[i] for i in P.region if kids[i]=='dsfd_rstg'})
try:
    pl = P.plan()
    print('PLAN OK lands', len(pl['lands']), 'bits', sum(L['width'] for L in pl['lands']), 'pads', len(pl['pads']), 'tmax', max(pl['t'].values()))
except SystemExit as e:
    print('PLAN FAIL', str(e)[:1500])
json.dump(spec, open(f'/tmp/frame_lp_spec_{master}.json','w'), indent=1)

# --- loop anatomy: SCCs of the child graph; landed edges inside an SCC
drv, rd, out_drv = P.graph()
G = collections.defaultdict(set); E = []
for n, inst, pin in rd:
    for d in drv.get(n, ()):
        if d.startswith('port:'): continue
        G[d].add(inst); E.append((d, inst, n, pin))
sys.setrecursionlimit(100000)
idx, low, st, on, comp = {}, {}, [], set(), {}
c = [0]
def sc(v):
    idx[v] = low[v] = c[0]; c[0] += 1; st.append(v); on.add(v)
    for w in G[v]:
        if w not in idx: sc(w); low[v] = min(low[v], low[w])
        elif w in on: low[v] = min(low[v], idx[w])
    if low[v] == idx[v]:
        while True:
            w = st.pop(); on.discard(w); comp[w] = v
            if w == v: break
for v in list(P.region):
    if v not in idx: sc(v)
sz = collections.Counter(comp.values())
big = [k for k, n in sz.items() if n > 1]
print('SCCs >1:', [(sz[k]) for k in big][:10])
cross = collections.Counter()
for d, i, n, pin in E:
    if P.region[d] != P.region[i] and comp[d] == comp[i]:
        cross[(kids[d], P.region[d], kids[i], P.region[i], pin)] += 1
for k, v in sorted(cross.items(), key=lambda x: -x[1])[:40]:
    print(v, k)
# per-cut class summary (bits crossing each region boundary, by direction)
dirs = collections.Counter(); bits = collections.Counter()
wid = {}
for d, i, n, pin in E:
    if P.region[d] != P.region[i]:
        key = (P.region[d], P.region[i])
        dirs[key] += 1
seen=set()
for d, i, n, pin in E:
    a,b=P.region[d],P.region[i]
    if a!=b and (n,b) not in seen:
        seen.add((n,b)); bits[(a,b)] += lp.eval_width(P.rng(n), P.env)
rec = dict(master=master, cuts_um=cuts, regions={k: len(v) for k, v in regions.items()}, region_of_crs4=P.region.get('u_cf'),
           scc_sizes=sorted(sz[k] for k in big), nodes=len(P.region),
           landed_bits_by_direction={f'{a}->{b}': v for (a, b), v in sorted(bits.items())},
           loop_classes=[dict(n=v, src=k[0], src_region=k[1], dst=k[2], dst_region=k[3], pin=k[4]) for k, v in sorted(cross.items(), key=lambda x: -x[1])])
json.dump(rec, open(W+f'/results/arch/s81_dv_1016/frame_l4_cluster/loop_anatomy_{master}.json','w'), indent=1)
print('bits by direction', rec['landed_bits_by_direction'])
