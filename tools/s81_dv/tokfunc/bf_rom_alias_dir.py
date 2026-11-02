#!/usr/bin/env python3
"""Prepare a fresh BF image alias directory; never changes an active directory."""
import argparse
import json
from pathlib import Path


def build(join, base, out):
    if join['status']!='PASS_NATIVE_BF_IDENTITY_AND_EXISTING_IMAGE_JOIN':
        raise ValueError('need the exact native identity/image join')
    links={p.name:p.resolve(strict=True) for p in base.glob('*.viamap.hex')}
    base_count=len(links)
    for row in join['images_join']:
        name=row['candidate_selector']+'.viamap.hex'
        if '/' in name or '\\' in name or name in links:
            raise ValueError('duplicate/unsafe candidate selector: '+name)
        source=Path(row['source']).resolve(strict=True)
        if source.stat().st_size!=row['bytes']:
            raise ValueError('source image size changed: '+str(source))
        links[name]=source
    if out.exists():raise FileExistsError(out)
    out.mkdir(parents=True)
    for name,source in links.items():(out/name).symlink_to(source)
    report=dict(status='PREP_ONLY_NATIVE_BF_ALIAS_DIRECTORY',base=str(base),base_images=base_count,
                added_BF_images=len(join['images_join']),total_images=len(links),frames=join['frames'],
                canonical_manifest_or_active_directory_changed=False,programmes_or_reset_qualified=False,
                full_token=False)
    (out/'bf_alias_scope.json').write_text(json.dumps(report,indent=2)+'\n')
    return report


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--join',type=Path,required=True);p.add_argument('--base',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    result=build(json.loads(a.join.read_text()),a.base.resolve(strict=True),a.out.resolve())
    print(result['status'],result['base_images'],result['added_BF_images'],result['total_images'])
if __name__=='__main__':main()
