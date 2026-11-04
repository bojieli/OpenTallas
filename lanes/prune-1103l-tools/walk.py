#!/usr/bin/env python3
# PRUNE-1103L read-only rollup walk. Output TSV: depth path kB newest_epoch signed keep files
# Rows for every dir at depth<=MAXD below root, plus every attempt_N dir and every git worktree root.
import os,sys,re,time
root,out=sys.argv[1],sys.argv[2]; MAXD=int(sys.argv[3]) if len(sys.argv)>3 else 4
SIG=re.compile(r'"verdict"\s*:\s*"(SIGNED|LOCAL_PASS_NEEDS_PARENT)"')
dev=os.lstat(root).st_dev
of=open(out+'.tmp','w'); sf=open(out+'.signed.tmp','w'); lf=open(out+'.links.tmp','w')
def walk(d,depth):
    kb=0;nw=0;sig=0;keep=0;files=0;git=0
    try:
        st=os.lstat(d); nw=st.st_mtime; kb=st.st_blocks//2
        it=list(os.scandir(d))
    except OSError:
        return kb,nw,sig,keep,files
    for e in it:
        try: st=e.stat(follow_symlinks=False)
        except OSError: continue
        if st.st_dev!=dev: continue
        if e.is_dir(follow_symlinks=False):
            r=walk(e.path,depth+1)
            kb+=r[0];nw=max(nw,r[1]);sig+=r[2];keep+=r[3];files+=r[4]
        else:
            kb+=st.st_blocks//2;nw=max(nw,st.st_mtime);files+=1
            if e.is_symlink():
                try: lf.write(e.path+'\t'+os.path.normpath(os.path.join(d,os.readlink(e.path)))+'\n')
                except OSError: pass
            if e.name=='.keep': keep+=1
            if e.name=='.git': git=1
            if e.name=='signoff.json' or e.name.endswith('.signoff.json'):
                try:
                    if SIG.search(open(e.path,errors='replace').read()):
                        sig+=1; sf.write(e.path+'\n')
                except OSError:
                    sig+=1; sf.write(e.path+'\n')
    if e_is_row(d,depth,git):
        of.write(f"{depth}\t{d}\t{kb}\t{int(nw)}\t{sig}\t{keep}\t{files}\t{git}\n")
    return kb,nw,sig,keep,files
ATT=re.compile(r'/attempt_\d+$')
def e_is_row(d,depth,git): return depth<=MAXD or git or ATT.search(d)
sys.setrecursionlimit(10000)
walk(root,0); of.close(); sf.close(); lf.close()
os.rename(out+'.tmp',out); os.rename(out+'.signed.tmp',out+'.signed'); os.rename(out+'.links.tmp',out+'.links')
