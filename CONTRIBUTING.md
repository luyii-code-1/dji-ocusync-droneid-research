# Contributing

[English](CONTRIBUTING.md) | [简体中文](CONTRIBUTING.zh-CN.md)

Contributions to protocol analysis, receivers and reproducible tests are welcome. Before submitting:

- distinguish measurements from published references and unverified interpretations, and cite your sources;
- include CRC or other validity checks for decoded packets, without committing real session keys;
- use synthetic or properly anonymized device IDs, locations, flight tracks and capture metadata;
- do not post private chat images, hardware photos without permission, authentication material, service tokens or key files;
- share IQ/firmware material only when you have redistribution rights, and preserve third-party licenses;
- obtain authorization before testing live services.

For route 2, the public material currently describes the research direction, not a complete reproducible decryptor. State the hardware and firmware scope of any new findings rather than extrapolating to all O4 devices.

Basic checks:

```bash
python3 -m py_compile src/*.py tests/*.py
python3 -m unittest discover -s tests -v
```
