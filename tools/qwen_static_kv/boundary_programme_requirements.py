#!/usr/bin/env python3
"""Decode actual production source demand; refuse invented KV reader calendars.

This creates no timing image or hardware qualification. It distinguishes writer
slots from the missing persistent-controller/front/return producer contracts.
"""
import argparse, hashlib, json, sys, re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools'))
import hdc_qwen_fullshape_isa_w12 as ISA
from qwen_kv_die.static_kv_calendar import model

SOURCES=[
 'tools/qwen_static_kv/native_programme.py',
 'rtl/qwen_sys/static_kv_20261014/qkd_kv_native_programme.sv',
 'rtl/qwen_sys/static_kv_20261014/qkd_ctrl_pc_host_static.sv',
 'rtl/qwen_sys/static_kv_20261014/ot_qkd_static_ctrl_pc_emb.sv',
 'rtl/qwen_sys/static_kv_20261014/ot_qkd_static_kv_timing.sv',
 'rtl/qwen_sys/static_kv_20261014/qkd_static_kv_return_calendar.sv',
 'rtl/qwen_sys/static_kv_20261014/qkd_kv_hbm_elastic_front.sv',
 'rtl/qwen_sys/static_kv_20261014/qkd_static_kv_return_slots.sv',
 'tools/qwen_kv_die/return_landing_admission.py',
 'rtl/physical/ot_qwen_kv_centre_slots.sv',
 'rtl/qwen_sys/host_20261013/qkd_host_program_loader.sv']


def requirements(program,plan,profile):
    digest=hashlib.sha256(program).hexdigest()
    if plan.get('files_sha256',{}).get('layer_candidate_program.hex')!=digest:
        raise ValueError('actual layer programme/plan SHA mismatch')
    if tuple(plan.get(k) for k in ('tp','groups','layers','layer_candidate_words'))!=(8,3072,36,25):
        raise ValueError('requires production TP8 GT3072 all36 source shape')
    rows=[dict(pc=pc,**ISA.decode_instruction(int(w,16))) for pc,w in enumerate(program.split())]
    native=[r for r in rows if r['unit']==1 and r['me_wsrc']]
    if len(rows)!=25 or len(native)!=1 or native[0]['pc']!=11:
        raise ValueError('requires actual sole native PC11 and25 encoded instructions')
    m=model()
    timing={k:int(v) for k,v in re.findall(r'\b(T_\w+)\s*=\s*(\d+)',(ROOT/'rtl/qwen_sys/static_kv_20261014/ot_qkd_static_kv_timing.sv').read_text().split(')(\n',1)[0])}
    if len(timing)<15:raise ValueError('actual persistent JEDEC timing constants unresolved')
    missing={
      'controller_reservation_producer':[
        'All36 per-PC absolute HBM start/reset/strap phase and actual phi-R clock receipts',
        'Source-bound initial JEDEC/open-row/refresh state and every exceptional host ingest/read/write window',
        'K descriptor [first=0,n=256) and V descriptor [first=512,n=768), layer row64+(stage-1), actual command launch ages',
        'Every strict PROFILE0 reserved_rd/static_col/write_col edge with actual refresh/turnaround/row conflict proof',
        'Current-token writer descriptors must commit before any read that includes their position; actual WDONE visibility',
        'Actual boot/control-image storage, address map, producer RTL and physical home; existing HOST pr143 is a distinct interface'],
      'front_block_release_producer':[
        'Actual off-die latency service window/watchdog and source-bound controller-to-front path ages',
        'Compiled8-sector blk_go for every block; enforce4-block/32-sector front capacity across prefetch and retirement',
        'Implemented blk_freed boundary reservation accounting and explicit exceptional hold/block-pause path in sequencer',
        'Current fixed-sequencer RTL has no hold input; late-block component preservation does not qualify native execution'],
      'return_expected_slot_producer':[
        'Actual HBM/core phase plus front publication/return path/capture ages for every physical PC',
        'Source-derived independent expected_put/sector/epoch/layer for all512 sectors perPC, never actual valid-driven',
        'All32 group K requests and actual two V issuers joined to128-row landing lifetimes with real mapped SRAM latencies',
        'Production-sequencer consumers and D2D attention command calendar; frozen fixture admission is capacity analysis only'],
      'writer_and_control_image_parent':[
        'Real HOST loader producer for181 writer boot words plus D2D cfg_tx/cfg_rx control image',
        'Actual programme start bound one edge before segment0 core-start; writer slot is receiver timing, not upstream transport launch',
        'Parent wire actual independent programme expectation identity as {identity59,generation2}, not writer echo',
        'Domain-safe actual drain/fault joins and measured all-source parent/physical clock/pin audits']}
    return dict(schema='opentallas.qwen-kv-boundary-programme-requirements.v1',
      status='REFUSED_MISSING_CONTROLLER_FRONT_RETURN_PROGRAMME',production_installable=False,
      program_sha256=digest,source_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in SOURCES},
      actual_native_operation=native[0],actual_writer_source_pcs=[rows[p] for p in (3,8,10)],
      immutable_shape=dict(context=m['context'],groups=m['groups'],pseudo_channels=m['pseudo_channels'],
        sectors_per_pc=512,die_read_sectors=128*512,sector_payload_bits=256,die_read_payload_bytes=128*512*256//8,
        hbm_period_fs=1024000,core_period_fs=833334,front_blocks=4,sectors_per_block=8,front_capacity_sectors=32,return_ring_depth=8,landing_rows_per_pc=128),
      address_order=dict(K=m['k_sector_order'],V_group0=m['v_first_group_sector_order'],physical_group_order=m['group_order']),
      existing_writer_profile=dict(stage_count=len(profile.get('stages',[])),
        status='COMPONENT_TEST_ONLY',stage1=profile.get('stages',[{}])[0],
        produces='Four writer word slots and independent write descriptors; no read acquisition/reservation/release/return calendar'),
      persistent_controller_timing_constants=timing,
      missing_contracts=missing,
      next_implementation='Compile a source-pinned complete persistent HBM service calendar including boot/ingest/writer and native reader windows; allocate real on-chip replay storage or analytically compressed counter/pattern producers before RTL/physical work. Existing PROFILE1/2 discovery is a compiler/bench vehicle, not native production hardware.',
      qualification='No guessed read age, ideal producer, inherited physical view or full-token claim')

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--program',type=Path,required=True);p.add_argument('--plan',type=Path,required=True);p.add_argument('--profile',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
 r=requirements(a.program.read_bytes(),json.loads(a.plan.read_text()),json.loads(a.profile.read_text()))
 a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(r,indent=2)+'\n')
 print(r['status'], 'read sectors',r['immutable_shape']['die_read_sectors'],'payload bytes',r['immutable_shape']['die_read_payload_bytes'])
