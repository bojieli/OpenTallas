"""Exact HC sidecar image: real4096x72 ROM, eleven words per op7.

This is a format encoder. Native emission separately requires actual six-kind
measured source profiles, operand producers, and related-clock epoch evidence.
"""
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools/s81_static_control'))
from pq_calendar import viamap

FIELDS=('y_tag','scalar_age','ss_age','done_age')

def encode(commands):
    words=[0]*4096
    seen=set()
    for command in commands:
        op=command['op']
        if type(op)is not int or not 0<=op<128 or op in seen:
            raise ValueError('unique actual command op7 required')
        seen.add(op)
        values=[command[k] for k in FIELDS]
        ages=command['post_ages']
        if not isinstance(ages,list) or len(ages)!=20:
            raise ValueError('twenty literal POST ages required')
        if any(type(v)is not int or not 0<=v<1<<32 for v in values+ages):
            raise ValueError('literal unsigned age/tag32 required')
        bundle=sum(value<<(32*i) for i,value in enumerate(values+ages))
        for i in range(11):words[op*11+i]=(bundle>>(72*i))&((1<<72)-1)
    return words

def image(commands):return viamap(encode(commands))

def validate_issue_edges(commands):
    edges=[c['stream_issue'] for c in commands]
    if any(type(e)is not int or e<0 or e%4 for e in edges):
        raise ValueError('HC command requires fixed stream phase0')
    if edges!=sorted(set(edges)) or any(b-a<24 for a,b in zip(edges,edges[1:])):
        raise ValueError('HC sidecar fixed command separation >=24 stream edges')
    return [dict(stream_issue=e,serial_delivery=(e//4)*3+14)for e in edges]
