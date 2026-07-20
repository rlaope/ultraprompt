#!/bin/sh
# ultraprompt installer — works both ways:
#   curl -fsSL https://raw.githubusercontent.com/rlaope/ultraprompt/main/install.sh | sh
#   ./install.sh   (from a local checkout)
#
# There is nothing to build: the skills are English prompts. This script just
# clones/updates the repo and links each skill into ~/.claude/skills/.
set -e

REPO_URL="https://github.com/rlaope/ultraprompt.git"

# Local checkout if the script sits next to skills/; otherwise clone/update.
SELF_DIR="$(cd "$(dirname "$0")" 2>/dev/null && pwd || true)"
if [ -n "$SELF_DIR" ] && [ -d "$SELF_DIR/skills" ]; then
  REPO_DIR="$SELF_DIR"
else
  REPO_DIR="${ULTRAPROMPT_DIR:-$HOME/.ultraprompt}"
  if [ -d "$REPO_DIR/.git" ]; then
    echo "==> Updating existing clone at $REPO_DIR"
    git -C "$REPO_DIR" pull --ff-only
  else
    echo "==> Cloning ultraprompt to $REPO_DIR"
    git clone "$REPO_URL" "$REPO_DIR"
  fi
fi

echo "==> Linking skills into ~/.claude/skills/"
mkdir -p "$HOME/.claude/skills"
for SKILL_DIR in "$REPO_DIR"/skills/*/; do
  [ -f "$SKILL_DIR/SKILL.md" ] || continue
  NAME="$(basename "$SKILL_DIR")"
  LINK="$HOME/.claude/skills/$NAME"
  TARGET="${SKILL_DIR%/}"
  if [ -L "$LINK" ] && [ "$(readlink "$LINK" 2>/dev/null)" = "$TARGET" ]; then
    echo "    $NAME: already linked"
  elif [ -e "$LINK" ] || [ -L "$LINK" ]; then
    rm -rf "$LINK"
    ln -s "$TARGET" "$LINK"
    echo "    $NAME: relinked (replaced existing)"
  else
    ln -s "$TARGET" "$LINK"
    echo "    $NAME: linked"
  fi
done

echo "==> Done. The skills are now available in Claude Code."
echo "    Load the axes you need, or paste any skills/<axis>/SKILL.md into another agent's system prompt."
