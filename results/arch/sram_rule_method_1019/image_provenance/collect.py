import datetime, json, pathlib, subprocess, sys
host=sys.argv[1]
ref="openroad/orfs@sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29"
binary="/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad"
out=pathlib.Path(__file__).parent/host
out.mkdir(exist_ok=True)
base=["ssh","-o","BatchMode=yes","-o","ConnectTimeout=8",host]
r=subprocess.run(base+["docker","image","inspect",ref,"--format", "'{{json .Id}} {{json .RepoDigests}}'"],capture_output=True,text=True,check=True)
(out/"image_inspect.txt").write_text(r.stdout+r.stderr)
dec=json.JSONDecoder();image_id,n=dec.raw_decode(r.stdout);digests=dec.decode(r.stdout[n:].strip())
r=subprocess.run(base+["docker","run","--rm","--entrypoint","/usr/bin/sha256sum",ref,binary],capture_output=True,text=True,check=True)
(out/"binary_sha256.txt").write_text(r.stdout+r.stderr)
sha=r.stdout.split()[0]
assert sha=="21eda99eeae7eccb22ca64ad28949c08a6c01dcece3ccb23e2206d635f8d2846"
record=dict(host=host,observed_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),kind="current_readonly_validation_not_retroactive_job_receipt",requested_ref=ref,image_id=image_id,repo_digests=digests,binary_path=binary,binary_sha256=sha)
(out/"observed.json").write_text(json.dumps(record,indent=2)+"\n")
print(json.dumps(record))
