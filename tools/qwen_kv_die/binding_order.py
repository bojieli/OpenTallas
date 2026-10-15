"""Keep physical clock-entry indices identical to their actual RTL vector bits."""
import re


def sliced_order(base, ports):
    ports=list(ports)
    # Ordinary data bundles retain their established ABI. Clock pin labels
    # explicitly number actual child entries; lexical 1,10,100,2 is invalid.
    if base.startswith(('ck_', 'hk_')):
        def key(name):
            match=re.fullmatch(r'(.*?)(\d+)',name)
            return (match.group(1),int(match.group(2))) if match else (name,-1)
        rest=sorted((p for p in ports if p!=base),key=key)
    else:
        rest=sorted(p for p in ports if p!=base)
    return ([base] if base in ports else [])+rest
