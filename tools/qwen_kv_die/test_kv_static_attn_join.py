"""KVJ-SMALL (a): the attention result face / service root joins close the programme's service face."""
import kv_static_attn_join as A


def test_programme_service_face_bound():
    g, bound = A.build()
    ins = {i['name']: i for i in g['instances']}
    p = ins['attention_programme']['inputs']
    for q in ('request_ready',) + A.PROG_FROM_FACE:
        assert p[q] is not None, q
    assert p['request_ready'][0]['instance'] == 'attn_root'
    assert all(p[q][0]['instance'] == 'attn_face' for q in A.PROG_FROM_FACE)
    face_open = sorted(k for k, v in ins['attn_face']['inputs'].items() if v is None)
    assert face_open == sorted(['ck', 'f_data', 'f_epoch', 'f_valid', 'rst_n', 'unit_fault'] + (['f_beat'] if A.STREAM else []))
    assert ins['attn_face']['parameters']['RESULT_RELAY'] is None       # compiler-priced
    root_open = sorted(k for k, v in ins['attn_root']['inputs'].items() if v is None)
    assert root_open == ['ck', 'rst_n']
    # RTL-BUILD-KV/FAULT P8: both capability inputs <- the die cfg capability word
    for n in A.CAP_CONSUMERS:
        assert ins[n]['inputs']['fused_program_capability'] == [dict(instance='diecfg', port='fused_program_capability',
                                                                     lo=0, width=1)], n
    assert ins['diecfg']['parameters']['CAP'] == 1 and ins['boot']['parameters']['DIECAP'] == 1


def test_widths():
    g, _ = A.build()
    ins = {i['name']: i for i in g['instances']}
    assert ins['attention_programme']['inputs']['result_data'][0]['width'] == 512
    assert ins['attn_face']['inputs']['cal'][0]['width'] == 176
