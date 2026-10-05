"""Source-only index producer domain check; zero checkpoint data reads.

The retained producer outputs decoded BF16-valued F32 arrays, not 68B wire rows.
Microfixtures reproduce that source quantizer; they are not GPU instructions.
"""
import ast
import hashlib
from pathlib import Path
import numpy as np
import hdc_golden as G
import hdc_golden_v41 as V


def build():
    root=Path(__file__).resolve().parents[1]
    paths=['tools/hdc_golden_v41.py','tools/w19_hbm_tp96_isa.py',
           'tools/deepseek_hbm_complete_executor.py',
           'tools/deepseek_hbm_complete_index_producer_scope.py']
    snippets={}
    for path in paths[:2]:
        tree=ast.parse((root/path).read_text())
        for node in ast.walk(tree):
            if isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef)) and node.name in ['qdq_fp4_e8m0','_ceil_log2','_round_grid','f_index_q','f_compressor']:
                segment=ast.get_source_segment((root/path).read_text(),node)
                snippets[path+':'+node.name]={'line':node.lineno,'sha256':hashlib.sha256(segment.encode()).hexdigest()}
    fixtures=[]
    for name,value in [('zero',np.float32(0)),('smallest_subnormal',np.nextafter(np.float32(0),np.float32(1))),
                       ('scale252',np.float32(6*2.0**125)),
                       ('finite_scale253',np.float32(6.1*2.0**125)),('maximum_finite_F32',np.finfo(np.float32).max)]:
        row=np.full(32,value,np.float32)
        amax=np.maximum(np.max(np.abs(row)),V.FP4_AMAX_FLOOR_E8M0).astype(np.float32)
        exponent=int(V._ceil_log2(G.mul(amax,V.FP4_MAX_INV)))
        with np.errstate(over='ignore',invalid='ignore',under='ignore'):out=V.qdq_fp4_e8m0(row)
        fixtures.append({'name':name,'input_bits':int(value.view(np.uint32)),'scale_exponent':exponent,
                         'UE8M0_candidate_code':exponent+127,'output_first_bits':int(out[0].view(np.uint32)),
                         'all_outputs_finite':bool(np.all(np.isfinite(out))),
                         'ingress_scale_1_to_252_admitted':1<=exponent+127<=252})
    return {'schema':'opentallas.deepseek.index-producer-domain.v1',
            'source_pins':{p:hashlib.sha256((root/p).read_bytes()).hexdigest() for p in paths},
            'function_bindings':snippets,'checkpoint_data_reads':0,'microfixtures':fixtures,
            'finite_F32_input_scale_domain':[1,253],
            'candidate_ingress_scale_domain':[1,252],'full_source_domain_coverage':False,
            'actual_source_storage':'decoded BF16-valued F32 arrays; StateArray software byte view of decoded values',
            'actual_68B_producer_found':False,'wire_ordering_admitted_from_source':False,
            'required_before_production':['packed producer explicit code/scales output and byte order',
                'scale253 handling incl producer BF16 overflow/no-Inf policy',
                'zero sign/canonicalization preserved at producer rounding points',
                'integer quantizer/packer cost and finite shared/controller publication binding'],
            'numerical_microfixture_backend':'retained reference source, no GPU/DUT credit',
            'physical_admission':'FAIL_CLOSED'}
