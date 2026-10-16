"""Native attention microcalendar (PC11: ME WSRC native59 -> KV-die static attention service) for compile_calendar.

The production service is ot_qwen_tp8_attention_native_service_w16 (16 V rows/cycle P.V, results/arch/
qwen_attention_rate_1015).  Its per-request 176-bit calendar and its measured service length come from
tools/qwen_attention_native/attn_calendar.py (production pv='w16'): nothing here is guessed or traced.
The link between the compute die and the KV die is NOT known to this module: the request edges (PC11 issue ->
service start_qk) and the result edges (last result beat -> compute-die landing) are required inputs from the link
owner (Q-DVM+LINK, tools/qwen_split/d2d_link_calendar.py); a missing or invalid age refuses the schedule.
The service holds one request at a time: a static buffer of capacity 1 (occupied start_qk .. last beat) makes the
compiler reject overlapping attention issues instead of the hardware stalling.
"""
import importlib.util
from pathlib import Path

from .calendar import ScheduleError

ROOT = Path(__file__).resolve().parents[2]
_spec = importlib.util.spec_from_file_location('attn_calendar', ROOT / 'tools/qwen_attention_native/attn_calendar.py')
AC = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(AC)
SERVICE_RTL = ('u_kvd.u_attention', 'ot_qwen_tp8_attention_native_service_w16')
Q_BEATS = 32
# KV-die v1.4.3 head stages (el1014-qwen-split-kvsys.log, Q-KVSYS-DIE G3S2): +3 gather in, +2 score back = +5 edges per
# attention request. ECTL HXK=13 includes the native r4 head's eight edges and these five stages.
# The full composition at 22ff95ba0 passes 53 contexts only when every dependent age moves +5;
# increasing the final duration alone emits an early, incorrect internal programme.
V143_HEAD_EDGES = 5
RESULT_BEATS = 32


def service(T, pv='w16'):
    """per-request calendar fields, hex word and the measured start_qk -> last result beat length (edges)"""
    if pv != 'w16':
        raise ScheduleError('production attention is the w16 service; w1 is reference only')
    try:
        c = AC.calendar(T, pv='w16', head_g3s2=True)
    except ValueError as error:
        raise ScheduleError(f'attention calendar refused: {error}') from error
    edges = AC.service_cycles(c)
    return dict(T=T, fields=c, calendar_hex=AC.hexcal(c), service_edges=edges,
                measured_w16_edges=edges - V143_HEAD_EDGES, head_stage_edges=V143_HEAD_EDGES)


# Measured link + KV endpoint ages (core edges), 2026-10-15:
#  * D2D data port, pin-registered r4 masters qfd/qkd_d2d_static_r1 + PHY 5 trained: send slot S -> KV die-master
#    OUTPUT pin S+18 (CMD / Q beats), RESULT beat S -> compute die-master output pin S+18 (Q-DVM+LINK 20:18:35,
#    results/arch/qwen_split_1014/link_static_1015/program_calendar_prod_1015/calendar.json, tools/qwen_split/
#    d2d_link_calendar.py --pinreg; physical qualification pending, CTS-only fixes expected, 0 cycles).
#  * KV static endpoint qkd_native_attention_programme (Codex Q-STATIC-ENDPOINT c5e2e9903, branch
#    codex/qwen-native-static-endpoint-2116, NOT yet on main / root review): record rx 1 edge, start_qk 2 edges after
#    the CMD record (Q beats stream in behind it), last result beat -> RESULT record tx 1 edge.
#  request_edges = CMD send slot -> start_qk = 18 + 2 = 20; result_edges = last result beat -> compute pin = 1 + 18 = 19.
MEASURED_LINK = dict(request_edges=18 + 2, result_edges=1 + 18,
                     sources=dict(link='results/arch/qwen_split_1014/link_static_1015/program_calendar_prod_1015/calendar.json',
                                  endpoint='c5e2e9903:results/arch/qwen_native_static_endpoint_1015/programme_8192.json'),
                     status='link RTL-compiled (physical pending); endpoint component unmerged')


def _age(link, name):
    v = link.get(name)
    if type(v) is not int or v < 1:
        raise ScheduleError(f'unassigned or invalid attention link age: {name}')
    return v


def pc11_implementation(record, T, layer, link, clock='core', period_fs=None):
    """compile_calendar instruction implementation of one actual PC11 word at context T.

    record: inventory record of the PC11 word (stage, pc, word, unit); link: {'request_edges', 'result_edges'};
    period_fs: the core clock period (edges -> fs)."""
    if record.get('unit') != 1:
        raise ScheduleError('attention is issued by the ME unit (PC11, WSRC native59)')
    if type(period_fs) is not int or period_fs <= 0:
        raise ScheduleError('attention microcalendar needs the implemented core clock period')
    req, res = _age(link, 'request_edges'), _age(link, 'result_edges')
    s = service(T)
    n = s['service_edges']
    ev = [dict(id='q_send', offset_fs=0, resource='attn.q_link', requires=[f'q:{layer}'], kind='attention_q', beat=0,
               buffer_delta={'attn.service': 1}),
          dict(id='start_qk', offset_fs=req * period_fs, resource='attn.service_start', kind='attention_start',
               epoch=layer, address=int(s['calendar_hex'], 16) & ((1 << 64) - 1)),
          dict(id='last_result_beat', offset_fs=(req + n) * period_fs, resource='attn.result', kind='attention_result',
               beat=RESULT_BEATS - 1, buffer_delta={'attn.service': -1}),
          dict(id='result_landed', offset_fs=(req + n + res) * period_fs, resource='attn.result_landing',
               kind='attention_landing', produces=[f'attn_out:{layer}'])]
    return dict(stage=record['stage'], pc=record['pc'], word=record['word'], unit=1, clock=clock,
                rtl_instance=SERVICE_RTL[0], rtl_module=SERVICE_RTL[1], events=ev,
                attention=dict(T=T, calendar_hex=s['calendar_hex'], service_edges=n, request_edges=req, result_edges=res,
                               source='tools/qwen_attention_native/attn_calendar.py pv=w16 head_g3s2=True HXK=13'))


def resources(clock='core'):
    return {k: dict(clock=clock, capacity=1) for k in ('attn.q_link', 'attn.service_start', 'attn.result', 'attn.result_landing')}


def buffers():
    return {'attn.service': dict(capacity=1, initial=0, final=0)}


def per_layer_table(contexts=(1, 1000, 4096, 8192)):
    return {T: service(T)['service_edges'] for T in contexts}
