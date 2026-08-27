# Contributing

[English](CONTRIBUTING.md) | [简体中文](CONTRIBUTING.zh-CN.md)

Reproducible protocol, DSP, and cryptographic research improvements are welcome.

Before submitting a contribution, please ensure that:

- conclusions are labeled as verified, strong evidence, or hypothesis;
- successful decodes include CRC24A, DJI CRC16, or another explicit consistency check;
- examples use synthetic or anonymized serial numbers, UUIDs, and locations;
- API keys, notes, and service credentials remain in a secure local environment;
- IQ and firmware samples are legally shareable;
- third-party code retains its source and license information;
- active service-side testing has explicit authorization.

Run the basic checks:

```bash
python3 -m py_compile src/*.py tests/*.py
python3 -m unittest discover -s tests -v
```
