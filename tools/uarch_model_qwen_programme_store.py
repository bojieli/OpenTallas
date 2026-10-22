"""Finite, unadopted Qwen release control/table storage sizing."""
from pathlib import Path
import hashlib
import re

ROOT = Path(__file__).resolve().parents[1]
LEF = 'physical/asap7_memory_macros/ot_rom_4096x266_m8/ot_rom_4096x266_m8.lef'


def model():
    from qwen_layerbench.programme_store import STRIDE, read_rows
    data = (ROOT / LEF).read_bytes()
    w, h = map(float, re.search(rb'SIZE\s+([\d.]+)\s+BY\s+([\d.]+)', data).groups())
    return dict(schema='opentallas.qwen.release-programme-store-model.v1', default_off=True,
        qualification='SIZED ONLY; not a native token pass, no physical admission',
        source=dict(lowering_commit='4e718c0107e99f869c95db0ecedcca8711577dff',
                    macro=LEF, macro_sha256=hashlib.sha256(data).hexdigest()),
        actual_old_image=dict(metadata_pw=480, decode_entries=390, estimated_boot_entries=21,
            total_calendar_pw=822, table_chunks=dict(prog=72,btab=188,crom=528),
            table_pw=12608, total_required_pw=13910, available_pw=976,
            decode_only_without_tables_pw=1260, max_decode_entries_at_base480=248,
            note='Historical layer diagnostic; new admission leaf is a separate plane'),
        local_tables=dict(slices=12, users=4, stages=36, row_bits=1051,
            physical_row_bits=1064, rows_per_layer=STRIDE, used_rows=36*STRIDE,
            depth=4096, spare_rows=4096-36*STRIDE, macros=48,
            layout='4 distinct user PROG x6 + shared immutable BTAB18 + shared immutable CROM64',
            user_reads_per_layer=len(read_rows(36,3)),
            exact_max_per_slice=dict(prog=6,btab=18,crom=64),
            excludes='RoPE payload is position-dependent and requires its own real producer'),
        mutable_table_partitions=dict(
            crom=dict(unit='16-pair rows',user_stride=128,local_max_rows=68,total_user_rows=512,array_rows=1024),
            btab=dict(unit='16-BF16 words',user_stride=128,decode_max_words=72,total_user_words=512,array_words=512),
            prog=dict(unit='instructions',user_stride=128,local_instructions=12,total_user_instructions=512,array_instructions=512),
            contract='Compile four exact SU operand-address copies; preserve 1024-bit records. '
                     'Each user table load owns a disjoint bank; single write port still needs an exclusive static window.',
            source_parameter_receipt='q_ready_programme/capacity.json at f344a9570, source0d4c9808f; '
                'calpipe confirmed productionUVM4096/PIDX128; old16384/64 were bench-only. '
                'Complete live VM remapping and final GEN parameter binding remain OPEN'),
        calendar=dict(macros=1, entry_bits=128, proposed_depth=4096,
            needed_old_entries=411, actual_final_entries=None, address_bits=12,
            contract='Dedicated immutable calendar read port; preserve existing MU playhead fetch latency; '
                     'new descriptor ABI must state exact base/count and validate every range'),
        f16_admission=dict(qualification='ROOT-selected shape, exact artifact and source receipt pending',
            lifecycle_rows=8216,physical_rom_rows=12288,macros_of4096=3,address_bits=14,
            period=8053632,period_bits=23,ovl_entries_per_list=3260,ovl_depth=4096,ovl_address_bits=12,
            area='Lifecycle ROM family differs; do not add its area from the 266-bit table macro'),
        resources=dict(macs_per_cycle=0,rom_bytes_per_slice_cycle=133,table_write_bytes_per_slice_cycle=128,
            boundary_bits_per_slice=1051,new_global_payload_bus_bits=0,
            replicas=12,mux='Four concatenated266bit ROMs; fixed user/layer address map',
            fanout='Regional registered stage/user control; physical copies unimplemented',
            local_macro_um=[w,h],four_macro_safe_outline_um=[388.8,302.4],
            local_macro_origins_um=[[43.2,43.2],[216,43.2],[43.2,172.8],[216,172.8]],
            macro_channels_um=[50.976,66.69],
            all12_local_outline_area_mm2=12*388.8*302.4/1e6,
            ctlm_calendar_candidate_origin_um=[475.2,388.8],
            ctlm_candidate_outline_um=[777.6,518.4],
            ctlm_slot_height_delta_um=86.4,
            raw_49macro_area_mm2=49*w*h/1e6,
            tracks=dict(demand_bits=1051,layers=2,pitch_um=.096,channel_um=86.4,
                        cut_ratio=1051/(2*86.4/.096)),slot_fit=False),
        latency=dict(fixed_read_slots=88,provisional_pipeline_edges=5,reserved_edges_per_layer=93,
            extra_edges_per_36layer_token=3348,reference_layer_period=5569,
            estimated_su_layer_ratio=(5569+93)/5569,
            measured=False,mu_write_windows_proved=False,
            rule='No wait/ready/credit. Reserve non-overlapping88-read windows per user; '
                 'measure macro/loader/VM visibility and recompile all dependent events.'),
        admission=dict(build_admitted=False,rtl_complete=False,
            missing=['All36 checkpoint table payloads and user-address rewrite certificate',
                'Actual MU calendar image and all exclusive loader windows',
                'Dedicated calendar read ABI + loader + real-macro RTL execution',
                'Exact die slot rectangles, registered interface and SAFE checklist',
                'Setup TT, hold FF, native clock spread and area/cycle pricing']))
