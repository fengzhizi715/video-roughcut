# video-roughcut

macOS 可用的视频自动粗剪工具，面向技术口播和屏幕录制。当前版本只做一件事：检测并删除明显静音段和长停顿，输出 `xxx_rough.mp4`，便于后续导入剪映继续精剪和生成字幕。

## 功能

- 支持输入单个 `mp4` / `mov` / `mkv`
- 支持输入目录，批量处理其中的视频文件
- 使用 `FFmpeg` 做静音分析，使用 `auto-editor` 做粗剪渲染
- 支持 `config.yaml`
- 支持命令行参数覆盖配置
- 支持 `dry-run`，只分析不导出视频
- 输出 `cut_log.json`
- 输出 `report.md`
- 后端已预留扩展点，后续可新增纯 `FFmpeg` 实现

## 目录结构

```text
video-roughcut/
├── config.yaml
├── pyproject.toml
├── requirements.txt
├── src/video_roughcut/
│   ├── backends/
│   ├── cli.py
│   ├── config.py
│   ├── discovery.py
│   ├── models.py
│   ├── reporting.py
│   ├── runner.py
│   └── tools.py
└── tests/
```

## 依赖安装

### 1. 安装 FFmpeg

推荐使用 Homebrew：

```bash
brew install ffmpeg
```

安装完成后确认：

```bash
ffmpeg -version
ffprobe -version
```

### 2. 最省事的方式

如果你只想直接开始用，先装好 `FFmpeg` 和 `auto-editor`，然后直接运行：

```bash
brew install ffmpeg auto-editor
```

再执行：

```bash
./run.sh --help
```

`run.sh` 会自动完成这些事情：

- 创建 `.venv`
- 安装 `requirements.txt`

之后就一直用 `./run.sh ...` 即可。

### 3. 手动创建虚拟环境

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 4. 手动安装 Python 依赖

```bash
pip install -r requirements.txt
```

如果你希望额外获得 `video-roughcut` 这个命令行入口，而不是通过 `./run.sh` 或 `PYTHONPATH=src` 运行，再执行：

```bash
pip install --no-build-isolation -e .
```

如果你只想本地运行，也可以不执行 `pip install -e .`，改用：

```bash
PYTHONPATH=src python -m video_roughcut.cli --help
```

### 5. 手动初始化 auto-editor

`auto-editor` 不再通过 `pip` 安装。当前项目把它当作系统工具依赖，推荐直接使用 Homebrew 安装：

```bash
brew install auto-editor
```

安装完成后确认：

```bash
auto-editor --help
```

## 配置文件

默认读取根目录下的 `config.yaml`：

```yaml
input_dir: null
output_dir: outputs
silence_threshold: -35
min_silence_duration: 0.6
padding_before: 0.25
padding_after: 0.25
min_clip_duration: 0.5
quality_profile: high
video_codec: libx264
audio_codec: aac
video_crf: 18
video_preset: slow
audio_bitrate: 192k
output_suffix: "_rough"
overwrite: false
```

### 参数说明

- `input_dir`: 输入文件或目录路径
- `output_dir`: 输出目录
- `silence_threshold`: 静音阈值，单位 dB，中文技术口播建议 `-35`
- `min_silence_duration`: 被识别为可删停顿的最短时长，单位秒
- `padding_before`: 删除静音前保留的时间，单位秒
- `padding_after`: 删除静音后保留的时间，单位秒
- `min_clip_duration`: 最小保留片段时长，避免切得过碎
- `quality_profile`: 导出质量预设，支持 `standard` 和 `high`
- `video_codec`: 视频编码器，默认 `libx264`
- `audio_codec`: 音频编码器，默认 `aac`
- `video_crf`: 视频质量参数，越低画质越高，默认 `18`
- `video_preset`: 编码预设，默认 `slow`
- `audio_bitrate`: 音频码率，默认 `192k`
- `output_suffix`: 输出文件后缀，默认 `_rough`
- `overwrite`: 是否覆盖已有输出

### 高质量粗剪模式

默认 `quality_profile: high`，更适合技术口播和屏幕录制，尤其是代码字体和小字较多的场景。

- `high`: `libx264 + aac + crf 18 + slow + 192k`
- `standard`: `libx264 + aac + crf 23 + medium + 128k`

如果你设置了 `video_codec`、`audio_codec`、`video_crf`、`video_preset`、`audio_bitrate`，这些显式参数会覆盖 `quality_profile` 的默认值。

## 命令行用法

### 处理单个视频

```bash
video-roughcut /path/to/demo.mp4
```

或者直接用项目脚本：

```bash
./run.sh /path/to/demo.mp4
```

首次运行时，`run.sh` 会自动补齐虚拟环境和 Python 依赖。

### 批量处理目录

```bash
video-roughcut /path/to/videos
```

```bash
./run.sh /path/to/videos
```

### dry-run

```bash
video-roughcut /path/to/demo.mp4 --dry-run
```

```bash
./run.sh /path/to/demo.mp4 --dry-run
```

### 覆盖配置参数

```bash
video-roughcut /path/to/demo.mp4 \
  --output-dir outputs \
  --silence-threshold -32 \
  --min-silence-duration 0.8 \
  --padding-before 0.2 \
  --padding-after 0.2 \
  --min-clip-duration 0.6 \
  --quality-profile high \
  --video-crf 16 \
  --video-preset slower \
  --overwrite
```

### 指定配置文件

```bash
video-roughcut --config /path/to/config.yaml
```

## 输出结果

每次运行会在输出目录中生成：

- `xxx_rough.mp4`
- `cut_log.json`
- `report.md`

### `cut_log.json` 内容

- 输入文件
- 输出文件
- 使用参数
- 删除片段
- 删除总时长
- 粗剪前后时长

### `report.md` 内容

- 本次处理文件数
- 是否 dry-run
- 总删除时长
- 每个文件的粗剪摘要

## 依赖缺失时的行为

程序启动时会检查：

- `ffmpeg`
- `ffprobe`
- `auto-editor`

如果缺少任一依赖，会给出清晰报错，不会直接失败退出到难以理解的堆栈。

## 当前实现说明

- 静音分析基于 `FFmpeg silencedetect`
- 视频渲染调用 `auto-editor`
- 日志中的删除片段来自分析层标准化结果，用于粗剪摘要与人工复核

这意味着日志会尽量贴近实际删除行为，但不保证和 `auto-editor` 的内部切点逐帧完全一致。当前版本的重点是稳定粗剪工作流，而不是帧级语义一致性。

## 开发与测试

运行测试：

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

## 后续扩展建议

- 新增 `backends/ffmpeg.py`
- 把“分析”和“渲染”进一步拆成独立策略
- 增加导出 EDL / XML
- 增加 GUI 包装层
