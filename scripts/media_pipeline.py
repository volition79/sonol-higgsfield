#!/usr/bin/env python3
"""Deterministic FFmpeg/ffprobe helpers for production finishing and evidence."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


class MediaError(RuntimeError):
    pass


def executable(name: str) -> str:
    value = shutil.which(name)
    if not value:
        raise MediaError(f"required executable not found: {name}")
    return value


def checked_input(path: Path) -> Path:
    value = path.expanduser().resolve()
    if not value.is_file():
        raise MediaError(f"input file not found: {value}")
    return value


def output_path(path: Path) -> Path:
    value = path.expanduser().resolve()
    value.parent.mkdir(parents=True, exist_ok=True)
    return value


def run(command: list[str], dry_run: bool = False) -> dict[str, object]:
    if dry_run:
        return {"dry_run": True, "command": command}
    completed = subprocess.run(command, text=True, capture_output=True, timeout=1800, check=False)
    if completed.returncode:
        raise MediaError((completed.stderr or completed.stdout).strip())
    stderr_lines = [line for line in completed.stderr.splitlines() if "warning" in line.casefold()]
    return {"ok": True, "command": command, "warnings": stderr_lines[-10:]}


def atempo_chain(factor: float) -> str:
    if factor <= 0:
        raise MediaError("speed factor must be positive")
    values: list[float] = []
    remaining = factor
    while remaining > 2.0:
        values.append(2.0)
        remaining /= 2.0
    while remaining < 0.5:
        values.append(0.5)
        remaining /= 0.5
    values.append(remaining)
    return ",".join(f"atempo={value:.8f}" for value in values)


def final_mix_command(
    ffmpeg: str,
    video: Path,
    output: Path,
    *,
    dialogue: Path | None = None,
    ambience: Path | None = None,
    effects: list[Path] | None = None,
    music: Path | None = None,
) -> list[str]:
    """Build a deterministic external-stem mix that never keeps source video audio."""
    stems: list[tuple[Path, float]] = []
    if dialogue:
        stems.append((dialogue, 1.0))
    if ambience:
        stems.append((ambience, 0.35))
    stems.extend((item, 0.8) for item in (effects or []))
    if music:
        stems.append((music, 0.22 if dialogue else 0.5))
    if not stems:
        raise MediaError("final-mix requires at least one external audio stem")
    command = [ffmpeg, "-y", "-i", str(video)]
    for path, _ in stems:
        command.extend(("-i", str(path)))
    labels: list[str] = []
    filters: list[str] = []
    for index, (_, volume) in enumerate(stems, start=1):
        label = f"s{index}"
        filters.append(f"[{index}:a:0]aresample=48000,volume={volume:.3f}[{label}]")
        labels.append(f"[{label}]")
    filters.append(
        "".join(labels)
        + f"amix=inputs={len(labels)}:duration=longest:dropout_transition=0,"
        + "loudnorm=I=-16:LRA=11:TP=-1.5[mix]"
    )
    command.extend(
        (
            "-filter_complex",
            ";".join(filters),
            "-map",
            "0:v:0",
            "-map",
            "[mix]",
            "-c:v",
            "copy",
            "-c:a",
            "aac",
            "-b:a",
            "256k",
            "-shortest",
            str(output),
        )
    )
    return command


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    sub = parser.add_subparsers(dest="command", required=True)

    cmd = sub.add_parser("probe")
    cmd.add_argument("input", type=Path)

    cmd = sub.add_parser("boundary-frames")
    cmd.add_argument("input", type=Path)
    cmd.add_argument("output_dir", type=Path)

    cmd = sub.add_parser("extract-audio")
    cmd.add_argument("input", type=Path)
    cmd.add_argument("output", type=Path)

    cmd = sub.add_parser("trim")
    cmd.add_argument("input", type=Path)
    cmd.add_argument("output", type=Path)
    cmd.add_argument("--start", type=float, required=True)
    cmd.add_argument("--duration", type=float, required=True)

    cmd = sub.add_parser("concat")
    cmd.add_argument("output", type=Path)
    cmd.add_argument("inputs", nargs="+", type=Path)

    cmd = sub.add_parser("stretch")
    cmd.add_argument("input", type=Path)
    cmd.add_argument("output", type=Path)
    cmd.add_argument("--factor", type=float, required=True, help="playback speed; 1.05 is 5 percent faster")

    cmd = sub.add_parser("mux")
    cmd.add_argument("video", type=Path)
    cmd.add_argument("audio", type=Path)
    cmd.add_argument("output", type=Path)

    cmd = sub.add_parser("strip-audio")
    cmd.add_argument("input", type=Path)
    cmd.add_argument("output", type=Path)

    cmd = sub.add_parser("final-mix")
    cmd.add_argument("video", type=Path)
    cmd.add_argument("output", type=Path)
    cmd.add_argument("--dialogue", type=Path)
    cmd.add_argument("--ambience", type=Path)
    cmd.add_argument("--effect", action="append", default=[], type=Path)
    cmd.add_argument("--music", type=Path)
    args = parser.parse_args()

    try:
        ffmpeg = executable("ffmpeg")
        ffprobe = executable("ffprobe")
        if args.command == "probe":
            source = checked_input(args.input)
            command = [ffprobe, "-v", "error", "-show_streams", "-show_format", "-of", "json", str(source)]
            if args.dry_run:
                result = {"dry_run": True, "command": command}
            else:
                completed = subprocess.run(command, text=True, capture_output=True, timeout=60, check=False)
                if completed.returncode:
                    raise MediaError(completed.stderr.strip())
                result = json.loads(completed.stdout)
        elif args.command == "boundary-frames":
            source = checked_input(args.input)
            folder = args.output_dir.expanduser().resolve()
            folder.mkdir(parents=True, exist_ok=True)
            start = output_path(folder / "start.png")
            end = output_path(folder / "end.png")
            first = run([ffmpeg, "-y", "-i", str(source), "-frames:v", "1", "-update", "1", str(start)], args.dry_run)
            second = run([ffmpeg, "-y", "-sseof", "-0.05", "-i", str(source), "-frames:v", "1", "-update", "1", str(end)], args.dry_run)
            result = {"start": str(start), "end": str(end), "commands": [first, second]}
        elif args.command == "extract-audio":
            source, target = checked_input(args.input), output_path(args.output)
            result = run([ffmpeg, "-y", "-i", str(source), "-vn", "-c:a", "pcm_s24le", str(target)], args.dry_run)
        elif args.command == "trim":
            if args.start < 0 or args.duration <= 0:
                raise MediaError("start must be non-negative and duration must be positive")
            source, target = checked_input(args.input), output_path(args.output)
            result = run(
                [ffmpeg, "-y", "-ss", str(args.start), "-i", str(source), "-t", str(args.duration),
                 "-c:v", "libx264", "-crf", "16", "-preset", "slow", "-c:a", "aac", "-b:a", "192k", str(target)],
                args.dry_run,
            )
        elif args.command == "concat":
            sources = [checked_input(item) for item in args.inputs]
            target = output_path(args.output)
            with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".txt", delete=False) as handle:
                concat_path = Path(handle.name)
                for source in sources:
                    escaped = str(source).replace("'", "'\\''")
                    handle.write(f"file '{escaped}'\n")
            try:
                result = run(
                    [ffmpeg, "-y", "-f", "concat", "-safe", "0", "-i", str(concat_path),
                     "-c:v", "libx264", "-crf", "16", "-preset", "slow", "-c:a", "aac", "-b:a", "192k", str(target)],
                    args.dry_run,
                )
            finally:
                concat_path.unlink(missing_ok=True)
        elif args.command == "stretch":
            source, target = checked_input(args.input), output_path(args.output)
            audio = atempo_chain(args.factor)
            result = run(
                [ffmpeg, "-y", "-i", str(source), "-filter_complex",
                 f"[0:v]setpts=PTS/{args.factor:.8f}[v];[0:a]{audio}[a]",
                 "-map", "[v]", "-map", "[a]", "-c:v", "libx264", "-crf", "16", "-c:a", "aac", str(target)],
                args.dry_run,
            )
        elif args.command == "mux":
            video, audio, target = checked_input(args.video), checked_input(args.audio), output_path(args.output)
            result = run(
                [ffmpeg, "-y", "-i", str(video), "-i", str(audio), "-map", "0:v:0", "-map", "1:a:0",
                 "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest", str(target)],
                args.dry_run,
            )
        elif args.command == "strip-audio":
            source, target = checked_input(args.input), output_path(args.output)
            result = run(
                [ffmpeg, "-y", "-i", str(source), "-map", "0:v:0", "-c:v", "copy", "-an", str(target)],
                args.dry_run,
            )
        else:
            video, target = checked_input(args.video), output_path(args.output)
            dialogue = checked_input(args.dialogue) if args.dialogue else None
            ambience = checked_input(args.ambience) if args.ambience else None
            effects = [checked_input(item) for item in args.effect]
            music = checked_input(args.music) if args.music else None
            result = run(
                final_mix_command(
                    ffmpeg,
                    video,
                    target,
                    dialogue=dialogue,
                    ambience=ambience,
                    effects=effects,
                    music=music,
                ),
                args.dry_run,
            )
    except (MediaError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
