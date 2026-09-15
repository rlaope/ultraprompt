#!/bin/sh
# ultraprompt installer. Run `install.sh --help` for usage.
#   curl -fsSL https://raw.githubusercontent.com/rlaope/ultraprompt/main/install.sh | sh
#   ./install.sh   (from a local checkout)
#
# There is nothing to build: the skills are English prompts. This script clones/updates
# the repo and links (or copies) each skills/<name>/ into the Claude Code skills directory,
# recording what it installed in <skills dir>/.ultraprompt-installed so that --uninstall
# removes exactly that set and nothing else. It never deletes a directory it did not
# create: a pre-existing real directory with the same name is moved aside to
# <name>.bak-<timestamp> and left for you to inspect.
set -eu

REPO_URL="https://github.com/rlaope/ultraprompt.git"
SKILLS_HOME="${CLAUDE_SKILLS_DIR:-$HOME/.claude/skills}"
MARKER=".ultraprompt-managed"
MANIFEST="$SKILLS_HOME/.ultraprompt-installed"
MODE="link"
ACTION="install"

for arg in "$@"; do
  case "$arg" in
    --copy) MODE="copy" ;;
    --uninstall) ACTION="uninstall" ;;
    --help|-h)
      cat <<'USAGE'
ultraprompt installer
  sh install.sh [--copy] [--uninstall] [--help]
  curl -fsSL https://raw.githubusercontent.com/rlaope/ultraprompt/main/install.sh | sh -s -- [--copy] [--uninstall]

  --copy        copy each skill directory instead of symlinking it
  --uninstall   remove the skills this script installed (from its manifest), nothing else
  --help, -h    this text

  ULTRAPROMPT_DIR    clone location when not run from a checkout (default ~/.ultraprompt)
  CLAUDE_SKILLS_DIR  destination skills directory (default ~/.claude/skills)

  A pre-existing real directory with a skill's name is moved to <name>.bak-<timestamp>
  and is never touched again, including by --uninstall.
USAGE
      exit 0 ;;
    *) echo "unknown flag: $arg (try --help)" >&2; exit 2 ;;
  esac
done

# Local checkout if the script sits next to skills/_TEMPLATE.md; otherwise clone/update.
SELF_DIR="$(cd "$(dirname "$0")" 2>/dev/null && pwd || true)"
if [ -n "$SELF_DIR" ] && [ -f "$SELF_DIR/skills/_TEMPLATE.md" ] && [ -f "$SELF_DIR/install.sh" ]; then
  REPO_DIR="$SELF_DIR"
else
  REPO_DIR="${ULTRAPROMPT_DIR:-$HOME/.ultraprompt}"
  if [ "$ACTION" = "install" ]; then
    if [ -d "$REPO_DIR/.git" ]; then
      echo "==> Updating existing clone at $REPO_DIR"
      git -C "$REPO_DIR" pull --ff-only
    else
      echo "==> Cloning ultraprompt to $REPO_DIR"
      git clone --depth 1 "$REPO_URL" "$REPO_DIR"
    fi
  fi
fi

# Remove one installed entry if it is ours: a symlink into a skills/<name> dir, or a copy carrying our marker.
remove_entry() {
  ENTRY="$1"; NAME="$(basename "$ENTRY")"
  if [ -L "$ENTRY" ]; then
    case "$(readlink "$ENTRY" 2>/dev/null)" in
      */skills/"$NAME") rm -f "$ENTRY"; echo "    $NAME: unlinked"; return 0 ;;
    esac
  elif [ -d "$ENTRY" ] && [ -f "$ENTRY/$MARKER" ]; then
    rm -rf "$ENTRY"; echo "    $NAME: removed (copied install)"; return 0
  fi
  return 1
}

# ---------- uninstall ----------
if [ "$ACTION" = "uninstall" ]; then
  echo "==> Removing ultraprompt skills from $SKILLS_HOME"
  REMOVED=0
  if [ -f "$MANIFEST" ]; then
    while IFS= read -r NAME; do
      [ -n "$NAME" ] || continue
      ENTRY="$SKILLS_HOME/$NAME"
      { [ -e "$ENTRY" ] || [ -L "$ENTRY" ]; } || continue
      remove_entry "$ENTRY" && REMOVED=$((REMOVED+1)) || true
    done < "$MANIFEST"
    rm -f "$MANIFEST"
  else
    # No manifest (installed by an older version of this script): fall back to symlinks into this repo.
    for ENTRY in "$SKILLS_HOME"/*; do
      { [ -e "$ENTRY" ] || [ -L "$ENTRY" ]; } || continue
      if [ -L "$ENTRY" ]; then
        case "$(readlink "$ENTRY" 2>/dev/null)" in
          "$REPO_DIR"/skills/*) remove_entry "$ENTRY" && REMOVED=$((REMOVED+1)) || true ;;
        esac
      fi
    done
  fi
  if [ "$REMOVED" -eq 0 ]; then
    echo "==> Nothing removed. No manifest at $MANIFEST and no symlinks into $REPO_DIR/skills."
    echo "    If you installed from another checkout, run its ./install.sh --uninstall, or set ULTRAPROMPT_DIR to that path."
  else
    echo "==> Done. Removed $REMOVED skill(s)."
    [ -d "$REPO_DIR" ] && echo "    The clone at $REPO_DIR was left in place." || true
  fi
  exit 0
fi

# ---------- install ----------
echo "==> Installing skills into $SKILLS_HOME ($MODE mode)"
mkdir -p "$SKILLS_HOME"
: > "$MANIFEST.tmp"
COUNT=0
for SKILL_DIR in "$REPO_DIR"/skills/*/; do
  [ -f "$SKILL_DIR/SKILL.md" ] || continue
  NAME="$(basename "$SKILL_DIR")"
  case "$NAME" in _*) continue ;; esac   # templates / shared assets are not skills
  DEST="$SKILLS_HOME/$NAME"
  TARGET="${SKILL_DIR%/}"

  if [ -L "$DEST" ] && [ "$(readlink "$DEST" 2>/dev/null)" = "$TARGET" ] && [ "$MODE" = "link" ]; then
    echo "    $NAME: already linked"
  else
    if [ -L "$DEST" ]; then
      rm -f "$DEST"   # a stale or foreign symlink: safe to drop, it owns no files
    elif [ -d "$DEST" ] && [ -f "$DEST/$MARKER" ]; then
      rm -rf "$DEST"  # our own previous copy
    elif [ -e "$DEST" ]; then
      BAK="$DEST.bak-$(date +%Y%m%d%H%M%S)"
      mv "$DEST" "$BAK"
      echo "    $NAME: existing directory moved to $(basename "$BAK")"
    fi
    if [ "$MODE" = "copy" ]; then
      cp -R "$TARGET" "$DEST"
      : > "$DEST/$MARKER"
      echo "    $NAME: copied"
    else
      ln -s "$TARGET" "$DEST"
      echo "    $NAME: linked"
    fi
  fi
  echo "$NAME" >> "$MANIFEST.tmp"
  COUNT=$((COUNT+1))
done
mv "$MANIFEST.tmp" "$MANIFEST"

echo "==> Done. $COUNT skill(s) available in Claude Code (recorded in $MANIFEST)."
echo "    Load the axes you need, or paste any skills/<axis>/SKILL.md into another agent's system prompt."
echo "    Uninstall: install.sh --uninstall   (or: curl -fsSL https://raw.githubusercontent.com/rlaope/ultraprompt/main/install.sh | sh -s -- --uninstall)"
