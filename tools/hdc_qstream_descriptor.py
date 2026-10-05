"""Explicit reduced128/full160 QE fetch ABI. All addresses are unsigned."""
FIELDS = ('hbm','rom','n','fp4','pred','ind','ibase','istride','grp')
WIDTHS = {'reduced':(24,24,16,1,2,1,24,24,8),
          'full_shape':(30,30,21,1,2,1,30,30,8)}
BITS = {'reduced':128, 'full_shape':160}

def encode(entry, profile='reduced'):
    widths=WIDTHS[profile]; out=0; shift=0
    for field,width in zip(FIELDS,widths):
        value=int(entry[field])
        if not 0 <= value < 1<<width:
            raise ValueError(f'{profile} {field}={value} exceeds unsigned {width}-bit field')
        out |= value << shift; shift += width
    return out

def decode(word, profile='reduced'):
    if not 0 <= word < 1<<sum(WIDTHS[profile]):
        raise ValueError('negative word or nonzero reserved bits')
    result={}; shift=0
    for field,width in zip(FIELDS,WIDTHS[profile]):
        result[field]=(word>>shift)&((1<<width)-1); shift+=width
    return result

def encode_list(entries, profile='reduced'):
    return [encode(e,profile) for e in [*entries,dict.fromkeys(FIELDS,0)]]
