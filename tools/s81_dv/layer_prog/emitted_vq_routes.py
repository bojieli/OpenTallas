"""Read actual80 native VQ fragment producers and their XG receive wiring.

This exposes the selected final-normalization publication interfaces. It does
not assign activation values or infer absolute GO/RSTD/START dates.
"""
import hashlib,json,re
from pathlib import Path
from layer_prog.emitted_norm_source import EmittedNormSource,_params
from layer_prog.emitted_leaf_routes import Wiring
from layer_prog.bound_control import BoundControl


def collect(inventory,latency):
    die=EmittedNormSource(inventory);top_path=Path(die.source_record['source_top']);top=top_path.read_text()
    bind=top_path.parent.parent;names=json.loads((bind/'bind_names.json').read_text())
    raw=json.loads(Path(latency).read_text())
    if raw.get('schema')!='opentallas.die_plan.bind.v1':raise ValueError('actual bound lane record required')
    lanes={row['lane']:row for row in raw['buses']};out=[]
    for sl,row in sorted(die.rows.items(),key=lambda item:item[1]['sid']):
        ctext=Path(row['wrapper_file']).read_text();cw=Wiring(ctext)
        xg=list(re.finditer(r'^\s*(ot_s81sl_xg\w*)\s+(\w+)\s*\((.*?)^\s*\);',ctext,re.M|re.S))
        if len(xg)!=1:raise ValueError('one actual XG fragment receiver required')
        ports=_params(xg[0][3]);fields={n:cw.bits(ports[n])for n in('xf_v','xf_s','xf')}
        if [len(fields[n])for n in('xf_v','xf_s','xf')]!=[5,5,1380]:raise ValueError('actual five-leaf fragment receiver width differs')
        for leaf in range(5):
            part=row['part'][:-2]+'_L'+str(leaf)
            header=re.search(r'^\s*(\w+)(?:\s+#\((.*?)\))?\s+'+re.escape(part)+r'\s*\(',top,re.M)
            if not header:raise ValueError('actual selected native leaf absent')
            native=top_path.parent/(header[1]+'.sv');body=native.read_text()
            vq=list(re.finditer(r'^\s*(ot_s81sl_vq)\s+#\((.*?)\)\s+(\w+)\s*\((.*?)^\s*\);',body,re.M|re.S))
            if len(vq)!=1:raise ValueError('one actual native VQ producer required')
            vq=vq[0];p=_params(vq[4]);params=_params(vq[2])
            if params!={'AQ_XMEM':'2'}or p['clk']!='clk':raise ValueError('actual VQ SRAM/clock selection differs')
            vn=list(re.finditer(r'^\s*(ot_s81sl_vn_b)\s+#\((.*?)\)\s+(\w+)\s*\((.*?)^\s*\);',body,re.M|re.S))
            if len(vn)!=1:raise ValueError('one actual native VN output producer required')
            vn=vn[0];np=_params(vn[4]);nw=Wiring(body);ystages=set()
            va=list(re.finditer(r'^\s*ot_s81sl_vn_a\s+#\((.*?)\)\s+\w+\s*\((.*?)^\s*\);',body,re.M|re.S))
            if len(va)!=1:raise ValueError('one actual native VN low-half producer required')
            na=_params(va[0][2])
            for field in('y_v','y_i','y'):
                a=(nw.bits(na['y'])+nw.bits(np['y']))if field=='y'else nw.bits(np[field])
                b=nw.bits(p[field]);terminals={n for n,_ in a}
                if len(a)!=len(b):raise ValueError('actual VN-to-VQ stream width differs')
                for aa,bb in zip(a,b):
                    name,index,age=nw.trace(bb,terminals)
                    if(name,index)!=aa:raise ValueError('actual VN-to-VQ output bit/order differs')
                    ystages.add(age)
            if len(ystages)!=1:raise ValueError('actual VN-to-VQ valid/index/data age differs')
            yage=ystages.pop()
            producer=names.get(part+'.'+vq[3])
            if not producer or not producer.startswith(sl+'.')or not producer.endswith('.u_vq'):
                raise ValueError('native VQ source lacks exact bound identity')
            defaults={name:value for width,name,value in re.findall(r'parameter\s+\[(\d+):0\]\s+(\w+)\s*=\s*([^,\n]+)',body)}
            overrides=_params(header[2]or'')
            def strap(port,width):
                m=re.fullmatch(r'(\w+)\['+str(width-1)+r':0\]',p[port])
                if not m:raise ValueError('actual VQ strap expression differs')
                return BoundControl._integer(overrides.get(m[1],defaults.get(m[1],'')))
            sid,k=strap('sid',4),strap('k',3)
            if sid!=row['sid']or not 0<=k<8:raise ValueError('actual VQ source SID/K differs')
            up=lanes['up_'+part]
            if up['src']!=part or up['dst']!=row['part']:raise ValueError('actual VQ fragment lane endpoints differ')
            mappings={};ages=set()
            for field,bits in [('xf_v',[fields['xf_v'][leaf]]),('xf_s',[fields['xf_s'][leaf]]),('xf',fields['xf'][276*leaf:276*(leaf+1)])]:
                mapped=[]
                for index,bit in enumerate(bits):
                    q,j,extra=cw.trace(bit,set(cw.inputs));expr,width=cw.inputs[q];external=cw.bits(expr)[j]
                    if external[0]in cw.landings:external=cw.bits(cw.landings[external[0]])[external[1]]
                    if width!=up['width']or external!=(up['bus_in'],j)or up['source_bits'][j]!=['leaf',producer,field,index]:
                        raise ValueError('actual VQ fragment bit/order/producer differs')
                    mapped.append(j);ages.add(extra)
                mappings[field]=mapped
            if len(ages)!=1:raise ValueError('VQ fragment valid/start/data ages differ')
            extra=ages.pop()
            out.append(dict(slice=sl,sid=sid,leaf=leaf,global_beat=5*sid+leaf,
                source=producer,source_module=vq[1],source_instance=vq[3],source_parameters=params,VN_to_VQ_stream_edges=yage,native_VN_b_parameters=_params(vn[2]),
                native_part=part,native_module=header[1],native_source_sha256=hashlib.sha256(native.read_bytes()).hexdigest(),
                output_ports=dict(valid='xf_v',fragment0='xf_s',data='xf'),fragment_width=276,fragments_per_beat=4,
                bf16_values_per_beat=64,bf16_value_bits=16,selected_vq_k=k,selected_local_stagger_edges=4*k,
                lane=up['lane'],fragment_bus_bits=mappings,VQ_output_to_XG_input_edges=up['bound_stages']+extra,
                source_clock='native leaf clk',receiver_clock='C-wrapper XG clk',physical_phase_qualified=False,
                actual_output_edge=None,payload_source='selected native VN normalization stream into VQ; no fixture output substituted'))
    if len(out)!=80:raise ValueError('all80 actual publication producers required')
    return dict(schema='opentallas.s81.emitted_VQ_publication_boundary.v1',status='PASS_CURRENT_VQ_SOURCE_AND_BOUNDARY_WIRING',
        source_top_sha256=die.die_sha,source_view_sha256=die.source_record['source_view_sha256'],records=out,
        publication_beats=80,bf16_elements=5120,fragment_beats=320,global_calendar_qualified=False,
        numeric_values_verified=False,physical_START_qualified=False,full_token=False,
        holds=['actual native input state/final_NORM producer programme','RSTD/VN/VQ dates and output collisions',
               'complete source-bound transport to HEAD and actual current HOST/calendar programme'])
