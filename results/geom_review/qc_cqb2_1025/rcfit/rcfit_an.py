import glob,statistics as S,sys,os
d=sys.argv[1]
def ld(f):
    ck={};hs={};w=None
    for l in open(f):
        t=l.rstrip('\n').split('\t')
        if t[0]=='CK' and t[2]: ck[t[1]]=float(t[2])
        elif t[0]=='HS' and t[2]: hs[t[1]]=float(t[2])
        elif t[0]=='WNS': w=t[1:]
    return ck,hs,w
for c in ('tt','ff'):
    rc,rh,rw=ld(f'{d}/rcx_{c}.tsv')
    print(c,'RCX wns/nviol',rw, 'ck mean %.1f'%S.mean(rc.values()))
    for f in sorted(glob.glob(f'{d}/est_*_{c}.tsv')):
        ec,eh,ew=ld(f); e=[ec[k]-rc[k] for k in rc if k in ec]
        # hold slack error on endpoints with RCX hold slack < 30
        h=[eh[k]-rh[k] for k in rh if k in eh and rh[k]<30]
        print('  %-22s ck err mean %+.1f min %+.1f max %+.1f sd %.1f | hold err(est-rcx, rcx<30) mean %+.1f min %+.1f max %+.1f n%d | wns %s'%(os.path.basename(f),S.mean(e),min(e),max(e),S.pstdev(e),S.mean(h),min(h),max(h),len(h),ew))
