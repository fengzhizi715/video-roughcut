# video-roughcut

macOS 可用的视频自动粗剪工具，面向技术口播和屏幕录制。

它当前聚焦一件事：检测并删除明显静音段和长停顿，输出 `xxx_rough.mp4`，方便后续导入剪映或其他 NLE 继续精剪、配字幕和包装。

## 适合什么场景

- 技术口播
- 屏幕录制
- 一条长内容的自动粗剪
- 同一次录制被拆成多段后重新拼接

当前版本暂不覆盖：

- 多机位同步
- 自动转场
- 自动统一不同编码参数后再拼接
- 按时间轴做复杂素材编排

## 核心能力

- 支持输入单个 `mp4` / `mov` / `mkv`
- 支持输入目录，批量处理其中的视频文件
- 支持先合并分段录制视频，再进入粗剪
- 使用 `FFmpeg` 做静音分析，使用 `auto-editor` 做粗剪渲染
- 支持 `config.yaml`
- 支持命令行参数覆盖配置
- 支持 `dry-run`，只分析不导出视频
- 输出 `cut_log.json`
- 输出 `report.md`
- 后端已预留扩展点，后续可新增纯 `FFmpeg` 实现

## 快速开始

### 方式 1：直接用 `./run.sh`

如果你现在只是本地测试，这是最省事的方式。

先装系统依赖：

```bash
brew install ffmpeg auto-editor
```

然后直接运行：

```bash
./run.sh /path/to/demo.mp4
```

如果录制被拆成两段或多段：

```bash
./run.sh merge /path/to/part1.mp4 /path/to/part2.mp4 --output /path/to/merged.mp4
./run.sh /path/to/merged.mp4
```

`./run.sh` 会自动：

- 创建 `.venv`
- 安装 `requirements.txt`
- 用项目内环境启动 `video_roughcut.cli`

### 方式 2：安装成正式命令 `video-roughcut`

如果你未来准备把它做成 skill，推荐安装成正式命令行入口，而不是长期依赖 `./run.sh`。

这个项目已经在 [pyproject.toml](/Users/tony/PycharmProjects/video-roughcut/pyproject.toml:1) 里配置了命令入口：

```bash
video-roughcut = "video_roughcut.cli:main"
```

安装步骤建议这样走：

1. 安装系统依赖

```bash
brew install ffmpeg auto-editor
```

2. 创建虚拟环境

```bash
python3 -m venv .venv
source .venv/bin/activate
```

3. 安装 Python 依赖

```bash
pip install -r requirements.txt
```

4. 把项目安装成命令

```bash
pip install -e .
```

通常直接用这条命令就够了，也最不容易踩到构建环境缺失的问题。

如果你非常确定当前虚拟环境里已经装好了构建依赖，例如 `setuptools>=68`，才考虑使用：

```bash
pip install --no-build-isolation -e .
```

安装完成后验证：

```bash
video-roughcut --help
```

之后就可以直接这样调用：

```bash
video-roughcut /path/to/demo.mp4
video-roughcut merge /path/to/part1.mp4 /path/to/part2.mp4 --output /path/to/merged.mp4
```

### `./run.sh` 和 `video-roughcut` 怎么选

- `./run.sh`
  - 适合本地开发和临时测试
  - 会自动补环境，最省事
- `video-roughcut`
  - 适合稳定调用、脚本集成、后续 skill 封装
  - 语义更清晰，也更容易迁移到别的环境

如果你的目标是“未来让 skill 直接调用这个工具”，推荐优先把调用面固定成：

```bash
video-roughcut <args>
```

而不是：

```bash
./run.sh <args>
```

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

## 安装说明

### 系统依赖

推荐使用 Homebrew 安装：

```bash
brew install ffmpeg auto-editor
```

安装完成后确认：

```bash
ffmpeg -version
ffprobe -version
auto-editor --help
```

### Python 环境

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 安装成命令

```bash
pip install -e .
```

这里的 `-e` 表示 editable install。它的好处是：

- 会生成 `video-roughcut` 这个命令
- 你改了 `src/` 里的代码后，不需要每次重新打包安装
- 很适合开发阶段和 skill 封装阶段

默认推荐这条命令，因为 `pip` 会更稳地处理构建环境。

如果你想使用 `--no-build-isolation`，先确保当前虚拟环境里已经安装了构建依赖：

```bash
pip install "setuptools>=68" wheel
pip install --no-build-isolation -e .
```

否则可能会遇到类似 `Cannot import 'setuptools.build_meta'` 的报错。

### 只想本地跑源码，不安装命令

如果你暂时不想安装命令，也可以这样运行：

```bash
PYTHONPATH=src python -m video_roughcut.cli --help
```

## 命令行用法

完整的命令行说明已拆分到：

[docs/cli-usage.md](/Users/tony/PycharmProjects/video-roughcut/docs/cli-usage.md)

如果你只想先记住最常用的几个入口：

- `video-roughcut /path/to/demo.mp4`
- `video-roughcut /path/to/videos`
- `video-roughcut merge ... --output ...`

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

## 默认行为

参数优先级：**命令行参数 > `config.yaml` > 内置默认值**。

### 不传任何参数

直接运行 `video-roughcut`（不传输入路径），会立刻报错：

```text
Error: Provide an input file/directory via --input or config.yaml input_dir.
```

（注：错误消息里的 `--input` 是历史文案，实际 CLI 的输入是位置参数 `input`，直接接路径即可，不需要 `--input` 前缀。）

你至少要通过以下两种方式之一告诉它要处理什么：

- 命令行参数：`video-roughcut /path/to/demo.mp4`
- 配置文件：在 `config.yaml` 里设置 `input_dir: /path/to/videos`

如果命令行和 `config.yaml` 都没给输入，工具不会尝试"用当前目录"或"用上一次跑过的"那种隐式行为。

### 没有 `config.yaml` 时的行为

`config.yaml` 不是必须的。`build_config` 会先尝试加载它：

- 文件存在 → 读取里面的值
- 文件不存在 → 静默忽略，不报错，继续用内置默认值
- 文件存在但解析失败（YAML 语法错、不是顶层 mapping）→ 抛 `ConfigError` 并退出

没有 `config.yaml` 时，实际生效的默认值是：

| 字段 | 默认值 | 说明 |
|------|--------|------|
| `input_dir` | `null` | 必须显式提供，否则报错 |
| `output_dir` | `outputs` | 相对当前工作目录 |
| `silence_threshold` | `-35` | dB |
| `min_silence_duration` | `0.6` | 秒 |
| `padding_before` | `0.25` | 秒 |
| `padding_after` | `0.25` | 秒 |
| `min_clip_duration` | `0.5` | 秒 |
| `quality_profile` | `high` |  |
| `video_codec` | `libx264` | high 预设 |
| `audio_codec` | `aac` | high 预设 |
| `video_crf` | `18` | high 预设（与 `config.yaml` 里的 16 不同） |
| `video_preset` | `slow` | high 预设（与 `config.yaml` 里的 slower 不同） |
| `audio_bitrate` | `192k` | high 预设（与 `config.yaml` 里的 256k 不同） |
| `output_suffix` | `_rough` |  |
| `overwrite` | `false` |  |

也就是说，`config.yaml` 里显式写出的 `video_crf: 16`、`video_preset: slower`、`audio_bitrate: 256k` 会**覆盖** `high` 预设的默认值；删掉 `config.yaml` 后，会回退到 `high` 预设自带的 18 / slow / 192k。如果你想在没有 `config.yaml` 的情况下也拿到 README 文档承诺的最高画质，可以通过命令行显式传：

```bash
video-roughcut /path/to/demo.mp4 \
  --video-crf 16 \
  --video-preset slower \
  --audio-bitrate 256k
```

### 自定义配置文件路径

默认找 `./config.yaml`。可以用 `--config` 指定别的位置：

```bash
video-roughcut --config /path/to/my-config.yaml /path/to/demo.mp4
```

如果指定的文件不存在，会抛 `ConfigError: Config file not found: ...`，**这种情况和"不传 `--config`、根目录没 `config.yaml`"的静默忽略行为不同**。

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
