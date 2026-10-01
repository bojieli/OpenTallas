#!/usr/bin/env python3
"""Actual-command software CROM wave/catalog compiler; no payload/RTL changes."""
import argparse,collections,gzip,hashlib,json
from pathlib import Path
import w11_dsrom_crom_demand as D
I=D.I
WORD_BITS=274;WORD_BYTES=35

def encode_fill(selectors,mask,operand,group):
    if len(selectors)!=16 or not 0<=mask<2**16 or operand not in (0,1) or not 0<=group<64:
        raise ValueError('fill field range')
    w=mask<<128 | operand<<144 | group<<145
    for lane,s in enumerate(selectors):
        if not isinstance(s,int) or not 0<=s<135:raise ValueError('selector out of landing range')
        if not mask>>lane&1 and s:raise ValueError('masked selector must be canonical zero')
        w|=s<<(8*lane)
    return w

def decode_fill(w):
    if not 0<=w<2**WORD_BITS or w>>151:raise ValueError('control padding/range')
    fields={'selectors':[(w>>(8*i))&255 for i in range(16)],'mask':(w>>128)&65535,
            'operand':(w>>144)&1,'group':(w>>145)&63}
    for lane,s in enumerate(fields['selectors']):
        if s>=135 or (not fields['mask']>>lane&1 and s):raise ValueError('invalid selector/mask')
    return fields

def verify_waves(waves,uses):
    """Consumer-side replay from control bits, independent of compiler selectors."""
    wanted={(op,lane):a for op,lane,a in uses};got={}
    if len(wanted)!=len(uses):raise ValueError('duplicate expected destination')
    for wave in waves:
        landing=decode_requests(wave['requests'])
        for w in wave['fills']:
            f=decode_fill(w)
            for lane,s in enumerate(f['selectors']):
                if f['mask']>>lane&1:
                    if s>=len(landing):raise ValueError('selector beyond current wave')
                    key=(f['operand'],f['group']*16+lane)
                    if key in got:raise ValueError('duplicate destination write')
                    got[key]=landing[s]
    if got!=wanted:raise ValueError('coefficient use missing or aliased')
    return True

def encode_requests(addresses):
    cells={}
    for a in addresses:
        if not 0<=a<549760:raise ValueError('logical address out of chosen home')
        c,slot=divmod(a,3);row,bank=divmod(c,45)
        if bank in cells and cells[bank][0]!=row:raise ValueError('two rows in one bank wave')
        old=cells.get(bank,(row,0));cells[bank]=(row,old[1]|1<<slot)
    bits=0
    for bank,(row,mask) in cells.items():bits|=(row|1<<12|mask<<13)<<(16*bank)
    return [(bits>>(WORD_BITS*i))&((1<<WORD_BITS)-1) for i in range(3)]

def decode_requests(words):
    if len(words)!=3 or any(not 0<=w<2**WORD_BITS for w in words):raise ValueError('request word range')
    bits=sum(w<<(WORD_BITS*i) for i,w in enumerate(words))
    if bits>>720:raise ValueError('request padding')
    values=[]
    for bank in range(45):
        field=(bits>>(16*bank))&65535;row=field&4095;valid=(field>>12)&1;mask=field>>13
        if not valid:
            if field:raise ValueError('invalid bank fields not canonical')
            continue
        if not mask or row>=4073:raise ValueError('invalid bank row/mask')
        for slot in range(3):
            if mask>>slot&1:
                a=(row*45+bank)*3+slot
                if a>=549760:raise ValueError('request outside required words')
                values.append(a)
    return sorted(values)

def bank_waves(addresses):
    bybank=collections.defaultdict(list)
    for c in sorted({a//3 for a in addresses}):bybank[c%45].append(c)
    for idx in range(max(map(len,bybank.values()),default=0)):
        containers={v[idx] for v in bybank.values() if idx<len(v)}
        yield sorted(a for a in addresses if a//3 in containers)

def compile_burst(uses):
    """Use identity=(operand ordinal, live lane, logical source address)."""
    expected={(op,lane):a for op,lane,a in uses}
    if len(expected)!=len(uses):raise ValueError('duplicate destination use')
    delivered={};waves=[]
    for values in bank_waves(set(expected.values())):
        request=encode_requests(values);landing=decode_requests(request)
        if landing!=values or len(landing)>135:raise AssertionError('request/landing mismatch')
        lookup={a:i for i,a in enumerate(landing)};groups=collections.defaultdict(list)
        for (op,lane),a in expected.items():
            if a in lookup:groups[(op,lane//16)].append((lane%16,a))
        fills=[]
        for (op,group),targets in sorted(groups.items()):
            selectors=[0]*16;mask=0
            for lane,a in targets:selectors[lane]=lookup[a];mask|=1<<lane
            word=encode_fill(selectors,mask,op,group);decoded=decode_fill(word)
            if decoded!={'selectors':selectors,'mask':mask,'operand':op,'group':group}:raise AssertionError('fill bit roundtrip')
            for lane in range(16):
                if decoded['mask']>>lane&1:
                    sel=decoded['selectors'][lane]
                    if sel>=len(landing):raise ValueError('selected unavailable landing')
                    key=(decoded['operand'],decoded['group']*16+lane)
                    if key in delivered:raise AssertionError('duplicate accepted destination')
                    delivered[key]=landing[sel]
            fills.append(word)
        waves.append({'requests':request,'fills':fills,'landing':landing})
    if delivered!=expected:raise AssertionError('missing or aliased coefficient destination')
    verify_waves(waves,uses)
    return waves

def build(model_pin,model_path):
    modelraw=D.obj_at(model_pin,model_path) if hasattr(D,'obj_at') else __import__('subprocess').check_output(['git','show',model_pin+':'+model_path],cwd=D.ROOT)
    model=json.loads(modelraw)
    fields=model.get('compiler_control_storage',{})
    if fields.get('fill_selector_bits_per_entry')!=151:raise ValueError('model not corrected151bit selector')
    auditraw=D.obj(D.PREFIX+'.json');audit=json.loads(auditraw)
    demandraw=__import__('subprocess').check_output(['git','show','f4bce8fa0:results/uarch/w11_crom_demand_20261001/demand_v2.json.gz'],cwd=D.ROOT)
    demand=json.loads(gzip.decompress(demandraw));records=demand['ranks'][0]['records']
    requests=bytearray();fills=bytearray();catalog=[];covered=0;mutants=[];high_indices=set();wave_count=0
    encoded=gzip.decompress(D.obj(D.PREFIX+'.rank0.templates.bin.gz'))
    assert hashlib.sha256(encoded).hexdigest()==audit['ranks'][0]['encoded_template_sha256']
    for rec in records:
        f=I.decode(int.from_bytes(encoded[rec['global_instruction']*256:(rec['global_instruction']+1)*256],'little'),full_shape=True)
        command={'layer':rec['layer'],'pc':rec['global_instruction'],'pred':rec['pred'],'operands':rec['operand_demands'],'bursts':[]}
        for bi,coords in enumerate(D.batches(f)):
            uses=[]
            for oi,o in enumerate(rec['operand_demands']):
                for lane,(outer,inner) in enumerate(coords):
                    a=o['base']+outer*o['outer_stride']+(inner//2 if o['half_inner'] else inner)*o['inner_stride']
                    if o['kind']=='unbound_generated':a+=508800+(20480 if rec['layer']==14 else 0)
                    uses.append((oi,lane,a))
            waves=compile_burst(uses);covered+=len(uses);entries=[]
            for wave in waves:
                reqstart=len(requests)//WORD_BYTES;fillstart=len(fills)//WORD_BYTES
                for w in wave['requests']:requests.extend(w.to_bytes(WORD_BYTES,'little'))
                for w in wave['fills']:
                    fills.extend(w.to_bytes(WORD_BYTES,'little'));de=decode_fill(w)
                    for lane,s in enumerate(de['selectors']):
                        if de['mask']>>lane&1 and s>=128:
                            high_indices.add(s)
                            if not any(m['selector']==s for m in mutants):
                                alias=s&127;assert wave['landing'][s]!=wave['landing'][alias]
                                mutants.append({'selector':s,'truncated_7bit_selector':alias,'correct_address':wave['landing'][s],
                                    'aliased_address':wave['landing'][alias],'pc':rec['global_instruction'],'burst':bi,
                                    'operand':de['operand'],'lane':de['group']*16+lane,'mutant_verdict':'FAIL_ALIAS'})
                entries.append({'request_start_word':reqstart,'fill_start_word':fillstart,'fill_words':len(wave['fills']),
                    'landing_values':len(wave['landing']),'landing_policy':'hold unchanged until every masked destination accepts; no release at transmit'})
                wave_count+=1
            command['bursts'].append({'burst':bi,'coefficient_uses':len(uses),'waves':entries})
        catalog.append(command)
    assert len(catalog)==491 and covered==549760 and high_indices==set(range(128,135))
    rank_bindings=[]
    for rank in audit['ranks']:
        raw=gzip.decompress(D.obj(D.PREFIX+f".rank{rank['rank']}.templates.bin.gz"))
        assert hashlib.sha256(raw).hexdigest()==rank['encoded_template_sha256']
        assert demand['ranks'][rank['rank']]['records']==records
        rank_bindings.append({k:rank[k] for k in ['rank','CROM_image_sha256','encoded_template_sha256']})
    actual=model['compiler_control_storage'];assert actual['request_bank_wave_entries']==wave_count and actual['fill_packet_entries']==len(fills)//WORD_BYTES
    metadata={'schema':'opentallas.w11.CROM-control-catalog.v1','model_source':{'commit':model_pin,'path':model_path,'sha256':hashlib.sha256(modelraw).hexdigest()},
        'compiler_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'encoded_program_source':{'commit':D.PIN,'path':D.PREFIX+'.json','sha256':hashlib.sha256(auditraw).hexdigest()},
        'rank_program_image_bindings':rank_bindings,'commands':catalog,'counts':{'commands_per_rank':491,'coefficient_uses_per_rank':covered,
            'bank_waves':wave_count,'request_control_words':len(requests)//WORD_BYTES,'fill_control_words':len(fills)//WORD_BYTES},
        'format':{'control_word_bits':274,'serialized_bytes_per_word':35,'serialized_top6_bits_zero':True,
            'request_bank_fields':'45x16bits:row[11:0],valid[12],lane-mask[15:13]; 3x274 columns, bits720..821zero',
            'fill_fields':'selectors16x8bits[127:0],mask[143:128],operand[144],group[150:145],padding[273:151]zero',
            'landing_order':'sort selected logical addresses decoded from bank requests; compact indices0..134'},
        'old_7bit_mutants':mutants,'old_failure_pin':'785cdfa41','old_model_pin':'bc1ec8b8f','same_coefficient_producer':True,
        'runtime_context_requirement':'rank/imageSHA/layer/PC/burst/epoch and held landing valid; catalog word is not a substitute for live tag/credit checking',
        'generated_product_physical_home':None,'scope':'Exact software control metadata roundtrip only. Generated Engram symbolicappend follows model, source L1 remainsunbound. All predicated command branches enumerated, not a runtime completion proof.',
        'hardware_admission':False,'checkpoint_reads':0,'jobs_launched':0}
    return metadata,bytes(requests),bytes(fills)

def verify_serialized(metadata,requests,fills):
    """Replay persisted words and every lane destination against immutable ISA."""
    expected_counts=metadata['counts'];covered=0
    for data in (requests,fills):
        if len(data)%WORD_BYTES:raise ValueError('serialized word extent')
        if any(data[i+34]&252 for i in range(0,len(data),WORD_BYTES)):raise ValueError('serialized top bits')
    if len(requests)//WORD_BYTES!=expected_counts['request_control_words'] or len(fills)//WORD_BYTES!=expected_counts['fill_control_words']:
        raise ValueError('serialized catalog count')
    encoded=gzip.decompress(D.obj(D.PREFIX+'.rank0.templates.bin.gz'))
    for command in metadata['commands']:
        pc=command['pc'];f=I.decode(int.from_bytes(encoded[pc*256:(pc+1)*256],'little'),full_shape=True)
        coords_list=list(D.batches(f))
        if len(coords_list)!=len(command['bursts']):raise ValueError('burst metadata mismatch')
        for burst,coords in zip(command['bursts'],coords_list):
            uses=[]
            for oi,o in enumerate(command['operands']):
                for lane,(outer,inner) in enumerate(coords):
                    a=o['base']+outer*o['outer_stride']+(inner//2 if o['half_inner'] else inner)*o['inner_stride']
                    if o['kind']=='unbound_generated':a+=508800+(20480 if command['layer']==14 else 0)
                    uses.append((oi,lane,a))
            waves=[]
            for wave in burst['waves']:
                rs=wave['request_start_word'];fs=wave['fill_start_word'];fc=wave['fill_words']
                r=[int.from_bytes(requests[i*WORD_BYTES:(i+1)*WORD_BYTES],'little') for i in range(rs,rs+3)]
                ff=[int.from_bytes(fills[i*WORD_BYTES:(i+1)*WORD_BYTES],'little') for i in range(fs,fs+fc)]
                waves.append({'requests':r,'fills':ff})
            verify_waves(waves,uses);covered+=len(uses)
    if covered!=expected_counts['coefficient_uses_per_rank']:raise ValueError('total coverage mismatch')
    return covered

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--model-pin',required=True);p.add_argument('--model-path',required=True);p.add_argument('--out',required=True,type=Path);a=p.parse_args()
 m,r,f=build(a.model_pin,a.model_path)
 if a.out.exists():raise ValueError('refuse overwrite immutable catalog')
 a.out.mkdir(parents=True)
 for name,b in [('catalog.json',json.dumps(m,sort_keys=True).encode()),('request-controls.bin',r),('fill-controls.bin',f)]:
  (a.out/(name+'.gz')).write_bytes(gzip.compress(b,mtime=0))
 loaded=json.loads(gzip.decompress((a.out/'catalog.json.gz').read_bytes()))
 verify_serialized(loaded,gzip.decompress((a.out/'request-controls.bin.gz').read_bytes()),gzip.decompress((a.out/'fill-controls.bin.gz').read_bytes()))
 print(json.dumps(m['counts']))
