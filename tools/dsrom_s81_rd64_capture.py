"""Source-bound NOREADY return/VM capture calendar. No return or codec RTL.

A ready mask describes actual TARGET write acceptance. It never flows back to
RD64. Admission reserves capacity BEFORE GO; absence of a service guarantee
requires the entire per-root phase output, not a guessed FIFO depth.
"""
from pathlib import Path
import hashlib,json
ROOT=Path(__file__).resolve().parents[1]
NP,R,RD,ROOTD=2417,128,64,128
SOURCES=['rtl/v41die/ot_v41_retn_w17w10.sv','rtl/v41rom/ot_v41_ret.sv',
 'rtl/v41die/ot_v41_spine_w17w10.sv','rtl/v41die/ot_v41_rom_adapt.sv',
 'rtl/chip/ckvsel/ot_chip_v41x_tile.sv',
 'results/uarch/dsrom_c_recheck_20261004/DECISION.md',
 'results/uarch/dsrom_c_recheck_20261004/model.json']


def pair_spans():
    # W1 metadata dsrom.active_pair_return.v1, topology only: no credit RTL.
    return [(r*NP//R,(r+1)*NP//R) for r in range(R)]


def required_depths(arrivals, accepted_vm):
    """NBA edge identity: old captured writes retire before new rows capture.

    arrivals[e][r] is0/1 actual unconditional root valid. accepted_vm[e][r]
    describes availability of that root's existing target write port. Holds
    accumulate even when zero ready; the producer is never stalled/filtered.
    Returns exact minimal capture depth for the supplied finite calendar ONLY.
    """
    if len(arrivals)!=len(accepted_vm):raise ValueError('calendar lengths')
    if not arrivals:raise ValueError('empty calendar')
    roots=len(arrivals[0]);q=[0]*roots;peak=[0]*roots;accepted=[0]*roots
    journal=[]
    for edge,(a,s) in enumerate(zip(arrivals,accepted_vm)):
        if len(a)!=roots or len(s)!=roots or any(type(v) is not int or v not in (0,1) for v in a+s):
            raise ValueError('one return per root per edge and explicit acceptance')
        writes=[int(q[r]>0 and s[r]) for r in range(roots)]
        q=[q[r]-writes[r]+a[r] for r in range(roots)]
        peak=[max(peak[r],q[r]) for r in range(roots)]
        accepted=[accepted[r]+writes[r] for r in range(roots)]
        journal.append(dict(edge=edge,captured=a,VM_accepted=writes,remaining=list(q)))
    return dict(required_depths=peak,pending=q,VM_accepted=accepted,journal=journal)


def pre_go_admission(root_rows, positions, capacity, *, guaranteed_service=None):
    """Actual symbolic row-owner manifest; no uniform nrow/R assumption.

    For no service guarantee each root must reserve ALL future rows. With a
    complete guaranteed source-bound calendar, reserve its proven peak instead.
    This function supplies a software model decision, never hardware READY.
    """
    if len(root_rows)!=R or len(capacity)!=R or not 1<=positions<=8:
        raise ValueError('actual128 root capacities and1..8positions')
    rows=[row for group in root_rows for row in group]
    if any(type(row) is not int or not 0<=row<65536 for row in rows) or len(set(rows))!=len(rows):
        raise ValueError('immutable exclusive row ownership and16bit row tags')
    if any(type(c) is not int or c<0 for c in capacity):raise ValueError('finite capacity')
    total=[len(group)*positions for group in root_rows]
    need=total if guaranteed_service is None else guaranteed_service['required_depths']
    if len(need)!=R or any(need[r]>total[r] or need[r]<0 for r in range(R)):
        raise ValueError('calendar inconsistent with manifest')
    return dict(admitted=all(capacity[r]>=need[r] for r in range(R)),required=need,
                reserved_phase_returns=sum(total),per_root_totals=total,
                interpretation='model only; hardware must reserve actual seats before GO',
                root_rows_manifest_sha256=hashlib.sha256(json.dumps(root_rows,separators=(',',':')).encode()).hexdigest())


def verify_native_vm_trace(*, root_rows, positions, obase, ops, fmt, rsplit,
                           phase_fp32_low, phase_fp32_high, VM_AW,
                           returns, vm_writes):
    """Match actual NOREADY returns to actual native tile VM commit edges.

    Inputs are observational journals from the SAME simulator clock/context.
    No hardware input, numerical oracle, grant, ready or completion is driven.
    Rows/addresses derive the actual captured phase descriptor; VM payload is
    compared with the actual returned bits, not recomputed arithmetic.
    """
    admission=pre_go_admission(root_rows,positions,[len(x)*positions for x in root_rows])
    if fmt not in (0,1,2) or type(VM_AW) is not int or not 1<=VM_AW<=30:
        raise ValueError('actual VM width/phase format')
    if any(type(v) is not int or v<0 for v in (obase,ops,rsplit)):
        raise ValueError('captured address/row split fields')
    expected={(root,row,pos) for root,rows in enumerate(root_rows) for row in rows for pos in range(positions)}
    seen=set();expected_writes={};addresses=set()
    for e in returns:
        edge,root,row,pos=(e[k] for k in ('edge','root','row','pos'))
        if any(type(v) is not int or v<0 for v in (edge,root,row,pos)):
            raise ValueError('actual edge/root/row/position')
        key=(root,row,pos)
        if key not in expected or key in seen:raise ValueError('foreign or duplicate unconditional return')
        if e['error']:raise ValueError('real return fault; no healthy visibility credit')
        if (edge,root) in expected_writes:raise ValueError('more than one root return per edge')
        fp32,bf16=e['fp32'],e['bf16']
        if type(fp32) is not int or not 0<=fp32<2**32 or type(bf16) is not int or not 0<=bf16<2**16:
            raise ValueError('raw returned payload widths')
        address=obase+row+pos*ops
        if address>=1<<VM_AW or address in addresses:
            raise ValueError('VM address truncation/overlapping declared outputs')
        use_fp32=fmt==1 or (fmt==0 and (phase_fp32_low if row<rsplit else phase_fp32_high))
        expected_writes[(edge,root)]=(edge+1,address,fp32 if use_fp32 else bf16<<16)
        addresses.add(address);seen.add(key)
    if seen!=expected:raise ValueError('missing declared return debt')
    observed={}
    other_writes=[]
    for e in vm_writes:
        if e.get('writer')!='ROM':other_writes.append(e);continue
        key=(e['edge']-1,e['root'])
        if key in observed:raise ValueError('duplicate VM write observation')
        observed[key]=(e['edge'],e['address'],e['data'])
    if observed!=expected_writes:raise ValueError('actual VM commits differ from captured return calendar/identity/payload')
    if any(e['address'] in addresses for e in other_writes):
        raise ValueError('other writer overlaps exclusively owned result lease')
    last=max((x[0] for x in observed.values()),default=None)
    return dict(status='OBSERVED_NATIVE_VM_CAPTURE_PASS',returns=len(seen),VM_commits=len(observed),
                last_actual_VM_commit_edge=last,expected_manifest_sha256=admission['root_rows_manifest_sha256'],
                source_capture_to_VM_edges=1,return_drain='all declared rows captured and positively committed',
                scope='provided single-context actual journals only; no physical port/clock/fulltoken qualification')


def model():
    texts={p:(ROOT/p).read_text() for p in SOURCES}
    anchors={SOURCES[0]:['parameter integer RD = 64','output wire        o_v'],
      SOURCES[1]:['if (i_v) qw <= qw + 1\'b1','if (i_v && qc == QD && !use_q) fault <= 1\'b1'],
      SOURCES[2]:['w_we <= {R{1\'b0}}','if (r_v[kr])','rows_left <= rows_left - 19\'($countones(r_v))'],
      SOURCES[3]:['assign ready = st == S_IDLE && s_ready','S_GO: if (s_ready)'],
      SOURCES[4]:['for (q = 0; q < ROM_R; q = q + 1) if (rom_we[q]) vm[rom_waddr[q*AW +: VM_AW]] <= rom_wdata[32*q +: 32]']}
    for path,needles in anchors.items():
        for needle in needles:
            if needle not in texts[path]:raise ValueError('source contract changed: '+path+' '+needle)
    if 'build S81' not in texts[SOURCES[5]]:raise ValueError('selected decision')
    nodes=2*NP-R;bits=nodes*(2*RD*65+66)+R*ROOTD*(65+66)
    spans=pair_spans();allready=required_depths([[1]*R]*32+[[0]*R],[[1]*R]*33)
    return dict(schema='dsrom.s81.rd64.capture.v1',selected_decision='73851317f/main55e2',
      geometry=dict(active_pairs=NP,BF_pairs=519,roots=R,macro_leaves=2*NP,nodes=nodes,padded_pair_seats=0,
        regions18=sum(hi-lo==18 for lo,hi in spans),regions19=sum(hi-lo==19 for lo,hi in spans),pair_spans=spans,
        pair_map_status='selected W1 contiguous active-pair topology; S81 tensor/row-owner export must bind these spans, not S82'),
      original_return=dict(RD=64,RST=1,BYPASS=1,root_D=128,root_QD=128,NO_READY=True,
        state_lower_bits=bits,node_queue_lower_bits=nodes*2*RD*65,root_lower_bits=R*ROOTD*131,
        control_mux_adder_clock_route_excluded=True,internal_sibling_skew_bounds_unproven=True,
        per_node_raw_input_write_bits_per_edge=130,per_node_raw_queue_read_bits_per_edge=130,
        node_and_root_FP32_adders=nodes+R,root_output_bits_per_edge=R*69),
      source_edges=dict(clock_scope='same actual native tile/spine clock; no CDC credit. Any selected clock-C crossing needs its actual finite FIFO/calendar',root_valid='root r_v unconditional; max1/root/edge, peak128allroots',
        capture='spine samples69bit row and registers w_we/address/data at E',
        visibility='actual tile VM nonblocking write of OLD w_we at E+1',
        VM_scope='simulation tile exposes128 independent writes, no ready. Physicalbank/ports not qualified',
        core_ready='rom_adapt ready=S_IDLE&&s_ready; NOT return seat admission',
        existing_holding_bits=R*(1+30+32),new_capture_FF_if_native_allports_accept=0,
        required_depth_native_simulation_ports=1,full_burst_rows_per_edge=R,VM_bytes_per_edge=R*4,
        capacity_or_delay_unknown='shared/physical VM sink must supply positive accepted write calendar/lease; no fake write-journal fence'),
      bounded_source_calendar_example=dict(scope='synthetic worst width128x32 consecutive returns, SAME native alwaysaccept VM behavior; not actualtoken',
        peak=max(allready['required_depths']),pending_after_one_drain_edge=sum(allready['pending']),
        VM_accepted=sum(allready['VM_accepted']),capture_to_VM_positive_edges=1),
      admission=dict(no_stall_guarantee='reserve exact per-root phase row count*positions before GO',
        finite_service_guarantee='peak cumulative unconditional arrivals minus positively accepted older writes; include final pending pipeline',
        root_owner_manifest_required=True,exclusive_VM_address_range_required=True,
        address_bounds='AW30 and actualVM_AW19 at full shape,16 reduced; reject truncation/alias, simultaneous cross-root collisions or concurrent writer ownership',
        completion='all declared rows captured AND allactualVMwrites accepted AND loader/streamer done; write-journal quiet alone insufficient'),
      per_rank_indexer_projection='wk/wq_b replicated on all4ranks, must appear in each actual phase/root trace; no rank0 multicast carry',
      missing=['actual S81 Arendt tensor->pair->root row map','Arch selected reduced-system targetVM acceptance/otherwriter arbitration',
               'source-bound complete phase accepted return timestamps incl per-rank indexer','Rawls finite RD64 sibling/node/root occupancy/skew under this map'],
      no_new_tree=True,no_new_codec=True,no_RD16=True,hardware_change_required=None,
      combined_token_qualified=False,physical_build_admitted=False,
      generator_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
      source_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in SOURCES})

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    if a.out.exists():raise FileExistsError(a.out)
    a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(model(),sort_keys=True,indent=2)+'\n')
