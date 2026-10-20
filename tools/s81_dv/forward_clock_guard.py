"""Admit immutable native forwarded-clock exports without rewriting Liberty arcs."""
import hashlib
import json
import math
import re


def _group(text, pin):
    matches = list(re.finditer(r'\bpin\s*\(\s*"?' + re.escape(pin) + r'"?\s*\)\s*\{', text))
    if len(matches) != 1:
        raise ValueError(f'forwarded clock needs one scalar {pin} group')
    depth = 0
    for i in range(matches[0].end() - 1, len(text)):
        depth += (text[i] == '{') - (text[i] == '}')
        if depth == 0:
            return text[matches[0].start():i + 1]
    raise ValueError('unterminated forwarded clock pin')


def validate_native_forwarding(master, corner, lib, read):
    """read(relative_path) resolves bytes from the SAME immutable view git ref.

    The loaded lib is returned unchanged. Legacy SELF tables and hand-edited
    polarity cannot be promoted by the die consumer. Raw native extraction and
    signoff artifacts must travel with the exporter receipt.
    """
    if not re.search(r'\bpin\s*\(\s*"?ck_o"?\s*\)', lib):
        if master.startswith(('dsfd_dvrlyh_', 'dsfd_dvrly_')):
            raise ValueError('relay source requires scalar forwarded clock output')
        return None
    cells = re.findall(r'\bcell\s*\(\s*"?([^"()\s]+)"?\s*\)', lib)
    if cells != [master]:
        raise ValueError('native Liberty master identity mismatch')
    def artifact(name):
        value = read(name)
        if value is None:
            raise ValueError(f'{master}/{corner}: missing native forwarding artifact {name}')
        return value.encode() if isinstance(value, str) else value
    def checked(name, digest):
        if not re.fullmatch('[0-9a-f]{64}', digest or ''):
            raise ValueError(f'invalid native provenance hash: {name}')
        data = artifact(name)
        if hashlib.sha256(data).hexdigest() != digest:
            raise ValueError(f'native provenance mismatch: {name}')
        return data.decode()
    receipt = json.loads(artifact('forwarded_clock.json'))
    abstract = json.loads(artifact('abstract.json'))
    if receipt.get('schema') != 'opentallas.forwarded_clock.routed.v1':
        raise ValueError('missing native routed forwarding schema')
    fc = receipt['corners'][corner]
    if len({v['timing_sense'] for v in receipt['corners'].values()}) != 1:
        raise ValueError('cross-corner forwarding polarity disagreement')
    if abstract.get('forwarded_clock', {}).get(corner) != fc:
        raise ValueError('forwarding receipt differs from source abstract')
    name = abstract['name']
    if name != master or not abstract['corners'][corner]['done']:
        raise ValueError('native export identity/corner incomplete')
    digest = hashlib.sha256(lib.encode()).hexdigest()
    if digest != fc['exported_etm_sha256'] or digest != abstract['files'][f'{master}_{corner}.lib']:
        raise ValueError('native exported Liberty identity mismatch')
    if (fc['input_pin'], fc['output_pin']) != ('ck', 'ck_o'):
        raise ValueError('native forwarding scalar pin contract mismatch')
    sense = fc['timing_sense']
    if master.startswith('dsfd_dvrlyh_') and sense != 'negative_unate':
        raise ValueError('half-cycle source requires native negative polarity')
    if sense not in ('positive_unate', 'negative_unate'):
        raise ValueError('unknown native forwarding polarity')
    group = _group(lib, 'ck_o')
    if re.findall(r'related_pin\s*:\s*"([^"]+)"', group) != ['ck'] or re.findall(r'timing_type\s*:\s*(\w+)', group) != ['combinational'] or re.findall(r'timing_sense\s*:\s*(\w+)', group) != [sense]:
        raise ValueError('legacy SELF/relabelled forwarding arc refused')
    comb = checked(f'forwarded_{corner}.lib.raw', fc['native_combinational_lib_sha256'])
    if _group(comb, 'ck_o') != group:
        raise ValueError('forwarded pin differs from native clock-free ETM')
    raw = checked(f'sequential_{corner}.lib.raw', fc['sequential_etm_before_merge_sha256'])
    # Preserve all sequential/data groups, including every byte outside ck_o.
    if raw.replace(_group(raw, 'ck_o'), '', 1) != lib.replace(group, '', 1):
        raise ValueError('nonforwarded native ETM bytes changed')
    checked(f'export_{corner}.tcl', fc['extraction_tcl_sha256'])
    checked(f'forwarded_clock_signoff_{corner}.sdc', fc['native_signoff_sdc_sha256'])
    for key in ('odb_sha256', 'spef_sha256'):
        if not re.fullmatch('[0-9a-f]{64}', fc.get(key, '')):
            raise ValueError('missing native physical source identity')
    wave = fc['root_waveform_ps']
    if len(wave) != 2 or not all(math.isfinite(x) for x in wave) or wave[0] >= wave[1]:
        raise ValueError('invalid source waveform provenance')
    inverted = sense == 'negative_unate'
    for out_edge, input_edge in (('rise', 'fall' if inverted else 'rise'), ('fall', 'rise' if inverted else 'fall')):
        if fc[f'output_{out_edge}_input_edge'] != input_edge:
            raise ValueError('native phase/polarity provenance inconsistent')
        for bound in ('max', 'min'):
            output_absolute = fc['output_absolute_ps'][f'arrival_{bound}_{out_edge}']
            input_absolute = fc['input_absolute_ps'][f'arrival_{bound}_{input_edge}']
            if not math.isfinite(output_absolute) or not math.isfinite(input_absolute):
                raise ValueError('nonfinite native absolute arrival')
            observed = output_absolute - input_absolute
            if not math.isfinite(observed):
                raise ValueError('nonfinite native observed transfer')
            local = fc['clk_in_to_clk_out_ps'][f'arrival_{bound}_{out_edge}']
            if not math.isfinite(local) or local < 0 or abs(observed-local) > 0.001:
                raise ValueError('native local transfer/input phase mismatch')
    return dict(master=master, corner=corner, timing_sense=sense, exported_etm_sha256=digest,
                odb_sha256=fc['odb_sha256'], spef_sha256=fc['spef_sha256'], root_waveform_ps=wave)
