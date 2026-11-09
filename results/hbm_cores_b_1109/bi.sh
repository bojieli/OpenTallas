cd /srv/opentallas-scratch2/claude/kw35/us
ls -la --time-style=+%H:%M | awk '{print $5,$6,$7}' | head -30
sed -n 30,200p scan.py | grep -n "argv\|ssh\|def main\|host" | head -12 | cut -c1-160
grep -c . /srv/opentallas-scratch2/claude/kw35/us/*.sh 2>/dev/null
F=fea7df0c0a6697d41517b58c057d71122506a6d0
R=/srv/opentallas-scratch2/claude/kw35/wt_us
python3 -I - <<'PY'
import json,subprocess,hashlib,os
c=json.load(open("/home/ubuntu/coord/autopilot/kit_wave.json"))
for k,d in c["dies"].items():
    if not isinstance(d,dict): continue
    s=os.path.realpath(d["src"])
    b=open(s+"/tools/die_plan/bind.py","rb").read() if os.path.exists(s+"/tools/die_plan/bind.py") else b""
    print(k,"src",d["src"],"real",s,"bind_md5",hashlib.md5(b).hexdigest()[:8],len(b),"src_sha",str(d.get("src_sha"))[:12],"queue_src",str(d.get("queue_src"))[:110],"gen",d.get("gen_hosts"))
PY
for f in stage/bind_*.py; do echo $f $(md5sum $f | cut -c1-8); done
st=$(ls -d /srv/opentallas-scratch2/claude/kw35/src_c303p/tools/die_plan 2>/dev/null); echo $st; ls -ld /srv/opentallas-scratch2/claude/kw35/src_c303p/tools/die_plan/bind.py | cut -c1-60
git -C $R log -3 --format='%h %s' | cut -c1-90
