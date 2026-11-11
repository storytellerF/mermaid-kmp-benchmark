"""Fetch immutable upstream source snapshots; never modifies an existing checkout."""
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent

def run(*args):
    return subprocess.check_output(args, cwd=ROOT, text=True).strip()

def prepare():
    for name, library in json.loads((ROOT / "libraries.lock.json").read_text()).items():
        if library.get("artifact") and "commit" not in library:
            print(f"{name}: published artifact {library['artifact']} (verified by Gradle)", flush=True)
            continue
        destination = ROOT / ".upstream" / name
        if not destination.exists():
            destination.mkdir(parents=True)
            run("git", "-C", str(destination), "init", "--quiet")
            run("git", "-C", str(destination), "remote", "add", "origin", "https://github.com/" + library["repository"] + ".git")
            run("git", "-C", str(destination), "sparse-checkout", "init", "--cone")
            run("git", "-C", str(destination), "sparse-checkout", "set", *library["modules"])
            run("git", "-C", str(destination), "fetch", "--depth=1", "--filter=blob:none", "origin", library["commit"])
            run("git", "-C", str(destination), "checkout", "--detach", "FETCH_HEAD")
        actual = run("git", "-C", str(destination), "rev-parse", "HEAD")
        if actual != library["commit"]:
            raise RuntimeError(f"{name}: expected {library['commit']}, found {actual}")
        if run("git", "-C", str(destination), "status", "--porcelain", "--untracked-files=no"):
            raise RuntimeError(f"{name}: upstream checkout has tracked changes")
        print(f"{name}: {actual}", flush=True)

if __name__ == "__main__":
    prepare()
