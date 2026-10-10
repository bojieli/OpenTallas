"""G25 native row gather, sized before RTL; generic frontend still pending."""
from pathlib import Path
import hashlib
import re


def inverse_selected_model(k=512, group=96, row_words=32):
    """Candidate compact inverse OWNED map; no throughput/adoption credit."""
    if not (1 <= k <= 2048 and group in (1, 2, 4, 8, 96) and row_words in (9, 16, 32)):
        raise ValueError('inverse map shape outside accepted native shape')
    root = Path(__file__).resolve().parents[1]
    lef_path = Path('physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.lef')
    lef = (root / lef_path).read_bytes()
    width, height = map(float, re.search(rb'SIZE\s+([\d.]+)\s+BY\s+([\d.]+)', lef).groups())
    macro_area = width * height
    replicas = 4
    # 32-bit payload with 7 SECDED bits. Six independently protected records
    # fit one 256-bit word; actual macro exposes a 256-bit write mask.
    map_words = (2048 + 5) // 6
    owner_words = (96 + 5) // 6
    map_macros = (map_words + 127) // 128
    owner_macros = (owner_words + 127) // 128
    count = replicas * (map_macros + owner_macros)
    fifo_macros = replicas * 3
    return dict(schema='hgi.inverse-selected.candidate.v1', default_enable=0,
        qualification='MODEL ONLY; no RTL, route or rate credit',
        models=['DeepSeek-V4.1 HBM', 'Qwen3-8B HBM'], replicas_per_die=1,
        k=k, group=group, row_words=row_words, row_bytes=row_words*64,
        mapping='count owner occurrences in R; prefix counts -> base[r]; inverse[base[r]+j]=original selected index i',
        empty_slot='j>=count[r] drains and returns credit without VM write; never reads inverse entry',
        restore_order='final row i exactly follows original selected list R, including duplicate selections as distinct owned slots',
        map_payload='32b protected record: 11b selected i plus reserved validity/identity; bounds checked against K',
        owner_payload='32b protected record: 12b base and 12b count; count/base sum checked against K',
        records_per_sram_word=6, protected_record_bits=39,
        map_max_records=2048, owner_max_records=96,
        read_replicas=replicas, map_words_per_replica=map_words,
        owner_words_per_replica=owner_words,
        map_macros_per_replica=map_macros, owner_macros_per_replica=owner_macros,
        map_macro_count=count, map_macro_area_um2=count*macro_area,
        macro_lef=str(lef_path), macro_lef_sha256=hashlib.sha256(lef).hexdigest(),
        macro_dimensions_um=[width,height], macro_area_um2=macro_area,
        lookup_mux='4 independent: owner6:1x39, map3:1x256 and6:1x39; each macro pin and decode boundary registered',
        build_write='one selected entry per issue, replicated to all four maps; bit-mask39 per record, full readiness guard after build',
        provider_warning='legacy native SRAM simulation model ignores w_mask_in; not usable for packed-map proof',
        map_init='no per-op full clear: overwrite every live owner and all K compact records before accepting delivery; slots outside owner count suppressed',
        build_cycles_conservative=6*k+2*group+16,
        build_cycle_basis='two serialized R passes, three cycles per entry per pass including count read/modify/write and inverse publish; owner count initialization and prefix plus16 pipeline/drain',
        lookup_added_cycles=8,
        finite_credit_candidate_per_lane=128,
        credit_register_bits=replicas*8*2+1,
        credit_control_protection='8b remaining count and its complement per lane; mismatch blocks reservation combinationally and latches fault',
        credit_added_pipeline_cycles=0,
        credit_round_trip_basis='35 forward wire +35 return wire +8 lookup +2 VM acknowledgement =80 cycles before arbitration; actual arbitration may extend it and stalls must be measured',
        fifo_macro_count=fifo_macros, fifo_macro_area_um2=fifo_macros*macro_area,
        fifo_protection='512b payload as sixteen SECDED39 records +48b protected identity =672b; three256b macros per lane,128 entries',
        credit_contract='reserve before endpoint delivery selection; return on filtered slot or acknowledged destination; protected counters and overflow/underflow/identity faults mandatory',
        memory_read_bytes_per_cycle=replicas*2*32,
        memory_write_bytes_per_cycle=replicas*32,
        deliver_bits_per_cycle=replicas*545, vm_requested_bytes_per_cycle=replicas*64,
        vm_ack='each64B flit two32B sectors; shared per-bank producer arbiter and routed completion ledger required',
        vm_bank_conflict='FP32 row stride64sectors aliases row starts at bank0 in VM32; cannot assume four flits accepted per cycle',
        vm_capacity='K512 FP32 n512 consumes full1MiB VM; live interval admission or separately priced protected destination is required',
        total_candidate_sram_area_um2=(count+fifo_macros)*macro_area,
        floorplan_slot_um=[600,240], sram_slot_fit_fraction=(count+fifo_macros)*macro_area/(600*240),
        area_fit_status='SRAM only; clock channels, logic, muxes and consumer storage excluded, floorplan pending',
        macs_per_cycle=0, communication_intensity='bit-preserving selection restore',
        routing_tracks_needed=4*545+4*(512+20+16+1), routing_capacity=6250,
        routing_basis='separate pin faces; shared VM boundary and credit return boundary still require route proof',
        latency_contribution='transport model plus build and lookup/ack; finite-credit and bank-arbitration simulation pending, no latency headline')
def model(m=18, row_words=32, group=96):
    pf=m*row_words
    if not (1 <= m <= 2048 and row_words in (9,16,32)):
        raise ValueError('native staged gather shape outside M2048')
    chunk_rows=512//row_words
    chunks=(m+chunk_rows-1)//chunk_rows
    return dict(schema='hgi.native-row-gather.v1', default_enable=0,
        models=['DeepSeek-V4.1 HBM','Qwen3-8B HBM'], replicas_per_die=1,
        macs_per_cycle=0, compute_intensity='bit-preserving gather and address transpose',
        communication_bytes=group*pf*64, memory_read_bytes_per_cycle=64,
        memory_write_bytes_per_cycle=4*64,
        destination_writer_status='256B/cycle sink assumed by endpoint bus; real HBM writer throughput and ack binding required before credit', staging_bytes=512*64, row_bytes=row_words*64, native_epochs=chunks, rows_per_epoch=chunk_rows,
        descriptor_contract='current DS compiler FP32 n512 ->2048B row /32flits; packed288B read/decode not implemented or credited',
        staging_required_protection='external existing protected SU/VM store; no unprotected new SRAM',
        inject_bits_per_cycle=512, deliver_bits_per_cycle=4*545,
        control_input_bits=8+8+16+16, output_bits_per_cycle=4*(512+20+16+1),
        mux_cost='existing endpoint single bypass inject, four independent delivery address pipelines',
        demux_cost='recipient rank guard; four independently registered sink lanes',
        fanout='one registered run descriptor per delivery lane',
        routing_tracks_needed=4*545+4*(512+20+16+1), routing_capacity=6250,
        routing_basis='separate input/output faces: each needs <=2196 tracks, versus6250 per300um layer; estimate, actual boundary check owed',
        new_register_bits=4*(4*512+3*8+4*16+7)+56+4,
        pipeline_address_arithmetic='rank*pf then local /9,%9 or shift, then slot*G+rank; each boundary registered',
        estimated_new_cell_area_um2=16000, floorplan_slot_um=[600,240],
        area_fit_fraction=16000/(600*240),
        delivery_added_cycles=4, launch_added_cycles=1, completion_added_cycles=5,
        gather_flits_per_rank=pf, endpoint_pfmax=512,
        full_group_gi_limit=65536, largest_epoch_gi=group*512-1,
        chunk_staging_contract='load_v/load_row/load_rows ->load_r only after protected inject store fully staged',
        delivery_service_floor_cycles=(group*pf+3)//4,
        software_slot_cycles=m*(768+633),
        native_analytical_cycles=pf+chunks*633+(group*pf+3)//4+chunks*12,
        latency_composition='stage owned flits + one TU flight per <=512flit complete-row epoch + delivery floor +12 control/drain/pin edges per epoch; overlap not credited',
        numerical_order='no arithmetic; rank-major wire stream maps to slot-major j*G+r',
        qualification='analytic only; exact endpoint full shape, record/HBM binding and physical closure required')
