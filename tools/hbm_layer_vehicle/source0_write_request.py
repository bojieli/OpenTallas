#!/usr/bin/env python3
"""Finite opt-in SOURCE0 write producer request, without allocating physical events."""
import argparse
import collections
import json
from pathlib import Path


def request(footprint):
    rows=footprint['rows']; rings={(r['ring_base_byte'],r['ring_slots'],r['slot_stride_bytes'],r['words'])for r in rows}
    assert len(rings)==1
    base,slots,stride,n=rings.pop();assert (slots,stride,n)==(128,2048,512)
    assert base%32==0 and base>>35==0
    variants=[]
    for slot in range(slots):
        chunks=[]
        for off in range(n//8):
            sector=(base+slot*stride)//32+off
            quad=((sector>>6)^(sector>>11)^(sector>>16))&1
            ordinal=((sector>>7)<<6)|(sector&63)
            assert ((ordinal>>6)<<7)|((quad^((ordinal>>10)&1)^((ordinal>>15)&1))<<6)|(ordinal&63)==sector
            if chunks and chunks[-1]['quad']==quad and chunks[-1]['ordinal_first']+chunks[-1]['sectors']==ordinal:
                chunks[-1]['sectors']+=1
            else:
                chunks.append(dict(quad=quad,ordinal_first=ordinal,real_sector_first=sector,VM_word_offset=off*8,sectors=1))
        variants.append(dict(ring_slot=slot,fragments=chunks))
    residues=collections.Counter(r['VM_source_word']%64 for r in rows)
    return dict(status='SOURCE_ONLY_ABI_MODEL_REQUEST; NO_CANONICAL_EVENT_OR_PHYSICAL_ADOPTION',
        selected_scope=dict(KVWB_commands=footprint['KVWB_commands'],scalar_rows=len(rows),scalar_write_bytes=2048,
            total_payload_bytes=len(rows)*2048,accepted_token_normalization=False),
        canonical_spill_source_gap=footprint.get('canonical_spill_STORE'),
        actual_gap='Frozen469cell C11E has onlySOURCE2 dbk_NE/NW andwbk_NE/NW. NoSOURCE0writer; no0→2alias/readfixturecredit.',
        existing_reuse=dict(
            SRC0_soft_read_wrapper='24de429cd:rtl/hbm_accel/loader/service_native/split/ot_hbm_static_load_stack0_service.sv',
            wrapper_currently_write_capable=False,
            reason='Its8VMKS wbw_v/base/total andw_k inputs are tied0; it exports no WB completion interface.',
            real_write_capable_children=['ot_hbm_svc_vm_kshare_splitstrap WBwindow/Kports/truew_k_wr_done',
                'ot_hbm_svc_pc_ctrl_leaf_cfg_h9b actualwritecolumns/data/strobes',
                'ot_hbm_svc_wb_kport_q realquadrantordinalwriter withACK counting',
                'ot_hgi_dma_back_static_vp4_banks_cp conditionalalignedVM→HBM sourceproducer'],
            qualification='Reuse ofRTLcapability only; no integratedSOURCE0writepathPASS or currentdieplacement credit'),
        proposed_soft_boundary=dict(
            two_half_window_commands=dict(each_fields=dict(valid=1,base_real_sector=30,total=12),bits=86),
            write_K_ports=dict(valid=32,address=960,data=8192,ready=32,write_done=32),
            total_added_port_bits=9334,
            mapping='Groupg=0..7 gets4ports g*4+:4, half0groups0..3,half1groups4..7; forwardactualVMKS ready/done unchanged.',
            phy='Retain real32PCcolumn/row/data/strobe boundary; no new fake DRAM service or response.',
            harden_wrapper=False,canonical_graph_changed=False),
        producer_ABI=dict(per_actor=dict(command_bits=308,move_bits=227,issue_relative=32,drain_relative=32,
                WB_bank=1,WB_epoch=16,VM_rq_bits=136,VM_rr_bits=2056,
                WB_data_bits=2312,WB_ACK_count_bits=12),
            required_partners=2,partner_quads=[0,1],stack=0,
            model_candidate='Two existingDBK-class command interfaces andtwoWBpartners, ONLY if actualVMreadgroups/bankvisibility are allocated; otherwiseactorcount/VMgather must be revised.',
            VM_binding='ActualscalarVMsources0..36128; resolve eachnativeowner/readgroup/address. Never reuseSOURCE2 q1rr wiring or invent freeports.',
            targets='NewactualHOST target allocations required; fixture106/126/127 are not adopted.',
            RR_RT='Actualnewroute measurement required; oldSOURCE2 RR_RT80 is a reference, not the newprofile.',
            lower_bound_RTL_storage_if_two_DBK_two_WB=dict(DBK_landing_macros=16,DBK_table_macros=4,WB_payload_macros=64,total_128x256_macros=84,
                scope='LiteralgenericRTL8landing+2table perDBK and32payload perWB. No area/physicalview claim; SRC0readfamily32PC/8VMKS/2REF itself is not currentdiecredit.')),
        lowering=dict(
            position='ActualruntimeDYNbankposition required; never recordordinal. Confirm MTP POS_SLOT versus legacyglobal rec_pos1 source; actualCW308 has no runtimePOS decoder.',
            scalar='slot=POS&127; dstbyte=base+slot*2048; m=1,n=512,FP32 unchanged.',
            native_address='q=s[6]^s[11]^s[16]; ordinal=deletebit6(s). Partitionreal64sectorrow into contiguoussamequad/ordinalfragments.',
            slot_variant_counts=dict(collections.Counter(len(v['fragments'])for v in variants)),
            maximum_native_commands=2*len(rows),maximum_commands_per_quad=len(rows),
            command_pages_per_quad_max=2,table_depth=128,maximum_CFG256_table_writes=4*len(rows),
            source_VM_mod64=dict(residues),original_rows_not64wordaligned=sum(v for k,v in residues.items()if k),
            native_constraint='DBK p_static_ok requires VMbase%64==0, n%8==0. Allselectedsources are8wordaligned;9arenot64aligned. Ordinary39/25sectorfragments add VMoffset312words, also unaligned.',
            required_resolution='RealdatedCOPY/gather intoallocated64wordalignedVMscratch OR qualifiedunalignedproducerextension. Neither is currently adopted; no freecopy/scratch/reorder.',
            scratch_candidate='Two512wordalignedslots onlyifactualVMallocator/visibility/lifetime proof permits; no allocation made.',
            order='Preserve originalBODY/ROWXwriteorder andKVWB-vs-attention/LOAD barriers; no groupingbyquad across barriers.'),
        host_and_cycles=['Publishactualbankpositions, physicalVMowners, inversefoldaddresses, targetIDs andper-commandissue/drain dates.',
            'Price anyCOPY/staging, commandtableload/rearm/pagechange, WBbank/epochreserve, clock/resetrelease andglobalfence.',
            'WBwindowopens after prior Kclient writes/readreturns are correctlydrained; no overlap/completionmissteering.',
            'mv_src/sourceconsumed is notHBMvisibility. DateactualKwriteACKcountdrain/mv_done andglobalfence before affectedLOAD/refill; no newon-diewaitprotocol.',
            'Invalidate retainedreadwindow versions, releaseoldownedepochafterlastconsumer, refillupdatedDRAM,acquirenewepoch.',
            'CTL.ACCEPT doesnotrollbackotherstate underR-POS; rejected-rowwrites mustnotresurrect stalecacheversions.'],
        holds=['No actualproducer/softwriteboundary/sourceplan added bythisrequest.',
            'N6ring128 preappendcanoverwriteearlyrowwindow; confirmactualcohort/ATTmapping beforeallocationchange. No256patch.',
            'Native152providers/48strictunplanned remain independent; newSOURCE0writegap is additional.',
            'No newheavygate/PNR/fullnumericmission. Integrationdecision andactualsourceclock/reset/controlcohorts required.'],
        real_sector_to_ordinal_variants=variants)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--footprint',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    a=p.parse_args()
    if a.out.exists():raise ValueError('Freshoutputrequired')
    a.out.write_text(json.dumps(request(json.loads(a.footprint.read_text())),indent=2)+'\n')
