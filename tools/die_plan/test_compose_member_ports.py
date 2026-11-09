import json
import compose_member_ports as C


def spec():
    return {'cores': [{'inst': 'h.__cut_vm', 'module': 'x', 'members': ['h.u_body.u_vmasm', 'h.u_body.u_writer'],
                       'ports': {
                           'clk': {'dir': 'input', 'bits': [[{'member': 'h.u_body.u_vmasm', 'port': 'clk', 'bit': 0},
                                                             {'member': 'h.u_body.u_writer', 'port': 'clk', 'bit': 0}]]},
                           'vm_kq': {'dir': 'output', 'bits': [[{'member': 'h.u_body.u_writer', 'port': 'kq1', 'bit': 0}],
                                                               [{'member': 'h.u_body.u_writer', 'port': 'kq0', 'bit': 1}],
                                                               [{'member': 'h.u_body.u_writer', 'port': 'kq0', 'bit': 0}],
                                                               [{'member': 'h.u_body.u_writer', 'port': 'kq1', 'bit': 1}]]},
                           'vm_rr__b2': {'dir': 'input', 'bits': [[{'member': 'h.u_body.u_vmasm', 'port': 'rd_il', 'bit': 2}],
                                                                  [{'member': 'h.u_body.u_vmasm', 'port': 'rd_il', 'bit': 3}]]},
                           'vm_rr__b0': {'dir': 'input', 'bits': [[{'member': 'h.u_body.u_vmasm', 'port': 'rd_il', 'bit': 0}],
                                                                  [{'member': 'h.u_body.u_vmasm', 'port': 'rd_il', 'bit': 1}]]},
                       }}]}


def test_rename(tmp_path):
    inp = tmp_path / 'c.json'
    inp.write_text(json.dumps(spec()))
    out = tmp_path / 'o.json'
    C.main([str(inp), str(out), '--inst', r'h\.__cut_vm', '--prefix', 'u_writer=writer_', '--prefix', 'u_vmasm=vmasm_',
            '--add-input', 'writer_sid=u_writer.sid:2'])
    d = json.loads(out.read_text())['cores'][0]['ports']
    assert sorted(d) == ['clk', 'vmasm_rd_il', 'writer_kq0', 'writer_kq1', 'writer_sid']
    assert [b[0]['bit'] for b in d['writer_kq0']['bits']] == [0, 1]
    assert [b[0]['port'] for b in d['vmasm_rd_il']['bits']] == ['rd_il'] * 4
    assert [b[0]['bit'] for b in d['vmasm_rd_il']['bits']] == [0, 1, 2, 3]
    assert d['writer_kq1']['dir'] == 'output'
    assert d['writer_sid']['dir'] == 'input' and len(d['writer_sid']['bits']) == 2


def test_hole_fails(tmp_path):
    s = spec()
    s['cores'][0]['ports']['vm_rr__b0']['bits'].pop()
    inp = tmp_path / 'c.json'
    inp.write_text(json.dumps(s))
    try:
        C.main([str(inp), str(tmp_path / 'o.json'), '--inst', r'h\.__cut_vm', '--prefix', 'u_writer=writer_', '--prefix', 'u_vmasm=vmasm_'])
    except SystemExit as e:
        assert 'holes' in str(e)
    else:
        raise AssertionError
