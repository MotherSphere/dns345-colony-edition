#!/usr/bin/env bash
# Build dns345-colony-edition.module — D-Link Add-Ons compatible artifact.
#
# Format reverse-engineered from /usr/sbin/apkg (the installer binary)
# strings + /usr/local/modules/cgi/app_mgr/apkg_mgr.cgi behavior.
#
# .module is a gzipped tar with this layout at the top level (no wrapping dir):
#
#   apkg.xml          — manifest in D-Link XML schema (name, version,
#                       show_name, description, model_id, signed, ...)
#   module.tar.gz     — payload tarball (extracted by apkg via "tar zxf
#                       module.tar.gz" into the module's install dir)
#   preinst.sh        — runs before payload extraction
#   install.sh        — runs after payload extraction (optional)
#   start.sh          — runs to start the module
#   stop.sh           — runs to stop the module
#   remove.sh         — runs on uninstall
#   clean.sh          — runs to clean leftovers
#
# Install dir lives at /mnt/HD/HD_a2/Nas_Prog/<module-name>/

set -euo pipefail

REPO="$(cd "$(dirname "$0")/.." && pwd)"
NAME="dns345-colony-edition"
VERSION="0.1.0"
SHOW_NAME="DNS-345 Colony Edition"
DESCRIPTION="Beige + burgundy Colony reskin for the DNS-345 web UI"
MODEL_ID="DNS-345"

BUILD="$REPO/build"
STAGE="$BUILD/stage"        # outer tarball staging (becomes .module)
PAYLOAD="$BUILD/payload"    # inner module.tar.gz staging

rm -rf "$BUILD"
mkdir -p "$STAGE" "$PAYLOAD/ffp/colony/overlay" "$PAYLOAD/ffp/start"

# --- 1. Stage the inner payload tarball (module.tar.gz) ---------------------
echo "[1/5] Staging inner payload"

# Overlay tree (mirrors /usr/local/modules/web/ paths) goes under
# ffp/colony/overlay/ so colony.sh can find it at /ffp/colony/overlay/.
cp -r "$REPO/theme/assets/"* "$PAYLOAD/ffp/colony/overlay/"

# Stitched style.css = D-Link stock + Colony tokens + overrides
mkdir -p "$PAYLOAD/ffp/colony/overlay/pages/css"
DLINK_STYLE="$REPO/extracted/web/pages/css/style.css"
if [ ! -f "$DLINK_STYLE" ]; then
    echo "ERROR: missing $DLINK_STYLE" >&2
    echo "Run scripts/extract-dlink-ui.sh first." >&2
    exit 1
fi
{
    echo "/* === D-LINK STOCK style.css === */"
    cat "$DLINK_STYLE"
    echo ""
    echo "/* === COLONY EDITION tokens === */"
    cat "$REPO/theme/css/colony-tokens.css"
    echo ""
    echo "/* === COLONY EDITION overrides === */"
    cat "$REPO/theme/css/overrides.css"
} > "$PAYLOAD/ffp/colony/overlay/pages/css/style.css"

# Boot hook
cp "$REPO/module/scripts/colony.sh" "$PAYLOAD/ffp/start/colony.sh"
chmod 755 "$PAYLOAD/ffp/start/colony.sh"

# --- 2. Pack module.tar.gz --------------------------------------------------
echo "[2/5] Packing module.tar.gz"
(cd "$PAYLOAD" && tar czf "$STAGE/module.tar.gz" .)

# --- 3. Write apkg.xml manifest ---------------------------------------------
# Schema reverse-engineered from /usr/sbin/apkg strings. Order matters less
# than completeness — missing fields tend to be more dangerous than extras.
echo "[3/5] Writing apkg.xml"
TODAY="$(date +%Y-%m-%d)"
cat > "$STAGE/apkg.xml" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<apkg>
    <name>${NAME}</name>
    <show_name>${SHOW_NAME}</show_name>
    <version>${VERSION}</version>
    <description>${DESCRIPTION}</description>
    <model_id>${MODEL_ID}</model_id>
    <ps_name>${NAME}</ps_name>
    <signed>0</signed>
    <apkg_version>1</apkg_version>
    <user_control>0</user_control>
    <center_type>0</center_type>
    <protect>0</protect>
    <enable>1</enable>
    <date>${TODAY}</date>
    <inst_date>${TODAY}</inst_date>
    <email>colony@motherphere</email>
    <homepage>https://github.com/MotherSphere/dns345-colony-edition</homepage>
    <icon>icon.png</icon>
    <inst_conflict></inst_conflict>
    <inst_depend></inst_depend>
    <start_conflict></start_conflict>
    <start_depend></start_depend>
    <custom_id>${NAME}</custom_id>
</apkg>
EOF

# imodule.xml: identical content under a different filename. apkg first
# looks at imodule.xml then falls back to apkg.xml in the strings trace.
cp "$STAGE/apkg.xml" "$STAGE/imodule.xml"

# --- 4. Write lifecycle scripts ---------------------------------------------
echo "[4/5] Writing lifecycle scripts"

cat > "$STAGE/preinst.sh" << 'PREINST'
#!/bin/sh
# Pre-install: verify fun_plug is installed (we need /ffp to deploy into).
if [ ! -d /ffp/start ] || [ ! -d /mnt/HD/HD_a2 ]; then
    echo "ERROR: fun_plug not installed or /mnt/HD/HD_a2 missing" >&2
    exit 1
fi
exit 0
PREINST

cat > "$STAGE/install.sh" << 'INSTALL'
#!/bin/sh
# Install: D-Link's apkg has already extracted module.tar.gz into the
# install dir (typically /mnt/HD/HD_a2/Nas_Prog/dns345-colony-edition/).
# Move our payload from that staging dir into /ffp/ where colony.sh
# expects to find it.
INSTALL_DIR="$1"
[ -z "$INSTALL_DIR" ] && INSTALL_DIR="/mnt/HD/HD_a2/Nas_Prog/dns345-colony-edition"

# Copy overlay assets into /ffp/colony/
if [ -d "$INSTALL_DIR/ffp/colony" ]; then
    mkdir -p /ffp/colony
    cp -r "$INSTALL_DIR/ffp/colony/"* /ffp/colony/
fi

# Copy boot hook into /ffp/start/
if [ -f "$INSTALL_DIR/ffp/start/colony.sh" ]; then
    cp "$INSTALL_DIR/ffp/start/colony.sh" /ffp/start/colony.sh
    chmod 755 /ffp/start/colony.sh
fi
exit 0
INSTALL

cat > "$STAGE/start.sh" << 'START'
#!/bin/sh
# Start: kick off the bind-mount overlay.
[ -x /ffp/start/colony.sh ] && /ffp/start/colony.sh start
exit 0
START

cat > "$STAGE/stop.sh" << 'STOP'
#!/bin/sh
# Stop: tear down bind mounts.
[ -x /ffp/start/colony.sh ] && /ffp/start/colony.sh stop
exit 0
STOP

cat > "$STAGE/remove.sh" << 'REMOVE'
#!/bin/sh
# Remove: stop overlay + delete our /ffp/ deployment.
[ -x /ffp/start/colony.sh ] && /ffp/start/colony.sh stop
rm -f /ffp/start/colony.sh
rm -rf /ffp/colony
exit 0
REMOVE

cat > "$STAGE/clean.sh" << 'CLEAN'
#!/bin/sh
# Clean: catch-all cleanup, same as remove.sh.
sh remove.sh
exit 0
CLEAN

chmod 755 "$STAGE/"*.sh

# --- 5. Pack the outer tarball ----------------------------------------------
# Outer is gzipped tar at top level (no wrapping dir).
echo "[5/6] Packing outer tarball"
(cd "$STAGE" && tar czf "$BUILD/$NAME.tgz" \
    apkg.xml imodule.xml module.tar.gz \
    preinst.sh install.sh start.sh stop.sh remove.sh clean.sh)

# --- 6. Blowfish-CBC encrypt the tarball into a .module ---------------------
# Reverse-engineered from /lib/libapkg2.so strings: D-Link's apkg runs
#   openssl-0.9.8 bf-cbc -d -in <module> -k "UGi1o.yn3fir6"
# to decrypt the uploaded module. We do the encrypt side here.
#
# Modern openssl 3.x removes bf-cbc from default providers — use -provider
# legacy to keep it. The cipher itself hasn't changed since OpenSSL 0.9.8,
# so encrypt output is byte-compatible.
BF_KEY='UGi1o.yn3fir6'

echo "[6/6] Encrypting .tgz -> .module (Blowfish CBC, hardcoded D-Link key)"
# NAS runs openssl-0.9.8 which uses MD5 as the password-key derivation
# function. Modern OpenSSL >= 1.1 uses SHA-256 by default. We MUST pass
# -md md5 so that the NAS can decrypt the file we produce.
ENC_OPTS=(-bf-cbc -md md5 -k "$BF_KEY")

# Build encrypt args: legacy provider needed on modern OpenSSL 3.x.
encrypt() {
    openssl enc "${ENC_OPTS[@]}" -in "$BUILD/$NAME.tgz" -out "$BUILD/$NAME.module" 2>/dev/null \
        || openssl enc "${ENC_OPTS[@]}" -provider legacy -provider default \
            -in "$BUILD/$NAME.tgz" -out "$BUILD/$NAME.module"
}

if ! encrypt; then
    echo "ERROR: openssl bf-cbc not available" >&2
    exit 1
fi

# Sanity: the produced .module must round-trip through bf-cbc -d to the
# original .tgz.
decrypt() {
    openssl enc "${ENC_OPTS[@]}" -d -in "$BUILD/$NAME.module" 2>/dev/null \
        || openssl enc "${ENC_OPTS[@]}" -d -provider legacy -provider default \
            -in "$BUILD/$NAME.module" 2>/dev/null
}

if ! decrypt | cmp -s - "$BUILD/$NAME.tgz"; then
    echo "ERROR: round-trip decrypt didn't match original tarball" >&2
    exit 1
fi

SIZE=$(du -h "$BUILD/$NAME.module" | cut -f1)
echo
echo "Done: $BUILD/$NAME.module ($SIZE)"
echo
echo "Outer tarball (before encryption) contents:"
tar tzf "$BUILD/$NAME.tgz" | sed 's/^/  /'
echo
sha256sum "$BUILD/$NAME.module"
echo
echo "Install: web UI → Application Management → Add Ons → File Path → Apply"
