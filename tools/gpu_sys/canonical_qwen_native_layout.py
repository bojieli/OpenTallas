"""Compile layout addresses and literal command bits, never numerical outputs.

Static plans feed the ONE controller's retained operand selector. TAKE/SCATTER
are explicitly dynamic: their indices must be read/rangechecked in hardware.
They cannot be completed from a host reading an operand index.
"""
from math import prod
from tools.gpu_sys.canonical_qwen_native_opcode_abi import OPCODES


def need(ok, message):
    if not ok: raise ValueError(message)


def shape(s):
    need(isinstance(s,(list,tuple)) and len(s)<=8
         and all(type(x) is int and x>=0 for x in s) and prod(s)<=128,'finite layout shape')
    return tuple(s)


def coords(index,s):
    out=[]
    for n in reversed(s):index,q=divmod(index,n);out.append(q)
    return tuple(reversed(out))


def linear(c,s):
    out=0
    for x,n in zip(c,s):out=out*n+x
    return out


def compile_layout(op, shapes, attrs, result_shape):
    """Return source-select/index pairs or a source-bound dynamic index program.

    Address compilation uses shapes/attributes only; this API has no data input.
    Selectors0/1/2 address the retained A/B/C buffers. All instruction and result
    identities, captures and visibility are still owned by the physical pump.
    """
    need(op in OPCODES and 26<=OPCODES[op]<=37,'movement opcode')
    ss=tuple(shape(s) for s in shapes);out=shape(result_shape);count=prod(out)
    need(len(ss)<=3,'three retained movement operands')
    plan=dict(opcode=OPCODES[op],result_shape=list(out),words=count,addresses=[],dynamic=None)
    if op=='IOTA':
        need(not ss and len(out)==1,'source IOTA shape')
        plan['addresses']=[(0,i) for i in range(count)]
        return plan
    if op=='CONST':
        need(not ss and attrs.get('dtype') in ('F32','U32','I64'),'typed source literal')
        raw=attrs.get('bits') if attrs['dtype']=='F32' else attrs.get('value')
        literals=raw if isinstance(raw,list) else [raw]
        need(all(type(x) is int for x in literals) and len(literals)==count,'source literal bits/count')
        width=64 if attrs['dtype']=='I64' else 32
        # Emit command immediate bit patterns, never a computed result array.
        plan['literal_words']=[x&((1<<width)-1) for x in literals]
        plan['addresses']=[(0,i) for i in range(count)]
        return plan
    need(ss,'movement requires retained input')
    if op in ('TAKE','SCATTER'):
        axis=attrs['axis']
        need(type(axis) is int and 0<=axis<len(ss[0]),'dynamic source axis')
        need(len(ss)==(2 if op=='TAKE' else 3),'dynamic operand census')
        if op=='TAKE':
            need(out==ss[0][:axis]+ss[1]+ss[0][axis+1:],'TAKE result shape')
        else:
            need(ss[1]==() and out==ss[0] and ss[2]==ss[0][:axis]+ss[0][axis+1:],
                 'scalar SCATTER index/update shape')
        plan['dynamic']=dict(operation=op,index_operand=1,index_bound=ss[0][axis],
                             input_shapes=[list(x) for x in ss],axis=axis,
                             index_must_be_actual_held_I64=True,range_fault_before_capture=True)
        return plan
    if op in ('LOAD','ASSERT','PACKET_COMMIT','RESHAPE'):
        need(len(ss)==1 and prod(ss[0])==count,'unchanged movement extent')
        if op!='RESHAPE':need(ss[0]==out,'unchanged movement shape')
        plan['addresses']=[(0,i) for i in range(count)]
    elif op=='BROADCAST':
        need(len(ss)==1 and len(ss[0])<=len(out),'broadcast rank')
        padded=(1,)*(len(out)-len(ss[0]))+ss[0]
        need(all(a==b or a==1 for a,b in zip(padded,out)),'broadcast shape')
        plan['addresses']=[(0,linear(tuple(0 if n==1 else c for c,n in zip(coords(i,out),padded)),padded))
                           for i in range(count)]
    elif op=='TRANSPOSE':
        axes=tuple(attrs['axes'])
        need(len(ss)==1 and sorted(axes)==list(range(len(ss[0])))
             and out==tuple(ss[0][a] for a in axes),'source transpose permutation')
        for i in range(count):
            c=coords(i,out);original=[0]*len(axes)
            for j,a in enumerate(axes):original[a]=c[j]
            plan['addresses'].append((0,linear(original,ss[0])))
    elif op=='SLICE':
        axis=attrs['axis']
        need(len(ss)==1 and type(axis) is int and 0<=axis<len(ss[0]),'slice axis')
        indices=list(range(*slice(attrs['start'],attrs['stop'],attrs.get('step',1)).indices(ss[0][axis])))
        target=list(ss[0]);target[axis]=len(indices)
        need(tuple(target)==out,'slice result shape')
        for i in range(count):
            c=list(coords(i,out));c[axis]=indices[c[axis]]
            plan['addresses'].append((0,linear(c,ss[0])))
    elif op=='CONCAT':
        axis=attrs.get('axis',0)
        need(type(axis) is int and 0<=axis<len(out)
             and all(len(s)==len(out) for s in ss),'concat axis/rank')
        need(sum(s[axis] for s in ss)==out[axis]
             and all(s[j]==out[j] for s in ss for j in range(len(out)) if j!=axis),'concat shape')
        for i in range(count):
            c=list(coords(i,out));selected=0
            while c[axis]>=ss[selected][axis]:c[axis]-=ss[selected][axis];selected+=1
            plan['addresses'].append((selected,linear(c,ss[selected])))
    else:raise ValueError('unbound movement address opcode')
    need(all(0<=sel<3 and 0<=index<128 for sel,index in plan['addresses']), 'retained address bound')
    return plan
