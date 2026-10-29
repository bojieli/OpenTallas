"""Actual two-dimensional std-cell body occupancy for HEAD infrastructure.

Clock-node row phases need not be identical. A y-key interval map misses bodies
on nearby fractional rows; this index checks full XY intersections explicitly.
"""
from collections import defaultdict
import math


class Bodies:
    def __init__(self, height=.27, bucket=2.0):
        self.height=height
        self.bucket=bucket
        self.bins=defaultdict(list)
        self.next_id=0

    def keys(self,x0,x1,y):
        for i in range(math.floor(x0/self.bucket),math.floor(x1/self.bucket)+1):
            for j in range(math.floor(y/self.bucket),math.floor((y+self.height)/self.bucket)+1):
                yield i,j

    def add(self,x0,x1,y):
        entry=(self.next_id,x0,x1,y,y+self.height)
        self.next_id+=1
        for key in self.keys(x0,x1,y):self.bins[key].append(entry)

    def free(self,x0,x1,y):
        seen=set()
        for key in self.keys(x0,x1,y):
            for ident,a,b,c,d in self.bins.get(key,()):
                if ident in seen:continue
                seen.add(ident)
                if min(x1,b)>max(x0,a)+1e-6 and min(y+self.height,d)>max(y,c)+1e-6:return False
        return True


def row_orientation(y, origin=0.0, height=.27):
    row=round((y-origin)/height)
    if abs(origin+row*height-y)>1e-6:
        raise ValueError(f'cell y={y} is not on native0.27um row phase')
    return 'MX' if row%2 else 'R0'
