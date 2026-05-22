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
- `video-roughcut package --input ... --metadata ...`
  - 给粗剪结果加上 HyperFrames 包装

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

## 指定配置文件

```bash
video-roughcut --config /path/to/config.yaml
```
