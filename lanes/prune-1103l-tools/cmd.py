import os,re
S=set()
for pid in os.listdir('/proc'):
    if not pid.isdigit(): continue
    try:
        a=open(f'/proc/{pid}/cmdline','rb').read().replace(b'\0',b' ').decode('utf8','replace')
        S.update(re.findall(r'/srv/opentallas-scratch2?/[^\s\'"]+',a))
    except OSError: pass
print('\n'.join(sorted(S)))
