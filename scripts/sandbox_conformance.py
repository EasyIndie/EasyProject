#!/usr/bin/env python3
"""Opt-in Linux Rootless Podman conformance test; requires a trusted preloaded image."""
from __future__ import annotations
import argparse, json, os, re, shutil, signal, subprocess, sys, tempfile, time, uuid
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from sandbox_runtime import SandboxManager

PINNED = re.compile(r"^.+@sha256:[0-9a-f]{64}$")

def run_checked(argv, *, cwd=None, env=None, timeout=45):
    result = subprocess.run(argv, cwd=cwd, env=env, text=True, capture_output=True, check=False, timeout=timeout)
    if result.returncode:
        raise RuntimeError("Command failed: " + " ".join(argv) + "\n" + result.stdout + result.stderr)
    return result

def make_profile(image):
    return {
        "protocol_version":"1.0", "profile_id":"linux-conformance",
        "isolation_level":"workspace-write", "platform":"linux",
        "filesystem":{"workspace_read":True,"workspace_write":True,"stable_checkout":"deny","other_agent_workspaces":"deny","shared_git_metadata":"deny","user_home":"deny","credentials":"deny","runtime_directory":"deny","temporary_directory":"private","read_only_paths":[],"write_paths":["."]},
        "process":{"isolated_process_tree":True,"inherit_sandbox":True,"resource_limits":True,"timeout_enforced":True,"privilege_escalation":"deny","max_cpu":1,"max_memory_mb":512,"max_processes":64,"timeout_seconds":60},
        "network":{"default":"deny","allowed_domains":[],"allow_lan":False,"allow_host":False,"egress_proxy_required":True},
        "secrets":{"inherit_host_environment":False,"credential_mounts":False,"brokered_credentials":[]},
        "artifacts":{"export":["diff"],"direct_workspace_sharing":False,"symlink_policy":"reject-escape"},
        "runtime":{"backend":"linux-rootless-oci","image":image}
    }

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image",required=True,help="Preloaded digest-pinned image containing Python 3, Git and sleep.")
    args=parser.parse_args()
    if not PINNED.fullmatch(args.image): raise RuntimeError("--image must end in @sha256:<64 lowercase hex>.")
    manager=SandboxManager(); doctor=manager.doctor()
    if not doctor.get("enforcement_ready"): raise RuntimeError("Backend probe is not ready: "+json.dumps(doctor,sort_keys=True))
    backend=manager._backends.get("linux-rootless-oci")
    if backend is None: raise RuntimeError("Linux Rootless Podman backend is not registered.")
    run_checked([backend.podman,"image","exists",args.image],env=backend._host_environment())
    checks=[]
    old_secret=os.environ.get("EASYPROJECT_CONFORMANCE_SECRET")
    secret="conformance-"+uuid.uuid4().hex
    with tempfile.TemporaryDirectory(prefix="easyproject-sandbox-conformance-") as temp:
        root=Path(temp); workspace=root/"task-workspace"; stable=root/"stable"; other=root/"other"; runtime=root/"runtime"
        for p in (workspace,stable,other,runtime): p.mkdir()
        xdg=Path(os.environ.get("XDG_RUNTIME_DIR",""))
        if not xdg.is_dir(): raise RuntimeError("XDG_RUNTIME_DIR is required for rootless Podman.")
        with tempfile.TemporaryDirectory(prefix=".easyproject-conformance-",dir=Path.home()) as home_temp:
            home_sentinel=Path(home_temp)/"credential-sentinel.txt"; home_sentinel.write_text("blocked",encoding="utf-8")
            stable_sentinel=stable/"stable-sentinel.txt"; stable_sentinel.write_text("blocked",encoding="utf-8")
            other_sentinel=other/"other-sentinel.txt"; other_sentinel.write_text("blocked",encoding="utf-8")
            runtime_sentinel=runtime/"runtime-sentinel.txt"; runtime_sentinel.write_text("blocked",encoding="utf-8")
            subprocess.run(["git","init","-q",str(workspace)],check=True,capture_output=True)
            for key,value in (("user.name","Conformance"),("user.email","conformance@localhost.invalid"),("core.hooksPath",os.devnull)):
                subprocess.run(["git","-C",str(workspace),"config",key,value],check=True,capture_output=True)
            (workspace/"README.md").write_text("baseline\n",encoding="utf-8")
            subprocess.run(["git","-C",str(workspace),"add","README.md"],check=True,capture_output=True)
            subprocess.run(["git","-C",str(workspace),"commit","-qm","baseline"],check=True,capture_output=True)
            escape=workspace/"escape-to-home"; escape.symlink_to(home_sentinel)
            xdg_sentinel=xdg/(".easyproject-conformance-"+uuid.uuid4().hex); xdg_sentinel.write_text("blocked",encoding="utf-8")
            socket_path=xdg/"podman"/"podman.sock"
            os.environ["EASYPROJECT_CONFORMANCE_SECRET"]=secret
            try:
                profile_path=root/"profile.json"; profile_path.write_text(json.dumps(make_profile(args.image),sort_keys=True),encoding="utf-8")
                permissions={"repository_read":True,"repository_write":True,"network_access":False,"secret_access":False}
                check_code = """
import os, pathlib, socket, subprocess, sys
for p in sys.argv[1:6]:
    if pathlib.Path(p).exists(): raise AssertionError("host path visible: "+p)
if pathlib.Path(sys.argv[6]).exists(): raise AssertionError("workspace symlink escaped")
if pathlib.Path(sys.argv[7]).exists(): raise AssertionError("host Podman socket visible")
if os.environ.get(sys.argv[8]) is not None: raise AssertionError("host environment secret leaked")
if os.stat("/proc/self/ns/pid").st_ino == int(sys.argv[9]): raise AssertionError("PID namespace is not private")
memory=int(pathlib.Path("/sys/fs/cgroup/memory.max").read_text())
if memory > 512*1024*1024: raise AssertionError("memory limit is not effective: "+str(memory))
quota,period=pathlib.Path("/sys/fs/cgroup/cpu.max").read_text().split()
if quota == "max" or int(quota)/int(period) > 1.01: raise AssertionError("CPU limit is not effective: "+quota+" "+period)
pids=pathlib.Path("/sys/fs/cgroup/pids.max").read_text().strip()
if pids == "max" or int(pids) > 64: raise AssertionError("PID limit is not effective: "+pids)
pathlib.Path("/workspace/conformance-write.txt").write_text("ok")
try:
    pathlib.Path("/workspace/.git/agent-write-test").write_text("blocked")
    raise AssertionError(".git metadata is writable")
except OSError:
    pass
subprocess.run(["git","-C","/workspace","status","--porcelain"],check=True,capture_output=True)
try:
    socket.create_connection(("1.1.1.1",443),timeout=2)
    raise AssertionError("external network is reachable")
except OSError:
    pass
"""
                argv=["python3","-c",check_code,str(home_sentinel),str(stable_sentinel),str(other_sentinel),str(runtime_sentinel),str(xdg_sentinel),str(escape),str(socket_path),"EASYPROJECT_CONFORMANCE_SECRET",str(os.stat("/proc/self/ns/pid").st_ino)]
                cmd,env,_=manager.build_command(argv,profile_path,"linux-conformance",workspace,runtime,permissions)
                env["EASYPROJECT_CONFORMANCE_SECRET"]=secret
                run_checked(cmd,cwd=workspace,env=env)
                if not (workspace/"conformance-write.txt").is_file(): raise RuntimeError("Workspace write did not persist.")
                checks.extend(["workspace read/write","host home and credentials isolation","stable checkout and other workspace isolation","runtime directory and Podman socket isolation","no inherited Agent environment secrets","private PID namespace","effective memory/CPU/PID cgroup limits","read-only Git metadata","network=none"])
                child_code = "import pathlib,subprocess; p=subprocess.Popen([\"sleep\",\"600\"]); s=pathlib.Path(f\"/proc/{p.pid}/status\").read_text(); n=next(x for x in s.splitlines() if x.startswith(\"NSpid:\")); print(\"CHILD_HOST_PID=\"+n.split()[1],flush=True)"
                child_cmd,child_env,_=manager.build_command(["python3","-c",child_code],profile_path,"linux-conformance-child",workspace,runtime,permissions)
                child=subprocess.run(child_cmd,cwd=workspace,env=child_env,text=True,capture_output=True,check=False,timeout=30)
                if child.returncode: raise RuntimeError("Child cleanup test launch failed: "+child.stderr)
                match=re.search(r"CHILD_HOST_PID=(\d+)",child.stdout)
                if not match: raise RuntimeError("Container did not report child host PID: "+child.stdout)
                child_pid=int(match.group(1)); deadline=time.monotonic()+5; terminated=False
                while time.monotonic()<deadline:
                    stat=Path("/proc")/str(child_pid)/"stat"
                    if not stat.exists(): terminated=True; break
                    try:
                        if stat.read_text().split()[2]=="Z": terminated=True; break
                    except (OSError,IndexError): terminated=True; break
                    time.sleep(0.1)
                if not terminated:
                    try: os.kill(child_pid,signal.SIGKILL)
                    except ProcessLookupError: pass
                    raise RuntimeError("Child process survived container exit; process-tree cleanup is not enforced.")
                checks.append("process-tree termination on container exit")
            finally:
                xdg_sentinel.unlink(missing_ok=True)
                if old_secret is None: os.environ.pop("EASYPROJECT_CONFORMANCE_SECRET",None)
                else: os.environ["EASYPROJECT_CONFORMANCE_SECRET"]=old_secret
    print(json.dumps({"status":"passed","backend":"linux-rootless-oci","image":args.image,"checks":checks},indent=2))
    return 0

if __name__=="__main__":
    try: raise SystemExit(main())
    except Exception as exc:
        print("CONFORMANCE FAILED: "+str(exc),file=sys.stderr)
        raise SystemExit(1)
