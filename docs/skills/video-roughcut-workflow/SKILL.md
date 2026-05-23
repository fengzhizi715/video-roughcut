---
name: video-roughcut-workflow
description: "Use this skill when a user wants to automatically rough-cut talking-head or screen-recording videos by removing silence and long pauses, batch rough-cut a directory, or merge split recordings before rough-cutting. This skill is CLI-first: it maps requests to the `video-roughcut` command, falls back to `./run.sh` when the command is unavailable, and should not be used for multi-camera sync, complex editing, subtitles, or packaging."
---

# video-roughcut-workflow

This skill is a CLI-first workflow for agents that need to process videos with `video-roughcut`.

The skill does not reimplement rough-cut logic. It selects and runs the appropriate `video-roughcut` command, explains what it is doing, and reports the resulting output files.

## Use This Skill When

Trigger this skill when the user wants to:

- Rough-cut a single talking-head or screen-recording video
- Remove silence, long pauses, or obvious dead air
- Batch rough-cut a directory of videos
- Merge split recordings from the same session and then rough-cut the merged result

Example requests:

- "Help me rough-cut this video"
- "Remove the pauses from this recording"
- "Rough-cut everything in this folder"
- "I recorded this in two parts, merge them and then rough-cut it"

## Do Not Use This Skill When

Do not use this skill for:

- Multi-camera sync
- Complex timelines or non-linear editing
- Mixing unrelated source clips
- Subtitles or caption generation
- Intro/outro packaging
- Chapter card insertion

If the user wants packaging or title cards, hand off to a different workflow after rough-cutting.

## Core Rules

1. Prefer the stable CLI command `video-roughcut`.
2. If `video-roughcut` is unavailable, fall back to `./run.sh`.
3. Treat split recordings from the same session as one workflow: `merge` first, then rough-cut.
4. Do not silently add transcoding, transitions, subtitles, packaging, or other editing steps.
5. If the inputs are not clearly continuous segments of the same recording, do not assume `merge` is appropriate.

## Command Selection

### Single Video

Preferred:

```bash
video-roughcut /path/to/demo.mp4
```

Fallback:

```bash
./run.sh /path/to/demo.mp4
```

### Directory Batch

Preferred:

```bash
video-roughcut /path/to/videos
```

Fallback:

```bash
./run.sh /path/to/videos
```

### Split Recording Workflow

Use this only when the inputs are continuous parts of the same recording session.

Preferred:

```bash
video-roughcut merge /path/to/part1.mp4 /path/to/part2.mp4 --output /path/to/merged.mp4
video-roughcut /path/to/merged.mp4
```

Fallback:

```bash
./run.sh merge /path/to/part1.mp4 /path/to/part2.mp4 --output /path/to/merged.mp4
./run.sh /path/to/merged.mp4
```

## Input Routing Rules

Choose the workflow in this order:

1. If the input is one video file, rough-cut it directly.
2. If the input is a directory, batch rough-cut the directory.
3. If the input is multiple files and the user wants one continuous result, use `merge` first, then rough-cut.
4. If the input files appear to be unrelated clips, do not merge them by default. Explain that this skill is for continuous recordings, not editorial assembly.

## Merge Guidance

Use `merge` when:

- The user says the recording was split into two or more parts
- The clips are successive parts of the same talk, demo, or screen recording
- The desired output is one rough-cut result

Do not use `merge` when:

- The clips come from different cameras
- The clips represent different scenes or unrelated takes
- The user is assembling a final edit rather than recovering a split recording

## Output Expectations

After a successful run, explain:

- Which command was used
- Whether `merge` was run first
- Where the output file or output directory is
- That rough-cut outputs typically include:
  - `xxx_rough.mp4`
  - `cut_log.json`
  - `report.md`

## Failure Handling

When a command fails, explain the most likely cause in plain language.

Common causes:

- Missing `ffmpeg`
- Missing `ffprobe`
- Missing `auto-editor`
- Input path does not exist
- Output path already exists and overwrite was not enabled
- `merge` failed because input files do not share compatible codecs, resolution, or stream layout

For `merge` failures, explicitly note:

- The workflow prefers lossless concat first
- It does not automatically transcode on failure
- The user may need to normalize the clips before trying again

## Agent Compatibility

This skill is designed to be portable across agents.

Assumptions:

- The agent can run local shell commands
- The agent can inspect stdout and stderr
- The agent can summarize failures clearly

Non-goals:

- Direct Python API integration
- Codex-only tools or MCP requirements
- IDE-specific behavior

## Implementation Notes

If both `video-roughcut` and `./run.sh` are available, prefer `video-roughcut` because it is easier to reuse in scripts, automations, and other agents.

If only `./run.sh` is available, it is acceptable as a bootstrap path for local development environments.
