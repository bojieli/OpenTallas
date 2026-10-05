"""Released wo_a codec and finite source expert-route lifetime, added to r31.
No operator callback, regenerated retained history, or hardware visibility claim.
"""
import hashlib
import numpy as np
import h3_ds_checkpoint_provider_r31 as B


def wo_a_payload(codes, scales):
    """Q8.dense then G.to_bf16, on a selected aligned 512-column payload."""
    codes = np.asarray(codes)
    scales = np.asarray(scales)
    if codes.dtype != np.uint8 or scales.dtype != np.uint8 or codes.ndim != 2:
        raise ValueError('released E4M3/biased UE8M0 bytes required')
    if scales.shape != (codes.shape[0], codes.shape[1] // 32) or codes.shape[1] % 32:
        raise ValueError('expanded scale rows and aligned32 K blocks')
    # E4M3 values are exact binary rationals in binary64, including signed zero.
    c = codes.astype(np.int32); e = (c >> 3) & 15; m = c & 7
    if np.any((e == 15) & (m == 7)) or np.any(scales == 255):
        raise ValueError('poison checkpoint wo_a code/scale')
    q = np.where(e == 0, m / 8.0 * 2.0**-6, (1.0 + m / 8.0) * np.exp2(e - 7))
    q = np.where(c & 128, -q, q)
    exponent = np.repeat(scales.astype(np.int32) - 127, 32, axis=1)
    with np.errstate(over='raise', invalid='raise'):
        dense = (q * np.exp2(exponent)).astype(np.float32)
    bits = dense.view(np.uint32).astype(np.uint64)
    rounded = ((bits + 0x7FFF + ((bits >> 16) & 1)) >> 16) << 16
    value = rounded.astype(np.uint32).view(np.float32)
    if not np.all(np.isfinite(value)):
        raise ValueError('nonfinite converted checkpoint wo_a')
    value.flags.writeable = False
    return value


class Provider(B.Provider):
    def __init__(self, *args):
        super().__init__(*args)
        self.pending_routes = {}; self.routes = {}; self.route_consumers = {}
        self.codec_receipts = []

    def read_views(self, op, owned, generation):
        if op['family'] == 'expert_fetch':
            if self.routes or len(self.pending_routes) >= 96:
                raise ValueError('finite96 route snapshots; prior consumers must retire')
            if (op['pc'], owned['rank']) in self.pending_routes:
                raise ValueError('duplicate source fetch owner')
        views = super().read_views(op, owned, generation)
        if op['family'] == 'expert_fetch':
            ids = views['route_ids']['data']
            table = views['expert_descriptor_table']['data']
            if ids.dtype != np.int64 or ids.shape != (6,) or len(set(ids.tolist())) != 6 or np.any(ids < 0) or np.any(ids >= 384):
                raise ValueError('source accepted six distinct expert IDs')
            if table.dtype != np.int64 or table.shape != (384, 3, 4):
                raise ValueError('source descriptor table shape/type')
            layer = op['source_op']['layer']; rank = owned['rank']
            value = ids.copy(); value.flags.writeable = False
            self.pending_routes[op['pc'], rank] = dict(ids=value, layer=layer,
                generation=generation, source_version=views['route_ids']['version'],
                descriptor_sha256=hashlib.sha256(table[ids].tobytes()).hexdigest())
        return views

    def weight_view(self, name, required, owned, spec):
        tensor = required['logical_tensor']
        if isinstance(tensor, list):
            op = self._weight_op(required, owned)
            layer = op['source_op']['layer']; slot, matrix = tensor
            if type(slot) is not int or matrix not in ('w1', 'w3', 'w2') or not 0 <= slot <= 6:
                raise ValueError('source expert slot/matrix')
            if slot < 6:
                route = self.routes.get((layer, owned['rank']))
                if route is None or route['generation'] != self.generation:
                    raise ValueError('expert fetch must retire with exact route identity before weight read')
                tensor = f'layers.{layer}.ffn.experts.{int(route["ids"][slot])}.{matrix}.weight'
            else:
                tensor = f'layers.{layer}.ffn.shared_experts.{matrix}.weight'
            required = dict(required, logical_tensor=tensor)
        if name == 'weight' and isinstance(tensor, str) and tensor.endswith('attn.wo_a.weight'):
            rank = owned['rank']; lo, hi = required['row_intervals'][rank]
            if [lo, hi] != owned['row_interval'] or rank >= 64 or hi - lo != 1024:
                raise ValueError('source wo_a head/group row ownership')
            k0 = (rank % 8) * 512; k1 = k0 + 512
            codes, dt = self.checkpoint.tensor(tensor, rows=[lo, hi], cols=[k0, k1])
            scales, st = self.checkpoint.tensor(tensor.removesuffix('.weight') + '.scale', rows=[lo // 32, (hi + 31) // 32], cols=[k0 // 32, k1 // 32])
            if dt != 'F8_E4M3' or st != 'F8_E8M0':
                raise ValueError('released wo_a source codecs')
            scales = scales[np.arange(lo, hi) // 32 - lo // 32]
            value = wo_a_payload(codes, scales)
            if list(value.shape) != spec['shape'] or value.dtype != np.float32:
                raise ValueError('source wo_a native LOAD shape')
            self.codec_receipts.append(dict(tensor=tensor, rank=rank, rows=[lo, hi], K=[k0, k1],
                decoded_words=value.size, checkpoint_code_bytes=codes.nbytes,
                source_scale_bytes=(hi - lo) // 32 * 16, expanded_scale_bytes=scales.nbytes,
                output_sha256=hashlib.sha256(value.tobytes()).hexdigest(), hardware=False))
            return value
        return super().weight_view(name, required, owned, spec)

    def _weight_op(self, required, owned):
        matches = [o for o in self.native['instructions'] if o['family'] == 'linear_q'
                   and any(r is owned for r in o['rank_bindings'])
                   and any(b == required for bs in o['provider_bindings'].values() for b in bs.values())]
        if len(matches) != 1:
            raise ValueError('exact native weight call identity required')
        return matches[0]

    def retire_operation(self, pc, generation):
        result = super().retire_operation(pc, generation)
        op = self.native['instructions'][pc]
        if op['family'] == 'expert_fetch':
            layer = op['source_op']['layer']
            required_ranks = {r['rank'] for r in op['rank_bindings'] if not r.get('empty_owned_extent')}
            if {rank for p, rank in self.pending_routes if p == pc} != required_ranks:
                raise ValueError('all source expert-fetch ranks must finish before route acceptance')
            values = [self.pending_routes[pc, r] for r in sorted(required_ranks)]
            if any(not np.array_equal(v['ids'], values[0]['ids']) for v in values):
                raise ValueError('rank route identity mismatch')
            for rank in required_ranks:
                self.routes[layer, rank] = self.pending_routes.pop((pc, rank))
            self.route_consumers[layer] = {o['pc'] for o in self.native['instructions']
                if o['source_op'].get('layer') == layer and isinstance(o['source_op'].get('w'), list)
                and isinstance(o['source_op']['w'][0], int) and o['source_op']['w'][0] < 6}
        layer = op['source_op'].get('layer')
        if layer in self.route_consumers and pc in self.route_consumers[layer]:
            self.route_consumers[layer].remove(pc)
            if not self.route_consumers[layer]:
                del self.route_consumers[layer]
                for key in list(self.routes):
                    if key[0] == layer: del self.routes[key]
        return result

    def drain(self, generation):
        if self.routes or self.pending_routes or self.route_consumers:
            raise ValueError('accepted route descriptors still owned')
        return super().drain(generation)


def create_provider(manifest, native_program, bounded_dispatch, residence_homes):
    return Provider(manifest, native_program, bounded_dispatch, residence_homes)
