#!/usr/bin/env bash
# Build dns345-colony-edition.module - a single uploadable artifact for
# D-Link's Application Management -> Add Ons page.
#
# Output: build/dns345-colony-edition.module (gzipped tar with the right shape)
#
# Internal structure of the produced .module:
#
#   dns345-colony-edition/
#   ├── name                   plain text display name
#   ├── version                plain text "0.1.0"
#   ├── description            short description
#   ├── checksum               sha1 of payload.tar.gz
#   ├── payload.tar.gz         the actual files dropped on the NAS
#   └── scripts/
#       ├── pre-install.sh
#       ├── post-install.sh
#       ├── pre-uninstall.sh
#       └── post-uninstall.sh
#
# After install (D-Link convention, to be confirmed empirically):
#   payload.tar.gz extracts into /mnt/HD/HD_a2/Nas_Prog/<module-name>/
#   then post-install.sh runs, which:
#     - copies /ffp/start/colony.sh (the boot hook) into place
#     - copies the overlay tree to /ffp/colony/overlay/
#     - calls colony.sh start to bind-mount immediately
set -euo pipefail

REPO="$(cd "$(dirname "$0")/.." && pwd)"
NAME="dns345-colony-edition"
VERSION="0.1.0"
DESCRIPTION="Beige + burgundy Colony reskin for the DNS-345 web UI"

BUILD="$REPO/build"
STAGE="$BUILD/stage"
PAYLOAD="$BUILD/payload"

# --- clean ---
rm -rf "$BUILD"
mkdir -p "$STAGE/$NAME/scripts" "$PAYLOAD/ffp/colony/overlay" "$PAYLOAD/ffp/start"

# --- 1. Stage payload: this is what gets extracted onto the NAS ---
echo "[1/4] Staging payload"

# 1a. Overlay tree mirrors /usr/local/modules/web/ paths under /ffp/colony/overlay/
cp -r "$REPO/theme/assets/"* "$PAYLOAD/ffp/colony/overlay/"

# 1b. Ship our CSS as a bind-mount target. Note: the actual bind happens at
# runtime, here we just place the file so the boot hook can find it.
mkdir -p "$PAYLOAD/ffp/colony/overlay/pages/css"
# Concatenate tokens + overrides into one file the bind-mount can point at.
{
    cat "$REPO/theme/css/colony-tokens.css"
    echo ""
    cat "$REPO/theme/css/overrides.css"
} > "$PAYLOAD/ffp/colony/overlay/pages/css/style.css"

# 1c. Boot hook in /ffp/start/ - executed by fun_plug on every boot
cp "$REPO/module/scripts/colony.sh" "$PAYLOAD/ffp/start/colony.sh"
chmod 755 "$PAYLOAD/ffp/start/colony.sh"

# 1d. Bundle the fonts so JetBrainsMono renders properly. Web UI references
# fonts at /web/fonts/. We ship them under that path via bind-mount.
if [ -d "$REPO/theme/fonts" ] && [ "$(ls -A "$REPO/theme/fonts" 2>/dev/null | grep -v .gitkeep)" ]; then
    mkdir -p "$PAYLOAD/ffp/colony/overlay/pages/fonts"
    cp "$REPO/theme/fonts/"*.ttf "$PAYLOAD/ffp/colony/overlay/pages/fonts/" 2>/dev/null || true
fi

# 1e. Tar the payload
echo "[2/4] Compressing payload.tar.gz"
(cd "$PAYLOAD" && tar czf "$STAGE/$NAME/payload.tar.gz" .)
PAYLOAD_CHECKSUM=$(sha1sum "$STAGE/$NAME/payload.tar.gz" | cut -d' ' -f1)

# --- 2. Module metadata ---
echo "[3/4] Writing metadata"
echo "$NAME"        > "$STAGE/$NAME/name"
echo "$VERSION"     > "$STAGE/$NAME/version"
echo "$DESCRIPTION" > "$STAGE/$NAME/description"
echo "$PAYLOAD_CHECKSUM" > "$STAGE/$NAME/checksum"

cat > "$STAGE/$NAME/scripts/pre-install.sh" << 'PRE_INSTALL'
#!/bin/sh
# Runs before payload extraction. Verify fun_plug is present.
if [ ! -d /ffp/start ] || [ ! -f /mnt/HD/HD_a2/fun_plug ]; then
    echo "ERROR: fun_plug not installed. Install fun_plug first." >&2
    exit 1
fi
exit 0
PRE_INSTALL

cat > "$STAGE/$NAME/scripts/post-install.sh" << 'POST_INSTALL'
#!/bin/sh
# Runs after payload extraction. D-Link extracts payload.tar.gz to
# /mnt/HD/HD_a2/Nas_Prog/<module-name>/ (to be confirmed) but our boot
# hook expects /ffp/colony/ and /ffp/start/colony.sh. We move files into
# place from wherever D-Link dropped them.
PKG_DIR="/mnt/HD/HD_a2/Nas_Prog/dns345-colony-edition"
if [ -d "$PKG_DIR/ffp/colony" ]; then
    mkdir -p /ffp/colony
    cp -r "$PKG_DIR/ffp/colony/"* /ffp/colony/
fi
if [ -f "$PKG_DIR/ffp/start/colony.sh" ]; then
    cp "$PKG_DIR/ffp/start/colony.sh" /ffp/start/colony.sh
    chmod 755 /ffp/start/colony.sh
fi
# Start immediately (don't wait for reboot)
[ -x /ffp/start/colony.sh ] && /ffp/start/colony.sh start
exit 0
POST_INSTALL

cat > "$STAGE/$NAME/scripts/pre-uninstall.sh" << 'PRE_UNINSTALL'
#!/bin/sh
# Stop the bind mounts before removing files.
[ -x /ffp/start/colony.sh ] && /ffp/start/colony.sh stop
exit 0
PRE_UNINSTALL

cat > "$STAGE/$NAME/scripts/post-uninstall.sh" << 'POST_UNINSTALL'
#!/bin/sh
# Clean up any leftover files outside D-Link's package directory.
rm -f  /ffp/start/colony.sh
rm -rf /ffp/colony
exit 0
POST_UNINSTALL

chmod 755 "$STAGE/$NAME/scripts/"*.sh

# --- 3. Tar the module ---
echo "[4/4] Producing $NAME.module"
(cd "$STAGE" && tar czf "$BUILD/$NAME.module" "$NAME")
SIZE=$(du -h "$BUILD/$NAME.module" | cut -f1)
echo
echo "Done: $BUILD/$NAME.module ($SIZE)"
echo "      sha1=$PAYLOAD_CHECKSUM (payload only)"
echo "      sha256 of artifact:"
sha256sum "$BUILD/$NAME.module"
echo
echo "To install: upload via D-Link web UI:"
echo "  Management -> Application Management -> Add Ons -> File Path -> Apply"
echo
echo "Or manually via SSH (if the .module mechanism rejects unsigned):"
echo "  scp $BUILD/$NAME.module dns345:/tmp/"
echo "  ssh dns345 'cd /tmp && tar xzf $NAME.module && cd $NAME && \\"
echo "             sh scripts/pre-install.sh && tar xzf payload.tar.gz -C / && \\"
echo "             sh scripts/post-install.sh'"
