#!/usr/bin/env python3
"""Podman launcher unit tests; not kernel conformance."""
from __future__ import annotations
import importlib.util, tempfile, unittest, sys
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
SPEC=importlib.util.spec_from_file_location("podman_rootless",ROOT/"scripts/sandbox_backends/podman_rootless.py")
podman=importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
sys.modules["podman_rootless"]=podman
SPEC.loader.exec_module(podman)
from sandbox_runtime import SandboxLaunchSpec, SandboxEnforcementError
def spec_for(ws,writable=True,image=None):
    ws.mkdir(parents=True,exist_ok=True)
    if not (ws/".git").exists(): (ws/".git").mkdir()
    profile={"runtime":{"backend":"linux-rootless-oci","image":image or ("registry.example/agent@sha256:"+"a"*64)},"filesystem":{"workspace_read":True,"workspace_write":writable},"process":{"max_memory_mb":2048,"max_cpu":2,"max_processes":128},"network":{"default":"deny"}}
    return SandboxLaunchSpec("task-1",profile,"b"*64,ws,ws/"runtime",600)
class PodmanTests(unittest.TestCase):
    def test_rootless_private_networkless_and_limits(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws=Path(tmp)/"ws"; ws.mkdir()
            cmd=podman.RootlessPodmanBackend("/usr/bin/podman").build_command(["python","-m","pytest"],spec_for(ws)); joined=" ".join(cmd)
            for flag in ("--userns=keep-id","--network=none","--pid=private","--read-only","--cap-drop=ALL","--security-opt=no-new-privileges","--pids-limit=128","--memory=2048m","--cpus=2","--pull=never","dst=/workspace,rw","dst=/workspace/.git,ro","GIT_OPTIONAL_LOCKS=0"): self.assertIn(flag,joined)
            self.assertEqual(cmd[-3:],["python","-m","pytest"])
    def test_read_only_workspace(self):
        with tempfile.TemporaryDirectory() as tmp:
            cmd=podman.RootlessPodmanBackend().build_command(["true"],spec_for(Path(tmp),False)); self.assertIn("dst=/workspace,ro"," ".join(cmd))
    def test_git_worktree_pointer_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws=Path(tmp); (ws/".git").write_text("gitdir: /shared/.git/worktrees/task")
            with self.assertRaises(SandboxEnforcementError): podman.RootlessPodmanBackend().build_command(["true"],spec_for(ws))
    def test_shared_git_common_directory_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws=Path(tmp); (ws/".git").mkdir(); (ws/".git"/"commondir").write_text("../shared")
            with self.assertRaises(SandboxEnforcementError): podman.RootlessPodmanBackend().build_command(["true"],spec_for(ws))
    def test_mutable_image_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            for image in ("agent:latest","agent:1.0","agent@sha256:abc"):
                with self.subTest(image=image), self.assertRaises(SandboxEnforcementError): podman.RootlessPodmanBackend().build_command(["true"],spec_for(Path(tmp),image=image))
    def test_agent_environment_is_minimal(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch.dict("os.environ",{"XDG_RUNTIME_DIR":tmp,"PATH":"/usr/bin"},clear=True): env=podman.RootlessPodmanBackend().build_environment(spec_for(Path(tmp)))
            self.assertEqual(set(env),{"PATH","HOME","XDG_RUNTIME_DIR","LANG","LC_ALL"}); self.assertNotIn("API_KEY",env)
if __name__=="__main__": unittest.main(verbosity=2)
