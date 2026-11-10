# HBM-CORES-B q3bc CF2 (COORD option B): register the u_flow SRAM read and check_row, compare one edge later.
# usage: patch_cf2.py IN OUT [mutant]   Not cycle-exact: fault/configured/init_busy move +1 at the end of the scan; proved by bench.
# mutant: M1 fin not shifted (old checking/last), M2 last-row compare skipped in bad, M3 rbd kill on the restart removed,
#         M3 both restart kills removed (proved redundant, see prove_cf2.ys; survives by design)
#         M6 (MUX only) core fault U.fault one extra register
#         M4 reject gates not extended, M5 rd registered but check_row not (compare misaligned by one row)
import re,sys
src,dst=sys.argv[1],sys.argv[2]; mut=sys.argv[3] if len(sys.argv)>3 else ''
s=open(src,errors='ignore').read()
P='\\u_body.g_q3.n_u_fj.u_fj.u.u_program.'
TOK=re.compile(r'\\\S+ |\b_\d+_\b')
A={};CON={};CL={}
for m in re.finditer(r'(?m)^  assign (.+?) = (.*);$',s):
    l,r=m[1],m[2]
    if l.startswith('{'):
        ws=TOK.findall(l)
        for w in ws: CON[w]=l
        CL[l]=r
    else: A[l if l.endswith(' ') or l.startswith('_') else l+' ']=r
leaf=lambda t:(t.startswith(P+'g_fsram.rd[') or t.startswith(P+'check_row['))
memo={}
def dep(t):
    if t in memo: return memo[t]
    memo[t]=False
    if leaf(t): memo[t]=True; return True
    r=A.get(t)
    if r is None and t in CON: r=CL[CON[t]]
    v=False
    if r is not None:
        for x in TOK.findall(r+' '):
            if dep(x): v=True
    memo[t]=v; return v
root=P+'row_bad '
assert root in A,'row_bad'
C=set();L=set();conc=set();st=[root]
while st:
    t=st.pop()
    if t in C: continue
    if leaf(t): L.add(t); continue
    if not dep(t): continue
    C.add(t)
    r=A.get(t)
    if r is None:
        conc.add(CON[t]); r=CL[CON[t]]
        for w in TOK.findall(CON[t]): C.add(w)
    st+=TOK.findall(r+' ')
L=sorted(L,key=lambda x:(('check_row' in x),int(re.search(r'\[(\d+)\]',x)[1])))
idx={t:i for i,t in enumerate(L)}
def nm(t): return ('\\'+t[1:-1]+'__hcbr ') if t.startswith('\\') else '_hcbr'+t
def sub(r):
    def f(m):
        t=m[0]
        if t in idx:
            if mut=='M5' and 'check_row' in t: return t
            if mut=='MUX' and 'check_row' in t: return '(_hcbr_mut==5 ? %s: _hcbr_l[%d]) '%(t,idx[t])
            return '_hcbr_l[%d] '%idx[t]
        return nm(t) if t in C else t
    return TOK.sub(f,r+' ')
out=(["  integer _hcbr_mut=0; initial if(!$value$plusargs(\"mut=%d\",_hcbr_mut)) _hcbr_mut=0;"] if mut=='MUX' else [])+['  // HBM-CORES-B CF2 (option B, 11-10): u_flow read and check_row registered; row_bad clone compares one edge later.',
 '  reg [%d:0] _hcbr_l;'%(len(L)-1)]
wires=sorted(C)
for w in wires:
    assert not re.search(r'(?m)^\s*(wire|reg)\s*\[[^\]]*\]\s*'+re.escape(w.strip())+r'\s*;',s),('multi-bit clone',w)
for w in wires: out.append('  wire %s;'%nm(w))
for w in wires:
    if w in A: out.append('  assign %s = %s;'%(nm(w),sub(A[w])))
for l in sorted(conc):
    out.append('  assign %s = %s;'%(TOK.sub(lambda m:nm(m[0]),l+' '),sub(CL[l])))
out.append('  always @(posedge clk_program) _hcbr_l <= { %s };'%', '.join(reversed([t for t in L])))
ck=P+'checking '
out+=[
 '  always @(posedge clk_program, negedge \\u_body.g_q3.n_u_fj.u_fj.u.rst_q )',
 '    if (!\\u_body.g_q3.n_u_fj.u_fj.u.rst_q ) begin _hcbr_ck <= 1\'h0; _hcbr_last <= 1\'h0; _hcbr_clr <= 1\'h0; end',
 '    else begin _hcbr_ck <= %s; _hcbr_last <= %s&& _027185_; _hcbr_clr <= _027215_ && !_027256_; end'%(ck,ck)]
block='\n'.join(out)+'\n'
def rep(a,b,n=1):
    global s
    assert s.count(a)==n,(a,s.count(a)); s=s.replace(a,b)
# F block
a='_hcb_fin <= %s && _027185_; _hcb_bad <= _027232_;'%ck.rstrip(' ') if False else None
m=re.search(r'_hcb_fin <= (\\\S+ ) && _027185_; _hcb_bad <= _027232_;',s); assert m
rowc=nm(root)
fin='%s&& _027185_'%ck if mut=='M1' else ('(_hcbr_mut==1 ? %s&& _027185_ : _hcbr_last)'%ck if mut=='MUX' else '_hcbr_last')
bad='%s'%(P+'check_bad ') if mut=='M2' else ('%s|| (_hcbr_mut!=2 && %s)'%(P+'check_bad ',rowc) if mut=='MUX' else '%s|| %s'%(P+'check_bad ',rowc))
s=s.replace(m[0],'_hcb_fin <= %s; _hcb_bad <= %s;'%(fin,bad))
m=re.search(r'_hcb_rbd <= (\\\S+ ) && (\\\S+ ) && !\(_027215_ && !_027256_\);',s); assert m
kill="1'b1" if mut=='M3' else ('(_hcbr_mut==3 || (!(_027215_ && !_027256_) && !_hcbr_clr))' if mut=='MUX' else '!(_027215_ && !_027256_) && !_hcbr_clr')
s=s.replace(m[0],'_hcb_rbd <= _hcbr_ck && %s && %s;'%(rowc,kill))
# reject gates
gates=['_027237_','_027249_','_027258_','_027264_','_027273_','_027284_']
if mut!='M4':
    for g in gates:
        m=re.search(r'(?m)^  assign %s = (.*?)\|\| %s;$'%(g,re.escape(ck)),s); assert m,g
        s=s.replace(m[0],'  assign %s = %s|| %s|| %s;'%(g,m[1],ck,'(_hcbr_ck && _hcbr_mut!=4)' if mut=='MUX' else '_hcbr_ck'))
# init_busy: visible +1
ib=P+'init_busy '
ibq=P+'init_busy_q '
n0=s.count(ib)
rep('  reg %s;'%ib,'  wire %s;\n  reg %s;\n  reg _hcbr_ck, _hcbr_last, _hcbr_clr;'%(ib,ibq))
for pat in [r'if \(!\\u_body\.g_q3\.n_u_fj\.u_fj\.u\.rst_q \) '+re.escape(ib)+r' <= 1\'h0;',r'else '+re.escape(ib)+r' <= _020096_;']:
    m=re.search(pat,s); assert m,pat; s=s.replace(m[0],m[0].replace(ib,ibq))
for g in ['_036457_','_036458_']:
    m=re.search(r'(?m)^  assign %s = .*$'%g,s); assert m,g; s=s.replace(m[0],m[0].replace(ib,ibq))
left=[l.strip()[:90] for l in s.split('\n') if ib in l]
print('init_busy remaining refs',len(left),[x.replace(P,'P.')[:70] for x in left])
tag='  reg _hcb_fin, _hcb_bad, _hcb_f0;\n'
rep(tag,block+'  assign %s = %s|| _hcbr_ck;\n'%(ib,ibq)+'  wire _hcbr_p1 = (_027215_ && !_027256_) && (%s|| _hcbr_ck);\n  wire _hcbr_p2 = _hcbr_clr && _hcbr_ck;\n'%ck+tag)
if mut=='MUX':   # M6: core fault U.fault delayed one more edge (2 after program_fault): must fail the bench
    UF='\\u_body.g_q3.n_u_fj.u_fj.u.fault '
    m=re.search(r'else '+re.escape(UF)+r' <= (_\d+_);',s); assert m,'U.fault reg'
    s=s.replace(m[0],'else %s <= (_hcbr_mut==6) ? _hcbr_fd : %s;'%(UF,m[1]))
    rep('  reg _hcbr_ck, _hcbr_last, _hcbr_clr;','  reg _hcbr_ck, _hcbr_last, _hcbr_clr;\n  reg _hcbr_fd; always @(posedge clk_program) _hcbr_fd <= %s;'%m[1])
open(dst,'w').write(s)
print('leaves',len(L),'rd',sum('rd[' in x for x in L),'row',sum('check_row' in x for x in L),'clones',len(C),'concat',len(conc),'mut',mut or '-')
