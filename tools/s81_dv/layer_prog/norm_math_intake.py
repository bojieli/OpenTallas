"""Attach actual current norm component evidence to its exact native input image.

This is a math/source contract only. It cannot supply transport/GO/retirement or
physical START authority, and cannot repair an unadopted PDSK selector.
"""
import hashlib,json
from pathlib import Path

REQUIRED_SOURCES=frozenset((
    'physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v',
    'physical/asap7_memory_macros_v2/ot_sram_1r1w_512x128_m4_r0c0/ot_sram_1r1w_512x128_m4_r0c0.v',
    'rtl/dsrom_sys/s81_dv/ot_s81dv_norm.sv',
    'rtl/dsrom_sys/s81_dv/slice/ot_s81sl_aq12x.sv',
    'rtl/dsrom_sys/s81_dv/slice/ot_s81sl_vn.sv',
    'rtl/dsrom_sys/s81_dv/slice/ot_s81sl_vp.sv',
    'rtl/dsrom_sys/s81_dv/slice/ot_s81sl_vq.sv',
    'rtl/dsrom_sys/s81_dv/slice/ot_s81sl_vs.sv',
    'rtl/dsrom_sys/s81_dv/slice/ot_s81sl_vsw.sv',
    'rtl/dsrom_sys/s81_suhc/hier/ot_s81_su_rxh.sv',
    'rtl/dsrom_sys/s81_suhc/hier/ot_s81_su_sw.sv',
    'rtl/dsrom_sys/s81_suhc/ot_s81_su_rw.sv',
    'rtl/dsrom_sys/s81_suhc/ot_s81_su_rx.sv',
    'rtl/hdc/ot_hdc_delay.sv',
    'rtl/hdc/ot_hdc_fastfp.sv',
    'rtl/hdc/ot_hdc_fastfp_lat_f12.sv',
    'rtl/hdc/ot_hdc_fp32_add_lat.sv',
    'rtl/hdc/ot_hdc_fp32_f12.sv',
    'rtl/hdc/ot_hdc_fp32_mul_lat.sv',
    'rtl/hdc/ot_hdc_fp32_mul_pipe.sv',
    'rtl/hdc/ot_hdc_fpu.sv',
    'rtl/hdc/ot_hdc_prefix.sv',
    'rtl/hdc/ot_hdc_sfu.sv',
    'rtl/hdc/v41/ot_hdc_actquant.sv',
    'rtl/hdc/v41/ot_hdc_fdiv.sv',
    'rtl/hdc/v41/ot_hdc_fsqrt.sv',
    'rtl/hdc/v41/ot_hdc_softplus.sv',
    'rtl/hdc/v41x/ot_dsrom_aq12.sv',
    'rtl/hdc/v41x/ot_dsrom_divc.sv',
    'rtl/hdc/v41x/ot_dsrom_fp32_add_l6.sv',
    'rtl/hdc/v41x/ot_dsrom_su_add6.sv',
    'rtl/hdc/v41x/ot_dsrom_su_f12.sv',
    'rtl/hdc/v41x/ot_dsrom_su_fdiv_f12.sv',
    'rtl/hdc/v41x/ot_dsrom_su_hcpost.sv',
    'rtl/hdc/v41x/ot_dsrom_su_hcpost_lane_pr.sv',
    'rtl/hdc/v41x/ot_dsrom_su_norm.sv',
    'rtl/hdc/v41x/ot_dsrom_su_swiglu.sv',
    'rtl/hdc/v41x/ot_hbm_norm_split.sv',
    'rtl/hdc/v41x/ot_hdc_v41x_sfu.sv',
    'rtl/hdc/v41x/ot_hdc_v41x_spshort.sv',
    'rtl/lib/ot_rst_relay.sv',
    'rtl/proto/ot_fp32_add_rne_pipe.sv',
))


def attach_math(entry,program,directory,source_root):
    directory=Path(directory);source_root=Path(source_root)
    read=lambda name:json.loads((directory/name).read_text())
    captured=read('valid_capture/receipt.json');xf=read('xf/receipt.json');rescale=read('rescale/receipt.json')
    if captured['status']!='PASS_ACTUAL_VALID_PARTIAL_CAPTURE' or xf['status']!='PASS_CURRENT_SELECTED_MATH_COMPONENT_ONLY' or rescale['status']!='PASS_CURRENT_NATIVE_NORM_RESCALE_COMPONENT_ONLY':
        raise ValueError('passing current native norm component chain required')
    for proof in (captured,xf,rescale):
        if proof['selected_source_top_sha256']!=program['die_sha256']or entry['die_sha256']!=program['die_sha256']:
            raise ValueError('current norm math and selected native source differ')
        if proof['clock_ps']!=833:raise ValueError('current norm component clock differs')
    from layer_prog.emitted_norm_source import EmittedNormSource
    EmittedNormSource(program['source_inventory'])
    native=read('producer/native_params.json')['leaves']
    if len(native)!=80 or {(r['slice'],r['leaf'])for r in native}!={(sl,k)for sl in program['selected_slices']for k in range(5)}:
        raise ValueError('complete current80-leaf native operator selection required')
    for row in native:
        if row['a']['params']!=dict(LA=6,LM=5)or row['b']['params']!=dict(HW_STAGE=0,LA=6,LM=5)or row['vp_n_go_to_vn_edges']!=0 or row['vn_chain_extra_edges']!=0:
            raise ValueError('actual native norm operator parameters/seams differ')
        if hashlib.sha256(Path(row['native_file']).read_bytes()).hexdigest()!=row['native_sha256']:
            raise ValueError('actual selected native leaf body changed')
    selection=captured['source_selection']
    selected_path=Path(selection['path'])
    if hashlib.sha256(selected_path.read_bytes()).hexdigest()!=selection['sha256']:
        raise ValueError('actual norm source selection changed')
    defines=json.loads(selected_path.read_text())['defines']
    for proof in(captured,xf,rescale):
        if proof['defines']!=defines or set(proof['source_sha256'])!=REQUIRED_SOURCES:
            raise ValueError('complete selected norm dependency/define closure required')
    image=[]
    for sid in range(16):
        for k in range(5):
            writes=[w for w in entry['writes']if w['sid']==sid and w['leaf']==k]
            if len(writes)!=49:raise ValueError('current norm entry needs49 real rows per leaf')
            image.extend(f'{w["row"]:04x}{w["data128"]}'for w in writes)
    image_hash=hashlib.sha256(('\n'.join(image)+'\n').encode()).hexdigest()
    if image_hash!=captured['actual_input_image_sha256']or image_hash!=rescale['actual_input_image_sha256']:
        raise ValueError('norm component input image differs from current genuine entry')
    partial_file=directory/'valid_capture/actual_partials80.hex'
    partial_sha=hashlib.sha256(partial_file.read_bytes()).hexdigest()
    if len(partial_file.read_text().split())!=80 or partial_sha!=captured['actual_partial_input_sha256']or partial_sha!=xf['actual_partial_input_sha256']:
        raise ValueError('actual valid-time partial handoff differs')
    scalar=xf['actual_rstd32'];scalar_sha=hashlib.sha256((scalar+'\n').encode()).hexdigest()
    if scalar!=rescale['actual_rstd32']or scalar_sha!=rescale['actual_rstd_input_sha256']:
        raise ValueError('actual XF scalar and VN rescale input differ')
    if xf['native_GO_config_epsilon_source']!=program['epsilon_source']:
        raise ValueError('actual norm epsilon differs from current native GO source')
    if xf['actual_selected_parameters']!=dict(NS=16,NVL=5,LM=5,LA=6,SIW=7):
        raise ValueError('actual selected XF dimensions/ABI differ')
    if rescale['actual_vectors128']!=640 or rescale['actual_BF16_elements']!=5120 or rescale['errors']!=0:
        raise ValueError('complete exact current native rescale required')
    sources={}
    for proof in(captured,xf,rescale):
        for name,wanted in proof['source_sha256'].items():
            if Path(name).is_absolute()or '..'in Path(name).parts:raise ValueError('norm component source path differs')
            if name in sources and sources[name]!=wanted:raise ValueError('norm components use conflicting source bodies')
            sources[name]=wanted
    for name,wanted in sources.items():
        if hashlib.sha256((source_root/name).read_bytes()).hexdigest()!=wanted:raise ValueError('current norm component body changed: '+name)
    return dict(schema='opentallas.s81.current_norm_math_intake.v1',status='QUALIFIED_CURRENT_COMPONENT_MATH_ONLY',
        input_image_sha256=image_hash,actual_partial_sha256=partial_sha,actual_rstd32=scalar,
        actual_BF16_elements=5120,source_sha256=sources,
        component_edges=dict(VP_command_pin_to_partial=captured['VP_command_pin_to_partial_edges'],
            VN_RSTD_pin_to_first_Y=rescale['VN_RSTD_pin_to_first_Y_edges']),
        native_programme_qualified=False,global_GO_qualified=False,global_RSTD_dates_qualified=False,
        physical_START_qualified=False,full_token=False,
        holds=['actual selected PDSK/candidate adoption and native issuer/partial calendar',
            'actual physical NX/GO/RSTD/VQ K-profile and retirement','global HOST/reset/KS/START source authority'])
