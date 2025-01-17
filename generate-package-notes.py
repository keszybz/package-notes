#!/usr/bin/env python3
# SPDX-License-Identifier: CC0-1.0

"""
$ ./generate-package-notes.py --package-type rpm --package-name systemd --package-version 248~rc2-1.fc34 --cpe 'cpe:/o:fedoraproject:fedora:33'
SECTIONS
{
    .note.package : ALIGN(4) {
        BYTE(0x04) BYTE(0x00) BYTE(0x00) BYTE(0x00) /* Length of Owner including NUL */
        BYTE(0x64) BYTE(0x00) BYTE(0x00) BYTE(0x00) /* Length of Value including NUL */
        BYTE(0x7e) BYTE(0x1a) BYTE(0xfe) BYTE(0xca) /* Note ID */
        BYTE(0x46) BYTE(0x44) BYTE(0x4f) BYTE(0x00) /* Owner: 'FDO\x00' */
        BYTE(0x7b) BYTE(0x22) BYTE(0x74) BYTE(0x79) /* Value: '{"type":"rpm","name":"systemd","version":"248~rc2-1.fc34","osCpe":"cpe:/o:fedoraproject:fedora:33"}\x00' */
        BYTE(0x70) BYTE(0x65) BYTE(0x22) BYTE(0x3a)
        BYTE(0x22) BYTE(0x72) BYTE(0x70) BYTE(0x6d)
        BYTE(0x22) BYTE(0x2c) BYTE(0x22) BYTE(0x6e)
        BYTE(0x61) BYTE(0x6d) BYTE(0x65) BYTE(0x22)
        BYTE(0x3a) BYTE(0x22) BYTE(0x73) BYTE(0x79)
        BYTE(0x73) BYTE(0x74) BYTE(0x65) BYTE(0x6d)
        BYTE(0x64) BYTE(0x22) BYTE(0x2c) BYTE(0x22)
        BYTE(0x76) BYTE(0x65) BYTE(0x72) BYTE(0x73)
        BYTE(0x69) BYTE(0x6f) BYTE(0x6e) BYTE(0x22)
        BYTE(0x3a) BYTE(0x22) BYTE(0x32) BYTE(0x34)
        BYTE(0x38) BYTE(0x7e) BYTE(0x72) BYTE(0x63)
        BYTE(0x32) BYTE(0x2d) BYTE(0x31) BYTE(0x2e)
        BYTE(0x66) BYTE(0x63) BYTE(0x33) BYTE(0x34)
        BYTE(0x22) BYTE(0x2c) BYTE(0x22) BYTE(0x6f)
        BYTE(0x73) BYTE(0x43) BYTE(0x70) BYTE(0x65)
        BYTE(0x22) BYTE(0x3a) BYTE(0x22) BYTE(0x63)
        BYTE(0x70) BYTE(0x65) BYTE(0x3a) BYTE(0x2f)
        BYTE(0x6f) BYTE(0x3a) BYTE(0x66) BYTE(0x65)
        BYTE(0x64) BYTE(0x6f) BYTE(0x72) BYTE(0x61)
        BYTE(0x70) BYTE(0x72) BYTE(0x6f) BYTE(0x6a)
        BYTE(0x65) BYTE(0x63) BYTE(0x74) BYTE(0x3a)
        BYTE(0x66) BYTE(0x65) BYTE(0x64) BYTE(0x6f)
        BYTE(0x72) BYTE(0x61) BYTE(0x3a) BYTE(0x33)
        BYTE(0x33) BYTE(0x22) BYTE(0x7d) BYTE(0x00)
    }
}
INSERT AFTER .note.gnu.build-id;
"""

import argparse
import simplejson as json
import re

def read_os_release(field):
    try:
        f = open('/etc/os-release')
    except FileNotFoundError:
        f = open('/usr/lib/os-release')

    prefix = '{}='.format(field)
    for line in f:
        if line.startswith(prefix):
            break
    else:
        return None

    value = line.rstrip()
    value = value[value.startswith(prefix) and len(prefix):]
    if value[0] in '"\'' and value[0] == value[-1]:
        value = value[1:-1]

    return value

def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument('--package-type', default='package')
    p.add_argument('--package-name')
    p.add_argument('--package-version')
    p.add_argument('--cpe')
    p.add_argument('--rpm', metavar='NEVRA')

    opts = p.parse_args()

    if opts.cpe is None:
        opts.cpe = read_os_release('CPE_NAME')

    if opts.rpm:
        split = re.match('(.*?)-([0-9].*)', opts.rpm)
        if not split:
            raise ValueError('{!r} does not seem to be a valid package name'.format(opts.rpm))
        opts.package_type = 'rpm'
        opts.package_name = split.group(1)
        opts.package_version = split.group(2)

    return opts

def encode_bytes(arr):
    return ' '.join('BYTE(0x{:02x})'.format(n) for n in arr)

def encode_bytes_lines(arr, prefix='', label='string'):
    assert len(arr) % 4 == 0
    s = bytes(arr).decode()
    yield prefix + encode_bytes(arr[:4]) + ' /* {}: {!r} */'.format(label, s)
    for offset in range(4, len(arr), 4):
        yield prefix + encode_bytes(arr[offset:offset+4])

def encode_length(s, prefix='', label='string'):
    n = (len(s) + 1) * 4 // 4
    n1 = n % 0xFF
    n2 = n // 0xFF
    assert n2 < 0xFF
    return prefix + encode_bytes([n1, n2, 0, 0]) + ' /* Length of {} including NUL */'.format(label)

def encode_note_id(arr, prefix=''):
    assert len(arr) == 4
    return prefix + encode_bytes(arr) + ' /* Note ID */'

def pad_string(s):
    return [0] * ((len(s) + 4) // 4 * 4 - len(s))

def encode_string(s, prefix='', label='string'):
    arr = list(s.encode()) + pad_string(s)
    yield from encode_bytes_lines(arr, prefix=prefix, label=label)

def encode_note(note_name, note_id, owner, value, prefix=''):
    l1 = encode_length(owner, prefix=prefix + '    ', label='Owner')
    l2 = encode_length(value, prefix=prefix + '    ', label='Value')
    l3 = encode_note_id(note_id, prefix=prefix + '    ')
    l4 = encode_string(owner, prefix=prefix + '    ', label='Owner')
    l5 = encode_string(value, prefix=prefix + '    ', label='Value')
    return [prefix + '.note.{} : ALIGN(4) {{'.format(note_name),
            l1, l2, l3, *l4, *l5,
            prefix + '}']

NOTE_ID = [0x7E, 0x1A, 0xFE, 0xCA]

def json_serialize(s):
    return json.dumps(s,
                      ensure_ascii=False,
                      separators=(',', ':'))

def generate_section(opts):
    data = {
        'type':    opts.package_type,
        'name':        opts.package_name,
        'version': opts.package_version,
    }
    if opts.cpe:
        data['osCpe'] = opts.cpe
    else:
        data['os'] = read_os_release('ID')
        data['osVersion'] = read_os_release('VERSION_ID')

    json = json_serialize(data)

    section = encode_note('package', NOTE_ID, 'FDO', json, prefix='    ')
    return ['SECTIONS', '{',
            *section,
            '}', 'INSERT AFTER .note.gnu.build-id;']

if __name__ == '__main__':
    opts = parse_args()
    lines = generate_section(opts)

    print('\n'.join(lines))
