# video-roughcut

macOS 可用的视频自动粗剪工具，面向技术口播和屏幕录制。当前版本只做一件事：检测并删除明显静音段和长停顿，输出 `xxx_rough.mp4`，便于后续导入剪映继续精剪和生成字幕。

## 功能

- 支持输入单个 `mp4` / `mov` / `mkv`
- 支持输入目录，批量处理其中的视频文件
- 支持先合并分段录制视频，再进入粗剪
- 使用 `FFmpeg` 做静音分析，使用 `auto-editor` 做粗剪渲染
- 支持 `config.yaml`
- 支持命令行参数覆盖配置
- 支持 `dry-run`，只分析不导出视频
- 输出 `cut_log.json`
- 输出 `report.md`
- 支持 HyperFrames 包装实验模块
- 后端已预留扩展点，后续可新增纯 `FFmpeg` 实现

## 推荐工作流

### 场景 1：录完就是一整段

```bash
./run.sh /path/to/demo.mp4
```

适合一次录完、直接进入粗剪的情况。

### 场景 2：录制被拆成两段或多段

```bash
./run.sh merge /path/to/part1.mp4 /path/to/part2.mp4 --output /path/to/merged.mp4
./run.sh /path/to/merged.mp4
```

适合录制过程中暂停、崩溃、重录，最后形成多个连续片段的情况。推荐先合并成一条完整时间线，再做一次粗剪。

## 目录结构

```text
video-roughcut/
├── config.yaml
├── examples/
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
video_crf: 16
video_preset: slower
audio_bitrate: 256k
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
- `video_crf`: 视频质量参数，越低画质越高，默认 `16`
- `video_preset`: 编码预设，默认 `slower`
- `audio_bitrate`: 音频码率，默认 `256k`
- `output_suffix`: 输出文件后缀，默认 `_rough`
- `overwrite`: 是否覆盖已有输出

### 高质量粗剪模式

默认 `quality_profile: high`，更适合技术口播和屏幕录制，尤其是代码字体和小字较多的场景。

- `high`: `libx264 + aac + crf 16 + slower + 256k`
- `standard`: `libx264 + aac + crf 23 + medium + 128k`

如果你设置了 `video_codec`、`audio_codec`、`video_crf`、`video_preset`、`audio_bitrate`，这些显式参数会覆盖 `quality_profile` 的默认值。

## 命令行用法

### 命令概览

- `video-roughcut /path/to/demo.mp4`
  - 对单个视频做粗剪
- `video-roughcut /path/to/videos`
  - 批量处理目录中的视频
- `video-roughcut merge ... --output ...`
  - 先把多段录制合并成一个完整源视频
- `video-roughcut package --input ... --metadata ...`
  - 给粗剪结果加上 HyperFrames 包装

### 处理单个视频

```bash
video-roughcut /path/to/demo.mp4
```

或者直接用项目脚本：

```bash
./run.sh /path/to/demo.mp4
```

首次运行时，`run.sh` 会自动补齐虚拟环境和 Python 依赖。

### 先合并分段录制，再粗剪

如果一次录制被拆成了两段或多段，推荐先合并，再把合并结果作为一个完整输入去粗剪：

```bash
video-roughcut merge /path/to/part1.mp4 /path/to/part2.mp4 --output /path/to/merged.mp4
video-roughcut /path/to/merged.mp4
```

或者用项目脚本：

```bash
./run.sh merge /path/to/part1.mp4 /path/to/part2.mp4 --output /path/to/merged.mp4
./run.sh /path/to/merged.mp4
```

`merge` 子命令的第一版行为如下：

- 支持 2 个及以上输入文件，按命令行顺序拼接
- 优先使用 FFmpeg 的 concat demuxer 做无损拼接，不额外转码
- 如果输入文件的编码、分辨率或流布局不一致，FFmpeg 可能会失败，此时程序会直接报错
- 当前不自动降级为重新转码，也不添加转场、补黑场或音量归一化

常见建议：

- 如果这些片段本来就是同一次录制，只是中途被拆开，优先用 `merge`
- 如果这些片段是不同内容、不同机位或不同格式，不建议直接合并后粗剪
- 如果你不确定编码参数是否一致，可以先手动试一次 `merge`，失败时看报错再决定是否转码统一格式

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
  --audio-bitrate 256k \
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

`merge` 子命令只依赖 `ffmpeg`，不会额外检查 `ffprobe` 或 `auto-editor`。

## 适用边界

当前版本最适合：

- 技术口播
- 屏幕录制
- 一条长内容的自动粗剪
- 同一次录制被拆成多段后重新拼接

当前版本暂不覆盖：

- 多机位同步
- 自动转场
- 自动统一不同编码参数后再拼接
- 按时间轴做复杂素材编排

## HyperFrames 包装实验

这个实验模块用于验证 HyperFrames 是否适合给《Codex 工程实践》系列做统一包装。

### 第一版能力

- 根据 `metadata.yaml` 生成 3 秒片头标题卡
- 根据 `chapters` 生成独立章节转场卡
- 生成 3 秒片尾页
- 使用 FFmpeg 合成 `intro.mp4 + rough_cut.mp4 + outro.mp4 = final.mp4`
- 章节卡先只独立输出，不自动插入主视频

### 当前不做

- 字幕
- 自动章节识别
- 自动插入章节卡
- 复杂包装系统

### 包装风格

- 深色科技感
- 蓝紫霓虹
- 工程系统感
- 不要卡通
- 不要机器人

### 额外依赖

除了已有的 `ffmpeg` 之外，还需要 Node.js 22+，因为包装实验模块通过 `npx hyperframes` 渲染：

```bash
node --version
npx hyperframes --help
```

如果是首次运行，`npx` 可能需要先下载 HyperFrames CLI，因此会比后续调用慢一些。

### metadata 格式

第一版只支持极简结构：

```yaml
title: Codex 工程实践 01｜从粗剪到统一包装
chapters:
  - title: 为什么先做粗剪
  - title: HyperFrames 包装实验
  - title: 下一步计划
```

仓库里有一个可直接参考的示例：

[examples/package_metadata.yaml](/Users/tony/PycharmProjects/video-roughcut/examples/package_metadata.yaml)

### 运行方式

假设你已经有粗剪结果 `rough_cut.mp4`：

```bash
./run.sh package \
  --input /path/to/rough_cut.mp4 \
  --metadata /path/to/metadata.yaml
```

也可以指定包装输出目录：

```bash
./run.sh package \
  --input /path/to/rough_cut.mp4 \
  --metadata /path/to/metadata.yaml \
  --output-dir outputs/package
```

### 输出目录结构

默认会输出到：

```text
outputs/package/<metadata-slug>/
├── final.mp4
├── intro.mp4
├── outro.mp4
├── metadata.yaml
├── chapters/
│   ├── chapter_01.mp4
│   ├── chapter_02.mp4
│   └── ...
└── projects/
    ├── intro/
    ├── outro/
    └── chapter_01/
```

其中：

- `final.mp4` 是 `intro + rough_cut + outro` 的合成结果
- `chapters/` 里是独立章节卡
- `projects/` 里保留了 HyperFrames 项目源码，方便后续继续调风格和动画

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
