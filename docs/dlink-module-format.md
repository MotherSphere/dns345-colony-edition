# D-Link `.module` add-on format (reverse-engineered)

Status: **encryption cracked, install validation incomplete.** Modules built
by `module/build.sh` are accepted past the decryption gate but still
rejected at a later validation step we haven't fully isolated. Manual SSH
install (`tar xzf` payload + run `start.sh`) works fine and is the
currently supported install path.

## What we know

### File format

A `.module` is a **Blowfish-CBC encrypted gzipped tar** at the top level.
Layout once decrypted + untar'd:

```
.module  →  openssl bf-cbc -d  →  *.tar.gz  →  tar zxf  →
    apkg.xml          XML manifest (required, see schema below)
    imodule.xml       Identical copy (alternate name apkg first looks at)
    module.tar.gz     Payload tarball, extracted by apkg into
                      /mnt/HD/HD_a2/Nas_Prog/<name>/
    preinst.sh        Runs before payload extraction
    install.sh        Runs after payload extraction
    start.sh          Runs to start the module
    stop.sh           Runs to stop the module
    remove.sh         Runs on uninstall
    clean.sh          Catch-all cleanup
```

### Encryption (cracked)

```
openssl-0.9.8 enc -bf-cbc -md md5 -k "UGi1o.yn3fir6" -in <tgz> -out <module>
```

- Cipher: Blowfish CBC
- Key derivation: MD5 (D-Link's NAS ships OpenSSL 0.9.8 which used MD5 KDF
  by default; modern OpenSSL ≥ 1.1 defaults to SHA-256 so `-md md5` is
  mandatory on the build side or the NAS can't decrypt).
- Key: literal string `UGi1o.yn3fir6` (13 chars), found at offset `0x1dc0`
  of `/lib/libapkg2.so` immediately after the format string
  `openssl-0.9.8 bf-cbc -d -in "%s" -k "%s"`.
- Same key across all DNS-3xx ShareCenter firmware variants we know of
  (DNS-320, DNS-325, DNS-345 share the apkg subsystem).

`build.sh` does the encryption end-to-end and round-trips via decrypt to
verify the output is byte-compatible with what the NAS expects.

### apkg.xml schema (best guess)

From strings in `/lib/libapkg2.so` we identified these field names:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<apkg>
    <name>module-name</name>
    <show_name>Display Name</show_name>
    <version>0.1.0</version>
    <description>Short description</description>
    <model_id>DNS-345</model_id>           <!-- checked against device -->
    <ps_name>process-name</ps_name>
    <signed>0</signed>                     <!-- 0 = third-party -->
    <apkg_version>1</apkg_version>
    <user_control>0</user_control>
    <center_type>0</center_type>
    <protect>0</protect>
    <enable>1</enable>                     <!-- lowercase -->
    <date>YYYY-MM-DD</date>
    <inst_date>YYYY-MM-DD</inst_date>
    <email>contact@example</email>
    <homepage>https://...</homepage>
    <icon>icon.png</icon>
    <inst_conflict></inst_conflict>        <!-- comma-separated module names -->
    <inst_depend></inst_depend>
    <start_conflict></start_conflict>
    <start_depend></start_depend>
    <custom_id>module-name</custom_id>
</apkg>
```

### Install flow (apkg_mgr.cgi + libapkg2.so)

1. Web UI POST to `/cgi-bin/apkg_mgr.cgi` with `cmd=app` + multipart file
2. CGI saves to `/mnt/HD/HD_a2/.systemfile/upload/<file>`
3. CGI invokes `/usr/sbin/apkg` (daemon) via socket
4. apkg decrypts module via `openssl-0.9.8 bf-cbc -d -k UGi1o.yn3fir6`
5. apkg untars into staging dir
6. apkg parses `apkg.xml` (and/or `imodule.xml`)
7. apkg writes status to `/tmp/upload_apkg_status`:
   - `0` idle
   - `2` installing
   - `3` install failed (catch-all)
   - `4` success (?)
8. JS polls `cmd=module_show_install_status` for the value

### CGI commands observed in the web UI

| cmd | Purpose |
|---|---|
| `app` | Initial upload (multipart form) |
| `module_show_install_status` | Poll `/tmp/upload_apkg_status` |
| `module_re_install` | Re-install with `module_sign_flag` (1=signed, 0=third party) |
| `install_3_party_apkg` | Third-party install path |
| `module_uninstall` | Remove a module |
| `module_enable_disable` | Start/stop a module |

## What we don't know yet

The current module passes decryption + extract + xml parse manually
(verified on the NAS), but apkg still returns status=3. Possible
remaining checks:

1. **`apkg_version` value**: we set `1`; might need to match a specific
   firmware-supported version (`0`, `2`, ...).
2. **`signed` field validation**: even with `signed=0`, the upload path
   might require `cmd=install_3_party_apkg` instead of the default
   `cmd=app`. The web UI's hidden form for third-party install uses a
   different action.
3. **`model_id` exact match**: we set `"DNS-345"`; case or spelling might
   matter (`DNS345`, `dns-345`, ...).
4. **`icon` field**: we reference `icon.png` but don't ship one. Maybe the
   icon file must exist in module.tar.gz or at top level.
5. **Required scripts having specific exit codes / output format**: e.g.
   apkg might capture script stdout and treat non-empty output as error.

A community example `.module` we could dissect would resolve all these in
minutes. None located online so far.

## Manual install path (currently working)

```bash
scp build/dns345-colony-edition.module dns345:/tmp/
ssh dns345 '
    # Decrypt + extract outer
    /usr/sbin/openssl-0.9.8 bf-cbc -d -md md5 \
        -in /tmp/dns345-colony-edition.module \
        -k "UGi1o.yn3fir6" -out /tmp/decrypted.tgz
    cd /tmp && mkdir colony-stage && cd colony-stage
    tar xzf /tmp/decrypted.tgz

    # Extract inner payload to root
    tar xzf module.tar.gz -C /

    # Start the bind-mount overlay
    sh /ffp/start/colony.sh start
'
```

That's effectively what task 28 ("Test Colony Edition on the real NAS")
validated end-to-end. The web-UI install is purely a UX improvement.

## Reference: strings dump locations

- `/lib/libapkg2.so` - validation library (`APKG_CheckSign`, schema field names)
- `/usr/sbin/apkg` - daemon binary (`APKG_Daemon is starting`, install commands)
- `/usr/local/modules/cgi/app_mgr/apkg_mgr.cgi` - web UI CGI (form handlers, status reporting)
- `/usr/sbin/openssl-0.9.8` - the OpenSSL binary apkg shells out to

All three were SCP'd to `/tmp/` on the build machine for offline analysis.
