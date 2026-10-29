"""Explicit coherent-source parameters missing from the legacy r56 snapshot.

The opt-in belongs to the compute die's ONE source/profile event. It neither
changes RTL defaults nor silently upgrades historical bind manifests.
"""

SCHEMA = 'opentallas.qwen.head_prepare_params.v1'
SELECTED = {'d2d_rom': 'qfd_d2d_static_ovl_sf7_obs1',
            'native59': 'qfd_native59_dv_headprep_obs1',
            'sys_face': 'qfd_sys_face_lctx3_wrapped'}
REQUIRED = {'d2d_rom': {'HEAD_CONTEXT': 1},
            'native59': {'ROPE': 1},
            'sys_face': {'L_CONTEXTS': 1}}


def regen(ctx):
    profile = ctx.ab.get('qwen_head_prepare_profile')
    if profile is None:
        return {}, None
    if profile.get('schema') != SCHEMA or profile.get('selected_masters') != SELECTED:
        raise ValueError('explicit coherent HEAD source/profile selection required')
    index = ctx.cell_index()
    old = {}
    for path, master in SELECTED.items():
        if path not in index:
            raise ValueError('coherent HEAD leaf absent: ' + path)
        cell = ctx.F.cells[index[path]]
        if cell.module != master:
            raise ValueError('coherent HEAD selected master differs: ' + path)
        defaults = ctx.param_defaults.get((cell.ytype, cell.module), {})
        for key in REQUIRED[path]:
            value = str(cell.params.get(key, defaults.get(key, 'MISSING'))).strip('"')
            if value not in ('0', '1'):
                raise ValueError('coherent HEAD source parameter absent/nonboolean: ' + path + '.' + key)
            old[path + '.' + key] = int(value)
    return {path: dict(params) for path, params in REQUIRED.items()}, dict(
        schema=SCHEMA, selected_masters=dict(SELECTED), original=old,
        bound={path + '.' + key: value for path, params in REQUIRED.items() for key, value in params.items()},
        scope='SOURCE_CANDIDATE; changed native59 and glue types need current profile/image, model and physical qualification',
        added_pipeline_edges=0, native_embedding_terminal_index=dict(legacy=64, selected=84, delta=20),
        programme_effects=['enable existing recurring HEAD callback',
                           'enable existing eight-word RoPE read after embedding',
                           'select existing segment1 for layer stages2..36'])
