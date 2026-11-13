# X17M versus the Ulan the101 mtkclient fork

Offline investigation updated with the user's read-only BootROM query, 2026-09-29. **No DA upload has been run with this fork.** The X17M's acceptance of this DA remains untested.

## Live BootROM query and CLI flag correction

The user ran `gettargetconfig` and observed **BootROM**, HW code `0x0992`, subcode `0x8a00`, HW version `0xca01`, SW version `0x0001`, and target configuration `0xe5`: SBC and DAA enabled, BootROM SLA disabled, memory read/write authorization enabled, root certificate requirement not reported. These versions pass the bundled record's host-side selection thresholds (`0xca00` and `0x0000`), and the subcode equals the DA record. This establishes host metadata compatibility only; no DA was selected or sent by `gettargetconfig`. The initial handshake took several retries before the device appeared.

The user then ran `printgpt` with the same **before-command** flag placement. The client again ignored `--skipwdt`, `--stock`, and `--loader`, disabled the watchdog, entered `DaHandler`'s automatic BootROM bypass path, and attempted to send `generic_patcher_payload.bin` through Kamakiri. The log ends at `Error on sending payload.` It does **not** show DA selection, DA1 upload, `SEND_DA`, `JUMP_DA`, DA handshake, eMMC initialization, or GPT reading. The target effect visible in the log is a volatile watchdog register write and a failed RAM payload send; no nonvolatile storage command is shown. No result about this fork's DA acceptance can be inferred from this run.

**Correction to the original live procedure:** [mtk.py](mtkclient_UnbrickThe101/mtk.py) registers the same arguments on the top-level parser and each subparser. Its subparser defaults overwrite options placed *before* the command. An offline parse of the user's exact invocation showed `skipwdt=False`, `stock=False`, `loader=None`. The observed `Disabling Watchdog...` therefore indicates a real volatile watchdog register write despite the textual `--skipwdt`. It was not a flash write. Put all safety options **after** `gettargetconfig` or `printgpt`. An offline parse of the corrected `printgpt` command below confirmed `skipwdt=True`, `stock=True`, and the specified loader. Do not run the previously documented before-command `printgpt` form: it would silently lose `--stock` and `--loader` and could enter the automatic bypass path.

The client reports `SWJTAG enabled: True` for `0xe5`, but [mtk_preloader.py](mtkclient_UnbrickThe101/mtkclient/Library/mtk_preloader.py) calculates this with `target_config & 0x6`, overlapping the SLA/DAA bits. That line is not independent evidence of SWJTAG state.

## Finding

The fork bundles a **Quectel T750/MT6890 XML DA** with a 0x0992 directory entry. It differs from the inherited upstream V6 bundle, but is **byte-for-byte identical** (`cmp` exit 0, SHA-256 `90250ef6...`) to `/home/kali/Desktop/x17m/zlt-dump/lib/da/DA_BR_acc_bypass_emmc.bin`, the X28 eMMC DA already tested on the X17M. Its DA1 region is likewise the exact same 218,944-byte slice loaded at `0x00200000`. In the prior [X17M authentication-only test](X17M_DA_AUTH_TEST.md), BootROM accepted the `SEND_DA` header, received all bytes with matching `0x9a21` checksum, then returned final `0x7017` before `JUMP_DA`. **This fork provides no new DA authentication candidate.** No X17M/Tozed/Ulan identifier or fork-specific BootROM authentication bypass was found. The surrounding SDK/auth artifacts merit separate policy analysis, but they do not change the already observed no-auth rejection of these exact DA bytes.

`0x7017` in [error.py](mtkclient_UnbrickThe101/mtkclient/Library/error.py) is a BootROM DA authentication error. Repeating the same no-auth `SEND_DA` with this fork would not isolate a new variable. The fork's read/write modifications run only after successful DA execution.

## Offline binary and public-key comparison

The reproducible [trust comparison script](x17m_da_trust_compare.py) writes [trust_comparison.json](x17m_da_0992/trust_comparison.json). It reads only local files and Git history, parses the three-region DA descriptors, compares the fork container to `/home/kali/Desktop/x17m/zlt-dump/lib/da/DA_BR_acc_bypass_emmc.bin`, extracts public moduli from three available tool-auth objects and two keys in `rootfs_sig_a.img`, checks their presence in the eMMC Preloader, and verifies DA signatures. Run it offline with `python3 /home/kali/Desktop/x17m/analysis/x17m_da_trust_compare.py`.

The fork container and prior X28 eMMC container are **identical in every byte**. Both have SHA-256 `90250ef6ae3ce671d810a30ec0b8f5f4e708def678a5e9a4baa2756f9bbac0a6`. Region 1, including its 0x100-byte signature, hashes to `e7421ad34ed26a131e8b83ff463ca42b5b671e75ef90de263446f04d9990a54a`; region 2 hashes to `5046a18c2bec79bea4aed9e4b6d3727669f97d481f36a9350e991ac463e5b46b`. Its code, headers, signatures, version, and load addresses therefore do **not** differ from the previously rejected X28 candidate.

| Local key source | RSA modulus SHA-256 | X28/fork DA1 and DA2 signature check | Raw modulus in eMMC Preloader |
|---|---|---|---|
| Deleted fork `auth_sv5.auth` from Git `7dbfdec`, embedded DAA key | `07ac65a4b324a12b2603875a6deab203e7f62a069748ae0b964de822d3b4b556` | Neither verifies | Absent |
| Separate local `auth_sv5 (1).auth`, embedded DAA key | `a13ed7b7f399882f00e71ed34e140af7956ea863c56d26b9bc99265737a1e19f` | Neither verifies | Absent |
| SDK-generated `customer_da.auth`, embedded DAA key | `9af8a28bf1096b58751ab5ef5f696c5df3050124bb9fec51bd9bf190d04c618f` | Neither verifies | Absent |
| `rootfs_sig_a.img` certificate public key 1 | `9c1eb2433f7a064b6b9a31d464a0c04802b5c66f1760c52f91ac246e100a79bb` | Neither verifies | `0x3aa08`, `0x3beec` |
| `rootfs_sig_a.img` certificate public key 2 | `f7599dad94554ebe0f0cb6b4a3697f4b9eace9c357b75c5303016c4fc69f5ec3` | Neither verifies | `0x3c0f8` |

The checks use each descriptor's body and 0x100-byte signature with RSA-PSS/SHA-256 (32-byte or auto-detected salt) and PKCS#1 v1.5/SHA-256. The stock Quectel NAND `DA_BR.bin` is a positive control: both stages verify under the SDK-generated `9af8...` DAA key with RSA-PSS/SHA-256, 32-byte salt. The ACC-bypass NAND DA verifies under that key for stage 1 but not stage 2. Thus the comparison code and key extraction can produce a positive result on known material. The X28/fork eMMC negative results mean **none of these available keys verifies its signatures under the tested schemes**; they do not show that its signatures are intrinsically malformed, nor identify its real signer.

The deleted fork auth object has SHA-256 `f75f4387b279e27271cbf9c038837dd73620c75870bcf76bb56c1fc51f1f6c34`. Its outer GFH signature verifies under its own embedded root public key, but its embedded DAA key does not verify this fork's DA. Self-consistency of an auth file does not establish that the X17M BootROM trusts its root. The rootfs certificate keys' presence in the eMMC Preloader establishes **Preloader/certificate evidence**; it does not by itself prove that either key is the **BootROM DAA fused trust anchor**. Earlier workspace notes equating those domains are stronger than the evidence supports. The actual BootROM trust decision remains established by the live `0x7017` for the exact X28/fork bytes, not by these key-presence tests alone.

## Repository provenance and changes

Local Git comparison uses `0542a87` as the last inherited baseline and `7dbfdec` as the fork's main functional change. This is an in-repository upstream baseline, not a claim about the current remote upstream release.

| Area | Evidence | Relevance |
|---|---|---|
| README | [README.md](mtkclient_UnbrickThe101/README.md) claims Ulan the101, MT6890 eMMC and gives write/read examples. | Target claim only; no device authentication evidence. |
| Chip config | [brom_config.py](mtkclient_UnbrickThe101/mtkclient/config/brom_config.py), `0x992` entry: `dacode=0x0992`, XFLASH default, eFuse `0x11ec0000`, and modem name. | **Inherited**: the 0x992 entry exists in `65d8c4a`; the fork did not introduce it. The current name mentions MT6880/MT6890. |
| DA bundle | [MTK_DA_V6.bin](mtkclient_UnbrickThe101/mtkclient/Loader/MTK_DA_V6.bin), added/replaced in `90d25c0`. | Quectel/T750/MT6890 build, exactly identical to the already rejected local X28 eMMC DA. |
| DA selection | [daconfig.py](mtkclient_UnbrickThe101/mtkclient/Library/DA/daconfig.py) in `7dbfdec`: fallback for missing explicit loader; preserve explicitly supplied path. | Does not alter signature validation. One bug remains: duplicate check compares `da.hw_sub_code == da.hw_sub_code`, and selection checks HW/SW versions but **does not filter on subcode**. |
| XML connection | [mtk_da_handler.py](mtkclient_UnbrickThe101/mtkclient/Library/DA/mtk_da_handler.py) in `7dbfdec`: initialize a connected CDC port with no target config. | Connection reliability, after USB enumeration. |
| XML DA stage 2 | [xml_lib.py](mtkclient_UnbrickThe101/mtkclient/Library/DA/xmlflash/xml_lib.py) in `7dbfdec`: reconnect after USB speed change; tolerate absent patch pattern; extra read response waits. | Operates **after** DA1 acceptance/execution. Cannot resolve BootROM `0x7017`. |
| eMMC/NAND read path | `7dbfdec` changes [storage.py](mtkclient_UnbrickThe101/mtkclient/Library/DA/storage.py), [mtk_daloader.py](mtkclient_UnbrickThe101/mtkclient/Library/DA/mtk_daloader.py), [mtk_da_handler.py](mtkclient_UnbrickThe101/mtkclient/Library/DA/mtk_da_handler.py), and XML flash. | Full-size read trim and XML 0x1a00000 batching; named partition/PMT support is mainly NAND. Neither changes DA authentication. |
| XML write path | `7dbfdec` adds `WRITE-PARTITION` by name in [xml_cmd.py](mtkclient_UnbrickThe101/mtkclient/Library/DA/xmlflash/xml_cmd.py) and XML flash. | Post-DA, potentially destructive; irrelevant to first test. |
| XML extension | `7dbfdec` changes [v6.py](mtkclient_UnbrickThe101/mtkclient/Library/DA/xmlflash/extension/v6.py) and ARM helpers to tolerate missing patterns and adds 32-bit security/flash-policy patches. | Post-DA optional patching. Exclude with `--stock` in the live test. |
| SLA/DAA | BootROM `SEND_AUTH`, `SEND_CERT`, `SLA`, and `SEND_DA` live in inherited [mtk_preloader.py](mtkclient_UnbrickThe101/mtkclient/Library/mtk_preloader.py). XML `check_sla()` occurs after DA2 start. | No fork-specific 0x0992 DAA bypass was found. |

The fork deleted many upstream loaders and `download_agent` artifacts. Its older Git history briefly added `download_agent/auth_sv5.auth` and a `MT6890_openwrt_scatter.xml` in `7dbfdec`, then deleted that directory in `63dc7ad`. The auth file is **not available in HEAD** and was not supplied to the user's query. The current V6 binary SHA-256 is `90250ef6ae3ce671d810a30ec0b8f5f4e708def678a5e9a4baa2756f9bbac0a6` (402,332 bytes), exactly matching the previously tested local X28 eMMC file. The inherited upstream V6 bundle at `0542a87` was 13,529,076 bytes, SHA-256 `c4052322b6a4d7fae281322352a08cd4fa02d4afc7c65b5f88c5d06c50d7da70`, and **already included a 0x0992 record** with the same subcode/HW/SW version values but different region hashes. Thus 0x0992 support itself is not fork-specific.

## DA container and extraction

The header is `MTK_DOWNLOAD_AGENT`, version string `MTK_DA_v6_2023-12-20 13:07:58`, little-endian record count **1**. `DAconfig.parse_da_loader()` reads record 0 at `0x6c` and `DA` parses 10 16-bit fields followed by 20-byte region descriptors. The nominal record stride is `0xdc`; in this one-record file, executable data begins immediately after the three used descriptors at `0xbc`. The V6 header selects **XML mode**, even though the inherited chip config defaults to XFLASH.

| Record/region | HW code | Subcode | HW ver | SW ver | Mode | Region offset | Length | Load address | `m_start_offset` | Sig length |
|---|---:|---:|---:|---:|---|---:|---:|---:|---:|---:|
| 0 / 0 | `0x0992` | `0x8a00` | `0xca00` | `0x0000` | V6 XML | `0x0000bc` | `0x35740` | `0x00200000` | `0x356fc` | `0x100` |
| 0 / 1 (DA1) | `0x0992` | `0x8a00` | `0xca00` | `0x0000` | V6 XML | `0x0000bc` | `0x35740` | `0x00200000` | `0x356fc` | `0x100` |
| 0 / 2 (DA2) | `0x0992` | `0x8a00` | `0xca00` | `0x0000` | V6 XML | `0x0357fc` | `0x2cba0` | `0x40000000` | `0x6229c` | `0x100` |

Region count is **3**, `pagesize` field `0x1000`, `entry_region_index` 0. Region 0 and 1 are byte-identical; the XML upload implementation uses **region 1 for DA1** and **region 2 for DA2**. The file ends at `0x6239c`, exactly the end of region 2. In this new bundle, `m_start_offset` equals the absolute file offset of each trailing 0x100-byte block (`region offset + region length - 0x100`), unlike the inherited upstream 0x0992 entry where it equals `region length - 0x100`. The loader code does not use this field for XML DA upload, so its exact format meaning remains unverified.

Reproduce without modifying the container:

```sh
python3 /home/kali/Desktop/x17m/analysis/x17m_analyze_da.py
```

The script creates [manifest.json](x17m_da_0992/manifest.json), [region 0](x17m_da_0992/record0_region0.bin), [DA1](x17m_da_0992/record0_region1.bin), and [DA2](x17m_da_0992/record0_region2.bin), plus separate bodies and 0x100-byte trailing blocks. It validates file bounds and stores offsets, strings, markers and SHA-256 hashes. Region 0 and DA1 both hash to `e7421ad34ed26a131e8b83ff463ca42b5b671e75ef90de263446f04d9990a54a`; DA2 hashes to `5046a18c2bec79bea4aed9e4b6d3727669f97d481f36a9350e991ac463e5b46b`. The DA1 trailing block hashes to `517c86558ec542b6039fb4c8b65daad84f808cc2a6ba34572b20b6fad7cde0dc`; DA2's to `5bbdb6c46cd029e99ad8fd7fe01529f111ea8cc9ba04ac01901d38649ba2b7cd`.

## Headers, signatures and identity clues

DA1 begins with ARM instructions (`ffff ffea ...`), DA2 with an ARM branch vector (`070000ea ...`), not a top-level `MMM\x01` GFH header. Two `MMM\x01` byte sequences occur **inside DA2** at relative `0x189ec` and `0x18fcc`; surrounding bytes are executable-looking tables/code, so treating them as GFH structures without format validation would be unsound. The extraction script records them without labeling them valid GFH. No top-level GFH file-info, parsed certificate chain, PEM public key, or DER RSA OID was found. Each region has a 0x100-byte high-entropy trailing block described as a signature by the directory. This is consistent with a 2048-bit RSA signature, but the algorithm, covered digest, and signer cannot be proven from the container alone. No confirmed RSA modulus or SHA digest table was recovered. A `SHA` string in DA1 and `RSA`/`CERT` strings in DA2 are code/log text, not proof of embedded keys or certificates.

Strong binary identity clues include DA1 relative `0x2a064` and DA2 relative `0x1ea00` paths under `/home/quectel/workspace/Scm_MTK_T750/T750/...`, multiple `platform/mt6890/` source paths, DA2 `QUECTEL_PLATFORM` at `0x26030`, DA1 `MTK_EMMC_SUPPORT defined.` at `0x2aeb9`, and DA2 `emmc_init start.` at `0x2121c`. DA2 also contains `CMD:SECURITY-SET-FLASH-POLICY`, `CMD:SECURITY-SET-ALLINONE-SIGNATURE`, `hash_binding`, `img_auth_required`, security-policy messages, and `EMMC-USER` strings. These demonstrate relevant XML commands and eMMC support in the binary, not X17M authorization. No literal `X17M`, `TOZED`, `ULAN`, or `OEM_PUBK` string was found in the extracted regions. MD5, SHA-1 and SHA-256 digests of both the full DA2 and its body were searched as raw bytes in DA1; none matched, so there is no identified plain DA2 hash binding in this image.

## Actual code path and stop points

1. `mtk.py` creates `Mtk`; [Port.py](mtkclient_UnbrickThe101/mtkclient/Library/Port.py) and `mtk_preloader.py` perform USB CDC handshake. `Preloader.init()` sends `GET_HW_CODE` (`0xfd`), configures `0x0992`, reads `GET_TARGET_CONFIG` (`0xd8`), BL/BROM version, `GET_HW_SW_VER` (`0xfc`), and MEID. With default settings it also writes the watchdog register; `--skipwdt` avoids that **only when placed after the subcommand**. BL version echo identifies BootROM. Without `--auth` or `--cert`, no authentication bytes are sent in this phase; the code only warns if DAA is set.
2. `DAconfig` scans the loader path or an explicit `--loader`, matches `dacode=0x0992`, and accepts a record if record HW/SW versions are no greater than target values (or target values are zero). It does **not** match `0x8a00` against target subcode. V6 flips mode to XML. The exact selected record can be established offline from this one-record bundle, but target version compatibility still requires a live read.
3. `DaHandler.configure_da()` can invoke crash/exploit/bypass paths on a protected target unless `--stock` and explicit `--loader` are supplied. With these flags, it proceeds to stock DA upload. [xml_lib.py](mtkclient_UnbrickThe101/mtkclient/Library/DA/xmlflash/xml_lib.py) loads region 1, passes address `0x200000`, length `0x35740` and signature length `0x100` to `Preloader.send_da()`. This sends `SEND_DA` (`0xd7`) and parameters first; on preliminary status 0 it transfers the DA1 bytes and reads checksum/final status. A preliminary `0x7017` stops **before payload transfer**; a final `0x7017` stops after transfer but **before execution**. The earlier observation should be located against these two status points if possible.
4. Only if `send_da()` succeeds does `JUMP_DA` (`0xd5`) run. DA1 must answer XML `CMD:START` before runtime setup. DA1 then receives runtime/init commands. It requests DA2 via `CMD:BOOT-TO`; the host uploads DA2's body (signature excluded by the XML path), negotiates USB speed, reconnects, checks XML DA SLA, and asks for hardware/storage info. `--stock` suppresses host-side DA patches and exploit paths, but XML SLA logic may send a 0x100-byte dummy signature when no key is identified; failure should stop the test. BootROM DAA and DA XML SLA are distinct stages.
5. `get_hw_info()` parses `EMMC` and its block/boot/user/RPMB sizes after DA2 is alive; this is the first reliable host-visible storage initialization proof. `printgpt` then reads eMMC user sectors through the DA and parses GPT via [partition.py](mtkclient_UnbrickThe101/mtkclient/Library/partition.py). On NAND, the fork instead uses XML `READ-PARTITION-TABLE`/PMT. Printing GPT is a read operation; it is not required to establish SEND_DA acceptance or DA start.

An important caveat: `send_da()` has a BootROM SLA branch for status `0x1d0d`; the inherited `handle_sla()` treats `0x7017` from its own SLA command as success. This is **not** a general `SEND_DA 0x7017` success path; the ordinary SEND_DA error branch returns `False` and never jumps.

## Live test status and next gate

The user's `gettargetconfig` run completed the identification phase. It issued no DA or storage command. The earlier [X17M DA authentication-only test](X17M_DA_AUTH_TEST.md) already completed the no-auth `SEND_DA` phase with **the identical DA and stage-1 bytes**, ending in final `0x7017`, no jump and no storage command. There is no reason to repeat this exact no-auth test through `printgpt`; it would merely resend the rejected DA. The prior [SEND_AUTH result](MT6890_SEND_AUTH_LIVE_RESULT_20260922.md) and [policy reconciliation](MT6890_DAA_POLICY_OFFLINE_RECONCILIATION_20260922.md) describe a separate SDK auth + NAND DA attempt and its unresolved BootROM policy question. Those results do not make this eMMC DA newly authorized.

**Correct argument order for a future identification repeat, if ever needed:**

```sh
python3 mtk.py gettargetconfig --skipwdt --stock --loader mtkclient/Loader/MTK_DA_V6.bin
```

This sends the USB handshake, hardware/version/target-config queries and MEID query. `gettargetconfig` calls the target-config query again. With the options in this position, `--skipwdt` avoids the ordinary watchdog register write. It does **not** send a DA, alter eMMC, or bypass security. The user's already captured BootROM/version/config output is sufficient, so a repeat is unnecessary.

**The previously proposed `printgpt` command is withdrawn.** It has not been run from this fork, and there is no expected authentication gain from doing so without a new, independently justified authorization input. The next useful work is offline: identify a DA/auth pair that differs from the rejected X28 bytes and validate its signing relationship and target policy. Only after that should a new live command be specified and reviewed. In any future command with this CLI, put `--skipwdt`, `--stock`, `--loader`, and any other options **after** the subcommand; before-command options are silently overwritten.

## Interpretation of live results

| Observation | Meaning |
|---|---|
| No 0x0992 selection | Host matching/version issue; no trust verdict. |
| `SEND_DA` preliminary or final `0x7017` | Already observed for these exact stage-1 bytes in the no-auth state; no DA execution. |
| `SEND_DA` succeeds, `JUMP_DA` fails | DA transfer accepted, execution/startup unproven. |
| XML `CMD:START` from DA1 | DA1 executed. |
| DA2 starts, `EMMC` sizes reported | XML DA and eMMC initialized. |
| GPT printed | Read-only partition access works; does not authorize writes. |

No result here can be inferred merely from the container header or README claim. The decisive no-auth `SEND_DA` result for this exact DA is already `0x7017`; a new authorization artifact or a different validated DA is needed to make another test informative.
