"""Qwen r25 TOKEN18 host ABI and embedding layout. Explicit new program path.

This does not bind DS full73/PCWB modules or provide a complete Qwen kernel list.
Use one launch per layer/head after those entry kernels have passed their gates.
"""
VOCAB=151936
D=4096

def checked(value,limit,name):
    if type(value) is not int or not 0<=value<limit: raise ValueError(name)
    return value

def doorbell(token,pos,job,generation,*,valid=1,cmd_we=0,cmd_addr=0,cmd_wdata=0):
    checked(token,VOCAB,'token');checked(pos,1<<20,'position')
    fields=((cmd_we,1),(cmd_addr,8),(cmd_wdata,64),(valid,1),(token,18),(pos,20),(job,32),(generation,4))
    result=0;shift=0
    for value,width in fields:
        checked(value,1<<width,'tuple field');result|=value<<shift;shift+=width
    assert shift==148
    return result

def loader_pair(south,north):
    checked(south,1<<148,'south tuple');checked(north,1<<148,'north tuple')
    return south | north<<148

def embedding_addresses(token,weight_base,scale_base):
    checked(token,VOCAB,'embedding token')
    checked(weight_base,1<<64,'weight base');checked(scale_base,1<<64,'scale base')
    row=weight_base+token*D;scale=scale_base+token*2
    checked(row+D-1,1<<64,'weight extent');checked(scale+1,1<<64,'scale extent')
    return row,scale

def completion(token,status):
    checked(status,16,'completion status')
    if status: raise ValueError('processor completion failed: '+str(status))
    return checked(token,VOCAB,'completion token')

def launch_list(layer_entries,head_entry,*,sm_mask=65535):
    if len(layer_entries)!=36: raise ValueError('Qwen has 36 layers')
    checked(sm_mask,1<<16,'SM mask')
    if not sm_mask: raise ValueError('empty SM mask')
    words=[]
    for pc in list(layer_entries)+[head_entry]:
        checked(pc,1<<32,'entry PC');words.append((1<<60)|(sm_mask<<44)|pc)
    words.append(2<<60)
    assert len(words)<=256
    return words

if __name__=='__main__':
    # Exhaustive index/packing audit; RTL gate is separate.
    for t in range(VOCAB):
        packed=doorbell(t,(1<<20)-1,0xfedcba98,13)
        assert (packed>>74)&((1<<18)-1)==t
        assert (packed>>92)&((1<<20)-1)==(1<<20)-1
        assert (packed>>112)&0xffffffff==0xfedcba98
        assert (packed>>144)&15==13
        pair=loader_pair(packed,packed)
        assert pair&((1<<148)-1)==packed and pair>>148==packed
        assert embedding_addresses(t,1<<32,2<<32)==((1<<32)+t*4096,(2<<32)+t*2)
        assert completion(t,0)==t
    assert len(launch_list([i*64 for i in range(36)],4096))==38
    for bad in (-1,VOCAB,1<<18):
        try: embedding_addresses(bad,0,0)
        except ValueError: pass
        else: raise AssertionError('invalid token accepted')
    print('QWEN_PROGRAM18_PASS exhaustive_tokens=151936 tuple_bits=148 command_words=38 embedding_int8_stride=4096 scale_stride=2')
