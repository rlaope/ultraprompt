#!/bin/sh
# Validates every skills/<name>/ against the authoring contract in skills/_TEMPLATE.md
# and _SIMULATION.md. Pure POSIX sh + grep/awk/wc; no dependencies. Exit 1 on any failure.
#
#   sh scripts/validate-skills.sh          # run from the repo root (CI does this)
set -u
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

STATUS_LINE='> Status: v0.1 baseline draft — derived from the case catalog and axis definitions; awaiting trace evidence from Fable 5.1 case runs.'
SECTIONS='## When to apply
## Core loop
## Heuristics
## Anti-patterns
## Worked example
## Trace evidence'
MIN_LINES=120
MAX_LINES=220
MAX_DESC=1536        # Claude Code frontmatter budget for description (+ when_to_use)
EXPECTED_SKILLS=12   # 8 core + 4 draft; README, CHANGELOG and both manifests hardcode "twelve"

fail=0
skills=0
err() { echo "FAIL  $1: $2"; fail=$((fail+1)); }

for dir in skills/*/; do
  [ -d "$dir" ] || continue
  name="$(basename "$dir")"
  case "$name" in _*) continue ;; esac
  skills=$((skills+1))
  f="$dir/SKILL.md"
  c="$dir/CASES.md"

  [ -f "$f" ] || { err "$name" "missing SKILL.md"; continue; }
  [ -f "$c" ] || err "$name" "missing CASES.md (every skill ships a trace-evidence log)"

  # --- frontmatter ---
  [ "$(sed -n '1p' "$f")" = "---" ] || err "$name" "SKILL.md must start with a '---' frontmatter block"
  [ "$(awk 'NR>1 && /^---$/ {print NR; exit}' "$f")" != "" ] || err "$name" "frontmatter block is never closed with '---'"
  fm_name="$(awk 'NR>1 && /^---$/ {exit} /^name:/ {sub(/^name:[ \t]*/, ""); print}' "$f")"
  [ "$fm_name" = "$name" ] || err "$name" "frontmatter name '$fm_name' does not match directory name"
  fm_desc="$(awk 'NR>1 && /^---$/ {exit} /^description:/ {sub(/^description:[ \t]*/, ""); print}' "$f")"
  [ -n "$fm_desc" ] || err "$name" "frontmatter description is empty"
  dlen="$(printf '%s' "$fm_desc" | wc -c | tr -d ' ')"
  [ "$dlen" -le "$MAX_DESC" ] || err "$name" "description is $dlen bytes (> $MAX_DESC)"

  # --- status line (verbatim, per _SIMULATION.md quality bar) ---
  grep -qxF "$STATUS_LINE" "$f" || err "$name" "status line missing or not verbatim (check model name / wording against _SIMULATION.md)"
  for chk in "$f" "$c"; do
    [ -f "$chk" ] || continue
    ! grep -qE 'Fable 5([^.0-9]|$)' "$chk" || err "$name" "stale model name 'Fable 5' in $(basename "$chk") (expected 'Fable 5.1')"
  done

  # --- section order ---
  order="$(grep -E '^## (When to apply|Core loop|Heuristics|Anti-patterns|Worked example|Trace evidence)$' "$f")"
  [ "$order" = "$SECTIONS" ] || err "$name" "core sections missing or out of order (expected: When to apply, Core loop, Heuristics, Anti-patterns, Worked example, Trace evidence)"

  # --- draft marker on the worked example while no trace exists ---
  if grep -q '_awaiting case runs_' "$f"; then
    grep -qF '*Illustrative construction, not a recorded run.*' "$f" || err "$name" "worked example lacks the 'Illustrative construction' preface while trace evidence is still empty"
  fi

  # --- line budget ---
  n="$(wc -l < "$f" | tr -d ' ')"
  [ "$n" -ge "$MIN_LINES" ] && [ "$n" -le "$MAX_LINES" ] || err "$name" "SKILL.md is $n lines (budget $MIN_LINES-$MAX_LINES)"

  # --- template leftovers ---
  ! grep -q 'AUTHORING RULES' "$f" || err "$name" "template AUTHORING RULES comment block was not deleted"
  ! grep -qE '<(kebab-case-name|Human Title|trigger condition|step|rule)' "$f" || err "$name" "template placeholder left in file"

  # --- README must link the skill ---
  grep -q "skills/$name/SKILL.md" README.md || err "$name" "not linked from README.md"
done

# --- skill set as a whole ---
[ "$skills" -eq "$EXPECTED_SKILLS" ] || err "skills" "expected $EXPECTED_SKILLS skill directories, found $skills (update EXPECTED_SKILLS, README, CHANGELOG and manifests together)"
for link in $(grep -oE 'skills/[a-z0-9-]+/SKILL\.md' README.md | sort -u); do
  [ -f "$link" ] || err "README.md" "links to $link which does not exist"
done

# --- canonical status line must match the protocol and the template ---
for doc in _SIMULATION.md skills/_TEMPLATE.md; do
  grep -qF "$STATUS_LINE" "$doc" || err "$doc" "canonical status line drifted from the one this validator enforces"
done

# --- manifests ---
if command -v python3 >/dev/null 2>&1; then
  json_ok=1
  for j in .claude-plugin/plugin.json .claude-plugin/marketplace.json; do
    python3 -c "import json; json.load(open('$j'))" 2>/dev/null || { err "$j" "invalid JSON"; json_ok=0; }
  done
  if [ "$json_ok" -eq 1 ]; then
    pv="$(python3 -c "import json; print(json.load(open('.claude-plugin/plugin.json')).get('version',''))" 2>/dev/null)"
    mv="$(python3 -c "import json; print(json.load(open('.claude-plugin/marketplace.json'))['plugins'][0].get('version',''))" 2>/dev/null)"
    [ -n "$pv" ] && [ "$pv" = "$mv" ] || err "manifests" "plugin.json version ($pv) != marketplace.json plugin version ($mv)"
  fi
else
  err "manifests" "python3 not found; manifest JSON checks could not run"
fi

echo "checked $skills skills"
if [ "$fail" -gt 0 ]; then echo "$fail failure(s)"; exit 1; fi
echo "OK"
