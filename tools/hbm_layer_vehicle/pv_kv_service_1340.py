"""One real fixed-slot PV KV service programme (source candidate, no execution).

Real canonical K/V packets come from the selected native input capture. The
probability image is never read or emitted; pstore rows must be produced by the
real upstream SU/GQ/XQL programme before this consumer's fixed GO.
"""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'hbm_sm_attention'))
import sm_elem_bench as E
from hbm_layer_vehicle import smb_unit as SB
from hbm_layer_vehicle import sm_slice_lower as SL


def compile_service(*, record, op, probability_rows, latencies, go_at,
                    clear_at=32, dram_row=8, pcs=(0,1,2,3)):
    if type(go_at) is not int or go_at<SB.FIRST_GO:
        raise ValueError('fixed GO must retain selected service cold-fetch lead')
    if type(clear_at) is not int or not 8<=clear_at<go_at-16:
        raise ValueError('separate early fixed pstore clear required')
    cal,exp=E.compile_op(record,op,latencies,True,t0=8,
                         runtime_probability_rows=probability_rows)
    if cal.xw:raise ValueError('probability image is forbidden')
    packets=sorted(cal.pkt.items());lines=[];reads={}
    for cyc,packet in packets:
        tag=(packet>>1088)&1023
        if tag!=len(lines) or not (packet>>1098)&1:
            raise ValueError('one canonical ordered KV cache block required')
        lines.append(packet&((1<<1088)-1));reads[cyc]=(tag,tag)
    if not 1<=len(lines)<=64:
        raise ValueError('one actual64-line cache block required')
    svg=[];xc=[]
    for cyc,f in enumerate(cal.cyc):
        command=E.cmd_word(**f)
        # Attention consumes buffered KV beats through XCAL bit 152 and the SM
        # front requires arithmetic_v = attention && command[25] == consume, so
        # bit 25 stays in the SVG word (clearing it zeroed all 512 PV values,
        # unit367452).  Attention words carry the SVG ATT_MARK bit [119] so the
        # feed's S1 copy does not apply its normal issue-implies-packet rule.
        attention = bool((command >> 183) & 1)
        if (command >> 152) & 1 and not ((command >> 25) & 1 and attention):
            raise ValueError('attention consume without SM arithmetic issue')
        svg.append(SB.svg_word(command&((1<<83)-1),read=reads.get(cyc),
                               retire=(cyc==len(cal.cyc)-1),
                               att=attention and bool((command>>25)&1)))
        xc.append((command>>83)|(cal.kvd.get(cyc,0)<<109))
    if len(svg)>SB.PSTORE or len(xc)+2>SB.PSTORE:
        raise ValueError('real2048-row service programme capacity exceeded')
    # Early clear is an independent XCAL descriptor, not a fictitious probability
    # write. No SVG data block is associated with that two-word control segment.
    early=[E.cmd_word(mode=6,pclear=1)>>83,0]
    common=dict(row_base=dram_row,landing=0,epoch=1,rows=len(lines),tag_base=0,
                loops=1,lstep=0,mode=0,mrel=0,fl=0)
    sd=SB.desc_row(0,prog_base=0,prog_limit=len(svg),go_at=go_at,**common)
    cd0=SB.desc_row(0,prog_base=0,prog_limit=2,go_at=clear_at,**common)
    cd1=SB.desc_row(1,prog_base=2,prog_limit=len(xc)+2,go_at=go_at,**common)
    image=SL.hbm_image([dict(lines=lines,dram_row=dram_row)],list(pcs))
    return dict(status='SOURCE_CANDIDATE_CURRENT_PV_RETIRE_AND_JOIN_UNQUALIFIED',hardware_executed=False,
        probability_preloads=0,source_KV_lines=len(lines),actual_HBM_read_sectors=((len(lines)*136+127)//128)*4,
        svg_programme=[SB.prog_row(i,w,135) for i,w in enumerate(svg)],
        xc_programme=[SB.prog_row(i,w,173) for i,w in enumerate(early+xc)],
        svg_descriptors=[sd],xc_descriptors=[cd0,cd1],
        svg_run=dict(base=0,limit=1,loops=1),xc_run=dict(base=0,limit=2,loops=1),
        hbm_image={str(k):str(v) for k,v in image.items()},go_at=go_at,early_clear_at=clear_at,
        source_cold_fetch_bound=SB.FIRST_GO,go_to_first_SM_word=SB.LAT_GO,
        local_calendar=exp,local_preads=[dict(cycle=c,row=f['paddr']) for c,f in enumerate(cal.cyc) if f.get('pread')],
        result_semantics='partial key product: only op.rows, not full semantic N; sequential csum8 node;512FP32 values at64 real rv/rrow/rdata rows, coordinate8*rrow+column',
        consumed_key_rows=list(op[3]),semantic_key_count=len(record['K']),full_ATT_PV=False,
        downstream_VM_writer='NOT_QUALIFIED: MATVEC P1 would drop7columns; P8 FIFO/throughput not established; check actual SM result interface',
        timing_scope='latencies are explicit candidate profile to validate on exact source; no historical PASS inherited',
        remaining=['real producer/copy/XQL fixed epochs and pstore write/read ordering',
                   'exact CP/VM bank calendar and source counter anchors',
                   'actual512 result values/addresses/finite tail and all fault faces'])
