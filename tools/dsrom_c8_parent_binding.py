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
    def __init__(self, owner, selected, model_pin, interface_pin):
        self.owner = Path(owner).resolve()
        self.selected = Path(selected)
        if self.selected.is_absolute() or '..' in self.selected.parts:
            raise ValueError('selected allocation must be a relative owner path')
        self.model_pin, self.interface_pin = model_pin, interface_pin
        self.receipts = {}
        self.inventory = self._json('inventory.json')
        self.stage_map = self._json('stage_map.json')
        self.contract = self._json('physical_contract.json')
        self.return_baseline = self._json('return_baseline.json')
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
        self._pinned('tools/dsrom_s82_payload_interface.py', interface_pin)

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
                    C8_PUBLICATION=1, WINDOW_REFILL_OWNER_SAFE=1, WINDOW_REFILL_CREDITS=8)

    def scan_home(self, layer):
        return self.stage_map['scan_service_homes'][str(layer)]

    @property
    def payload_api_path(self):
        """The existing owner's native word/fragment API, without loading payloads."""
        self._pinned('tools/dsrom_s82_payload_interface.py', self.interface_pin)
        return self.owner / 'tools/dsrom_s82_payload_interface.py'

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
