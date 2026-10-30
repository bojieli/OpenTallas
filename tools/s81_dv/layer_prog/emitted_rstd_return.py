"""Actual emitted XF/XR-to-native-VN RSTD return boundary wiring, no epoch."""
import hashlib,json,re
from pathlib import Path
from layer_prog.emitted_leaf_routes import Wiring,_params
from layer_prog.emitted_norm_source import EmittedNormSource
from layer_prog.bound_control import BoundControl


def collect(inventory,latency,native_params):
    die=EmittedNormSource(inventory);lanes={b['lane']:b for b in json.loads(Path(latency).read_text())['buses']}
    native=json.loads(Path(native_params).read_text())['leaves'];by_leaf={(r['slice'],r['leaf']):r for r in native}
    if len(native)!=80 or len(by_leaf)!=80:raise ValueError('actual80-leaf native receiver selection required')
    top=Path(die.source_record['source_top']).read_text();result=[]
    def clock(part):
        h=re.search(r'^\s*\w+(?:\s+#\([^\n]*\))?\s+'+re.escape(part)+r'\s*\(',top,re.M)
        if not h:raise ValueError('actual native clock owner absent')
        body=top[h.end():].split('\n    );',1)[0]
        return _params(body)['clk']
    for sl,row in die.rows.items():
        ctext=Path(row['wrapper_file']).read_text();cw=Wiring(ctext)
        hit=re.search(r'^\s*'+re.escape(row['xr_master'])+r'\s+#\((.*?)\)\s+'+re.escape(row['xr_instance'])+r'\s*\((.*?)^\s*\);',ctext,re.M|re.S)
        ports=_params(hit[2]);valid=cw.bits(ports['rb_v']);data=cw.bits(ports['rb_d']);terminals={n for n,_ in valid+data}
        if len(valid)!=1 or len(data)!=32:raise ValueError('actual XR RSTD output ABI differs')
        if row['params_integer']['QDELAYS']!=0:raise ValueError('nonzero current RSTD release LUT needs its own selected timing contract')
        for k in range(5):
            n=by_leaf[sl,k];file=Path(n['native_file']);raw=file.read_bytes()
            expected_part=row['part'][:-2]+'_L'+str(k)
            head=re.search(r'^\s*(\w+)(?:\s+#\([^\n]*\))?\s+'+re.escape(expected_part)+r'\s*\(',top,re.M)
            expected_file=Path(die.source_record['source_top']).parent/(head[1]+'.sv')if head else None
            if not head or n['part']!=expected_part or n['native_master']!=head[1]or file.resolve()!=expected_file.resolve():
                raise ValueError('RSTD native receiver is not the actual selected top part/master')
            if hashlib.sha256(raw).hexdigest()!=n['native_sha256']:raise ValueError('actual VN receiver leaf changed')
            text=raw.decode();nw=Wiring(text);actual={}
            for half in('a','b'):
                hits=list(re.finditer(r'^\s*(ot_s81sl_vn_'+half+r')\s+#\((.*?)\)\s+(\w+)\s*\((.*?)^\s*\);',text,re.M|re.S))
                if len(hits)!=1:raise ValueError('one actual VN RSTD receiver half required')
                h=hits[0];actual[half]=dict(master=h[1],instance=h[3],params={key:BoundControl._integer(v)for key,v in _params(h[2]).items()},ports=_params(h[4]))
                expected=dict(LA=6,LM=5)
                if half=='b':expected['HW_STAGE']=0
                if actual[half]!=n[half]or actual[half]['params']!=expected or actual[half]['ports']['clk']!='clk':
                    raise ValueError('current qualified VN RSTD receiver ABI/parameter/clock differs')
            bus=lanes['dn_'+row['part'][:-2]+'_L'+str(k)]
            if bus['src']!=row['part']or bus['dst']!=n['part']:raise ValueError('actual RSTD down-lane endpoints differ')
            expr,width=cw.outputs[bus['bus_out']]
            if width!=bus['width']:raise ValueError('actual RSTD native active width differs')
            positions={}
            for i,bit in enumerate(cw.bits(expr)):
                try:net,bitno,age=cw.trace(bit,terminals)
                except ValueError:continue
                positions.setdefault((net,bitno),[]).append((i,age))
            down=[]
            for bit in valid+data:
                hits=positions.get(bit,[])
                if len(hits)!=1:raise ValueError('actual RSTD bit missing or duplicated in native packet')
                down.append(hits[0])
            if len({a for i,a in down})!=1:raise ValueError('actual RSTD valid/data pre-boundary ages disagree')
            receiver={}
            for half in('a','b'):
                fields={};ages=[]
                for port,wanted in [('rb_v',down[:1]),('rb_d',down[1:])]:
                    bits=nw.bits(n[half]['ports'][port])
                    if len(bits)!=len(wanted):raise ValueError('actual VN RSTD receiver width differs')
                    local=[]
                    for bit,(wanted_index,_)in zip(bits,wanted):
                        q,index,age=nw.trace(bit,set(nw.inputs));ext,nwidth=nw.inputs[q];outside=nw.bits(ext)[index]
                        if outside[0]in nw.landings:outside=nw.bits(nw.landings[outside[0]])[outside[1]]
                        if outside!=(bus['bus_in'],wanted_index)or nwidth!=bus['width']:
                            raise ValueError('actual RSTD bit order at VN receiver differs')
                        local.append(age)
                    if len(set(local))!=1:raise ValueError('actual RSTD receiver field ages disagree')
                    fields[port]=dict(bits=len(bits),local_edges=local[0]);ages+=local
                if len(set(ages))!=1:raise ValueError('actual VN RSTD valid/data local ages differ')
                receiver[half]=dict(native=n[half]['instance'],fields=fields,extra_edges=ages[0])
            if receiver['a']['extra_edges']!=receiver['b']['extra_edges']:raise ValueError('actual VN halves RSTD edges differ')
            header=re.search(r'^\s*output\s+wire\s+\[(\d+):0\]\s+'+re.escape(bus['bus_out'])+r'\s*,\s*//\s*(\d+) data \+ epoch \[(\d+)\]: lane '+re.escape(bus['lane'])+r', (\d+) cycles:',ctext,re.M)
            if not header or [int(header[i])for i in(1,2,3)]!=[width]*3 or int(header[4])!=bus['bound_stages']:
                raise ValueError('actual RSTD lane header/cycle differs')
            edges=down[0][1]+bus['bound_stages']+receiver['a']['extra_edges']
            result.append(dict(slice=sl,sid=row['sid'],leaf=k,lane=bus['lane'],active_packet_bits=width,
                rstd_bus_bits=dict(valid=down[0][0],data=[i for i,a in down[1:]]),
                source_clock=clock(row['part']),receiver_clock=clock(n['part']),
                XR_RSTD_output_to_VN_RSTD_input_edges=edges,source_local_edges=down[0][1],bound_lane_edges=bus['bound_stages'],receivers=receiver,
                local_XF_RSTD_to_XR_input_edges=0,XR_RSTD_input_to_output_source_edges=2,
                source_only_XF_RSTD_output_to_VN_input_edges=edges+2,
                source_only_XF_RSTD_output_to_first_Y_edges=edges+2+17,
                clock_scope='relative register-edge accounting under related833ps source clocks; physical phases/global origins unqualified'))
    if len(result)!=80:raise ValueError('all80 actual VN RSTD boundaries required')
    return dict(schema='opentallas.s81.emitted_RSTD_return_boundary.v1',status='PASS_CURRENT_RSTD_BOUNDARY_WIRING',
        source_top_sha256=die.die_sha,leaves=result,XR_local_two_edge_status='actual currentXR1 return cut measured2; XRT3 uses identical shared RSTD source recurrence with QDELAYS0',
        advertised_lane_counts_are_qualified_relative_dates=False,
        source_clock_contract='related833ps clocks with exact emitted tap/forwarded-port identities; physical relative phases are unqualified',
        global_RSTD_dates_qualified=False,physical_clock_phase_qualified=False,physical_START_qualified=False,full_token=False)
