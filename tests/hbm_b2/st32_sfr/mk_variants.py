"""old master -> module-prefixed copy; new master -> mutants (DIE-HBM-61/RTL-ST32)."""
import re,sys
old,new,out=sys.argv[1:4]
s=open(old).read()
mods=re.findall(r'^module (\\?\S+)',s,re.M)
for m in sorted(mods,key=len,reverse=True):
    nm=('\\old_'+m[1:]) if m.startswith('\\') else 'old_'+m
    s=s.replace(m+' ',nm+' ').replace(m+'(',nm+'(')
open(out+'/old.v','w').write(s)
n=open(new).read(); open(out+'/new.v','w').write(n)
def body_bypass(text,pat):
    # replace the body of every module whose name matches pat with q = d (face register removed)
    def f(mm):
        hdr=mm.group(1)
        if not re.search(pat,hdr.split('(')[0]): return mm.group(0)
        decl=[l for l in mm.group(2).splitlines() if re.match(r'\s*(input|output)\b',l)]
        decl=[l.replace('output reg','output').replace('reg ','') for l in decl]
        return hdr+'\n'+'\n'.join(decl)+'\n  assign q = d;\nendmodule'
    r,k=re.subn(r'(module [^\n]*\n)(.*?)endmodule',f,text,flags=re.S); return r
muts={}
muts['mut_nf_nodelay']=body_bypass(n,r'u_ff')
muts['mut_fi_bypass']=body_bypass(n,r'u_fi')
# word swap: data words 0 and 2 trade places at the input face (re-association changes rounding)
assert n.count('.d({ valid_in, data }),')==1
muts['mut_word_swap']=n.replace('.d({ valid_in, data }),','.d({ valid_in, data[1023:96], data[31:0], data[63:32], data[95:64] }),')
# node fault order: node_fault[0] <-> node_fault[16] at the face register output
assert n.count('.q(node_fault),')==1
muts['mut_nf_order']=n.replace('.q(node_fault),','.q({ node_fault[30:17], node_fault[0], node_fault[15:1], node_fault[16] }),')
# node-fault balance: level-1 faults leave one edge early (last stage of the level-1 delay chain skipped)
o='else q[15:0] <= \\g_l[1].r [31:16];'
assert n.count(o)==1,o
muts['mut_nf_balance']=n.replace(o,'else q[15:0] <= \\g_l[1].r [47:32];')
for k,v in muts.items():
    assert v!=n,k
    open(f'{out}/{k}.v','w').write(v)
print('mods',len(mods),'mutants',list(muts))
