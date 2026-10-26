"""Actual GQ covering-window programmes for scattered, runtime-produced PV words.

Only source addresses and explicit leased destination runs enter this compiler.
Collateral sectors are real VM reads/copies, never fixture images. Programmes
remain unqualified until producer/copy/loader/consumer execute together.
"""
from pathlib import Path
import hashlib
from hbm_layer_vehicle import gq_wave_1021 as GW

GQ_SHA256 = '4b244e6ff065b66c6109103cc72c57b691c3b820cbc3d9ecc27f71b3f53c192e'
QUARTERS = ('SW','SE','NW','NE')


def source_windows(input_plan):
    if input_plan['probability_M_events'] or input_plan['probability_values_accepted']:
        raise ValueError('runtime addresses only; no probability input images/values')
    physical = {f['physical_word'] for page in input_plan['pages'] for f in page['footprints']}
    return sorted({(w//8//16)*16 for w in physical})


def compile_transport(input_plan, *, destinations, contract, gq_source_path, first_fire=40):
    """destinations[window][quarter] are explicit allocated16-sector local runs.

    All four destination leases are required, including the SW self copy. The
    caller must keep them live through local BF16 reads and page retirement.
    This emits real programme rows but no launches/preloads or forged calendar.
    """
    if hashlib.sha256(Path(gq_source_path).read_bytes()).hexdigest()!=GQ_SHA256:
        raise ValueError('exact opt-in single-sender GQ candidate source required')
    if type(first_fire) is not int or first_fire < 0:
        raise ValueError('invalid fixed GQ programme first_fire')
    windows = source_windows(input_plan)
    if len(destinations)!=len(windows) or any(len(row)!=4 for row in destinations):
        raise ValueError('four explicit16-sector destination leases per source window required')
    if not windows or len(windows)>128:
        raise ValueError('bounded GQ128-row programme capacity exceeded')
    for q in range(4):
        intervals=[]
        for row in destinations:
            base=row[q]
            if type(base) is not int or base%8 or not 0<=base<=8192-16:
                raise ValueError('aligned16-sector destination run required')
            if any(max(base,a)<min(base+16,b) for a,b in intervals):
                raise ValueError('overlapping live destination leases')
            if q==0 and any(max(base,s)<min(base+16,s+16) for s in windows):
                raise ValueError('SW copy would overwrite live source window')
            intervals.append((base,base+16))
    rt=[contract['instances']['hcollgi_'+q]['params']['VM_RT'] for q in QUARTERS]
    # r15 bound VM_RT 74 on all four stops; r18 l12 binds 76. The wave compiler takes the bound value (equal on all stops).
    if len(set(rt))!=1 or rt[0] not in (74,76):
        raise ValueError('matching VM_RT74 (r15) / VM_RT76 (r18) four-stop source required')
    span=100+rt[0]  # = gq_wave_1021 wave_span (174 at VM_RT74)
    period=first_fire+len(windows)*span
    if type(first_fire) is not int or first_fire<0 or period>=65536:
        raise ValueError('invalid fixed GQ programme period')
    rows=[[] for _ in range(4)]
    transactions=[]
    for j,source in enumerate(windows):
        wave=GW.wave_plan(F=16,senders=(0,),source_sectors=[source,0,0,0],
            destination_sectors=list(destinations[j]),vm_rt=rt,first_fire=first_fire+j*span)
        for q in range(4):
            word=wave['rows'][q][0]
            word=(word&~((0xffff<<85)|(0xff<<224)))|(period<<85)|(j<<224)
            rows[q].append(word)
        transactions.append(dict(window=j,source_base_sector=source,destination_base_sectors=list(destinations[j]),
            first_fire=first_fire+j*span,vm_reads=wave['vm_reads'],vm_writes=wave['vm_writes'],
            ring_events=wave['ring_events'],last_bank_write=wave['last_commit']))
    remaps=[]
    for page in input_plan['pages']:
        for f in page['footprints']:
            physical=f['physical_word'];window=(physical//8//16)*16;j=windows.index(window)
            remaps.append(dict(logical_word=f['logical_word'],source_physical_word=physical,
                destination_physical_words=[8*((q<<13)|destinations[j][q])+(physical-8*window) for q in range(4)]))
    return dict(status='SOURCE_PROGRAMMES_ONLY_PRODUCER_COPY_LOADER_CONSUMER_JOIN_OPEN',hardware_executed=False,
        qualifies_native_layer=False,qualifies_native_chain=False,probability_M_events=0,collateral_M_events=0,
        source_sha256=GQ_SHA256,defines=[GW.DEFINE],source_windows=windows,rows=rows,
        descriptors=[dict(base=0,limit=len(windows),loops=1) for _ in range(4)],transactions=transactions,
        probability_word_remaps=remaps,first_fire=first_fire,period=period,
        fixed_transport_stream_edges=len(windows)*span,first_fire_and_CP_install_priced_separately=True,
        actual_source_read_bytes=len(windows)*16*32,actual_destination_write_bytes=len(windows)*4*16*32,
        unused_collateral_sectors='real source VM contents copied unchanged; no probability/collateral images',
        source_completion_qualification='singleSW transaction matches qualified F16 firstwave; composedprogramme termination unexecuted',
        calendar_obligation='finite whole-programme all-bank COLL readowner3/writecode2 epochs on all4quarters; bind real launch_sample+3; no guessed request-pad split',
        lifetime_obligation='sourceP and all destinationleases live until actuallocalBF16read/pageconsumer retires; producer/copy/loader/consumer exact fixedjoin still required')


def main():
    import argparse,json
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--input-plan',type=Path,required=True)
    p.add_argument('--destinations',type=Path,required=True,help='explicit component/layer lease array [window][quarter]')
    p.add_argument('--contract',type=Path,required=True)
    p.add_argument('--gq-source',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True)
    a=p.parse_args()
    result=compile_transport(json.loads(a.input_plan.read_text()),
        destinations=json.loads(a.destinations.read_text()),contract=json.loads(a.contract.read_text()),
        gq_source_path=a.gq_source)
    a.out.write_text(json.dumps(result,indent=1)+'\n')
    print(json.dumps({k:result[k] for k in ('status','fixed_transport_stream_edges','actual_source_read_bytes',
        'actual_destination_write_bytes','probability_M_events','collateral_M_events')}))


if __name__=='__main__':main()
