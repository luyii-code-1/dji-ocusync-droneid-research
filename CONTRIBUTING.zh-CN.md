# Contributing

[English](CONTRIBUTING.md) | [简体中文](CONTRIBUTING.zh-CN.md)

欢迎提交可复现的协议、DSP 和密码学研究改进。

提交前请确认：

- 结论标注为“已验证”“强证据”或“假设”；
- 解码成功提供 CRC24A、DJI CRC16 或其他明确一致性证据；
- 样本使用合成或脱敏的 SN、UUID 与位置数据，API Key、note 和服务凭据保存在本地安全环境；
- IQ/固件样本具备合法分享权限；
- 第三方代码保留来源和许可证，不直接复制许可证不兼容内容；
- 主动服务端测试已获得明确授权。

运行基础检查：

```bash
python3 -m py_compile src/*.py tests/*.py
python3 -m unittest discover -s tests -v
```
