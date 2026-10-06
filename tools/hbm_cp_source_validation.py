"""Validate the allocated CP source and measured successor without evaluating unrelated models."""
def hbm_cp_validate_allocated_sources(root, cp, fourcut=False, fast_owner=False):
    """Bind unchanged CP wiring across the two explicit default-off Jason W2 hooks."""
    import hashlib
    if fast_owner:
        import json
        model=json.loads((root/'results/uarch/hbm_cp_fast_frontier_20261006/model.json').read_text())
        exact=json.loads((root/model['exact_measurement']).read_text())
        if exact['verdict']!='PASS_EXACT_CONNECTED' or exact['checks']!=8713 or exact['parent_checks']!=266:
            raise ValueError('Fast frontier requires its changed exact/connected gate')
        for path,digest in exact['source_sha256'].items():
            if hashlib.sha256((root/path).read_bytes()).hexdigest()!=digest:
                raise ValueError('Fast frontier measured source changed: '+path)
        parent='rtl/hbm_accel/integrated_20261005/ot_ds_hbm_cluster20_integrated.sv'
        text=(root/parent).read_text()
        for hook in model['parent_hooks']:
            count=2 if hook==',.FAST_OWNER_FRONTIER(SU_FAST_OWNER_FRONTIER)' else 1
            if text.count(hook)!=count:raise ValueError('Missing/ambiguous fast CP parent hook: '+hook)
            text=text.replace(hook,'')
        if hashlib.sha256(text.encode()).hexdigest()!=model['parent_reference_sha256']:
            raise ValueError('Selected parent differs beyond actual defaultOFF CP frontier wiring')
        return {path:dict(actual_sha256=exact['source_sha256'][path],allocation_sha256=expected,
                    qualified_combinational_successor=True,parent_ports_unchanged=True,
                    private_factor_bits=12,added_RTL_FF=0,added_cycles=0)
                for path,expected in cp['association_join']['source_sha256'].items()
                if not path.startswith('rtl/test/')}
    checked={}
    parent='rtl/hbm_accel/integrated_20261005/ot_ds_hbm_cluster20_integrated.sv'
    hooks=[',W2_PROTECTED_TRANSACTION_PIPELINE=0',
           ',.PROTECTED_TRANSACTION_PIPELINE(W2_PROTECTED_TRANSACTION_PIPELINE)']
    if fourcut:
        import json
        model=json.loads((root/'results/uarch/hbm_cp_fourcut_20261005/model.json').read_text())
        exact=json.loads((root/model['exact_measurement']).read_text())
        if exact['verdict']!='PASS_EXACT_CONNECTED' or exact['checks']!=8713 or exact['parent_checks']!=266:
            raise ValueError('Four-cut CP source requires its exact connected gate')
        hooks += [',SU_FOUR_COMBINATIONAL_CUTS=0',
                  ',.FOUR_COMBINATIONAL_CUTS(SU_FOUR_COMBINATIONAL_CUTS)']
    for path, expected in cp['association_join']['source_sha256'].items():
        if path.startswith('rtl/test/'):
            continue
        raw=(root/path).read_bytes(); actual=hashlib.sha256(raw).hexdigest()
        normalized=raw
        applied=[]
        if fourcut and path=='rtl/hbm_accel/integrated_20261005/ot_hbm_integrated_su_cp_bind.sv':
            if actual!=exact['source_sha256'][path]:
                raise ValueError('Four-cut source differs from measured exact gate')
            checked[path]=dict(actual_sha256=actual,allocation_sha256=expected,
                unchanged_CP_ports=True,qualified_combinational_successor=True,
                added_FF=0,added_cycles=0)
            continue
        if fourcut and path==parent:
            for hook in hooks[-2:]:
                token=hook.encode()
                if normalized.count(token)!=1:
                    raise ValueError('Missing/ambiguous CP forwarding hook: '+hook)
                normalized=normalized.replace(token,b'',1);applied.append(hook)
            if hashlib.sha256(normalized).hexdigest()!=model['parent_reference_sha256']:
                raise ValueError('Selected parent differs beyond the two measured CP forwarding hooks')
            if actual!=exact['source_sha256'][path]:
                raise ValueError('Selected parent differs from connected-gate source pin')
            checked[path]=dict(actual_sha256=actual,allocation_sha256=expected,
                parent_reference_commit=model['parent_reference_commit'],
                parent_reference_sha256=model['parent_reference_sha256'],
                unchanged_CP_ports=True,unchanged_W2_wiring=True,joined_CP_hooks=applied)
            continue
        if actual!=expected and path==parent:
            for hook in hooks:
                token=hook.encode()
                if normalized.count(token)!=1:
                    raise ValueError('Missing/ambiguous selected W2 forwarding hook: '+hook)
                normalized=normalized.replace(token,b'',1);applied.append(hook)
        if hashlib.sha256(normalized).hexdigest()!=expected:
            raise ValueError('CP allocated source or parent wiring changed: '+path)
        checked[path]=dict(actual_sha256=actual, allocation_sha256=expected,
                           unchanged_CP_wiring=True, joined_W2_hooks=applied)
    return checked

