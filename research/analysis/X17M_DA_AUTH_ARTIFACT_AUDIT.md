# X17M / MT6890 DA authentication-artifact audit

Date: 2026-09-21  
Scope: offline inspection only. The three supplied RAR archives, their XML
metadata, DA containers, rootfs signature files, local mtkclient sources, and
existing workspace files were inspected. No device or image was modified.

## Result

No MediaTek BootROM authorization file was found in the three firmware
archives or in the relevant local X17M tool directories.

The archives do contain:

* a signed stock `DA_BR.bin`;
* an `DA_BR_unsign.bin` whose DA signature regions are zeroed;
* `root_ro.sig`, a rootfs/read-only image signature container;
* `flash.xml`, `flash.xsd`, and the NAND scatter XML.

They do **not** contain files named or structured as `auth_sv5.auth`, a DA
authorization blob, a BootROM root certificate, or a MediaTek flashing-tool
authorization package.

## Complete archive inventory relevant to authorization

All three RARs have the same relevant file set:

```text
download_agent/DA_BR.bin
download_agent/DA_BR.bin.rg500l-30.202-orig
download_agent/DA_BR_unsign.bin
download_agent/flash.xml
download_agent/flash.xsd
root_ro.sig
MT6890_openwrt_scatter.xml
```

The `DA_BR.bin.rg500l-30.202-orig` file is byte-identical to `DA_BR.bin`; it is
not a second authorization artifact.

No archive path contains `.auth`, `.auth_sv5`, `auth`, `cert`, `certificate`,
or a separate root-certificate filename. The XML files contain no `auth`,
`cert`, `signature`, `SLA`, or `DAA` element. `flash.xml` only selects:

```xml
<dagent>DA_BR.bin</dagent>
<scatter>../MT6890_openwrt_scatter.xml</scatter>
```

Thus the firmware bundle assumes that the flashing environment already has any
required authorization material, or that authorization is supplied by the OEM
tool/service rather than shipped with the public firmware package.

## DA container analysis

The stock DA files are identical across all three archives:

```text
DA_BR.bin        c3d9058aeb56373eaadc5868ce93198fb99a9cbf876a30f876714e9007d66d56
DA_BR_unsign.bin 9133e91fd2dd4e5871a84d1709f2cac33a973025ca69f14f007a4a9f1223cfc1
```

Both are MTK DA v6 containers for hardware code `0x0992` (the live target’s
MT6890-family hardware code). The container has three declared regions and
`0x100`-byte signature lengths. In the signed/unsigned pair, the executable
payload is the same; the two signature blocks are at file offsets:

* `0x2f5cc..0x2f6bb` (256 bytes)
* `0x5d1dc..0x5d2db` (256 bytes)

The unsigned file contains zero bytes at the starts of both regions, while the
stock file contains nonzero signature material. The pair differs in 509 of
those 512 signature bytes and nowhere else of significance. Therefore
`DA_BR_unsign.bin` is an unsigned DA payload variant, **not** a BootROM auth
file and not a substitute for `auth_sv5.auth`.

The DA’s embedded signature authenticates the DA image after the host has
provided it. It does not itself satisfy the separate BootROM DAA authorization
exchange observed on the failed X17M.

## `root_ro.sig` classification

`root_ro.sig` is 3,680 bytes and begins with the same MediaTek signature format
seen in the exact router’s `rootfs_sig_a`/`rootfs_sig_b` partitions:

```text
88 16 88 58 ... "cert1"
89 16 89 58 ...
...
"cert2"
```

It contains two embedded certificate/signature records (`cert1` and `cert2`),
with Mediatek X.509-like text and dates. Its purpose is rootfs/read-only image
verification, not BootROM DA authorization. The archive copies are identical
for 1.5.13 and 8.5.4.3 and differ in the later Pro package; none is a
`SEND_AUTH`/`auth_sv5.auth` object.

The matching exact-router signature partitions are padded to 1 MiB and have
different certificate/signature bytes, so these generic `root_ro.sig` files
should not be transplanted to the router.

## Live-tool authorization flow

The local mtkclient source confirms the distinction:

1. BootROM target configuration reports DAA enabled.
2. mtkclient requires a separate file passed with `--auth` and sends it using
   the BootROM `SEND_AUTH` command.
3. A separate optional `--cert` file is sent by `SEND_CERT` as a root
   certificate; it is not the same thing as the auth blob.
4. Only after this exchange does DA transfer proceed.

The failed-router live result was:

```text
SBC enabled: True
DAA enabled: True
Auth file required
generic_patcher_payload.bin: Error on sending payload
```

This occurred before DA execution or NAND/PMT access. The prior
authentication-only attempt likewise ended with `0x7017` (`DAA_Security_Error`)
after transfer of an unauthenticated candidate DA. The ACC-bypass code inside
that DA cannot affect a rejection that occurs before the DA is executed.

## Workspace search

The relevant X17M workspace contains no OEM `*.auth`, `auth_sv5.auth`, or
matching BootROM authorization/certificate bundle. Files named `cert`/`pem` in
OpenWrt roots are ordinary TLS, TR-069, or system CA material and are unrelated
to MediaTek BootROM authorization. The local mtkclient `Library/Auth` sources
contain protocol/key-handling code and example/commented values, but no private
OEM authorization file for this target.

## Conclusion and next legitimate source

The public firmware packages are incomplete from the BootROM authorization
perspective. They provide the signed DA and image signatures, but omit the
authorization artifact required by the live target’s DAA policy. The most
credible legitimate sources for the missing object are:

* the OEM/service flashing application and its private data directory;
* a vendor-provided `auth_sv5.auth`/certificate bundle for hardware code
  `0x0992` and this product family;
* an authorized service image/tool that performs the same `SEND_AUTH` exchange.

Do not pass `root_ro.sig`, ordinary TLS certificates, or `DA_BR_unsign.bin` as
the `--auth` file. Their formats and roles are different, and doing so would
not be a valid authorization test.

## Correction: the extracted T750 SDK contains the signing documentation

The earlier workspace-only search was incomplete. The extracted source tree at:

```text
/home/kali/Desktop/x17m/zlt x17m dumps/RG500LEUACR04A06M8G_OCPU_30.202.30.202/T750
```

and its sibling firmware directory contain the MediaTek secure-chip tool source,
configuration, key material, and shell scripts that document both DA re-signing
and tool-auth generation. This is a significant finding, but it does **not** by
itself prove that the included development keys match the failed router's fused
production key.

### Tool-auth generation is explicitly documented

`mtk/tools/common/security/secure_chip_tools/usage/toolauth_usage.txt` gives the
exact commands:

```text
python toolauth.py -i settings/toolauth/toolauth_key.ini \
  -g settings/toolauth/toolauth_gfh_config_legacy.ini \
  out/toolauth/auth_sv5.auth

# PSS variant
python toolauth.py -i settings/toolauth/toolauth_key.ini \
  -g settings/toolauth/toolauth_gfh_config_pss.ini \
  out/toolauth/auth_sv5.auth
```

`toolauth.py` describes the output as a public-key certificate for DAA/SLA. It
builds a GFH tool-auth header, creates a to-be-signed blob, signs it, and
concatenates the GFH and signature into the requested output path. The PSS
configuration is for MT6890 and specifies:

```text
start_addr      = 0x00201000
file_type       = 5
pad_type        = pss
daa_pad_type    = pss
sla_pad_type    = pkcs1
max_size        = 0x00040000
```

The same configuration says `flash_dev = emmc`, despite the X17M NAND target.
That is a compatibility caveat: it may be a generic tool-auth profile, but it
must not be assumed to be valid for this router without an authorized test.

The key-selection file points to:

```text
keys/toolauth/root_prvk.pem
keys/toolauth/img_prvk.pem
keys/toolauth/da_prvk.pem
```

The source tree contains no generated `auth_sv5.auth` or `customer_da.auth`
output. It contains the generator and its inputs, not a ready-to-use OEM auth
blob.

### The build script names the expected production artifact

`quectel/common/security/1.generate_key.sh` is a stronger confirmation than the
usage text. After generating/copying the secure-chip keys, it runs:

```text
python2.7 toolauth.py -i settings/toolauth/toolauth_key.ini \
  -g settings/toolauth/toolauth_gfh_config_pss.ini \
  out/toolauth/customer_da.auth
```

It then copies `customer_da.auth` into the eFuse/security output area. The
script also creates separate key-only and full-function eFuse configurations,
with DAA/SBC disabled in one and enabled in the other. This documents the
vendor's provisioning workflow; it is not evidence that the source keys are
the keys fused into either live router.

### DA re-signing is a separate operation

`quectel/common/security/mtk_tools/tool/sign_image.sh` copies the unsigned DA to
the secure-tool prebuilt directory, renames the product copy to
`DA_BR_unsign.bin`, then runs:

```text
python resign_da.py prebuilt/resignda/DA_BR.bin MT6890 \
  settings/resignda/bbchips_pss.ini all out/resignda/DA_BR_resigned.bin
```

The MT6890 section of `bbchips_pss.ini` matches the live silicon identifiers:

```text
hw_code    = 0x992
hw_sub_code= 0x8a00
hw_ver     = 0xca00
load_region0_sigpad = pss
load_region1_sigpad = pss
load_region2_sigpad = pss
```

This explains the signed/unsigned `DA_BR.bin` pair in the public packages. The
DA's embedded signatures and the separate BootROM `auth_sv5.auth` exchange are
different artifacts and different authorization stages.

### Key material and trust limitation

The SDK includes RSA private PEMs under `keys/toolauth`, `keys/resignda`,
`keys/pbp`, and `hsm_test_keys`. Several are duplicated across those locations;
the files are labelled as build/HSM test or customer-tool inputs. No generated
auth file is present, and no analysis has established that these public keys
match the target router's fused DAA root/key hash. A source private key should
therefore be treated as development/customer material, not as proof of service
authorization.

The NAND security configuration does explicitly set `Enable_DAA="true"`, which
is consistent with the live BootROM report (`DAA enabled: True`, `Auth file is
required`). It does not remove the key-matching requirement.

### Safe next step

The newly found source makes an **offline** compatibility study possible:

1. Parse `toolauth.py` and the PSS GFH configuration to document the generated
   auth header, lengths, hashes, and signature scheme.
2. If authorized, generate a temporary `customer_da.auth`/`auth_sv5.auth`
   artifact without connecting it to a device, and record its metadata only.
3. Compare its declared MT6890 parameters with the live target and the OEM
   tool's expected `SEND_AUTH` format.

No DA, auth file, certificate, erase, write, or device state was changed while
making this source-tree finding. Do not send a generated artifact to the router
until its provenance and authorization are established.
