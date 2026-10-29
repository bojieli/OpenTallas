import subprocess,re,collections,json,sys
R='/home/ubuntu/OpenTallas'; REV='origin/main'
def git(*a): return subprocess.run(['git','-C',R]+list(a),capture_output=True,text=True).stdout
files=[l for l in git('ls-tree','-r','--name-only',REV,'tools/').split('\n') if re.search(r'\.(py|tcl|sh)$',l)]
NAME=re.compile(r'clock|clk|cts|htree|h_tree|mesh|regtree|dme|skew|insertion|landing|landed|_tap|tap_|spine|trunk',re.I)
# content-based: count files whose content mentions clock-building/timing constructs
cont=set(l.split(':',1)[1] for l in git('grep','-l','-i','-E',r'clock_tree_synthesis|set_propagated_clock|create_clock|clock_latency|regtree|htree|h_tree|clk_landing|BUFx24|stage_ps|insertion',REV,'--','tools/').split('\n') if l)
istest=lambda f: bool(re.search(r'/tests?/|(^|/)test_',f))
def die(f):
    s=f.lower()
    if re.search(r'hbm',s): return 'HBM'
    if re.search(r's81_head|s81head|/head_|_head[_/.]|s81_hd',s): return 'HEAD'
    if re.search(r'kv',s): return 'KV'
    if re.search(r'qwen_compute|/qc_|_qc[_./]|qc_|qwen_split|qwen_romleaf|qwen_cluster|qwen_attention|qwen_tp8|qwen_vmwb|qwen_host|qwen_dv|romleaf',s): return 'QC'
    if re.search(r'qwen',s): return 'QC?'
    if re.search(r's81|dsrom|v41',s): return 'S81'
    return 'shared'
CATS=[('stage_model',r'stage|calib|_cal|spice|fit|model|aocv|ocv|derate'),
('landing_crossing',r'landing|landed|meso|crossing|_ca_|ca_|cfifo|ring'),
('tree_build',r'regtree|dme|htree|h_tree|spine|mesh|trunk|tree|cts|build|buffer|repeater|insert'),
('latency_targets',r'latency|insertion|target|tap|early'),
('sta_check',r'sta|skew|check|verdict|pair|gate|audit|verify|report|qual'),
('plan_region',r'plan|region|est|local|map|site|island'),
('viz',r'plot|render|viz|png|draw'),
('dump_io',r'dump|strip|extract|parse|def|odb|spef')]
def cat(f):
    b=f.split('/')[-1].lower()
    for c,p in CATS:
        if re.search(p,b): return c
    return 'other'
rows=[]
for f in files:
    if not (NAME.search(f) ): continue
    loc=len(git('show',f'{REV}:{f}').split('\n'))
    rows.append((f,die(f),cat(f),istest(f),loc,f.split('/')[1]))
json.dump(rows,open(sys.argv[1],'w'))
nt=[r for r in rows if not r[3]]
print('name-matched scripts',len(rows),'non-test',len(nt),'tests',len(rows)-len(nt),'content-matched(all tools)',len(cont))
c=collections.Counter(r[1] for r in nt); print('by die',c, 'LOC', {d:sum(r[4] for r in nt if r[1]==d) for d in c})
c2=collections.Counter((r[2],r[1]) for r in nt)
for k in sorted(set(r[2] for r in nt)):
    print(k, {d:c2[(k,d)] for d in ['shared','QC','QC?','KV','HEAD','S81','HBM'] if c2[(k,d)]}, 'LOC',sum(r[4] for r in nt if r[2]==k))
print('total LOC non-test',sum(r[4] for r in nt),'test LOC',sum(r[4] for r in rows if r[3]))
