"""PRIVATE final-cluster cut, no compiler activation and no build fallback.

Independent arithmetic is implemented here with explicit float32 ufuncs;
it imports no DUT or golden arithmetic. All output directories are immutable.
"""
import argparse, hashlib, json, os, pathlib, resource, shutil, sys, time, traceback
import numpy as np

ROOT = pathlib.Path('/srv/opentallas-scratch/claude/refill-1225/QWLAYER')
W = ROOT / 'matrix_final_cluster_1019'
SRC = W / 'src'
SHA = {1:'7ba89595a8c4d2e77ba02e76479b2703237c426caf994cc8f2911ec698b8ce86',
       4:'2b1db9ca2ff412ea081c66d66d135278960ed3044157e2af8cac96e295d073e1'}
sha = lambda p: hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
dump = lambda p, x: pathlib.Path(p).write_text(json.dumps(x, indent=2) + '\n')
def op(fn, a, b):
    x = fn(a, b, dtype=np.float32)
    return np.where(x == 0, np.float32(0), x).astype(np.float32)
def tree(x):
    while x.shape[-1] > 1:
        x = op(np.add, x[..., 0::2], x[..., 1::2])
    return x[..., 0]
def independent(f):
    with np.load(f) as z:
        w, x, s, g, split = [z[k] for k in ('w','x','s','gold_y','split')]
    w, x, s = w.astype(np.float32), x.astype(np.float32), s.astype(np.float32)
    assert w.shape[1] == 4096 and w.shape[0] in (768,3072)
    assert np.isfinite(w).all() and np.isfinite(x).all() and np.isfinite(s).all()
    u = x.view(np.uint32).astype(np.uint64)
    xb = (((u + 0x7fff + ((u >> 16) & 1)) >> 16) << 16).astype(np.uint32).view(np.float32)
    split = int(split); kc = w.shape[1] // split
    ww, xx = w.reshape(w.shape[0],split,kc), xb.reshape(split,kc)
    acc = np.zeros((w.shape[0],split), np.float32)
    for k in range(kc):
        prod = op(np.multiply, ww[:,:,k], xx[:,k])
        acc = op(np.add, acc, prod)
    cluster = tree(acc.reshape(w.shape[0],split//64,64))
    y = op(np.multiply, tree(cluster), s)
    mismatch = np.flatnonzero(y.view(np.uint32) != g.astype(np.float32).view(np.uint32))
    scaled_early = tree(op(np.multiply, cluster, s[:,None]))
    seq = np.zeros(len(s),np.float32)
    for c in range(cluster.shape[1]): seq = op(np.add, seq, cluster[:,c])
    seq = op(np.multiply,seq,s)
    result = dict(fixture=str(f),sha256=sha(f),rows=len(s),split=split,k_per_chunk=kc,
                  isa_equal=len(s)-len(mismatch),isa_words=len(s),
                  mismatches=mismatch[:20].tolist(),cluster_bits_sha256=hashlib.sha256(cluster.tobytes()).hexdigest(),
                  scale_before_tree_different=int(np.sum(scaled_early.view(np.uint32)!=y.view(np.uint32))),
                  sequential_clusters_different=int(np.sum(seq.view(np.uint32)!=y.view(np.uint32))))
    assert not len(mismatch), result
    return cluster.T.copy(), y, result
def stage():
    W.mkdir(exist_ok=False)
    shutil.copytree(ROOT/'staging_replay_1019/src', SRC)
    here = pathlib.Path(__file__).parent
    patch = (here/'final_cluster_only.PROPOSAL.patch').read_text()
    parent_pins=json.loads((here/'parent_source_hashes.json').read_text())
    for name,digest in parent_pins.items():
        p=SRC/name
        assert sha(p)==digest, ('parent source mismatch',name)
    # Exact four-keyword edit; assert the old source hashes before changing it.
    pins = json.loads((here/'source_hashes.json').read_text())
    checks = []
    for row in pins:
        p = SRC/row['path']
        if row['revision'] == '28ebdeac7': continue
        if row['path'].endswith('stn_ages.json'):
            p.parent.mkdir(parents=True,exist_ok=True); shutil.copy2(here/'stn_ages.json',p)
        assert p.is_file() and sha(p)==row['sha256'], (str(p),row)
        checks.append(dict(path=row['path'],sha256=sha(p),revision=row['revision']))
    replacements = {
      'tools/qwen_layerbench/dv_lower_mat.py':[
        ('D.cmd_stn(s, 3, 0, nw, 0, 0, 0)', 'D.cmd_stn(s, 3, 0, nw, 0, 0, 0, kc=1)'),
        ('D.cmd_stn(s, MODE[lv], 0, nw, sb, dst, db, amax=amax)', 'D.cmd_stn(s, MODE[lv], 0, nw, sb, dst, db, kc=1, amax=amax)')],
      'rtl/test/qwen_dv/dv_lower_mat_bench.py':[
        ('D.cmd_stn(s, 1, 1, 8, 0, M.DST_AR, 0x100 * (s + 1))','D.cmd_stn(s, 1, 1, 8, 0, M.DST_AR, 0x100 * (s + 1), kc=1)'),
        ('D.cmd_stn(s, 1, 1, 8, 0, 0, 0x40 * s, amax=1)','D.cmd_stn(s, 1, 1, 8, 0, 0, 0x40 * s, kc=1, amax=1)')]}
    for name, pairs in replacements.items():
        p=SRC/name; t=p.read_text()
        for old,new in pairs:
            assert t.count(old)==1; t=t.replace(old,new)
        p.write_text(t)
        checks.append(dict(path=name,private_after_sha256=sha(p),change='PRIVATE_FINAL_CLUSTER_KC1'))
    # Pin all previously verified compiled/runtime dependencies, allowing only our two source edits.
    ancestry=json.loads((here/'parent_source_ancestry.json').read_text())
    for row in ancestry:
        assert row['matches'], row
        if row['path'] not in replacements: assert sha(SRC/row['path'])==row['sha256'],row
    dump(W/'parent_source_ancestry.json',ancestry)
    dump(W/'stage_manifest.json',checks)
    (W/'PRIVATE_FINAL_CLUSTER_CUT').write_text('kc=1 completed cluster inputs; public/default unchanged\n')
    shutil.copy2(ROOT/'staging_replay_1019/fixtures.json',W/'fixtures.json')
    shutil.copy2(ROOT/'staging_replay_1019/executables.json',W/'executables.json')
def setup():
    os.environ.update(QWEN_O4_TP='8',QWEN_O4_GROUPS='3072',HDC_SU_WIDTH='64',HDC_KV_FMT='fp8',OT_GOLD_ROOT=str(SRC),PYTHONDONTWRITEBYTECODE='1')
    sys.path[:0]=[str(SRC/'rtl/test/qwen_dv'),str(SRC/'tools/qwen_layerbench')]
    import dv_lower_mat_bench as B
    return B
def preflight():
    B=setup(); rows=[]
    fixtures=json.loads((W/'fixtures.json').read_text())
    for nu in (1,4): assert sha(ROOT/f'nu{nu}/obj_n12/Vtb')==SHA[nu]
    for layer in (0,1):
        for mode in ('qkv','gu'):
            f=ROOT/f'fx_qk/L{layer}_mat_{mode}_tp8.npz'; assert sha(f)==fixtures[str(f)]
            parts,y,r=independent(f)
            with np.load(f) as z: B.FIX.clear();B.FIX.update({k:z[k] for k in z.files})
            gm=B.real_mat(mode,int(B.FIX['split']))
            assert np.array_equal(parts.view(np.uint32),np.asarray(gm['parts']).view(np.uint32))
            assert np.array_equal(y.view(np.uint32).astype(np.uint64),gm['y'])
            r['existing_bench_cluster_and_y_equal']=True;rows.append(r)
            class ReadyForRTL(Exception):pass
            oldrun=B.LB.run
            def dryrun(work,name,ev,ncyc):
                dump(W/f'preflight_L{layer}_{mode}_events.json',dict(count=len(ev.ev),ncyc=ncyc))
                raise ReadyForRTL()
            B.LB.run=dryrun
            try:
                B.run_vm(W,mode,B.M.load_ages(),np.random.default_rng(1),None)
                raise AssertionError('lowering failed to reach RTL boundary')
            except ReadyForRTL:pass
            finally:B.LB.run=oldrun
    dump(W/'independent_gold_preflight.json',rows)
    print('INDEPENDENT_PREFLIGHT_PASS',sum(r['isa_words'] for r in rows),'ISA words',flush=True)
def run(nu,layer,mode,mut):
    B=setup(); start=time.time(); d=W/f'nu{nu}'/f'L{layer}_{mode}_{mut}';d.mkdir(parents=True,exist_ok=False)
    f=ROOT/f'fx_qk/L{layer}_mat_{mode}_tp8.npz'
    assert all(r['isa_equal']==r['isa_words'] for r in json.loads((W/'independent_gold_preflight.json').read_text()))
    assert sha(f)==json.loads((W/'fixtures.json').read_text())[str(f)]
    exe=ROOT/f'nu{nu}/obj_n12/Vtb'; assert sha(exe)==SHA[nu]
    reads=set()
    def audit(event,args):
        if event=='open' and isinstance(args[0],str):
            p=pathlib.Path(args[0])
            if p.is_file() and (p.is_relative_to(SRC) or p.is_relative_to(ROOT/'fx_qk')):reads.add(str(p))
    sys.addaudithook(audit)
    def existing(work):
        assert work==d and sha(exe)==SHA[nu]
        print('RTL_EXEC_BEGIN',str(exe),'sha256='+SHA[nu],flush=True);return exe
    B.LB.build=existing
    original_lower=B.M.lower_matvec; state={}
    def lower(*a,**kw):
        low=original_lower(*a,**kw); state['low']=low
        dump(d/'lowering.json',low);return low
    B.M.lower_matvec=lower
    if mut=='kc2':
        original_cmd=B.D.cmd_stn
        def cmd(*a,**kw):kw['kc']=2;return original_cmd(*a,**kw)
        B.D.cmd_stn=cmd
    original_run=B.LB.run
    def rtl(work,name,ev,ncyc):
        if mut=='nearshift':
            near=sorted(t for t,p,v in ev.ev if p==B.P_RSS(0) and (v>>512)&1 and not (v>>1026)&1)
            assert len(near)==8,near
            ev.ev=[(t+1 if p==B.P_RSS(0) and t in near else t,p,v) for t,p,v in ev.ev]
            dump(d/'command_mutation.json',dict(kind=mut,old_edges=near,new_edges=[t+1 for t in near],port=B.P_RSS(0)))
        if mut=='predrain':
            far=min(t for t,p,v in ev.ev if p==B.P_RSS(0) and (v>>1026)&1)
            edge=far+8 # second STN before the first result/drain, same station, different destination base
            ev.cmd(edge,B.D.cmd_stn(0,B.M.MODE[state['low']['level']],0,16 if mode=='gu' else 8,32 if mode=='gu' else 0,1,128,kc=1))
            dump(d/'command_mutation.json',dict(kind=mut,second_stn_entry=edge,first_far=far,new_dbase=128))
        log=original_run(work,name,ev,ncyc)
        ledger={k:[dict(edge=t,word=hex(v)) for t,v in vals] for k,vals in log.items()}
        dump(d/'output_edges.json',ledger)
        dump(d/'terminal_status.json',dict(status={k:vals for k,vals in ledger.items() if k.endswith('ST') or k=='S0AG'},
             output_word_counts={k:len(v) for k,v in log.items()},event_count=len(ev.ev),ncyc=ncyc))
        return log
    B.LB.run=rtl
    oldout,olderr=sys.stdout,sys.stderr
    with (d/'bench.out').open('w') as out:
        sys.stdout=sys.stderr=out
        try:
            sys.argv=['PRIVATE_FINAL_CLUSTER_CUT','--work',str(d),'--run',mode,'--fixture',str(f)]
            if mut=='sbase1':sys.argv+=['--mutant','sbase1']
            rc=B.main()
        except BaseException:traceback.print_exc();rc=99
        print('BENCH_RC',rc,flush=True)
    sys.stdout,sys.stderr=oldout,olderr
    dump(d/'runtime_reads.json',{p:sha(p) for p in sorted(reads)})
    dump(d/'resources.json',dict(wall_seconds=time.time()-start,self_peak_rss_kb=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        child_peak_rss_kb=resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss,
        files={p.name:dict(bytes=p.stat().st_size,sha256=sha(p)) for p in d.iterdir() if p.is_file()}))
    print('CASE_TERMINAL',nu,layer,mode,mut,'rc',rc,flush=True)
    return rc
if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('action',choices=['stage','preflight','run']);ap.add_argument('--nu',type=int);ap.add_argument('--layer',type=int,default=0);ap.add_argument('--mode',default='gu');ap.add_argument('--mutant',default='positive');a=ap.parse_args()
    if a.action=='stage':stage()
    elif a.action=='preflight':preflight()
    else:sys.exit(run(a.nu,a.layer,a.mode,a.mutant))
