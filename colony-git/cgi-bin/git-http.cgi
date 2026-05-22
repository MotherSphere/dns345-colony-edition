#!/ffp/bin/bash
# /colony-git/repos/* CGI wrapper around git-http-backend.
#
# Why a wrapper instead of lighttpd auth.backend ?
#   The lighttpd 1.4.28 build that ships on this D-Link DNS-345 has a broken
#   mod_auth password-verify path. crypt(3) returns correct hashes via perl
#   and openssl, but lighttpd reports "password doesn't match" for every
#   stored format ($apr1$, $1$, DES, {SHA}, plaintext). Rather than fight a
#   patched binary, we authenticate here and unconditionally exec
#   git-http-backend on success.
#
# Inputs (CGI environment):
#   HTTP_AUTHORIZATION  - "Basic base64(user:pass)"  (from lighttpd)
#   REMOTE_ADDR         - client IP
#   PATH_INFO           - everything after /colony-git/repos
#   QUERY_STRING        - usually service=git-upload-pack / git-receive-pack
#   REQUEST_METHOD      - GET / POST
#
# Hash format on disk: openssl `passwd -1` (MD5 crypt, $1$salt$hash).
# We verify by calling `openssl passwd -1 -salt <stored_salt> <supplied_pw>`
# and string-comparing the full hash.

set -u

HTPASSWD=${COLONY_GIT_HTPASSWD:-/mnt/HD/HD_a2/ffp/etc/colony-git.htpasswd}
GIT_HTTP_BACKEND=/ffp/libexec/git-core/git-http-backend
REALM="Colony Git"

deny() {
    printf 'Status: 401 Unauthorized\r\n'
    printf 'WWW-Authenticate: Basic realm="%s"\r\n' "$REALM"
    printf 'Content-Type: text/plain; charset=utf-8\r\n'
    printf '\r\n'
    printf '%s\n' "$1"
    exit 0
}

# -- Extract Basic Authorization header -------------------------------------
AUTH=${HTTP_AUTHORIZATION:-}
case "$AUTH" in
    Basic\ *) ;;
    *) deny "authentication required" ;;
esac
B64=${AUTH#Basic }
DECODED=$(printf '%s' "$B64" | /ffp/bin/base64 -d 2>/dev/null)
if [ -z "$DECODED" ] || [ "${DECODED#*:}" = "$DECODED" ]; then
    deny "malformed Authorization header"
fi
USER=${DECODED%%:*}
PASS=${DECODED#*:}

# Username sanity (defense in depth - signup.cgi already enforces this).
case "$USER" in
    ''|*[!A-Za-z0-9_-]*) deny "invalid username" ;;
esac

# -- Lookup user in htpasswd ------------------------------------------------
if [ ! -f "$HTPASSWD" ]; then
    deny "user database missing"
fi
LINE=$(grep "^${USER}:" "$HTPASSWD" 2>/dev/null | head -n 1)
if [ -z "$LINE" ]; then
    deny "invalid credentials"
fi
STORED=${LINE#*:}

# -- Verify password --------------------------------------------------------
# Stored format is `$1$salt$hash`. Re-compute with the same salt and compare.
case "$STORED" in
    \$1\$*)
        # Extract salt: everything between the second and third '$'
        REST=${STORED#\$1\$}
        SALT=${REST%%\$*}
        COMPUTED=$(/ffp/bin/openssl passwd -1 -salt "$SALT" "$PASS" 2>/dev/null)
        ;;
    *)
        # Legacy/unsupported format. Reject rather than silently accept.
        deny "unsupported password format"
        ;;
esac

if [ "$COMPUTED" != "$STORED" ]; then
    deny "invalid credentials"
fi

# -- Authenticated. Hand off to git-http-backend ---------------------------
# git-http-backend reads PATH_INFO/QUERY_STRING/REQUEST_METHOD from env and
# writes its CGI response (headers + body) directly to stdout. lighttpd has
# already set GIT_PROJECT_ROOT and GIT_HTTP_EXPORT_ALL via setenv.
export REMOTE_USER=$USER
exec "$GIT_HTTP_BACKEND"
