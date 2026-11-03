#!/usr/bin/env python3
"""Default-OFF adapter for a future reviewed ClockLandings type-source hook.

No caller is installed in the shared generator. Explicit opt-in specializes the
already proved TT_C mechanism into an emitted type without changing top ports or
adding a parameter that an old parent would forget to set. The same input model
produces the paired count-origin record. Global consumers remain required.
"""
import hashlib
import json
import re
import tempfile
from pathlib import Path
try:
    from .source_model_join import validate
    from .prepare_event import build
except ImportError:
    from source_model_join import validate
    from prepare_event import build


def apply_generated_type(tn, text, model, *, enabled=False):
    if not enabled:
        return text, None
    if tn!='tt_ctlm':
        raise ValueError('TT regional origin opt-in is scoped to the selected existing tt_ctlm type')
    match=re.search(r'\bmodule\s+(qfd_qc_tt_ctlm_part(?:_bound)?)\s*\(',text)
    if not match or len(re.findall(r'\bmodule\s+',text))!=1:
        raise ValueError('Requires one unmodified selected TT_C generated type module')
    original_module=match[1]
    normalized=text[:match.start(1)]+'qfd_qc_tt_ctlm_part_bound'+text[match.end(1):]
    with tempfile.TemporaryDirectory(prefix='tt-regional-source-') as tmp:
        root=Path(tmp);source=root/'selected.sv';source.write_text(normalized)
        mapping,homes,raw=validate(source,model)
        event=build(source,mapping,homes,root/'out',raw_homes=raw)
        candidate=(root/'out'/'qfd_qc_tt_ctlm_part_bound_DISABLED.sv').read_text()
    # Explicit plan opt-in selects one fixed reviewed source event. The normal
    # generated design remains byte-identical when absent/default OFF.
    candidate=candidate.replace('qfd_qc_tt_ctlm_part_bound #(parameter integer OT_TT_REGIONAL_ORIGIN=0) (',
                                original_module+' (',1)
    candidate=candidate.replace('OT_TT_REGIONAL_ORIGIN','1')
    helper=Path(__file__).with_name('ot_dp_landing_origin_s_regional.sv').read_text()
    candidate+='\n'+helper
    record=dict(schema='opentallas.tt_generated_regional_origin.v1',enabled=True,
                source_stage_only=True,physical_qualified=False,global_derive_complete=False,
                input_source_sha256=hashlib.sha256(text.encode()).hexdigest(),
                emitted_source_sha256=hashlib.sha256(candidate.encode()).hexdigest(),
                kind='regional_strap',padw=1,raw_parent='rst_rl_85',raw_depth=3,
                retained_raw='rst_n_t0',retained_sampling=['sf','s0'],
                regions=model['qualified_regions'],receiver_regions=mapping,price=model['price'],
                model_sha256=hashlib.sha256(json.dumps(model,sort_keys=True).encode()).hexdigest(),
                helper_default_enable=0,new_top_parameters=0,
                pending_consumers=['ClockLandings manifest/count_origin regional model',
                                   'land_slots and source verifier exact regional forms',
                                   'global reset/START/source-clock rederive',
                                   'actual native count/KEEP/ABI and 63clock name/phase join',
                                   'all physical/parent/IO/TTFF holds'])
    return candidate,record


if __name__=='__main__':
    import argparse
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--source',type=Path,required=True)
    ap.add_argument('--model',type=Path,required=True)
    ap.add_argument('--out',type=Path,required=True)
    ap.add_argument('--enable-reviewed-source-prep',action='store_true')
    a=ap.parse_args()
    text,record=apply_generated_type('tt_ctlm',a.source.read_text(),json.loads(a.model.read_text()),enabled=a.enable_reviewed_source_prep)
    a.out.mkdir(parents=True,exist_ok=True)
    (a.out/'tt_ctlm_source_PREP.sv').write_text(text)
    (a.out/'tt_ctlm_model_PREP.json').write_text(json.dumps(record,indent=1)+'\n')
    print('TT_GENERATED_ADAPTER', 'EXPLICIT_SOURCE_PREP' if record else 'DEFAULT_OFF_BYTE_IDENTICAL')
