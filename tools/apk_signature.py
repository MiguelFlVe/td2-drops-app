#!/usr/bin/env python3
"""Checks the APK Signature Scheme v2 block of an APK and prints the signing certificate.
Usage: python3 tools/apk_signature.py drops-td2.apk   (needs: pip install cryptography)
"""
import sys, struct, hashlib
from cryptography import x509
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import hashes
d = open(sys.argv[1],'rb').read()
eocd = d.rfind(b'PK\x05\x06'); cd_off = struct.unpack_from('<I', d, eocd+16)[0]
assert d[cd_off-16:cd_off] == b'APK Sig Block 42'
size = struct.unpack_from('<Q', d, cd_off-24)[0]; bs = cd_off - size - 8
assert struct.unpack_from('<Q', d, bs)[0] == size
p = bs + 8; v2 = None
while p < cd_off - 24:
    ln, bid = struct.unpack_from('<QI', d, p)
    if bid == 0x7109871a: v2 = d[p+12:p+8+ln]
    p += 8 + ln
def lp(b, o):
    n = struct.unpack_from('<I', b, o)[0]; return b[o+4:o+4+n], o+4+n
signers, _ = lp(v2, 0); signer, _ = lp(signers, 0)
sdata, o = lp(signer, 0); sigs, o = lp(signer, o); pub, o = lp(signer, o)
digs, so = lp(sdata, 0); certs, so = lp(sdata, so)
cert_der, _ = lp(certs, 0)[0], None
cert_der = lp(certs, 0)[0]
cert = x509.load_der_x509_certificate(cert_der)
print('cert subject:', cert.subject.rfc4514_string(), '| expires', cert.not_valid_after_utc.date())
dig_entry, _ = lp(digs, 0); alg, = struct.unpack_from('<I', dig_entry, 0); exp_digest, _ = lp(dig_entry, 4)
sig_entry, _ = lp(sigs, 0); salg, = struct.unpack_from('<I', sig_entry, 0); sig, _ = lp(sig_entry, 4)
print('digest alg %#x, sig alg %#x' % (alg, salg))
cert.public_key().verify(sig, sdata, padding.PKCS1v15(), hashes.SHA256())
print('signature over signed-data: VALID')
# content digest
eocd_mod = bytearray(d[eocd:]); struct.pack_into('<I', eocd_mod, 16, bs)
sections = [d[:bs], d[cd_off:eocd], bytes(eocd_mod)]
chunks = []
for s in sections:
    for i in range(0, len(s), 1<<20):
        c = s[i:i+(1<<20)]
        chunks.append(hashlib.sha256(b'\xa5' + struct.pack('<I', len(c)) + c).digest())
top = hashlib.sha256(b'\x5a' + struct.pack('<I', len(chunks)) + b''.join(chunks)).digest()
print('content digest matches:', top == exp_digest)
