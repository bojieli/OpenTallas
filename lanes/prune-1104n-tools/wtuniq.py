#!/usr/bin/env python3
# PRUNE-1104N "none uniquely counted": every sign-off the counter cache names in worktree <name> must be tracked and the same blob on the hub main. usage: wtuniq.py cachepaths.txt ; lines: name<TAB>relpath
import subprocess as sp,sys,collections
R='/srv/opentallas-scratch2/claude/wt/'; res=collections.defaultdict(lambda:[0,0,[]])
for l in open(sys.argv[1]):
    n,rel=l.rstrip('\n').split('\t'); d=R+n
    def g(*a): return sp.run(['git','-C',d]+list(a),capture_output=True,text=True).stdout.strip()
    h=g('hash-object',rel); m=g('rev-parse','origin/main:'+rel)
    r=res[n]
    if h and h==m: r[0]+=1
    else: r[1]+=1; r[2].append(rel+(' main-absent' if m.startswith('origin/main') or not m else ' main-differs'))
for n,r in res.items():
    print(n,'same-on-main',r[0],'unique',r[1],r[2][:8])
print('main at',sp.run(['git','-C',R+n,'log','-1','--format=%h %ad','--date=format:%m-%d %H:%M','origin/main'],capture_output=True,text=True).stdout.strip())
