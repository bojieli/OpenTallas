"""Source-bound sizing proposals, not a floorplan gate or a SAFE claim.

Canonical macro abstracts remain byte-identical. Full-face periphery is only a
compiler proposal: it must be generated/physically validated, never LEF surgery.
"""
from __future__ import annotations
import collections
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
MACROS = dict(fifo='ot_sram_1r1w2c_8x285_m1',landing='ot_sram_1r1w_256x256_m2_r2c2',
              cache='ot_sram_1r1w_128x256_m1_r2c2',program='ot_sram_1r1w_1024x256_m2_r2c2')


def macro(name):
    path=ROOT/'physical/asap7_memory_macros_v2'/name/(name+'.lef')
    raw=path.read_bytes();text=raw.decode();w,h=map(float,re.search(r'SIZE ([.\d]+) BY ([.\d]+)',text).groups())
    faces=collections.Counter();proposal=collections.Counter();pins=0
    for pin,body in re.findall(r'\n  PIN (\S+)\n(.*?)\n  END \1(?=\n|$)',text,re.S):
        if re.search(r'USE (POWER|GROUND)',body):continue
        x0,y0,x1,y1=map(float,re.search(r'RECT ([.\d]+) ([.\d]+) ([.\d]+) ([.\d]+)',body).groups())
        dist=dict(W=x0,E=w-x1,S=y0,N=h-y1);faces[min(dist,key=dist.get)]+=1;pins+=1
        proposal['N' if pin.startswith('rd_out[') else 'S' if pin.startswith(('wd_in[','w_mask_in[')) else 'W']+=1
    return dict(name=name,source=str(path.relative_to(ROOT)),sha256=hashlib.sha256(raw).hexdigest(),
        width_um=w,height_um=h,area_um2=w*h,signal_clock_pins=pins,
        canonical_faces=dict(faces),canonical_face_density={f:n/(h if f in 'WE' else w) for f,n in faces.items()},
        fullface_compiler_proposal=dict(pins=dict(proposal),density={f:n/(h if f in 'WE' else w) for f,n in proposal.items()},
            status='PROPOSAL ONLY: regenerate real pin/periphery routing and macro abstracts/timing; preserve canonical views'))


def model(pair_stdcell_area_um2=None,rotator_stdcell_area_um2=None):
    m={k:macro(v) for k,v in MACROS.items()}
    pair_area=2*(m['landing']['area_um2']+m['fifo']['area_um2'])
    inventory=dict(landing=8,fifo=8,cache=5,program=2,descriptor=2)
    # Generous single-band proposal: two macro rows, one continuous cell band.
    placements=[dict(kind='landing',bank='j',origin_um=[43.2,43.2],orientation='R0'),
        dict(kind='fifo',bank='j',origin_um=[259.2,43.2],orientation='R0'),
        dict(kind='landing',bank='j+4',origin_um=[43.2,172.8],orientation='MX'),
        dict(kind='fifo',bank='j+4',origin_um=[259.2,172.8],orientation='MX')]
    band=[86.424,172.8];width=432.;height=259.2
    band_area=width*(band[1]-band[0])
    pair=dict(replica_count=4,banks=['j','j+4'],actual_macros=4,macro_area_um2=pair_area,
        landing_capacity='two 256x256 macros, each packs FOUR 64-row landing blocks; never four macros/bank',
        fifo_capacity='two actual 8x285 dual-clock SRAMs',
        outline_proposal_um=[width,height],aspect=width/height,macro_only_fill=pair_area/(width*height),
        macro_placements=placements,all_macro_origins_on_43p2_lattice=True,
        full_width_cell_band_y_um=band,band_area_um2=band_area,
        placement_util_target=[.4,.6],measured_stdcell_area_um2=pair_stdcell_area_um2,
        stdcell_band_height_at_50pct_um=None if pair_stdcell_area_um2 is None else pair_stdcell_area_um2/(.5*width),
        stdcell_band_rule='select a single connected full-width placement band from measured area; unused access channels are routing reservations; final dimensions OPEN until synthesis',
        access_channels_um=dict(left=43.2,between_macro_columns=259.2-(43.2+m['landing']['width_um']),
          right=width-(259.2+m['fifo']['width_um']),central_read_face_channel=band[1]-band[0]),
        proposed_fullface_orientation='bottom row R0 North-read faces band; upper row MX South-read faces band; write/mask face outward; canonical WE faces retain generous side channels',
        clocks=['pair_hbm_clk[j]','pair_clk[j]','return_clk[j]'],reset='separate two-stage release per root; balanced raw reset of HBM/stream FIFO and all return/cache roots',
        REQUIRED_source_remap='old bank g/4 stream_bank_clk/hbm_fifo_clk mapping spans BOTH roots for {j,j+4}; map BOTH banks to pair_clk[j] and explicit pair_hbm_clk[j]',
        return_partition='ENTIRE ringSlice inside pair: source wp/slots + forwarded-return rp/readmux/outputQ; registered261-wire output; no select feedback',
        port_budget=dict(HBM_data_valid_inputs=572,HBM_ready_overflow_outputs=4,
          stream_reserve_stop_read_inputs_per_bank=41,stream_control_inputs_two_banks=82,
          local_ordinal_valid_inputs=4,root_clock_reset_inputs=6,
          completion_bank_fault_outputs=8,registered_return_data_ordinal_valid_phasefault_outputs=261,
          total_inputs=664,total_outputs=273,total=937),
        face_proposal='return261+stream-control copies on cache-facing full E/W face; split572 HBM inputs across remaining full faces; pin-register collars stay connected to central band',
        return_face_density_all261_over_full_height=261/height,
        communication=dict(HBM_response_input_bits_per_edge=570,stream_landing_read_bits_per_edge=512,
          registered_return_bits_per_edge=261,useful_return_bytes_per_stream_edge=32,
          pair_target_bytes_per_stream_edge=99/4,return_payload_util_at_target=(99/4)/32,
          minimum_tracks_for_registered_bus=261,one_layer_channel_width_um_at_048_pitch=261*.048,
          full_face_length_um_at_6pins_per_um=261/6),
        max_external_density_at_capacity_6='one face may carry <=1555 pins at259.2um, <=2592 at432um; explicit final pin enumeration and collar placement remain OPEN',
        reach='put selected-data/return-Q mass at cache-facing edge; place both landing output capture/select slices adjacent; no logical end-to-end tile wire assumed; mapped <=405um audit OPEN',
        critical_fanout='kept per16bit selection/ring slices; replicated reset/control distribution and inherited epoch/seen/count bank-mux fanout require mapped audit',
        gate_ready=False)
    rot=dict(actual_macros=0,outline_proposal_um=[129.6,129.6],aspect=1.,diagonal_um=(2*129.6**2)**.5,
        inputs=1046,outputs=1029,functional_data_registers=3072,metadata_ring_bits=16,
        native_root='cache_clk',reset='two stages, balanced with pair/local-return roots; no payload reset mass',
        face_split=dict(N_input_pair01=522,S_input_pair23=522,E_outputs=515,W_outputs=514),
        max_face_density=522/129.6,pin_limited_min_face_um=522/6,
        full_width_connected_cell_region=True,clock_entry='beside input/rotate mass, centre-fed local root',
        measured_stdcell_area_um2=rotator_stdcell_area_um2,placement_util_target=[.4,.6],
        outline_rule='129.6 is pin-envelope proposal only; enlarge from measured synthesis area if >60%, reserve connected routing collar if pin-limited; no final utilization claim',
        gate_ready=False)
    cache=dict(actual_macros=5,macro=m['cache']['name'],macro_area_um2=5*m['cache']['area_um2'],
        separate_from_rotator=True,outline_proposal_um=[475.2,259.2],
        macro_origins_um=[[43.2,43.2],[172.8,43.2],[302.4,43.2],[43.2,172.8],[302.4,172.8]],
        full_width_cell_band_y_um=[84.264,172.8],orientation_bottom='R0',orientation_top='MX',
        utilization='OPEN: derive placement band from synthesis after assembler storage redesign',
        OPEN_STORAGE_BLOCKER=dict(source='rtl/hbm_accel/loader/service_native/ot_hbm_svc_static_sm_packed136.sv',
          object='words[0:15][255:0]',runtime_bits=4096,writes_per_edge_max=4,gather_reads_per_edge=5,
          head_advance=[4,4,4,5],input_pulses=[4,4,4,4,1],
          requirement='must become actual SRAM/banked prefetch storage, or a <=2kb ring only AFTER live-window proof + full burst bench; no speculative reduction'))
    total=8*m['landing']['area_um2']+8*m['fifo']['area_um2']+7*m['cache']['area_um2']+2*m['program']['area_um2']
    return dict(schema='opentallas.svg-source-bound-element-sizing.v1',macros=m,pair_element=pair,
        cache_rotator_element=rot,remaining_nine_macros=dict(payload_cache=cache,
          descriptor=dict(count=2,macro=m['cache']['name'],area_um2=2*m['cache']['area_um2'],source='ot_hbm_svc_sm_issuer_rel DD=256'),
          program=dict(count=2,macro=m['program']['name'],area_um2=2*m['program']['area_um2'],source='ot_smh_calendar_static_x AW=11')),
        whole_SM_current_inventory=inventory,current_macro_count=25,current_macro_area_um2=total,
        macro_inventory_warning='25 describes CURRENT source; resolving4096bit assembler may add macros. Not production-qualified.',
        canonical_pin_access_audit='OPEN: actual canonical LEFs are~10pins/um on WE M4 faces; 6/um applicability to macro versus external faces awaits owner interpretation. No cosmetic LEF edit or SAFE claim.',
        fullface_proposal='real compiler variant: all rd_out North, wd_in+w_mask_in South, controls/repair West; all counted faces<=6/um for these four macros except verify generated periphery timing',
        regional_clock_trees=dict(stream=9,HBM=4,total=13,source_domains='four pair HBM, four pair stream, four local forwarded cache-phase, one cache core',scope='landing/return minimum only; payload/program/issuer physical roots remain OPEN'),
        timing='return pipeline remains7edges; compiler prefetch15=8native landing+7return. Actual root/source mapping and ordinary nearest-edge timing OPEN before gate',
        qualification='MODEL/OUTLINE PROPOSAL ONLY; source macro inventory measured, synthesis area/face placement/reach/fanout/clock evidence missing; NO gate/submit')


if __name__=='__main__':
    print(json.dumps(model(),indent=2))
