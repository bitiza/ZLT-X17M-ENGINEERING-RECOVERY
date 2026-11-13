#!/usr/bin/env python3
"""Offline only. Reads artifacts; writes evidence beneath this research directory."""
from pathlib import Path
import re,struct,hashlib,json,subprocess
import capstone
ROOT=Path(__file__).resolve().parents[1]; E=ROOT/'evidence'
BACK=Path('/home/kali/Desktop/bozax17/backups/x17m-1gb-20260921-061524/logical')
paths=[BACK/n for n in ['mtd00_preloader.img','mtd01_preloader_backup.img','mtd25_lk_a.img','mtd39_lk_b.img']]
paths += list(Path('preloaders').glob('*'))
manifest=[]
for p in paths:
 b=p.read_bytes(); manifest.append(dict(path=str(p.resolve()),size=len(b),sha256=hashlib.sha256(b).hexdigest()))
 with (E/(p.name+'.strings.txt')).open('w') as f:
  for m in re.finditer(rb'[ -~]{4,}',b): f.write(f'{m.start():08x} {m.group().decode()}\n')
(E/'artifact-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
b=paths[2].read_bytes()
headers=[]
for m in re.finditer(bytes.fromhex('88168858'),b):
 o=m.start(); size=struct.unpack_from('<I',b,o+4)[0]; name=b[o+8:o+40].split(b'\0')[0].decode(); headers.append(dict(header=hex(o),payload=hex(o+512),size=hex(size),name=name))
(E/'lk-containers.json').write_text(json.dumps(headers,indent=2)+'\n')
terms=['fastboot','getvar:','download:','flash:','erase:','upload:','fetch:','reboot-bootloader','oem','unlock','boot_mode','recovery','bootloader','usb_download','download_mode','TOOBTSAF','FASTBOOT']
with (E/'term-scan.txt').open('w') as f:
 for p in paths[:4]:
  d=p.read_bytes(); f.write(f'\n{p}\n')
  for t in terms:
   hits=[hex(m.start()) for m in re.finditer(re.escape(t.encode()),d,re.I)]; f.write(f'{t}: {", ".join(hits) or "ABSENT"}\n')
# Relative Thumb references, using file coordinates so relocation cancels out.
md=capstone.Cs(capstone.CS_ARCH_ARM,capstone.CS_MODE_THUMB); md.detail=True; md.skipdata=True
out=[]
for start,end,label in [(512,0x2f000,'main'),(0x45c70,0x72900,'aee')]:
 hist=[]
 for i in md.disasm(b[start:end],start):
  if i.id==0: hist=[]; continue
  if i.mnemonic=='add' and i.op_str.endswith(', pc'):
   reg=i.op_str.split(',')[0]
   for j in reversed(hist[-7:]):
    if j.mnemonic.startswith('ldr') and j.op_str.startswith(reg+', [pc,'):
     try:
      imm=int(j.op_str.split('#')[1].split(']')[0],0)
      lit=((j.address+4)&~3)+imm
      delta=struct.unpack_from('<i',b,lit)[0]; target=(i.address+4+delta)&0xffffffff
      s=b[target:target+140].split(b'\0')[0]
      if s and all(32<=x<127 or x in [10,13,9] for x in s) and re.search(rb'fastboot|reboot|getvar|set_active|mrdump|product|is-userspace|serialno|boot mode',s,re.I):
       out.append((label,j.address,i.address,lit,target,s.decode()))
     except (ValueError,IndexError,struct.error): pass
     break
  hist.append(i)
# Main LK uses MOVW/MOVT absolute virtual addresses (0x84000000).
# Decode candidates at every halfword so literal pools cannot desynchronize scanning.
for start,end,label,vbase in [(512,0x2f000,'main',0x84000000),(0x45c70,0x72900,'aee',0x83000000)]:
 for off in range(start,end-4,2):
  ins=list(md.disasm(b[off:off+4],off,count=1))
  if not ins or ins[0].mnemonic!='movw': continue
  lo=ins[0]; reg=lo.operands[0].reg; value=lo.operands[1].imm
  for hi in md.disasm(b[off+lo.size:off+lo.size+24],off+lo.size):
   if hi.id and hi.mnemonic=='movt' and hi.operands[0].reg==reg:
    va=value+(hi.operands[1].imm<<16); target=va-vbase+start
    if 0<=target<len(b):
     st=b[target:target+160].split(b'\0')[0]
     if st and all(32<=x<127 or x in [10,13,9] for x in st) and re.search(rb'fastboot|reboot|getvar|set_active|mrdump|product|is-userspace|serialno|boot mode|download|continue|usb|udc',st,re.I):
      out.append((label,lo.address,hi.address,va,target,st.decode()))
    break
with (E/'thumb-string-xrefs.tsv').open('w') as f:
 for label,ld,ad,lit,t,s in out: f.write(f'{label}\tMOVW_or_LDR={ld:#x}\tMOVT_or_ADD={ad:#x}\taddress={lit:#x}\tstring={t:#x}\t{s!r}\n')
# Fixed descriptor search; candidates require internally consistent bLength/type.
with (E/'usb-descriptor-candidates.txt').open('w') as f:
 for off in range(len(b)-18):
  if b[off:off+2]==b'\x12\x01' and b[off+7] in [8,16,32,64] and b[off+8:off+10]==b'\x8d\x0e':
   f.write(f'DEVICE {off:#x}: {b[off:off+18].hex(" ")}\n')
  if b[off:off+2]==b'\x09\x04' and b[off+5:off+8]==b'\xff\x42\x03': f.write(f'FASTBOOT INTERFACE {off:#x}: {b[off:off+9].hex(" ")}\n')
with (E/'tool-output.txt').open('w') as f:
 for cmd in [['file',*[str(p) for p in paths[:4]]],['readelf','-h',str(paths[2])],['objdump','-f',str(paths[2])]]:
  r=subprocess.run(cmd,text=True,capture_output=True);f.write('$ '+' '.join(cmd)+'\n'+r.stdout+r.stderr+f'exit={r.returncode}\n')
print('Evidence generated. Thumb string xrefs:',len(out))

# Preserve selected instruction ranges, with file offsets rather than guessed symbols.
for name,ranges,mode,data in [
 ('lk-main-disassembly.txt',[(0x2c7a,0x2d04),(0x3360,0x354a),(0x36d8,0x3700)],capstone.CS_MODE_THUMB,b),
 ('lk-aee-disassembly.txt',[(0x4e640,0x4e830)],capstone.CS_MODE_THUMB,b),
 ('adbd-reboot-disassembly.txt',[(0xd848,0xd8e0),(0xe658,0xe670),(0xe928,0xe954)],0,Path('rootfs.original/sbin/adbd_usb').read_bytes())]:
 dis=capstone.Cs(capstone.CS_ARCH_ARM64 if name.startswith('adbd') else capstone.CS_ARCH_ARM,mode)
 with (E/name).open('w') as f:
  for lo,hi in ranges:
   f.write(f'\n# file offsets {lo:#x}..{hi:#x}\n')
   for i in dis.disasm(data[lo:hi],lo):f.write(f'{i.address:08x} {i.bytes.hex():12s} {i.mnemonic:9s} {i.op_str}\n')
# DTB starts after 64-byte wrapper inside lk_main_dtb container.
pos=b.find(bytes.fromhex('d00dfeed'),0x86d70)
size=struct.unpack_from('>I',b,pos+4)[0]
(E/'lk-main.dtb').write_bytes(b[pos:pos+size])
r=subprocess.run(['dtc','-I','dtb','-O','dts','-o',str(E/'lk-main.dts'),str(E/'lk-main.dtb')],capture_output=True,text=True)
(E/'dtc-stderr.txt').write_text(r.stderr)

with (E/'adbd-elf.txt').open('w') as f:
 for cmd in [['file','rootfs.original/sbin/adbd_usb'],['readelf','-l','rootfs.original/sbin/adbd_usb'],['readelf','-r','rootfs.original/sbin/adbd_usb']]:
  rr=subprocess.run(cmd,capture_output=True,text=True);f.write('$ '+' '.join(cmd)+'\n'+rr.stdout+rr.stderr)
with (E/'usb-init-disassembly.txt').open('w') as f:
 dis=capstone.Cs(capstone.CS_ARCH_ARM,capstone.CS_MODE_THUMB)
 for lo,hi in [(0x4eb9c,0x4ec60)]:
  for i in dis.disasm(b[lo:hi],lo):f.write(f'{i.address:08x} {i.bytes.hex():12s} {i.mnemonic:9s} {i.op_str}\n')
(E/'usb-structures.txt').write_text('All offsets in parent NAND LK partition. AEE VA = 0x83000000 + file_offset - 0x45c70.\n'+''.join(f'{o:#x}: {b[o:o+48].hex(" ")}\n' for o in [0x82810,0x828b0,0x82ba4,0x82bb8]))
