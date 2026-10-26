"""Carry explicit unqualified clock sources through reports; never grant qualification."""


def require_measured_input_boundaries(artifact):
    """A model input boundary cannot acquire a native target through absent-R fallback."""
    if artifact.get('unmeasured_input_boundaries'):
        raise ValueError('UNMEASURED input-boundary ETM has no native clock insertion target')


def carry_unqualified(*artifacts):
    sources, models = [], {}
    for artifact in artifacts:
        if not isinstance(artifact, dict):
            continue
        q = artifact.get('qualification')
        if artifact.get('physical_qualification_eligible') is False or q is False or \
                (isinstance(q, dict) and q.get('scope') == 'MODEL_ONLY'):
            sources.append(dict(schema=artifact.get('schema'), source=artifact.get('source'),
                                source_sha256=artifact.get('source_sha256'), qualification=q))
        for name, master in artifact.get('masters', {}).items():
            if master.get('physical_qualification_eligible') is False or master.get('view') == 'MODEL_PASS_THROUGH_R0':
                models[name] = master
    if not sources and not models:
        return {}
    return dict(physical_qualification_eligible=False,
                qualification=dict(scope='MODEL_ONLY', unqualified_sources=sources, modeled_masters=models))
