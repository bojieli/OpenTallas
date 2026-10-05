"""Actual site format capability and immutable shared word-depth accounting."""
from fractions import Fraction

Q_FRAME=Fraction('64825.596')
BF_FRAME=Fraction('142971.9984')
FORMATS={'fp4','fp8','bf16','raw'}

def rtl_bf_sites(np,nbf):
    if not 0<nbf<=np:raise ValueError('source NBF')
    return {i*np//nbf for i in range(nbf)}

def source_formats(kind):
    # Source capability is separate from qualified physical area/clock proof.
    normalized={'BF_DUAL':'dual','Q_ONLY':'q'}.get(kind,kind)
    if normalized=='dual':return {'fp4','fp8','bf16'}
    if normalized=='q':return {'fp4','fp8','raw'}
    if normalized=='BF':return {'bf16'}
    raise ValueError('source site class')

def validate_site_ids(compiled,nbf):
    np=compiled['compiled_NP'];all_sites=set(range(np))
    names=['BF_DUAL_site_IDs','Q_ONLY_site_IDs','weight_active_site_IDs','padding_site_IDs']
    sets={}
    for name in names:
        values=compiled[name]
        if len(values)!=len(set(values)) or any(not isinstance(v,int) or isinstance(v,bool) for v in values):
            raise ValueError('duplicate or noninteger explicit site ID')
        sets[name]=set(values)
    bf=sets['BF_DUAL_site_IDs'];q=sets['Q_ONLY_site_IDs']
    active=sets['weight_active_site_IDs'];padding=sets['padding_site_IDs']
    if bf!=rtl_bf_sites(np,nbf) or q!=all_sites-bf:
        raise ValueError('explicit site classes disagree with source BF predicate')
    if active & padding or active | padding != all_sites:
        raise ValueError('active and padding must cover compiled array exactly once')
    return {'source_compatible':True,'BF_DUAL_pairs':len(bf),'Q_ONLY_pairs':len(q),
            'padding_pairs':len(padding),'physical4096_macros':4*np,
            'physical_frame_um2':float(len(q)*Q_FRAME+len(bf)*BF_FRAME),
            'padding_is_occupancy_not_third_physical_class':True,
            'shared_storage_capacity_must_still_bind_word_intervals':True,
            'physical_or_SSFF_qualification_transferred':False}

def validate(sites,np,nbf):
    if len(sites)!=np or {s['pair'] for s in sites}!=set(range(np)):
        raise ValueError('every compiled physical pair must be declared exactly once')
    bfmask=rtl_bf_sites(np,nbf);frames=Fraction(0);resident={};bf_work=set();q_work=set();proof_gaps=[]
    for s in sites:
        p=s['pair'];kind={'BF_DUAL':'dual','Q_ONLY':'q'}.get(s['physical_class'],s['physical_class'])
        if kind not in ('q','BF','dual'):raise ValueError('source-matched physical class')
        if (kind in ('BF','dual')) != (p in bfmask):
            raise ValueError('physical class disagrees with source is_bf mask')
        frame=Q_FRAME if kind=='q' else BF_FRAME
        allowed={'fp4','fp8','raw'} if kind=='q' else {'bf16'}
        if kind=='dual':
            proof=s.get('dual_compute_proof',{})
            if not proof.get('whole_element_hard_abstract_available') or not proof.get('rtl_source_receipts') or not proof.get('abstract_source_receipts'):
                raise ValueError('q_on_BF requires actual source-matched dual-compute abstract proof')
            if proof.get('RTL_params',{}).get('BF16')!=1 or proof.get('RTL_params',{}).get('NB')!=2 or proof.get('RTL_params',{}).get('PP')!=1:
                raise ValueError('dual provider parameter mismatch')
            if set(proof['included_formats'])!={'fp4','fp8','bf16'}:
                raise ValueError('incomplete dual-compute abstract format coverage')
            area=Fraction(str(proof['outline_um'][0]))*Fraction(str(proof['outline_um'][1]))
            # A smaller actual source abstract is a separate owner reprice; never
            # quietly substitute it into current catalogue reservation here.
            if area<BF_FRAME:raise ValueError('dual abstract smaller than current frame requires explicit reprice')
            frame=area;allowed={'fp4','fp8','bf16'}
        intervals={0:[],1:[]};formats=set()
        for word in s['resident_words']:
            fmt=word['format'];slot=word['logical_slot'];a,b=word['begin'],word['end']
            if fmt not in FORMATS or fmt not in allowed:
                raise ValueError('q_on_BF or BF_on_q provider-format fault')
            if slot not in (0,1) or any(not isinstance(x,int) or isinstance(x,bool) for x in (a,b)) or not 0<=a<b<=8192:
                raise ValueError('finite paired physical4096 word interval')
            if not word.get('owner') or not word.get('source_receipts'):
                raise ValueError('resident immutable word identity unbound')
            intervals[slot].append((a,b,fmt));formats.add(fmt)
        count=0
        for ranges in intervals.values():
            ranges.sort()
            for left,right in zip(ranges,ranges[1:]):
                if right[0]<left[1]:raise ValueError('shared q/BF resident word overlap; no second capacity')
            count+=sum(b-a for a,b,_ in ranges)
        if formats&{'fp4','fp8'}:q_work.add(p)
        if 'bf16' in formats:bf_work.add(p)
        resident[p]={'formats':sorted(formats),'occupied_words_both_slots':count,'unused_words_both_slots':16384-count}
        frames+=frame
    return {'compiled_pairs':np,'physical4096_macros':4*np,'physical_frame_um2':float(frames),
            'q_work_sites':len(q_work),'BF_work_sites':len(bf_work),'mixed_work_sites':len(q_work&bf_work),
            'unique_resident_work_sites':len(q_work|bf_work),'resident_sites':resident,
            'storage_capacity_counted_once':True,'physical_or_SSFF_qualification_transferred':False}
