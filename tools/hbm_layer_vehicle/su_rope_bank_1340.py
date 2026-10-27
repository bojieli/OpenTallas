"""RoPE using real local C bank exchange and runtime B/D coefficient duplication.

scratch_base is an allocated physical VM WORD base. Scratch never enters M.
Only original pre-operation A/B/D enter the DUT; references feed comparisons.
"""
from pathlib import Path
import hashlib
import math
import re
import numpy as np


def _selected_pair_bindings(text):
    """Balanced parameter-list prefilter. Actual Verilator proof is still required."""
    result = {}
    for match in re.finditer(r"ot_hbm_su_static_pgslice_lg\s*#\s*\(", text):
        start = match.end(); depth = 1; stop = start
        while stop < len(text) and depth:
            depth += (text[stop] == "(") - (text[stop] == ")")
            stop += 1
        if depth:
            continue
        instance = re.match(r"\s*(su_SW[0-3])\s*\(", text[stop:])
        if instance is None:
            continue
        params = text[start:stop-1]
        # Each named argument is consumed completely; nested/malformed lists fail closed.
        fields = {}; cursor = 0
        while cursor < len(params):
            item = re.match(r"\s*\.(\w+)\s*\(\s*([^()]*)\s*\)\s*(,|$)", params[cursor:])
            if item is None:
                fields = {}; break
            if item[1] in fields:
                fields = {}; break
            fields[item[1]] = item[2].strip(); cursor += item.end()
        result[instance[1]] = fields.get("PAIR_C_READS")
    return result


def lower(raw, q=0, data=None, place=None, tag="", timing=None, scratch_base=None,
          pair_c_reads=0, pair_source_path=None, pair_die_path=None, **unused):
    from hbm_layer_vehicle import layer_images as LI
    from hbm_layer_vehicle.su_layer_lower_1021 import TreeLines, move_words_to_rf
    from hbm_layer_vehicle.native_profile import NativeTiming
    from su_program_inventory import decode
    from su_arith_compile import pack, physical_word
    _, unit, sut, desc = decode(raw)
    def refuse(reason):
        return dict(status="unsupported_lowering", reasons=[reason], sut=sut,
                    lowering=dict(supported=False, owner="CODEX-SU-ROPE-1340"))
    # Source inspection found that the old coefficient preparation drains RF
    # src1 through ports k%8. Actual pgslice permits src1 only on G0/h0 (port0).
    # Preserve the code below as diagnostic history until the owner supplies a
    # real RF->SU store->VM replacement and its newly measured/priced schedule.
    result = refuse("KNOWN_PROTOCOL_VIOLATION: RF_src1_VM_drain_requires_port0_G0_h0; "
                    "runtime_RF_to_SU_store_to_all_bank_drain_repair_required")
    result.update(execution_qualified=False, known_protocol_violation=True,
                  diagnostic_prior_serial_edges=2088, diagnostic_prior_stream_edges=2784,
                  diagnostic_prior_price_qualified=False)
    return result
    profile = dict.fromkeys(sut, 0)
    profile.update(c_pair=1, b_half=1, m1=1, qm=sut["qm"], ad=1, dst=1, rnd=sut["rnd"])
    if unit != 2 or sut != profile or sut["qm"] not in (3, 4) or set(desc) != {"A", "B", "D", "O"}:
        return refuse("exact_mul_plus_signed_pair_product_RoPE_profile_required")
    if q != 0 or timing != NativeTiming(18, 15):
        return refuse("selected_quarter0_READ_RETURN18_WRITE_RETURN15_required")
    if pair_c_reads != 1 or pair_source_path is None:
        return refuse("actual_optin_PAIR_C_READS_source_required")
    try:
        source = Path(pair_source_path).read_text()
    except OSError:
        return refuse("actual_pair_source_unreadable")
    if any(s not in source for s in ("PAIR_C_READS=0", "g_pair_request", "pair_c_age[2]")):
        return refuse("actual_C_request_and_return_exchange_missing")
    if pair_die_path is None:
        return refuse("actual_selected_die_PAIR_C_READS_binding_required")
    try:
        selected_die = Path(pair_die_path).read_text()
    except OSError:
        return refuse("actual_selected_die_source_unreadable")
    bindings = _selected_pair_bindings(selected_die)
    for group in range(4):
        if bindings.get("su_SW" + str(group)) != "1":
            return refuse("actual_selected_SW_instance_PAIR_C_READS1_missing:" + str(group))
    if type(scratch_base) is not int or scratch_base < 0 or scratch_base % 128:
        return refuse("allocated128word_aligned_physical_VM_WORD_scratch_base_required")
    if (scratch_base//8)>>13 != q or ((scratch_base+127)//8)>>13 != q:
        return refuse("scratch_run_must_fit_selected_quarter_VM")
    a, b, d, o = (desc[r] for r in "ABDO")
    n, m = a.n, a.m
    if n != 64 or not 1 <= m <= 32 or (o.n, o.m) != (n, m):
        return refuse("64columns_up_to32rows_required")
    for md in desc.values():
        if (md.space != "VM" or md.fmt != "FP32" or md.base % 8 or (md.istride or 1) != 1 or
            any(getattr(md,k) for k in ("lstride","dyn_sel","dyn_mul","n_sel","l1stride","ibcast","indexed"))):
            return refuse("aligned_contiguous_FP32_VM_descriptors_required")
    if b.stride or d.stride or b.n != n or d.n != n or (m > 1 and (a.stride < n or o.stride < n)):
        return refuse("reused_B_D_tables_and_nonoverlapping_A_O_rows_required")
    required = {a.base+i*a.stride+j for i in range(m) for j in range(n)}
    required |= set(range(b.base,b.base+32)) | set(range(d.base,d.base+32))
    if data is None or any(w not in data for w in required):
        return refuse("actual_pre_operation_A_B_D_words_required")
    before = {w:np.float32(v) for w,v in data.items()}
    if any(not np.isfinite(before[w]) for w in required):
        return refuse("finite_inputs_required")
    place = place if place is not None else LI.Placement(q)
    scratch_sectors = set(range(scratch_base//8,scratch_base//8+16))
    if scratch_sectors.intersection(place.map.values()):
        return refuse("scratch_overlaps_existing_operand_placement")
    for md in (a,o):
        for i in range(m):
            for j in range(8):
                ls=(md.base+i*md.stride)//8+j
                if ls in place.map and place.map[ls]%8 != j:
                    return refuse("A_O_existing_VM_port_placement_conflict")
    ql=TreeLines()
    fills,drains,preload,expect,moves=[],[],{},[],[]
    duplicate_sources=[r.base+j//2 for r in (b,d) for j in range(n)]
    edge0=0
    for k in range(0,128,8):
        mv=move_words_to_rf(ql,words=duplicate_sources[k:k+8],rf_addrs=list(range(k,k+8)),
            q=q,data=before,place=place,tag=tag+":coefficient_move",timing=timing,
            row0=0,edge0=edge0,red_d0=k)
        fills.extend(mv["fills"]);preload.update(mv["preload"])
        moves.append(dict(source_words=duplicate_sources[k:k+8],RF_words=list(range(k,k+8)),
                          exports=mv["exports"],RF_write_pins=mv["rf_ready"]))
        edge0=mv["rf_ready"]+4
    scratch_last=0;scratch_events=[]
    for k in range(16):
        read=edge0+k;drain=read+2;commit=drain+timing.drain_done;ps=scratch_base//8+k
        ql.put("rf",read,5*9,9,0x100|(8*k))
        ql.vmw(drain,k%8,1,0,0,ps,255)
        refs=[int(before[w].view(np.uint32)) for w in duplicate_sources[8*k:8*k+8]]
        expect.append(dict(sector=ps,mask=255,edge=commit,words=[],value=refs,
                           role="runtime_scratch_comparison_only"))
        scratch_events.append(dict(physical_sector=ps,RF_row=8*k,read_edge=read,
            drain_edge=drain,commit_edge=commit,mask=255,source_words=duplicate_sources[8*k:8*k+8]))
        scratch_last=max(scratch_last,commit)
    start_fill=scratch_last+1;last_fill=start_fill
    for i in range(m):
        for j in range(8):
            ls=(a.base+i*a.stride)//8+j;ps=place.get(ls,j,tag+":A");e=start_fill+i
            if ps in scratch_sectors:raise ValueError("scratch allocation collided with A")
            ql.vmr(e,j,ps,j,i);fills.append((ls,e));last_fill=max(last_fill,e)
            if ls not in place.written:preload[ps]=list(range(8*ls,8*ls+8))
    scratch_reads=[]
    for role in range(2):
        for j in range(8):
            e=start_fill+m+role;ps=scratch_base//8+8*role+j
            ql.vmr(e,j,ps,j,m+role);last_fill=max(last_fill,e)
            scratch_reads.append(dict(physical_sector=ps,edge=e,local_row=m+role))
    setup=last_fill+timing.fill_commit+1
    terms=sum((1<<bit)<<(24*(10*role+bit)) for role in range(5) for bit in range(7))
    base=dict(no=1,ni=64,ls=6,lvw=6,ld_c=terms,srcs=0,cpair=1,dst=1,co_dst=1,
              cp_m1=1,cm_m1=1,cm_qm=sut["qm"],ca_ad=1,co_rnd=sut["rnd"])
    def control(i,**flags):
        rows=(i,m,i,m+1,m+2+i)
        vb=sum(physical_word(q,r)<<(24*s) for s,r in enumerate(rows))
        return pack(dict(base,vb=vb,**flags))
    ql.f["control"][setup]=control(0,ld=1)
    issues=[];post={};last_commit=0
    for i in range(m):
        issue=setup+LI.SETUP_TO_EMIT+i
        ql.f["control"][issue]=control(i,emit=1);issues.append(issue)
        aa=np.array([before[a.base+i*a.stride+j] for j in range(n)],np.float32)
        bb=np.array([before[b.base+j//2] for j in range(n)],np.float32)
        dd=np.array([before[d.base+j//2] for j in range(n)],np.float32)
        bits=LI.vop_golden(sut,dict(A=aa,B=bb,C=aa[np.arange(n)^1],D=dd))
        de=issue+LI.FIRST_OUT-LI.SETUP_TO_EMIT+1;co=de+timing.drain_done
        for j in range(8):
            ls=(o.base+i*o.stride)//8+j;ps=place.get(ls,j,tag+":O")
            if ps in scratch_sectors:raise ValueError("scratch allocation collided with O")
            ql.vmw(de,j,0,j,m+2+i,ps,255)
            words=list(range(o.base+i*o.stride+8*j,o.base+i*o.stride+8*j+8))
            expect.append(dict(sector=ps,mask=255,edge=co,words=words,
                               value=[int(v) for v in bits[8*j:8*j+8]]))
            drains.append((ls,co));place.written.add(ls)
        post.update({str(o.base+i*o.stride+j):f"{int(bits[j]):08x}" for j in range(n)})
        last_commit=max(last_commit,co)
    hold=control(0)
    for e in range(setup,last_commit+1):ql.f["control"].setdefault(e,hold)
    lines=ql.lines()
    if len(lines)>LI.EDGES_MAX:return refuse("actual_programme_capacity_exceeded")
    input_words=sorted({w for words in preload.values() for w in words})
    input_bits={str(w):f"{int(before[w].view(np.uint32)):08x}" for w in input_words}
    # Shared compiler reference state updates only after M bits are frozen.
    for word,bits in post.items():data[int(word)]=np.uint32(int(bits,16)).view(np.float32)
    return dict(status="emitted",reasons=[],sut=sut,ql=ql,lines=lines,fills=fills,drains=drains,
        preload=preload,expect=expect,data=input_bits,preload_data=input_bits,inputs_placeholder=False,
        preload_provenance="original pre-operation A/B/D only; scratch never imaged",
        setup_edge=setup,issue_edges=issues,last_commit=last_commit,fill_sectors=len(preload),
        drain_sectors=len(drains)+16,expected_post_state=post,expected_post_state_only=True,
        lowering=dict(supported=True,execution_qualified=False,owner="CODEX-SU-ROPE-1340",
            mode="local_C_pair_exchange_and_runtime_BD_VM_RF_duplication"),
        native_timing=timing.as_dict(),command_width=2470,
        source_contract=dict(PAIR_C_READS=1,extra_C_serial_edges=0,
            source_sha256=hashlib.sha256(source.encode()).hexdigest(),
            selected_die_sha256=hashlib.sha256(selected_die.encode()).hexdigest(),scratch_base_unit="physical_VM_WORD",
            scratch_base=scratch_base,scratch_words=128,external_neighbour_operands=False,RF_external_drive=False),
        runtime_coefficient_moves=moves,scratch_write_footprint=scratch_events,
        scratch_read_footprint=scratch_reads,scratch_reuse_after_serial=last_commit+1,
        control_reservation=dict(first=0,last=last_commit,policy="exclusive_record"),
        timing_obligations=dict(serial_edges=last_commit+1,stream_edges=math.ceil(4*(last_commit+1)/3),
            RF_relay=32,RF_LOCAL=1,old_price_preserved=False,connected_selected_RTL_required=True))
