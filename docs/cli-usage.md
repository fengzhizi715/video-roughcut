# video-roughcut CLI 用法

这份文档专门说明 `video-roughcut` 的命令行接口。

如果你还没有完成安装，先看主文档：[README.md](/Users/tony/PycharmProjects/video-roughcut/README.md)

## 命令概览

- `video-roughcut /path/to/demo.mp4`
  - 对单个视频做粗剪
- `video-roughcut /path/to/videos`
  - 批量处理目录中的视频
- `video-roughcut merge ... --output ...`
  - 先把多段录制合并成一个完整源视频
- `video-roughcut split ... --start ... --end ...`
  - 从视频中截取一个片段

## 处理单个视频

```bash
video-roughcut /path/to/demo.mp4
```

或者直接用项目脚本：

```bash
./run.sh /path/to/demo.mp4
```

首次运行时，`run.sh` 会自动补齐虚拟环境和 Python 依赖。

## 先合并分段录制，再粗剪

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

## 批量处理目录

```bash
video-roughcut /path/to/videos
```

```bash
./run.sh /path/to/videos
```

## dry-run

```bash
video-roughcut /path/to/demo.mp4 --dry-run
```

```bash
./run.sh /path/to/demo.mp4 --dry-run
```

## 覆盖配置参数

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

## 截取视频片段

```bash
video-roughcut split /path/to/input.mp4 --start 00:01:30 --end 00:05:00
```

```bash
./run.sh split /path/to/input.mp4 --start 30.5 --duration 60 --output clip.mp4
```

参数说明：

| 参数 | 说明 |
|---|---|
| `-s`, `--start` | 起始时间。默认 `0`。支持 `HH:MM:SS.mmm`、`MM:SS.mmm` 或秒数 |
| `-e`, `--end` | 结束时间（与 `--duration` 二选一） |
| `-d`, `--duration` | 时长（秒），与 `--end` 二选一 |
| `-o`, `--output` | 输出路径。省略则自动生成 `xxx_HH.MM.SS.mmm-HH.MM.SS.mmm.mp4` |
| `--reencode` | 重新编码以实现帧精确切割（较慢但更精确） |
| `--overwrite` | 覆盖已有输出文件 |

默认使用快速模式（`-c copy`，按关键帧切割、不重新编码）。如需帧精确的起止位置，添加 `--reencode`。

## 图形界面 (GUI)

```bash
video-roughcut-gui
```

或通过脚本启动：

```bash
./run.sh --gui
```

GUI 将三个主要功能（粗剪、合并、拆分）组织为三个标签页，所有参数可视化配置。点击“加入队列”后，任务会在“任务队列”页顺序执行；该页面集中显示当前任务日志、完成状态，并在任务完成后提供输出位置的“打开”入口。粗剪页支持保存和应用常用参数预设。

## 指定配置文件

```bash
video-roughcut --config /path/to/config.yaml
```
