"""Exact row footprints of the existing SU descriptors; not a native allocation.

Descriptor/read ordering follows ot_s81_su_hctl and ot_s81_su_core. Addresses
are the fixture's current ones and must be rebound to actual producers before
any native compiler can use them. Expected row data is never an owned producer.
"""

def footprint(kind, arg, vm, shape, expected):
    base = arg & 16383
    descriptor = vm[base]
    words = [(descriptor >> (32*i)) & 0xffffffff for i in range(16)]
    obase, ibase, count = words[:3]
    np = 5 if kind in ('KV','SO','QR','CN','IK') else 1 + (shape['SM_H']+15)//16 if kind=='SE' else 1
    nrows = {'QN':80, 'KV':32, 'QB':count*shape['QB_NB']*2,
             'SW':count*2*shape['SW_W']//16,
             'SE':count*shape['SM_H']*shape['SM_LPH']//16,
             'SO':512*shape['SM_H']//16, 'GQ':80,'GK':32,
             'RA':count,'RB':2*count,'QR':4*count,'RW':count,'CN':32,'IK':32}[kind]
    if kind=='QR':
        addresses=[ibase+32*(i//4)+28+i%4 for i in range(nrows)]
    elif kind=='RB':
        addresses=[ibase+i//2+(count if i%2 else 0) for i in range(nrows)]
    else:
        addresses=list(range(ibase,ibase+nrows))
    width = 2 if kind in ('RB','QR') else 1 if kind in ('RA','RW') else shape['S_RD']
    operand_groups=[addresses[i:i+width] for i in range(0,len(addresses),width)]
    if kind in ('GQ','GK'):
        outrows=[]
    elif kind=='QR':
        outrows=[obase+32*(i//4)+28+i%4 for i in range(nrows)]
    elif kind=='RW':
        outrows=[obase]
    elif kind=='CN':
        outrows=list(range(obase,obase+32))+list(range(words[2],words[2]+16))
        if len(set(outrows))!=48: raise ValueError('CN raw/norm/qdq outputs overlap')
    elif kind=='IK':
        outrows=list(range(obase,obase+8))
    else:
        # All expected output rows of this job are contiguous from its base.
        # The fixture records row count separately; caller supplies only this job.
        outrows=sorted(expected)
    masks={str(row):0xffff for row in outrows}
    if kind=='RW': masks[str(obase)]=((1<<words[5])-1)<<words[4]
    # The last norm tile explicitly writes all remaining exponent-row words
    # (including reserved zero padding), so the aggregate final row mask is
    # ffff for QN/KV as well. Individual partial events need the RTL trace.
    return dict(kind=kind,arg=arg,descriptor_row=base,descriptor_words=words,
                descriptor_parameter_rows=list(range(base,base+np)),
                operand_format='16x32-bit words per512-bit VM row (float32 except RW id row)',
                operand_rows=addresses,operand_groups=operand_groups,
                output_rows=outrows,output_final_word_masks=masks, output_write_events='must use actual RTL trace: exponent rows have multiple masked writes',
                output_format='descriptor-dependent FP8 codes/UE8M0 exponents/packed BF16 or FP32',
                native_producer_bound=False,native_allocation=False,
                source_contract='ot_s81_su_core rows_in/oaddr and hierarchical hctl RB/QR pairs; actual per-write events require trace',
                required='bind actual field/SVC/selector/constant producers and true per-write masks/service edges')
