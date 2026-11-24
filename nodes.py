from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import folder_paths

MODELS = ["kiyo-v4", "kiyo-ltx-v1"]
VR = ["off", "side-by-side", "side-by-side, fisheye mosaic"]
_PCT = re.compile(r"(detect|ltx|preparing|remaster|remux|download|mosaic):\s+([0-9.]+)%")
_STAGES = {"download": "First run: downloading the models", "preparing": "Preparing", "detect": "Finding mosaics",
           "ltx": "Restoring with LTX", "remaster": "Restoring", "remux": "Finishing", "mosaic": "Adding mosaics"}
_FILE = re.compile(r"^downloading (\S+) \(([0-9]+) MB\)")
_SHOW = re.compile(r"^(downloading|weights |done:|error:|kukkiri\.)")
_DROP_ENV = ("PYTORCH_CUDA_ALLOC_CONF", "PYTHONPATH", "PYTHONHOME")


def _kukkiri_command(given: str) -> list[str]:
    for cand in (given.strip(), os.environ.get("KUKKIRI", "").strip()):
        if cand:
            return [cand]
    if sys.platform == "win32":
        app = Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "kukkiri" / "kukkiri.cmd"
        if app.is_file():
            return [str(app)]
    found = shutil.which("kukkiri")
    if found:
        return [found]
    raise RuntimeError(
        "kukkiri was not found: install the kukkiri app (Windows) or kukkiri from source (Linux), see "
        "https://github.com/treehog2/kukkiri/releases , or give the path to its command in the node's `kukkiri_path` input "
        "(e.g. C:\\Users\\you\\AppData\\Local\\Programs\\kukkiri\\kukkiri.cmd)"
    )


def _source_file(video) -> Path:
    src = video.get_stream_source()
    start, duration = video.get_active_trim_window() if hasattr(video, "get_active_trim_window") else (0.0, 0.0)
    if isinstance(src, str) and not start and not duration:
        return Path(src)
    out_dir, name, counter, _, _ = folder_paths.get_save_image_path("kukkiri_in", folder_paths.get_temp_directory())
    path = Path(out_dir) / f"{name}_{counter:05}.mp4"
    video.save_to(str(path))
    return path


def _temp_output() -> Path:
    out_dir, name, counter, _, _ = folder_paths.get_save_image_path("kukkiri", folder_paths.get_temp_directory())
    return Path(out_dir) / f"{name}_{counter:05}.mp4"


def _run(cmd: list[str], dst: Path, unique_id):
    import comfy.utils
    from comfy_api.input_impl import VideoFromFile

    bar = comfy.utils.ProgressBar(100)
    env = {k: v for k, v in os.environ.items() if k not in _DROP_ENV}
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1,
                         errors="replace", env=env)
    tail, buf, stage, file, shown = [], "", None, "", None

    def status(text):
        nonlocal shown
        if text != shown and unique_id is not None:
            shown = text
            try:
                from server import PromptServer

                PromptServer.instance.send_progress_text(text, unique_id)
            except Exception:
                pass

    while True:
        ch = p.stdout.read(1)
        if not ch:
            break
        if ch not in "\r\n":
            buf += ch
            continue
        m = _PCT.search(buf)
        if m:
            if m.group(1) != stage:
                stage = m.group(1)
                print(f"[kukkiri] {stage}", flush=True)
            pct = int(float(m.group(2)))
            bar.update_absolute(pct, 100)
            if stage == "preparing":
                status("Loading the models…")
            else:
                status(f"{_STAGES.get(stage, stage)}{file if stage == 'download' else ''}: {pct}%")
        elif buf.strip():
            f = _FILE.search(buf.strip())
            if f:
                file = f" ({f.group(1)}, {int(f.group(2)) / 1000:.1f} GB)" if int(f.group(2)) >= 1000 else f" ({f.group(1)})"
            if _SHOW.search(buf.strip()):
                print(f"[kukkiri] {buf.strip()}", flush=True)
            tail = (tail + [buf])[-20:]
        buf = ""
    if p.wait() != 0 or not dst.is_file():
        raise RuntimeError("kukkiri failed:\n" + "\n".join(tail))
    bar.update_absolute(100, 100)
    status("Done")
    return (VideoFromFile(str(dst)),)


class KukkiriMosaicRestore:

    CATEGORY = "kukkiri"
    RETURN_TYPES = ("VIDEO",)
    RETURN_NAMES = ("video",)
    FUNCTION = "restore"

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "video": ("VIDEO", {"tooltip": "the video to restore (connect Load Video)"}),
                "model": (MODELS, {"default": "kiyo-ltx-v1",
                                   "tooltip": "kiyo-ltx-v1: best quality, needs an 8 GB GPU and a 15 GB download on first "
                                              "use; kiyo-v4: fast, any supported GPU"}),
                "sensitivity": (["normal", "high", "low"], {"default": "normal",
                                                            "tooltip": "high also finds faint or small mosaics"}),
                "vr": (VR, {"default": "off", "tooltip": "side-by-side 180° VR video"}),
                "keep_fps": ("BOOLEAN", {"default": False,
                                         "tooltip": "kiyo-ltx: keep 60 fps videos at their full frame rate (about "
                                                    "twice as slow); by default they are restored at 30 fps"}),
            },
            "optional": {
                "kukkiri_path": ("STRING", {"default": "", "tooltip": "path to the kukkiri command, if it is not found "
                                                                 "automatically"}),
            },
            "hidden": {"unique_id": "UNIQUE_ID"},
        }

    def restore(self, video, model, sensitivity, vr, keep_fps, kukkiri_path="", unique_id=None):
        src = _source_file(video)
        dst = _temp_output()
        cmd = _kukkiri_command(kukkiri_path) + ["restore", str(src), "-o", str(dst), "--model", model, "--skip-check"]
        if sensitivity != "normal":
            cmd += ["--sensitivity", sensitivity]
        if keep_fps:
            cmd.append("--keep-fps")
        if vr != "off":
            cmd += ["--vr", "sbs"] + (["--vr-lens", "fisheye"] if "fisheye" in vr else [])
        return _run(cmd, dst, unique_id)


class KukkiriMosaicAdd:

    CATEGORY = "kukkiri"
    RETURN_TYPES = ("VIDEO",)
    RETURN_NAMES = ("video",)
    FUNCTION = "add_mosaic"

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "video": ("VIDEO", {"tooltip": "the video to add mosaics to (connect Load Video)"}),
                "sensitivity": (["normal", "high", "low"], {"default": "normal",
                                                            "tooltip": "high misses fewer, low mosaics fewer false finds"}),
                "block_size": ("INT", {"default": 0, "min": 0, "max": 256,
                                       "tooltip": "mosaic block size in pixels; 0 = a 36th of the frame height"}),
            },
            "optional": {
                "kukkiri_path": ("STRING", {"default": "", "tooltip": "path to the kukkiri command, if it is not found "
                                                                 "automatically"}),
            },
            "hidden": {"unique_id": "UNIQUE_ID"},
        }

    def add_mosaic(self, video, sensitivity, block_size, kukkiri_path="", unique_id=None):
        dst = _temp_output()
        cmd = _kukkiri_command(kukkiri_path) + ["add-mosaic", str(_source_file(video)), "-o", str(dst)]
        if sensitivity != "normal":
            cmd += ["--sensitivity", sensitivity]
        if block_size:
            cmd += ["--block", str(block_size)]
        return _run(cmd, dst, unique_id)


class KukkiriRestore(KukkiriMosaicRestore):

    DEPRECATED = True


NODE_CLASS_MAPPINGS = {"KukkiriMosaicRestore": KukkiriMosaicRestore, "KukkiriMosaicAdd": KukkiriMosaicAdd,
                       "KukkiriRestore": KukkiriRestore}
NODE_DISPLAY_NAME_MAPPINGS = {"KukkiriMosaicRestore": "Kukkiri Mosaic Restore", "KukkiriMosaicAdd": "Kukkiri Mosaic Add",
                              "KukkiriRestore": "Kukkiri Mosaic Restore (old)"}
