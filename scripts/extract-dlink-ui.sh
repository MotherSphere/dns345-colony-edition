#!/usr/bin/env bash
# Pull the D-Link web UI from a running DNS-345 into ./extracted/web/
# for offline study. Idempotent: safe to re-run.
#
# Requires:
#   - SSH access to the NAS via the `dns345` config alias
#     (see MotherSphere/dotfiles/dns345/ssh_config.snippet)
#   - The NAS must have fun_plug installed (we tar via /mnt/HD/HD_a2 because
#     /tmp on the NAS is a 9 MB tmpfs that can't hold 16 MB of web/)
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DEST="$REPO_ROOT/extracted"
HOST="${HOST:-dns345}"

mkdir -p "$DEST"
rm -rf "$DEST/web" "$DEST/dlink-web.tar.gz"

echo "[1/4] Tarring /usr/local/modules/web/ on $HOST (via /mnt/HD/HD_a2 staging)"
ssh "$HOST" 'cd /usr/local/modules && tar czf /mnt/HD/HD_a2/dlink-web.tar.gz web/'

echo "[2/4] Downloading to $DEST/"
scp -q "$HOST:/mnt/HD/HD_a2/dlink-web.tar.gz" "$DEST/"

echo "[3/4] Cleaning up remote staging"
ssh "$HOST" 'rm /mnt/HD/HD_a2/dlink-web.tar.gz'

echo "[4/4] Extracting locally"
tar xzf "$DEST/dlink-web.tar.gz" -C "$DEST"

echo
echo "Done. Stats:"
du -sh "$DEST/web"
find "$DEST/web" -type f | wc -l | xargs printf "  %s files\n"
echo
echo "Note: extracted/ is gitignored. Don't commit D-Link's UI files."
