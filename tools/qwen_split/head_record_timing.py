"""Derive one shared P1 capture age from the actual bound HEAD/witness paths."""
from pathlib import Path
import re


def coherent_depth(ctx, sink, ports, source, source_ports):
    depths = set()
    for port, source_port in zip(ports, source_ports):
        rows = ctx.timing_depths(sink, port)
        if not rows:
            raise ValueError('missing actual P1 tuple: ' + sink + '.' + port)
        for row in rows.values():
            if (row.get('kind') not in ('intra', 'crossing') or
                    row.get('source') != source or row.get('source_port') != source_port):
                raise ValueError('wrong actual P1 tuple source: ' + sink + '.' + port)
            value = row.get('landed_stages')
            if type(value) is not int or value < 0:
                raise ValueError('unknown actual P1 path age: ' + sink + '.' + port)
            depths.add(value)
    if len(depths) != 1:
        raise ValueError('incoherent actual P1 tuple: ' + sink)
    return depths.pop()


def derive(ctx):
    head = coherent_depth(ctx, 'sys_face', ['prog_head_context_slot'],
                          'd2d_rom', ['prog_head_context_slot'])
    witness = coherent_depth(ctx, 'sys_face', ['prog_witness_slot'],
                             'd2d_rom', ['prog_witness_slot'])
    record = coherent_depth(ctx, 'd2d_rom', ['prog_tx_observed_v', 'prog_tx_record'],
                            'sys_face', ['prog_tx_observed_v', 'prog_tx_record'])
    # The explicit three-master source cohort selects PR1 on the D2D end and
    # the exact wrapped face: callback output capture1 + face input1 + actual
    # record producer1 + face output1 + D2D input capture1. These are not wires.
    intrinsic = dict(d2d_callback_capture=1, face_input_capture=1,
                     record_producer=1, face_output_capture=1, d2d_record_capture=1)
    if head != witness:
        raise ValueError(f'P1 callback paths differ: HEAD {head}, witness {witness}; '
                         f'align existing INNER callback paths to {max(head,witness)} before binding')
    txd = head + record + sum(intrinsic.values())
    if not 1 <= txd <= 255:
        raise ValueError('actual P1 producer capture age exceeds TXDP byte')
    return dict(schema='opentallas.qwen.head_record_timing.v1',
                head_callback_edges=head, witness_callback_edges=witness,
                record_return_edges=record, intrinsic_edges=intrinsic,
                port1_txd=txd, send_slot_to_bank_sample_edges=head+2,
                scope='Source endpoint ages; current phase/clock, package calendar and physical closure remain separate')


def emitted(bound, *, paths_only=False):
    """Independent readback of emitted glue, not the hook's claimed depths."""
    text = (Path(bound)/'rtl/qfd_qc_glue_part.sv').read_text()
    headers = {}
    def connections(master, instance):
        match = re.search(r'\b' + master + r'\s*(?:#\(.*?\))?\s+' + instance + r'\s*\((.*?)\n\s*\);', text, re.S)
        if match is None:
            raise ValueError('actual selected P1 emitter instance missing: ' + instance)
        headers[instance] = match.group(0).split(instance, 1)[0]
        return dict(re.findall(r'\.([A-Za-z_]\w*)\(([^()]*)\)', match.group(1)))
    face = connections('qfd_sys_face_lctx3_wrapped', 'u_sys_face')
    link = connections('qfd_d2d_static_ovl_sf7_obs1', 'u_d2d_rom')
    delays = {}
    for match in re.finditer(r'ot_dp_dly\s*#\(\.W\(\d+\),\s*\.D\((\d+)\)\)\s+\w+\s*\(\.clk\([^()]+\),\s*\.d\((\w+)\),\s*\.q\((\w+)\)\)', text):
        stages, source, sink = match.groups()
        if sink in delays:
            raise ValueError('duplicate emitted P1 delay driver')
        delays[sink] = (source, int(stages))
    def depth(sink, port, source, source_port):
        net = re.sub(r'\[[^]]*\]', '', (face if sink=='sys_face' else link)[port]).strip()
        expected = 'w_' + source + '_' + source_port
        total = 0; seen = set()
        while net != expected:
            if net in seen or net not in delays:
                raise ValueError('emitted P1 path is not the declared registered source: ' + port)
            seen.add(net);net, count = delays[net];total += count
        return {0: dict(kind='intra', source=source, source_port=source_port, landed_stages=total)}
    class Readback:
        def timing_depths(self, sink, port):
            if sink == 'sys_face':
                return depth(sink, port, 'd2d_rom', port)
            return depth(sink, port, 'sys_face', port)
    ctx = Readback()
    if paths_only:
        return dict(
            head_callback=coherent_depth(ctx,'sys_face',['prog_head_context_slot'],'d2d_rom',['prog_head_context_slot']),
            witness_callback=coherent_depth(ctx,'sys_face',['prog_witness_slot'],'d2d_rom',['prog_witness_slot']),
            record_return=coherent_depth(ctx,'d2d_rom',['prog_tx_observed_v','prog_tx_record'],'sys_face',['prog_tx_observed_v','prog_tx_record']),
            context_ingress=coherent_depth(ctx,'sys_face',['prog_context_slot','prog_rx_v','rx_payload'],'d2d_rom',['prog_context_slot','prog_rx_v','rx_payload']))
    result = derive(ctx)
    native = (Path(bound)/'rtl/qfd_qc_native59_part.sv').read_text()
    for text, key in ((headers['u_d2d_rom'],'HEAD_CONTEXT'),
                      (headers['u_sys_face'],'L_CONTEXTS'), (native,'ROPE')):
        if not re.search(r'\.'+key+r'\(\s*1\s*\)', text):
            raise ValueError('actual emitted coherent source parameter is not enabled: ' + key)
    return result
