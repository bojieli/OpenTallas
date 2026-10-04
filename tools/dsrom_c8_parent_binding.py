#!/usr/bin/env python3
"""Bind the native C8 source selection to the owner's canonical allocation.

The caller supplies the owner checkout and immutable model/interface pins.
No allocator is run, no checkpoint is read, and no legacy shape is a fallback.
SourceExecution / execution_fragments still own matrix addressing and order.
"""
import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NATIVE_PIN = 'f6df84e14c2bc5908bdbf85b2bd95cd56b1f5520'
SOURCES = [
    'ot_chip_v41x_kv_reqmux_c8.sv', 'ot_chip_v41x_kv_rope_reqmux_c8.sv',
    'ot_chip_v41x_ckv_die_service_c8.sv', 'ot_hdc_v41x_idx_hbm_c8.sv',
    'ot_chip_v41x_hbm3e_phy_c8.sv', 'ot_chip_v41x_die_owner_safe_c8.sv',
    'ot_v41_rt_die_l20_c8.sv', 'ot_dsrom_c8_write_journal.sv',
    'ot_dsrom_c8_stage_context.sv',
]


class ParentBinding:
    def __init__(self, owner, selected, model_pin, interface_pin, *,
                 payload_interface="tools/dsrom_s82_payload_interface.py",
                 released_return_binding=None):
        self.owner = Path(owner).resolve()
        self.selected = Path(selected)
        if self.selected.is_absolute() or '..' in self.selected.parts:
            raise ValueError('selected allocation must be a relative owner path')
        self.model_pin, self.interface_pin = model_pin, interface_pin
        self.payload_interface = Path(payload_interface)
        if (self.payload_interface.is_absolute() or ".." in self.payload_interface.parts
                or self.payload_interface.suffix != ".py"):
            raise ValueError("payload interface must be a pinned relative Python source")
        self.receipts = {}
        self.inventory = self._json('inventory.json')
        self.stage_map = self._json('stage_map.json')
        if released_return_binding is None:
            self.contract = self._json('physical_contract.json')
            self.return_baseline = self._json('return_baseline.json')
        else:
            # Main's actual canonical bundle and Rawls's inventory-bound return
            # receipt replace the historical S82 companion-file convention.
            rel = Path(released_return_binding)
            if rel.is_absolute() or '..' in rel.parts:
                raise ValueError('return binding must be a pinned relative source')
            release = self._json('binding.json')
            bound = json.loads(self._pinned(str(rel / 'binding_result.json'), model_pin))
            self.return_baseline = json.loads(self._pinned(str(rel / 'model.json'), model_pin))
            if (release['stages'], release['NP'], release['BF'], release['R'], release['RD']) != (81, 2417, 519, 128, 64):
                raise ValueError('actual released S81 selection required')
            if not bound['inventory_bound'] or not bound['canonical_matrix_map_pinned']:
                raise ValueError('return lacks actual inventory binding')
            for name, digest in bound['input_sha256'].items():
                data = self._pinned(str(self.selected / name), model_pin)
                if hashlib.sha256(data).hexdigest() != digest:
                    # Main's source-owned S81 label correction changes only
                    # emitter annotations, not geometry or a verdict field.
                    if name != 'mapping_verdict.json':
                        raise ValueError('return/canonical source mismatch: ' + name)
                    original = self._pinned(str(rel / 'input_mapping_verdict.json'), model_pin)
                    if hashlib.sha256(original).hexdigest() != digest:
                        raise ValueError('original return verdict receipt mismatch')
                    old, current = json.loads(original), json.loads(data)
                    labels = {'schema', 'W1_RD', 'selected_binding', 'return_binding'}
                    old_body = {k:v for k,v in old.items() if k not in labels}
                    current_body = {k:v for k,v in current.items() if k not in labels}
                    # Arendt's subsequent source-owned receipt acknowledges the
                    # very same inventory-bound Rawls graph. The only retired
                    # blocker may be this specific already-joined geometry item.
                    return_labels = {
                        'Selected active-pair RD64; mapping capacity PASS does not qualify return RTL/timing',
                        'Rawls 58168 canonical inventory binding PASS; RD64 strict-pruned 5090 retained nodes; RTL/timing and whole-token qualification remain separate'}
                    if current.get('return_binding', '').startswith('Rawls 58168 '):
                        expected = [x for x in old_body['blocking']
                                    if x != 'Ragged region assignment must join W1 generator']
                        if current_body['blocking'] != expected:
                            raise ValueError('unexpected canonical blocker removal')
                        old_body['blocking'] = expected
                    if (old_body != current_body
                            or old['W1_RD'] != 4 or current['W1_RD'] != 64
                            or old['schema'] != 'opentallas.dsrom.S73.PAIR1.metadata-map.v1'
                            or current['schema'] != 'opentallas.dsrom.S81.PAIR1.metadata-map.v1'
                            or current.get('selected_binding') != 'binding.json'
                            or current.get('return_binding') not in return_labels):
                        raise ValueError('substantive return verdict source mismatch')
                    self.receipts['return_verdict_label_correction'] = {
                        'original_sha256': digest,
                        'current_sha256': hashlib.sha256(data).hexdigest(),
                        'changed_annotations_only': sorted(labels),
                        'timing_or_adoption_transfer': False}
            if (bound['selected_return_contract']['retained_nodes'] != 5090
                    or bound['selected_return_contract']['retained_unilateral_nodes'] != 384):
                raise ValueError('selected return must retain active unary stages')
            self.contract = {'return_contract': bound['selected_return_contract']}
        self.pairs = self.inventory['pairs_per_rank_die']
        self.stages = len(self.stage_map['PHW_required_by_stage'])
        self.rank_dies = {(d['stage'], d['rank']): d['die_id']
                          for d in self.stage_map['rank_dies']}
        if (len(self.rank_dies) != len(self.stage_map['rank_dies'])
                or self.inventory['TP'] != 4
                or len(self.rank_dies) != self.stages * self.inventory['TP']):
            raise ValueError('incomplete or duplicate stage/rank ownership')
        if len(set(self.rank_dies.values())) != len(self.rank_dies):
            raise ValueError('duplicate physical die owner')
        bounds = self.stage_map['region_bounds']
        bf = self.stage_map['BF_site_IDs']
        if (bounds[0] != 0 or bounds[-1] != self.pairs
                or any(a >= b for a, b in zip(bounds, bounds[1:]))
                or len(bf) != len(set(bf)) or any(not 0 <= p < self.pairs for p in bf)):
            raise ValueError('invalid element/region ownership')
        if (self.inventory['macros_per_pair'] != 4
                or self.inventory['logical_slots_per_pair'] != 2):
            raise ValueError('native fixed4096 NB2 PP1 ownership mismatch')
        if self.contract['return_contract']['RD'] != 64:
            raise ValueError('rejected RD4 is not the selected return source')
        self._pinned(str(self.payload_interface), interface_pin)

    def _pinned(self, relative, pin):
        data = subprocess.check_output(['git', 'show', f'{pin}:{relative}'], cwd=self.owner)
        actual = (self.owner / relative).read_bytes()
        if actual != data:
            raise ValueError(f'owner source changed: {relative}')
        self.receipts[relative] = hashlib.sha256(data).hexdigest()
        return data

    def _json(self, name):
        return json.loads(self._pinned(str(self.selected / name), self.model_pin))

    def field_parameters(self, stage, rank):
        if type(stage) is not int or type(rank) is not int or (stage, rank) not in self.rank_dies:
            raise ValueError('unowned stage/rank')
        phw = self.stage_map['PHW_required_by_stage'][stage]
        regions = len(self.stage_map['region_bounds']) - 1
        # Caller uses NP/NBF for its external field; the retained L20 die top
        # consumes R/PHW and its resulting feedback-port width. No NP padding.
        return dict(die_id=self.rank_dies[stage, rank], RANK=rank,
                    ROM_R=regions, ROM_PHW=phw,
                    field_pairs=self.pairs, BF_pairs=len(self.stage_map['BF_site_IDs']),
                    physical_macros=4 * self.pairs, physical_rows=4096,
                    return_RD=64, return_ROOTD=self.contract['return_contract']['ROOTD'],
                    C8_PUBLICATION=1, C8_CONTEXT=1, WINDOW_REFILL_OWNER_SAFE=1, WINDOW_REFILL_CREDITS=8)

    def scan_home(self, layer):
        return self.stage_map['scan_service_homes'][str(layer)]

    def write_field_meta(self, path):
        """Native runtime inventory, with no invented power-of-two field slots."""
        path=Path(path)
        if path.exists():raise FileExistsError(path)
        bf=self.stage_map['BF_site_IDs']
        path.parent.mkdir(parents=True,exist_ok=True)
        path.write_text(f'np {self.pairs}\nr {len(self.stage_map["region_bounds"])-1}\n'
                        +'active '+' '.join(map(str,range(self.pairs)))+'\n'
                        +'bf16 '+' '.join(map(str,bf))+'\n')

    def bind_execution(self, resolved):
        """Join the owner's resolved source operation to actual field parameters.

        Preserve fragment / ordered-K / multicast / VM output metadata verbatim.
        This prepares the real dispatcher; it does not assume a free gather,
        broadcast or context restore and never re-encodes an instruction.
        """
        if resolved.get('source_identity_verified') is not True:
            raise ValueError('source operation identity not verified')
        joined = []
        for fragment in resolved['fragments']:
            matrix = fragment['matrix']
            stage, die = matrix['stage'], fragment['die_id']
            owners = [r for (s, r), d in self.rank_dies.items() if s == stage and d == die]
            if len(owners) != 1:
                raise ValueError('fragment has no unique physical field owner')
            if matrix['compiled_NP'] != self.pairs:
                raise ValueError('fragment belongs to a different partition')
            joined.append(dict(fragment=fragment, field_parameters=self.field_parameters(stage, owners[0])))
        return dict(resolved, parent_fragments=joined)

    @property
    def payload_api_path(self):
        """The existing owner's native word/fragment API, without loading payloads."""
        self._pinned(str(self.payload_interface), self.interface_pin)
        return self.owner / self.payload_interface

    def native_sources(self, original_export):
        """Actual 125-source engine list plus selected native completion copies.

        The caller elaborates ot_v41_rt_die_l20_c8 and connects all extra ports.
        This never substitutes this top into a legacy system testbench silently.
        """
        names = subprocess.check_output(
            ['git', 'show', NATIVE_PIN + ':tools/w17_current_fastpp_l20_window_owner_safe_sources.txt'],
            cwd=ROOT, text=True).split()
        paths = [Path(original_export) / n for n in names]
        paths += [ROOT / 'rtl/dsrom_sys/c8' / n for n in SOURCES]
        if not all(p.is_file() for p in paths):
            raise FileNotFoundError('native parent source export incomplete')
        for name in names:
            data = subprocess.check_output(['git', 'show', NATIVE_PIN + ':' + name], cwd=ROOT)
            if (Path(original_export) / name).read_bytes() != data:
                raise ValueError(f'native source changed: {name}')
        return paths
