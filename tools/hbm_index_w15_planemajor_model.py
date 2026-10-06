#!/usr/bin/env python3
"""Selected Rawls two-normal-gather book; immutable historical rank-major model."""
import hashlib
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def proposal():
    historical='results/uarch/hbm_index_w15_formatter_20261005/model.json'
    p=json.loads((ROOT/historical).read_text())
    p['schema']='hbm.index.w15.plane_major_formatter.minimum.v1'
    p['selected_enclosing_owner']='Rawls 2026-10-05T14:48:17 two normal W15 gathers, SAME leased393216B arena'
    p['selected_source']='rtl/hbm_accel/index/ot_hbm_accel_index_w15_planemajor_formatter.sv'
    p['historical_source_selected']=False
    p['layout']={'address_unit':'512b VM word, convert installer BYTE base/limit by exact checked divide64 in enclosing caller','pairs_per_rank':512,'words_per_rank_per_plane':32,'score_plane_words':3072,'ID_plane_word_offset':3072,'plane_rank_stride_words':32,'score_address_word':'BASEword+rank*32+(pair_word>>1)','ID_address_word':'BASEword+3072+rank*32+(pair_word>>1)','score_address_byte':'BASEbyte+rank*2048+64*(pair_word>>1)','ID_address_byte':'BASEbyte+196608+rank*2048+64*(pair_word>>1)','half':'pair_word[0], 8 of16 original32b lanes'}
    p['address_operator_delta']='same33b checked arithmetic, rank shift6 becomes shift5 and ID constant32 becomes3072; no extra state/port/backing, same positive address/mux allowance'
    p['actual_installer_book_bound']=False
    p['enclosing_requirements']=['pinned actual free/occupied installer extent book and real exclusive normal-gather owner','actual byte base/limit 64B aligned; never pass byte BASE directly into word-address pins','first score normal gather mode1/topk0/GW1/n32 -> BASE, second IDs gather -> BASE+196608; both source spans independently actual','both gathers actual writeACK/publication/drain before formatter start','actual337/273 singleMREQ256 bridge serial2sectors/read512; positive readACK/protection/CDC/arbiter costs composed by Rawls/Maxwell, no source-port9edge timing claim']
    p['source_fact_boundary']='Selected PLANE MAJOR two-normal-gather storage, NOT historical rank-major combined64words/rank. No implicit TOPK->VM copy or preloaded content.'
    p['source_sha256']={historical:hashlib.sha256((ROOT/historical).read_bytes()).hexdigest(),'tools/hbm_index_w15_planemajor_model.py':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    p['underlying_provider_traffic']={'existing_mreq_data_bits':256,'single_serial_sectors':24576,'bytes':786432,'one_GHz_payload_floor_us':24.576,'exclusive_VM_port_latency_and_CDC_in_serial_plan':'unbound, must replace9edge candidate service if actual slower; no free overlap'}
    return p

if __name__=='__main__':print(json.dumps(proposal(),indent=2))
