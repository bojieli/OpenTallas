import importlib.util, os, tempfile, time, unittest
sp = importlib.util.spec_from_file_location("ac", os.path.join(os.path.dirname(os.path.abspath(__file__)), "ot-autoclean.py"))
ac = importlib.util.module_from_spec(sp); sp.loader.exec_module(ac)


class PushGuard(unittest.TestCase):
    def test_stale_or_missing_coord_is_not_fresh(self):
        d = tempfile.mkdtemp(); os.makedirs(d + "/autopilot")
        self.assertFalse(ac.push_coord_fresh(d))
        p = d + "/autopilot/kit_wave.json"; open(p, "w").write("{}")
        self.assertTrue(ac.push_coord_fresh(d))
        os.utime(p, (time.time() - 7200, time.time() - 7200))
        self.assertFalse(ac.push_coord_fresh(d))
        self.assertTrue(ac.push_coord_fresh(d, now=os.path.getmtime(p) + 60))


    def test_push_preserves_read_only_tool_modes_and_refreshes_snapshot(self):
        from pathlib import Path
        import subprocess
        from types import SimpleNamespace

        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source = root / "source"
            tools = root / "installed tools"
            state = root / "remote state"
            snap = root / "incoming"
            for directory in (source, tools, state / "snapshot", snap):
                directory.mkdir(parents=True)
            for name, contents in {
                "ot-autoclean.py": "approved cleaner",
                "ot_delete_guard.py": "guard",
                "wt-reaper.py": "identical reaper",
            }.items():
                (source / name).write_text(contents)
            installed_cleaner = tools / "ot-autoclean.py"
            installed_cleaner.write_text("old cleaner")
            installed_cleaner.chmod(0o444)
            installed_reaper = tools / "wt-reaper.py"
            installed_reaper.write_text("identical reaper")
            installed_reaper.chmod(0o555)
            reaper_inode = installed_reaper.stat().st_ino
            (state / "snapshot" / "stamp").write_text("old")
            (snap / "stamp").write_text("new")

            def run_local(host, cmd, inp, binary):
                assert host == "fixture" and binary
                return subprocess.run(["bash", "-c", cmd], input=inp, capture_output=True)

            driver = ac.Driver.__new__(ac.Driver)
            driver.a = SimpleNamespace(coord=str(root / "missing-coord"))
            driver.r = SimpleNamespace(host=run_local)
            driver.script = str(source / "ot-autoclean.py")
            driver.rstate = str(state)
            driver.tools = str(tools)

            assert driver.push("fixture", str(snap)) == (True, "")
            assert installed_cleaner.read_text() == "approved cleaner"
            assert installed_cleaner.stat().st_mode & 0o777 == 0o444
            assert installed_reaper.stat().st_mode & 0o777 == 0o555
            assert installed_reaper.stat().st_ino == reaper_inode
            assert (tools / "ot_delete_guard.py").read_text() == "guard"
            assert (state / "snapshot" / "stamp").read_text() == "new"
