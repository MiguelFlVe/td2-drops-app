#!/usr/bin/env python3
"""Lists an APK's entries and decodes its binary AndroidManifest.xml (package, versionCode, versionName, SDKs).
Usage: python3 tools/apk_manifest.py drops-td2.apk
"""
import sys, zipfile, struct
apk = sys.argv[1]
z = zipfile.ZipFile(apk)
data = open(apk,'rb').read()
print('== ZIP entries ==')
for i in z.infolist():
    # local header offset -> data offset
    lh = i.header_offset
    n, e = struct.unpack('<HH', data[lh+26:lh+30])
    doff = lh + 30 + n + e
    print(f'{i.filename:55s} comp={i.compress_type} size={i.file_size:6d} dataoff={doff} align4={doff%4==0}')
print('zip test:', z.testzip())

# ---- minimal AXML parser ----
def axml(buf):
    out=[]; strings=[]; resids=[]
    pos=8
    def u16(o): return struct.unpack_from('<H',buf,o)[0]
    def u32(o): return struct.unpack_from('<I',buf,o)[0]
    ns={}
    while pos < len(buf):
        typ, hsz, csz = struct.unpack_from('<HHI', buf, pos)
        if typ == 0x0001:  # string pool
            cnt = u32(pos+8); flags = u32(pos+16); sstart = u32(pos+20)
            utf8 = flags & 0x100
            offs = [u32(pos+28+4*k) for k in range(cnt)]
            base = pos + sstart
            for o in offs:
                p = base + o
                if utf8:
                    l = buf[p]; p += 2 if l & 0x80 else 1
                    l2 = buf[p]
                    if l2 & 0x80: l2 = ((l2&0x7f)<<8)|buf[p+1]; p+=2
                    else: p+=1
                    strings.append(buf[p:p+l2].decode('utf8','replace'))
                else:
                    l = u16(p); p+=2
                    strings.append(buf[p:p+2*l].decode('utf16','replace'))
        elif typ == 0x0180:
            resids = [u32(pos+8+4*k) for k in range((csz-8)//4)]
        elif typ == 0x0102:  # start tag
            name = strings[u32(pos+20)]
            acount = u16(pos+28); astart = pos + 16 + u16(pos+24)
            attrs=[]
            for k in range(acount):
                a = astart + 20*k
                an = u32(a+4); raw = u32(a+8); dtype = buf[a+15]; dval = u32(a+16)
                aname = strings[an] if an < len(strings) else '?'
                if raw != 0xFFFFFFFF: val = strings[raw]
                elif dtype == 0x12: val = 'true' if dval else 'false'
                elif dtype == 0x10: val = str(dval)
                elif dtype == 0x01: val = '@0x%08x' % dval
                elif dtype == 0x03: val = strings[dval]
                else: val = f'(t{dtype:#x}){dval:#x}'
                attrs.append(f'{aname}={val}')
            out.append(f'<{name} ' + ' '.join(attrs) + '>')
        pos += csz
    return out
print('== AndroidManifest ==')
for line in axml(z.read('AndroidManifest.xml')): print(line)

# ---- signing block ----
eocd = data.rfind(b'PK\x05\x06')
cd_off = struct.unpack_from('<I', data, eocd+16)[0]
magic = data[cd_off-16:cd_off]
print('== Signing ==')
print('magic before CD:', magic)
size = struct.unpack_from('<Q', data, cd_off-24)[0]
blk_start = cd_off - size - 8
p = blk_start + 8
while p < cd_off - 24:
    ln, bid = struct.unpack_from('<QI', data, p)
    print(f'  block id {bid:#x} len {ln}', {0x7109871a:'v2', 0xf05368c0:'v3', 0x1b93ad61:'v3.1', 0x42726577:'padding', 0x504b4453:'dependency info'}.get(bid,''))
    p += 8 + ln
print('v1 META-INF signature files:', [n for n in z.namelist() if n.startswith('META-INF/') and n.split('.')[-1] in ('SF','RSA','DSA','EC','MF')])
