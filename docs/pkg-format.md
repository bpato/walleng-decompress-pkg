# .pkg File Format Specification

Wallpaper Engine `.pkg` files are package archives containing game assets. The format uses Pascal-style strings and little-endian integer encoding.

## File Structure

| Offset | Size | Field | Description |
|--------|------|-------|-------------|
| 0x00 | Variable | Root Path | Length-prefixed null-terminated UTF-8 string |
| +4 bytes | 4 | File Count | 32-bit unsigned integer (little-endian) |
| +4 bytes | Variable | File Entries | Repeated file entry structures |
| ... | Variable | File Data | Raw binary data for all files |

## Root Path

A Pascal string with a 4-byte length prefix followed by the string data:

```
[4 bytes: length][length bytes: UTF-8 string][0x00 padding]
```

Example: `b"\x05\x00\x00\x00" + b"audio\x00"` encodes the path "audio"

## File Entry Structure

Each file entry contains:

| Offset | Size | Field | Description |
|--------|------|-------|-------------|
| 0x00 | 4 bytes | Name Length | Length of filename |
| +4 | Variable | Filename | Length-prefixed null-terminated string |
| +length | 4 bytes | Offset | 32-bit unsigned integer (relative to data section) |
| +4 | 4 bytes | Length | 32-bit unsigned integer (file size in bytes) |

## Data Section

After all file entries, the file data begins. Each file's data is stored consecutively. Use the offset value from each file entry (added to the data section start) to locate the file.

## Example Hex Dump

```
00 00 00 06 00 00 00  "project"     ; Root: "project" (length=6)
0A 00 00 00              ; 10 files

; File entry 1:
04 00 00 00              ; name length = 4
6D 75 73 69 63 00        ; "music\x00"
00 10 00 00              ; offset = 4096 (0x1000)
00 20 03 00              ; length = 204800 (0x32000)
...
```

## Python Implementation

```python
def read_pascal_string(f):
    length = int.from_bytes(f.read(4), 'little')
    data = f.read(length)
    return data.decode('utf-8').rstrip('\x00')

def parse_package(path):
    with open(path, 'rb') as f:
        root = read_pascal_string(f)
        num_files = int.from_bytes(f.read(4), 'little')
        
        files = []
        for _ in range(num_files):
            name = read_pascal_string(f)
            offset = int.from_bytes(f.read(4), 'little')
            length = int.from_bytes(f.read(4), 'little')
            files.append({'name': name, 'offset': offset, 'length': length})
        
        data_offset = f.tell()
    
    return {'root': root, 'files': files, 'data_offset': data_offset}
```
