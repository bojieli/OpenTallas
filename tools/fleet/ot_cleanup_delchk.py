import sys,glob,os
refs=[l.rstrip('\n').split('\t') for l in open('/tmp/refs.tsv')]
refp=[r[0] for r in refs]
canon=lambda p:p.replace('/srv/opentallas-scratch/claude','/srv/opentallas-scratch2/claude').replace('/srv/opentallas-scratch3/claude','/srv/opentallas-scratch2/claude')
refp=[(canon(p),s) for p,s in refs]
hits=0
for f in glob.glob(os.path.expanduser('~/.local/state/ot-autoclean-auto/manifests/AUTOCLEAN-auto-*.tsv')):
    if os.path.getmtime(f)<float(sys.argv[1]): continue
    for l in open(f):
        x=l.rstrip('\n').split('\t')
        if len(x)<6 or x[3]!='DELETED': continue
        d=canon(x[5]).rstrip('/')
        for p,s in refp:
            if p==d or p.startswith(d+'/') or d.startswith(p+'/'):
                print('HIT deleted',d,'<- ref',p,'from',s); hits+=1; break
print('hits',hits)
