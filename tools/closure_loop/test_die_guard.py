"""drive-0849 2026-10-09: die-level runs are exempt from stuckscan actions and from loop container kills; every loop
flow container is memory-capped so an overrun cannot trigger a host OOM that takes a die run."""
import re, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import closure_loop as cl  # noqa: E402
import stuckscan as ss  # noqa: E402


def test_die_names_exempt():
    for n in ("qfd_dietop_r22k4", "de2_qwen_r22k", "die_r22k4", "dieev_hbm_rg_hub2_drt", "qwen_r22k4"):
        assert ss.is_die_run(dict(name=n, spec={})), n
    for n in ("cdc_die_m2-b8a77cff7", "hbm_svc_SE_s3_ps_79af6ba23_tc_hm0-cl", "qfd_tile_rp1pcl-2b92621e4-tc-cl-kr"):
        assert not ss.is_die_run(dict(name=n, spec={})), n
    assert ss.is_die_run(dict(name="x", spec={"die_level": True}))
    assert ss.is_die_run(dict(name="x", spec={}, run="/srv/s/claude/kv-die/die_kv4"))


def test_diagnose_lets_die_run():
    j = dict(name="qfd_dietop_x", status="RUNNING", spec={"block": "b"})
    d = ss.diagnose(j, {"fresh": 0, "cpu_cores": 0.0, "pid_alive": True, "bases": []}, {}, [], set(), 10 ** 6)
    assert d["action"] == "let_run" and d["kind"] == "die_exempt"


def test_container_regex():
    r = re.compile(cl.DIE_CONTAINER_RE)
    for n in ("/qfd_dietop_die_kv4_grt_kv", "/dieev_hbm_rg_attn_drt", "/de2_x", "/die_r22k4"):
        assert r.search(n), n
    for n in ("/festive_curie", "/silly_tu", "/cdc_die_m2"):
        assert not r.search(n), n
    src = Path(cl.__file__).read_text()
    assert src.count("for c in $(docker ps -q); do {DIE_CONTAINER_SKIP}") >= 3
    assert "{DIE_OOM_PROBE}" in src


def test_mem_cap():
    j = dict(spec={"peak_ram_gb": 40})
    assert cl.stage_mem_cap(j, dict(ram=40)) == 160
    assert cl.stage_mem_cap(j, dict(ram=8)) == 104
    assert cl.stage_mem_cap(dict(spec={"mem_cap_gb": 0}), dict(ram=40)) == 0
    assert cl.stage_mem_cap(dict(spec={"mem_cap_gb": 300}), dict(ram=40)) == 300
    assert cl.DOCKER_SHIM.count("${OT_MEM_CAP_GB:+--memory ${OT_MEM_CAP_GB}g --memory-swap ${OT_MEM_CAP_GB}g}") == 2
