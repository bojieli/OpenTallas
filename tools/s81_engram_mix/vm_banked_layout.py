"""Compiler storage ABI v1 for native MIX4/VM: payload descriptor bit18.

H/output rows retain HC's four-copy interleaved layout. K/W/V are external input
operands packed into otherwise reserved bankword bands; no DUT result is supplied.
"""
KW_BASE=8192
V_BASE=13824
DESC_ROW=14500
ABI_FLAG=1<<18

def bank(row):return (row&31)^(((row>>5)&7)<<2)
def operand_row(hbase,base,beat,lane,vstream=False):
    assert hbase%4==0 and base%32==0 and 0<=beat<160 and 0<=lane<20
    hhi=bank(hbase+4*beat)>>2
    addr=(base>>5)+(beat//8 if vstream else beat)
    assert addr<512
    bh=(hhi+1+(0 if vstream else lane>>2))&7
    target=(bh<<2)|(lane&3)
    return (addr<<5)|(target^((addr&7)<<2))
def pack(words):
    return sum(int(v)<<(32*i) for i,v in enumerate(words))
def operand_rows(key,wgt,value,hbase=0,kbase=KW_BASE,vbase=V_BASE):
    # Inputs are already FP32 bit patterns, never float-converted/recomputed here.
    import numpy as np
    key=np.asarray(key,dtype=np.uint32).reshape(4,5120)
    wgt=np.asarray(wgt,dtype=np.uint32).reshape(4,5120)
    value=np.asarray(value,dtype=np.uint32).reshape(5120)
    rows={}
    def put(r,data):
        assert r not in rows,('operand alias',r)
        rows[r]=pack(data)
    for b in range(160):
        for q in range(4):
            for half in range(2):
                lo=32*b+16*half
                put(operand_row(hbase,kbase,b,5*q+1+half),key[q,lo:lo+16])
                put(operand_row(hbase,kbase,b,5*q+3+half),wgt[q,lo:lo+16])
        for half in range(2):
            lo=32*b+16*half
            put(operand_row(hbase,vbase,b,1+half,True),value[lo:lo+16])
    assert len(rows)==2880
    assert not set(rows).intersection(range(hbase,hbase+640))
    return rows
