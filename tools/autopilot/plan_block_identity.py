"""Opt-in plan block identity using exact, resolved pins_file JSON payloads.

Only pins_file strings are replaced in hash input. All other fields and list
order remain significant. Legacy raw hashes and state stay unchanged unless
explicit, terminal record reuse is proven against an exact baseline profile.
This module uses only the standard library so its source can travel with a
remote kit-wave plan probe.
"""
import copy
import hashlib
import json
from pathlib import Path

RAW = 'raw'
PINS = 'pins_payload_v1'


def fingerprint(value):
    # This is exactly the original KIT-WAVE PROBE_PLAN raw hash spelling.
    return hashlib.sha256(json.dumps(value, sort_keys=True, default=str).encode()).hexdigest()


def normalize_pins(node, plan_path, cache=None):
    cache={} if cache is None else cache
    receipts=[];base=Path(plan_path).resolve().parent
    def visit(value, pointer):
        if isinstance(value, list):return [visit(v,pointer+[str(i)]) for i,v in enumerate(value)]
        if not isinstance(value,dict):return copy.deepcopy(value)
        out={}
        for key,item in value.items():
            if key!='pins_file':out[key]=visit(item,pointer+[key]);continue
            if not isinstance(item,str) or not item:raise ValueError('pins_file must name a resolvable JSON payload')
            path=Path(item);path=path if path.is_absolute() else base/path
            resolved=path.resolve(strict=True)
            if not resolved.is_file():raise ValueError('pins_file is not a regular payload: '+str(path))
            proof=cache.get(str(resolved))
            if proof is None:
                raw=resolved.read_bytes()
                def invalid_constant(value):raise ValueError('non-JSON constant in pins payload: '+value)
                parsed=json.loads(raw,parse_constant=invalid_constant)
                if not isinstance(parsed,(dict,list)):raise ValueError('pins payload must be a JSON object/list: '+str(path))
                proof=dict(sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw));cache[str(resolved)]=proof
            out[key]={'$opentallas_pins_payload_sha256_v1':proof['sha256']}
            receipts.append(dict(pointer='/'.join(pointer+[key]),path=item,resolved=str(resolved),**proof))
        return out
    normalized=visit(node,[])
    return normalized,receipts


def profiles(plan):
    types=plan.get('partition_types') or {};bud=plan.get('budgets')
    bud=bud if isinstance(bud,dict) else {}
    result={name:dict(kind='type',legacy_node={'type':v,'budget':bud.get(name)},cohorts=[])
            for name,v in types.items()}
    cores=[h for h in plan.get('hard_cores') or [] if isinstance(h,dict)]
    for value in types.values():cores += [h for h in (value.get('hard_cores') if isinstance(value,dict) else None) or [] if isinstance(h,dict)]
    for h in cores:
        name=str(h.get('module') or h.get('name') or '')
        if not name or (name in result and result[name]['kind']=='type'):continue
        if name not in result:result[name]=dict(kind='core',legacy_node={'core':h},cohorts=[])
        result[name]['cohorts'].append({'core':h})
    return result


def identities(plan, plan_path, mode=RAW, cache=None):
    if mode not in (RAW,PINS):raise ValueError('unsupported block_identity '+str(mode))
    cache={} if cache is None else cache
    result={}
    for name,profile in profiles(plan).items():
        raw=profile['legacy_node'];raw_sha=fingerprint(raw)
        if mode==RAW:
            result[name]=dict(kind=profile['kind'],raw_sha=raw_sha,block_sha=raw_sha)
            continue
        normalized,receipts=normalize_pins(raw,plan_path,cache);ambiguous=False
        if profile['kind']=='core':
            # Legacy global module keys picked the first core only. Account for
            # every unique physical/parameter cohort; a changed later profile
            # cannot hide behind an unchanged first entry.
            unique={}
            for cohort in profile['cohorts']:
                n,rs=normalize_pins(cohort,plan_path,cache);unique[json.dumps(n,sort_keys=True,default=str)]=n;receipts+=rs
            nodes=[unique[key] for key in sorted(unique)]
            ambiguous=len(nodes)>1
            normalized=nodes[0] if len(nodes)==1 else {'core_profiles':nodes}
        # Pin-free type profiles retain their exact legacy identity. A core
        # with several distinct cohorts changes conservatively even pin-free.
        sha=fingerprint(normalized) if receipts or ambiguous else raw_sha
        result[name]=dict(kind=profile['kind'],raw_sha=raw_sha,block_sha=sha,
                          normalized_node=normalized,pins=receipts,legacy_ambiguous=ambiguous)
    return result


def reuse_record(record, old_identity, new_identity, *, item, old_key, baseline_plan, current_plan):
    """Return one terminal record alias + receipt; never mutate caller state.

    Refuse incomplete old identities, in-flight records and ambiguous legacy
    core module keys. Equal hashes alone do not replace the exact normalized
    profile comparison.
    """
    if record.get('item')!=item or record.get('block_sha')!=old_identity['raw_sha']:
        raise ValueError('stored record does not match the exact baseline raw block hash/item')
    if record.get('status') not in ('PASS','FAIL'):
        raise ValueError('cannot migrate an in-flight legacy record')
    if old_identity.get('legacy_ambiguous'):
        raise ValueError('legacy module key covers ambiguous core cohorts')
    if old_identity.get('kind')!=new_identity.get('kind') or old_identity['normalized_node']!=new_identity['normalized_node']:
        raise ValueError('normalized block profiles differ')
    seal=record.get('block_identity_reuse_receipt')
    if seal and (seal.get('old_raw_sha')!=old_identity['raw_sha'] or seal.get('semantic_sha')!=new_identity['block_sha']):
        raise ValueError('baseline payload/profile changed after its identity receipt was sealed')
    original=copy.deepcopy(record);original.pop('block_identity_reuse_receipt',None)
    receipt=dict(schema='opentallas.plan_block_reuse.v1',mode=PINS,item=item,old_key=old_key,
                 baseline_plan=str(baseline_plan),current_plan=str(current_plan),
                 old_raw_sha=old_identity['raw_sha'],new_raw_sha=new_identity['raw_sha'],
                 semantic_sha=new_identity['block_sha'],original_record_sha=fingerprint(original),
                 old_pins=old_identity['pins'],new_pins=new_identity['pins'],
                 proof='exact stored baseline raw hash and exact normalized profile equality; terminal status preserved')
    out=copy.deepcopy(record);out.update(block_sha=new_identity['block_sha'],block_identity=PINS,
                                      legacy_block_sha=old_identity['raw_sha'],block_identity_receipt=receipt)
    return out


def reuse_blocks(blocks, current, baseline, records, *, die, event, receipts=None):
    """Return effective keys + holds, without changing state/config.

    Explicit receipts are produced offline by proposal(). Verified reuse keeps
    the original key and record, so status, attempts and stage counts survive.
    Unsealed legacy records are held rather than silently rebuilt.
    """
    effective=dict(blocks);holds={}
    if receipts is not None and not isinstance(receipts,dict):
        return effective,{item:'identity_reuse_receipts must be an object' for item in current}
    receipts=receipts or {}
    for item,new in current.items():
        old=(baseline or {}).get(item)
        candidates=[r for r in records.values() if r.get('die')==die and r.get('item')==item]
        # A semantic record already exists; normal selection retains its status.
        key=f"{die}|{item}|b{new['block_sha'][:12]}"
        existing=records.get(key)
        if existing:
            if existing.get('block_sha')!=new['block_sha']:
                holds[item]='identity key prefix collision'
            continue
        if not candidates:continue
        if old is None:
            holds[item]='legacy state requires an exact baseline profile and sealed reuse receipt';continue
        # A genuine non-path/profile change has a new identity, as before.
        if old['normalized_node']!=new['normalized_node']:continue
        old_key=f"{die}|{item}|b{old['raw_sha'][:12]}"
        record=records.get(old_key)
        if record is None:
            holds[item]='matching legacy record was not found at its exact baseline key';continue
        try:
            candidate=reuse_record(record,old,new,item=item,old_key=old_key,
                                   baseline_plan='',current_plan='')
            receipt=receipts.get(item)
            expected=candidate['block_identity_receipt']
            # Original payload receipts seal baseline content before opt-in.
            fields=('schema','mode','item','old_key','old_raw_sha','new_raw_sha',
                    'semantic_sha','original_record_sha','old_pins','new_pins')
            if not isinstance(receipt,dict) or any(receipt.get(k)!=expected[k] for k in fields):
                raise ValueError('missing or mismatched offline reuse receipt')
            effective[item]=old['raw_sha']
        except (KeyError,ValueError) as exc:
            holds[item]=str(exc)
    return effective,holds


def proposal(state, old_plan, new_plan, *, old_path, new_path, die, items):
    """Seal only explicitly named existing records. Does not write live state."""
    old=identities(old_plan,old_path,PINS);new=identities(new_plan,new_path,PINS)
    result={}
    for item in items:
        if item not in old or item not in new:raise ValueError('item absent from baseline/current plan: '+item)
        key=f"{die}|{item}|b{old[item]['raw_sha'][:12]}"
        record=state.get('items',{}).get(key)
        if record is None:raise ValueError('missing exact baseline record: '+key)
        result[item]=reuse_record(record,old[item],new[item],item=item,old_key=key,
                                 baseline_plan=old_path,current_plan=new_path)['block_identity_receipt']
    return result


def main():
    import argparse
    ap=argparse.ArgumentParser(description='Create explicit kit-wave reuse receipts; never edits state/config')
    ap.add_argument('--baseline-plan',required=True);ap.add_argument('--plan',required=True)
    ap.add_argument('--state',required=True);ap.add_argument('--die',required=True)
    ap.add_argument('--item',action='append',required=True)
    args=ap.parse_args()
    result=proposal(json.loads(Path(args.state).read_text()),json.loads(Path(args.baseline_plan).read_text()),
                    json.loads(Path(args.plan).read_text()),old_path=args.baseline_plan,new_path=args.plan,
                    die=args.die,items=args.item)
    print(json.dumps({'block_identity':PINS,'identity_baseline_plan':args.baseline_plan,
                      'identity_reuse_receipts':result},indent=2))


if __name__=='__main__':main()
