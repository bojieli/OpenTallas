"""Native QE callback bridge: canonical selected field QE/ME -> released raw words.

Private inherited connection, same existing wire codec; no filesystem socket,
allocator, images, activations, output oracle or numerical execution.
"""
import argparse
import hashlib
import json
import re
import socket
import struct
from pathlib import Path
import dsrom_s82_payload_interface as API
from dsrom_s82_native_word_server import serve_connection, receive


def require(ok, message):
    if not ok:
        raise ValueError(message)


def native_pp_word_map(matrix, pair):
    """PP issue address -> canonical payload address, within one allocated run.

    Match the existing PP image compiler's segment/half interleaving. The
    canonical payload inverse uses word-major/row-minor order; PP issues both
    FP8 halves for each row before moving to the next row. No values, macro
    capacity, request count or native arithmetic change.
    """
    S = API.M.C.S
    segments, addresses, allocated = [], {}, []
    for si, owner, first, n, stride, start, count in matrix['plans']:
        if owner != pair:
            continue
        e0, elems = matrix['segments'][si]
        order = S.segment_order(matrix['format'], e0, elems)
        require(len(order) == count, 'PP source word count mismatch')
        for j in range(n):
            index = len(segments)
            segments.append(dict(fmt=matrix['format'], e0=e0, elems=elems,
                                 row=first+j*stride, tensor=matrix['tensor']))
            for k, (u, b, h) in enumerate(order):
                addresses[index, u, b, h] = start+k*n+j
        allocated.extend(range(start, start+n*count))
    require(allocated and len(set(allocated)) == len(allocated), 'PP allocation absent/overlapping')
    start = min(allocated)
    require(set(allocated) == set(range(start, start+len(allocated))),
            'PP source phase must own a contiguous word range')
    issue = S.element_order(segments)
    require(len(issue) == len(allocated), 'PP phase coverage mismatch')
    result = {start+i: addresses[key] for i, key in enumerate(issue)}
    require(set(result.values()) == set(allocated), 'PP source packing must be bijective')
    return result


class ReleasedQeOperationWords:
    def __init__(self, execution, source, node, rank, *, fragment=0, expert_ids=None,
                 native_pp=False):
        require(re.fullmatch(r'L\d+\.I\d+', node) is not None, 'actual source node required')
        require(type(rank) is int and 0 <= rank < 4, 'TP4 rank')
        require(source.root.resolve().name == API.SNAPSHOT, 'released checkpoint required')
        instruction = execution.source.nodes[node]['instruction']
        unit = instruction['unit']
        qe = unit == 3 and instruction['qe_mode'] == 0
        me = unit == 1 and instruction['me_wsrc'] == 0
        require(qe or me, 'only source-weight mode0 QE or weight-source ME')
        slot = execution.source.bindings[node]['selector_slot']
        if slot is not None:
            require(expert_ids is not None, 'actual captured six EIDs required; no catalogue/default expert')
        else:
            require(expert_ids is None, 'unexpected expert selection for static source')
        # IDs come from the caller's accepted native EID publication and lease.
        # SourceExecution validates six distinct ascending IDs; never enumerate
        # the catalogue or select an expert without the supplied capture.
        kw = {} if expert_ids is None else {'expert_ids': expert_ids}
        resolved = execution.source.resolve(node, rank, **kw)
        dispatch = execution.dispatch(node, rank, **kw)
        require(dispatch['source_dispatch_bound'], 'canonical selected dispatch required')
        matrices = resolved['fragments']
        require(type(fragment) is int and 0 <= fragment < len(matrices), 'selected fragment')
        require(len(matrices) == len(dispatch['fragments']), 'dispatch fragment coverage')
        rows = instruction['qe_nout'] if qe else instruction['me_nout']
        K = instruction['qe_nb']*32 if qe else instruction['me_k']*(1 << instruction.get('me_split',0))
        require(sum(f['matrix']['rows'] for f in matrices) == rows and
                all(f['matrix']['K'] == K for f in matrices), 'full literal source dimensions')
        self.matrix = matrices[fragment]['matrix']
        self.selected = dispatch['fragments'][fragment]
        digest = hashlib.sha256(json.dumps(self.matrix, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
        require(self.selected['source_matrix_sha256'] == digest and self.selected['rank'] == rank and
                self.selected['stage'] == self.matrix['stage'], 'selected matrix identity')
        fmt, conversion = self.matrix['format'], self.matrix['conversion']
        require(self.matrix['compiled_NP'] == 2417 and fmt in ('fp4','fp8','bf16'),
                'source S81 codec required')
        require(conversion in ('native','FP8+UE8M0->BF16_RNE'), 'unsupported source conversion')
        if qe:
            require(conversion == 'native' and fmt == ('fp4' if instruction.get('qe_fp4',0) else 'fp8'),
                    'literal QE format mismatch')
        else:
            require(fmt == 'bf16', 'native ME format required')
        dtype = 'F8_E4M3' if conversion != 'native' or fmt == 'fp8' else ('I8' if fmt == 'fp4' else 'BF16')
        _, _, descriptor = source.descriptor(self.matrix['tensor'])
        require(descriptor['dtype'] == dtype, 'released native code dtype')
        scale = self.matrix['source_scale_tensor']
        if dtype != 'BF16':
            require(scale is not None, 'released scale source missing')
            _, _, descriptor = source.descriptor(scale)
            require(descriptor['dtype'] == 'F8_E8M0',
                    'released source scale dtype')
        self.expert_ids = None if expert_ids is None else tuple(expert_ids)
        self.source, self.rank = source, rank
        self.pairs = tuple(sorted({p[1] for p in self.matrix['plans']}))
        self.source_matrix_sha256 = digest
        require(not native_pp or qe, 'PP packing requires native mode0 QE')
        self.native_pp = native_pp
        self.pp_maps = {}

    def read(self, stage, rank, macro, physical_row):
        require(all(type(v) is int for v in (stage, rank, macro, physical_row)), 'integer address')
        require(stage == self.matrix['stage'] and rank == self.rank and
                0 <= macro < 4*2417 and macro//4 in self.pairs and 0 <= physical_row < 4096,
                'request outside selected QE source')
        require(self.matrix['conversion'] == 'native',
                'native source transform required; use raw_chunk, no host BF16 conversion')
        if self.native_pp:
            pair, leaf = divmod(macro, 4)
            if pair not in self.pp_maps:
                self.pp_maps[pair] = native_pp_word_map(self.matrix, pair)
            address = 2*physical_row+(leaf & 1)
            require(address in self.pp_maps[pair], 'PP request outside selected phase allocation')
            canonical = self.pp_maps[pair][address]
            macro = 4*pair+2*(leaf//2)+(canonical & 1)
            physical_row = canonical//2
        word = API.matrix_word(self.matrix, self.source, rank, macro, physical_row)
        require(type(word) is int and 0 <= word < 1 << 274, 'native word width')
        return word

    def raw_chunk(self, row, k, count):
        """Retained raw codes/BF16 and addressed scales, no dequantization.

        The native consumer applies the declared conversion/rounding. Coordinates
        are local to the selected fragment, not a guessed global tensor slice.
        """
        require(all(type(v) is int for v in (row,k,count)) and
                0 <= row < self.matrix['rows'] and 1 <= count <= 32 and
                0 <= k and k+count <= self.matrix['K'], 'raw source chunk bounds')
        homes = [API.M.physical_address(self.matrix,self.rank,row,k+j) for j in range(count)]
        sr, sk = homes[0]['source_row'], homes[0]['source_col']
        require(all(h['source_row']==sr and h['source_col']==sk+j for j,h in enumerate(homes)),
                'raw chunk crosses source slice')
        dtype = self.source.descriptor(self.matrix['tensor'])[2]['dtype']
        if dtype == 'I8':
            offset, end = sk//2, (sk+count+1)//2
            codes = self.source.raw(self.matrix['tensor'], sr*self.source.descriptor(self.matrix['tensor'])[2]['shape'][1]+offset, end-offset)
            first_nibble = sk % 2
        else:
            width = 2 if dtype == 'BF16' else 1
            cols = self.source.descriptor(self.matrix['tensor'])[2]['shape'][1]
            codes = self.source.raw(self.matrix['tensor'], (sr*cols+sk)*width, count*width)
            first_nibble = None
        scales = []
        if self.matrix['source_scale_tensor'] is not None:
            seen = set()
            for h in homes:
                scale_row = sr if dtype == 'I8' else sr//32
                scale_col = h['source_col']//32
                if (scale_row,scale_col) not in seen:
                    seen.add((scale_row,scale_col))
                    scales.append(dict(row=scale_row,col=scale_col,
                        bits=self.source.element(self.matrix['source_scale_tensor'],scale_row,scale_col)))
        return dict(source_matrix_sha256=self.source_matrix_sha256,selected=self.selected,
                    source_tensor=self.matrix['tensor'],source_row=sr,source_col=sk,count=count,
                    source_homes=homes,source_scale_tensor=self.matrix['source_scale_tensor'],
                    captured_expert_ids=self.expert_ids,
                    dtype=dtype,codes=codes,first_nibble=first_nibble,scales=scales,
                    conversion=self.matrix['conversion'],native_arithmetic_required=True)

    __call__ = read


class DelayedExpertWords:
    """One fixed node/rank/fragment actor; bind once from actual native capture.

    The parent retains its capture lease through drain. This object verifies
    source identity and tuple shape, not a numerical/publication grant.
    """
    def __init__(self, execution, source, node, rank, fragment=0):
        require(type(rank) is int and 0 <= rank < 4 and type(fragment) is int and fragment >= 0,
                'delayed actor rank/fragment')
        binding = execution.source.bindings[node]
        require(binding['selector_slot'] is not None, 'delayed binding requires dynamic source node')
        instruction = execution.source.nodes[node]['instruction']
        require(instruction['unit'] == 3 and instruction['qe_mode'] == 0,
                'delayed actor requires source-weight QE')
        require(source.root.resolve().name == API.SNAPSHOT, 'released checkpoint required')
        self.execution,self.source,self.node = execution,source,node
        self.rank,self.fragment = rank,fragment
        self.node_sha256 = binding['source_node_semantic_sha256']
        require(len(self.node_sha256) == 64, 'source node digest')
        self.provider = None
        self.fault = False

    def bind(self, node_sha256, rank, fragment, eids):
        require(not self.fault and self.provider is None, 'expert actor already bound/quarantined')
        try:
            require((node_sha256,rank,fragment) == (self.node_sha256,self.rank,self.fragment),
                    'captured EIDs supplied for wrong source node/rank/fragment')
            require(len(eids)==6 and all(type(e) is int and 0 <= e < 384 for e in eids) and
                    list(eids)==sorted(set(eids)), 'six captured ascending EIDs required')
            self.provider = ReleasedQeOperationWords(self.execution,self.source,self.node,self.rank,
                                                      fragment=self.fragment,expert_ids=eids)
        except Exception:
            self.fault = True
            raise

    def read(self, stage, rank, macro, row):
        require(not self.fault and self.provider is not None, 'expert actor unbound/quarantined')
        return self.provider.read(stage,rank,macro,row)


def serve_delayed_connection(sock, actor):
    # READY comes only after the child opened checkpoint/index and enrolled the
    # actual fixed source node. Parent constructor consumes it BEFORE threads.
    sock.sendall(struct.pack('<I',0)+bytes.fromhex(actor.node_sha256)+struct.pack('<I',1))
    while (request := receive(sock,16)) is not None:
        stage,rank,macro,row = struct.unpack('<4I',request)
        try:
            if stage == 0xffffffff:
                require(rank == 1, 'unknown delayed binding command')
                payload = receive(sock,56)
                require(payload is not None, 'missing captured EID command')
                actor.bind(payload[:32].hex(),macro,row,list(struct.unpack('<6I',payload[32:])))
                reply = bytes.fromhex(actor.node_sha256)+bytes(4)
            else:
                word = actor.read(stage,rank,macro,row)
                require(type(word) is int and 0 <= word < 1 << 274, 'native word width')
                reply = word.to_bytes(36,'little')
            sock.sendall(struct.pack('<I',0)+reply)
        except Exception as e:
            # Unbound reads refuse but keep the pre-spawned child available for
            # the later real capture. A bad binding permanently quarantines it.
            print(json.dumps(dict(status='REJECTED_DELAYED_EXPERT_SOURCE',error=str(e))),flush=True)
            sock.sendall(struct.pack('<I',1)+bytes(36))
    return not actor.fault


def main():
    from dsrom_s81_execution_binding import CanonicalS81Execution
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--fd', type=int, required=True)
    p.add_argument('--owner', type=Path, required=True)
    p.add_argument('--checkpoint', type=Path, required=True)
    p.add_argument('--node', required=True)
    p.add_argument('--rank', type=int, required=True)
    p.add_argument('--fragment', type=int, default=0)
    p.add_argument('--expert-ids', default='')
    p.add_argument('--delayed-expert-binding', action='store_true')
    a = p.parse_args()
    expert_ids = [int(x) for x in a.expert_ids.split(',')] if a.expert_ids else None
    source = API.Checkpoint(a.checkpoint)
    try:
        execution = CanonicalS81Execution(a.owner)
        with socket.socket(fileno=a.fd) as connection:
            if a.delayed_expert_binding:
                require(expert_ids is None, 'delayed actor cannot prefill EIDs')
                actor = DelayedExpertWords(execution,source,a.node,a.rank,a.fragment)
                return 0 if serve_delayed_connection(connection,actor) else 1
            provider = ReleasedQeOperationWords(execution,source,a.node,a.rank,
                                                 fragment=a.fragment,expert_ids=expert_ids)
            return 0 if serve_connection(connection,provider) else 1
    finally:
        source.close()

if __name__ == '__main__':
    raise SystemExit(main())
