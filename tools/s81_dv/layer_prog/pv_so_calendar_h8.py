"""R5 native H8 source calendar; actual route ages are required, no adoption."""


def plan_halves_h8(east_earliest, west_earliest, route_ages, cfg_capture_edge, parameter_last_pin_edge, gap=1):
    keys = ('E_E', 'E_W', 'W_E', 'W_W')
    if set(route_ages) != set(keys) or any(type(route_ages[k]) is not int or route_ages[k] < 0 for k in keys):
        raise ValueError('Four actual nonnegative integer route/landing ages required')
    if any(type(v) is not int or v < 0 for v in (cfg_capture_edge, parameter_last_pin_edge, gap)):
        raise ValueError('Source calendar uses nonnegative rising edges')
    if len(east_earliest) != 2 or len(west_earliest) != 2 or any(type(v) is not int or v < 0 for v in (*east_earliest, *west_earliest)):
        raise ValueError('Two actual earliest departures per half required')
    ea = max(route_ages['E_E'], route_ages['E_W'])
    wa = max(route_ages['W_E'], route_ages['W_W'])
    passes, next_arrival = [], cfg_capture_edge + 3
    for k in range(2):
        ed = max(east_earliest[k], next_arrival - ea)
        er = ed + ea
        wd = max(west_earliest[k], er + 320 + gap - wa)
        wr = wd + wa
        passes.append(dict(k=k, east_departure=ed, west_departure=wd, east_arrival=er, west_arrival=wr,
                           extra_source_edges=dict(E=ed-east_earliest[k], W=wd-west_earliest[k])))
        next_arrival = wr + 320 + gap
    er0, wr0 = passes[0]['east_arrival'], passes[0]['west_arrival']
    er1, wr1 = passes[1]['east_arrival'], passes[1]['west_arrival']
    fs = [x-cfg_capture_edge for x in (er0, wr0, er1, wr1)]
    if any(not 3 <= x < 65536 for x in fs):
        raise ValueError('Four first-record dates must fit actual16-bit fields after configuration')
    launch = max(wr1 + 321, parameter_last_pin_edge + 1)
    return dict(passes=passes, cfg_capture_edge=cfg_capture_edge, route_age=dict(route_ages),
                extra_padding={k:(ea if k[0]=='E' else wa)-route_ages[k] for k in keys},
                entry_E=dict(local_first=fs[0],peer_first=fs[1],local_first1=fs[2],peer_first1=fs[3]),
                entry_W=dict(local_first=fs[1],peer_first=fs[0],local_first1=fs[3],peer_first1=fs[2]),
                source_records_per_half_per_pass=320, joined_records=1280,
                launch_pin_edge=launch, first_generated_q=launch+2, last_generated_q=launch+1085,
                generated_words=534, generated_frames=17, job_gate_added_frames=17,
                so_order=[g for i in range(8) for g in (i,i+8)], so_operand_row_interval=2,
                calendar_qualified=False,
                remaining='Apply both passes GO/PVO and completion dates to actual source programme; join owner/epoch '
                          'and original SOT write/read/retire windows; qualify actual composed numerical mechanism')


def control_frames_h8(owner, position, se_jid, so_jid, local_first, peer_first, local_first1, peer_first1, parameters):
    if type(owner) is not int or not 0 <= owner < 2**20 or type(position) is not int or not 0 <= position < 2**21:
        raise ValueError('Actual20-bit owner and21-bit position required')
    if any(type(v) is not int or not 0 <= v < 256 for v in (se_jid, so_jid)):
        raise ValueError('Actual8-bit SE/SO identity required')
    fs = (local_first, peer_first, local_first1, peer_first1)
    if any(type(v) is not int or not 3 <= v < 65536 for v in fs) or any(abs(fs[i]-fs[j]) < 320 for i in range(4) for j in range(i+1,4)):
        raise ValueError('Four disjoint320-edge windows after configuration required')
    if local_first1 <= local_first or peer_first1 <= peer_first:
        raise ValueError('Each half must deliver pass0 before pass1')
    if len(parameters) != 5 or any(type(v) is not int or not 0 <= v < 2**512 for v in parameters):
        raise ValueError('Five actual position-owned512-bit parameter rows required')
    def hdr(subop, n, spec):
        return (15<<508)|(1<<503)|((owner&255)<<495)|(n<<480)|(position<<459)|(((owner>>8)&1023)<<449)|(subop<<444)|spec
    cfg = owner | (se_jid<<20) | (so_jid<<28)
    for x, shift in zip(fs, (36,52,68,84)):
        cfg |= x << shift
    return dict(CFG=[hdr(0,0,cfg)],PARAM=[hdr(1,5,owner)]+list(parameters),LAUNCH=[hdr(2,0,owner)])
