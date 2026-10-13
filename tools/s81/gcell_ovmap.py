#!/usr/bin/env python3
"""Overflow map from a gcell_usage.txt dump (tools/s81/gcell_dump.tcl): per layer and top 1-mm bins.  usage: gcell_ovmap.py gcell_usage.txt [bin_um]"""
import sys,collections
p=sys.argv[1]; B=float(sys.argv[2]) if len(sys.argv)>2 else 1000.
gx=gy=None; bins=collections.Counter(); lay=collections.Counter(); bl=collections.defaultdict(collections.Counter)
for ln in open(p):
    if ln.startswith('GRIDX'): gx=[int(v)/1000 for v in ln.split()[1].split(',')]
    elif ln.startswith('GRIDY'): gy=[int(v)/1000 for v in ln.split()[1].split(',')]
    elif ln.startswith('L '):
        f=ln.split(); L,j=f[1],int(f[2])
        for n,cu in enumerate(f[3:]):
            c,u=(float(v) for v in cu.split('/')); o=max(0,u-c)
            if o: k=(int(gx[4*n]//B),int(gy[j]//B)); bins[k]+=o; lay[L]+=o; bl[k][L]+=o
print('total',sum(lay.values()),dict(lay))
for k,v in bins.most_common(20): print('x%2d-%2d y%2d-%2d mm'%(k[0],k[0]+1,k[1],k[1]+1), int(v), dict(bl[k].most_common(3)))
