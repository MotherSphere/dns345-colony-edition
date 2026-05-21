#!/ffp/bin/bash
# Install/refresh Colony Git hooks into every bare repo under REPOS_ROOT.
#
# Idempotent: overwrites the hook file every run so updates propagate
# without manual fan-out. Run after deploying a new hook to roll it out.
#
# Usage:
#   ssh dns345 /ffp/colony/colony-git/scripts/install-hooks.sh
# Optional first arg overrides the colony-git source dir (handy when
# called from a CI or one-shot ssh).

set -u

COLONY_GIT_DIR=${1:-/ffp/colony/colony-git}
REPOS_ROOT=${COLONY_GIT_REPOS_ROOT:-/mnt/HD/HD_a2/git}

if [ ! -d "$COLONY_GIT_DIR/hooks" ]; then
    printf 'error: hooks dir not found at %s\n' "$COLONY_GIT_DIR/hooks" >&2
    exit 1
fi
if [ ! -d "$REPOS_ROOT" ]; then
    printf 'error: repos root not found at %s\n' "$REPOS_ROOT" >&2
    exit 1
fi

installed=0
skipped=0
for repo in "$REPOS_ROOT"/*.git; do
    [ -d "$repo" ] || continue
    [ -f "$repo/HEAD" ] || { skipped=$((skipped + 1)); continue; }

    target_dir="$repo/hooks"
    mkdir -p "$target_dir"

    for src in "$COLONY_GIT_DIR/hooks/"*; do
        [ -f "$src" ] || continue
        name=$(basename "$src")
        cp "$src" "$target_dir/$name"
        chmod 755 "$target_dir/$name"
    done
    installed=$((installed + 1))
    printf 'installed: %s\n' "$(basename "$repo")"
done

printf '\n%d repo(s) updated, %d skipped\n' "$installed" "$skipped"
