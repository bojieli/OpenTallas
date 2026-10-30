"""Read only actual emitted C-wrapper SID/XRT literals, never transport ages."""
import hashlib,json,re
from pathlib import Path
from layer_prog.bound_control import BoundControl


def _params(text):return {k:v.strip()for k,v in re.findall(r'\.(\w+)\(([^()]*)\)',text)}


class EmittedNormSource:
    def __init__(self,record):
        r=json.loads(Path(record).read_text())if not isinstance(record,dict)else record
        if r.get('schema')!='opentallas.s81.event3_emitted_sid_xr_inventory.v1':raise ValueError('actual emitted norm source inventory required')
        unhashed={k:v for k,v in r.items()if k!='source_view_sha256'}
        if hashlib.sha256(json.dumps(unhashed,sort_keys=True,separators=(',',':')).encode()).hexdigest()!=r.get('source_view_sha256'):
            raise ValueError('emitted source inventory payload changed')
        for name,wanted in r['source_files_sha256'].items():
            if hashlib.sha256(Path(name).read_bytes()).hexdigest()!=wanted:raise ValueError('actual emitted source changed: '+name)
        top=Path(r['source_top']).read_text()
        if r['source_files_sha256'].get(r['source_top'])!=r['source_top_sha256']:raise ValueError('emitted top identity missing')
        self.rows={};self.selected={};self.deskew={};self.die_sha=r['source_top_sha256'];self.source_record=r
        for row in r['slices']:
            sl=row['logical_slice'];part=row['part'];sid=row['sid']
            if not re.fullmatch(r's_[0-7][SN]_C',part)or row['xr_master']not in ('ot_s81sl_xrt1','ot_s81sl_xrt3'):
                raise ValueError('selected emitted slice/XR ABI differs')
            if type(sid)is not int or not 0<=sid<16 or sl!='u_'+part[:-2]or sl in self.rows or (sid&1)!=(1 if sl.endswith('N')else 0):
                raise ValueError('actual emitted slice/SID identity differs')
            text=Path(row['wrapper_file']).read_text()
            if r['source_files_sha256'].get(row['wrapper_file'])!=row['wrapper_sha256']:raise ValueError('wrapper identity absent')
            mod=re.search(r'^module (\w+)',text,re.M)
            if not mod or mod[1]!=row['wrapper_module']:raise ValueError('actual emitted wrapper master differs')
            pattern=r'^\s*'+re.escape(row['xr_master'])+r'\s+#\((.*?)\)\s+'+re.escape(row['xr_instance'])+r'\s*\((.*?)^\s*\);'
            hits=list(re.finditer(pattern,text,re.M|re.S))
            if len(hits)!=1:raise ValueError('actual emitted XR instance absent/ambiguous')
            hit=hits[0];params=_params(hit[1]);wanted=row['params_raw']
            if params!={k:v.strip()for k,v in wanted.items()}:raise ValueError('actual emitted XR parameter literals differ')
            integers={k:BoundControl._integer(v)for k,v in params.items()}
            if any(type(v)is not int for v in row['params_integer'].values())or integers!=row['params_integer']:
                raise ValueError('evaluated emitted XR parameters differ')
            if set(integers)!={'FACE_LAND','FOREG','PDSK','QDELAYS'}or not 0<=integers['PDSK']<1<<15:raise ValueError('actual XR parameter ABI differs')
            sidexpr=re.search(r'\.sid\(([^)]+)\)',hit[2])
            if not sidexpr or sidexpr[1]!=row['sid_expression']:raise ValueError('actual XR SID connection differs')
            actualpath=re.findall(r'// as-built (\S+)',text[:hit.start()])[-1]
            if actualpath!=row['canonical_emitted_leaf_path']:raise ValueError('actual emitted XR source path differs')
            defaults=dict(re.findall(r'parameter\s+\[3:0\]\s+(\w+)\s*=\s*([^,\n]+)',text))
            ipat=r'^\s+'+re.escape(row['wrapper_module'])+r'(?:\s+#\((.*?)\))?\s+'+re.escape(part)+r'\s*\('
            instances=list(re.finditer(ipat,top,re.M))
            if len(instances)!=1:raise ValueError('actual top partition instance absent/ambiguous')
            override=_params(instances[0][1]or'');sidname=row['sid_parameter']
            literal=override.get(sidname,defaults.get(sidname,''))
            if BoundControl._integer(literal)!=sid or literal.strip()!=row['sid_raw_literal'].strip()or override.get(sidname)!=row['sid_top_override']:
                raise ValueError('actual top SID override differs')
            allsid={n:override.get(n,v).strip()for n,v in defaults.items()if n.endswith('_sid')}
            if allsid!=row['all_sid_literals']or any(BoundControl._integer(v)!=sid for v in allsid.values()):raise ValueError('actual slice XF/XG/XR SID straps disagree')
            self.rows[sl]=row;self.selected[sl]=dict(sid=sid,master=row['wrapper_module'],params=integers,source_path=actualpath,physical_part=part)
            self.deskew[sl]=[(integers['PDSK']>>(3*k))&7 for k in range(5)]
        if len(self.rows)!=16 or sorted(s['sid']for s in self.selected.values())!=list(range(16)):
            raise ValueError('all16 actual source slices/SID0..15 required')
    def slices(self):return self.selected
