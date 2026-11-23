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
_PCT = re.compile(r"remaster:\s+([0-9.]+)%")
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
        "kukkiri was not found: install the kukkiri app (Windows) or kukkiri from source (Linux), or give the path to its "
        "command in the node's `kukkiri` input (e.g. C:\\Users\\you\\AppData\\Local\\Programs\\kukkiri\\kukkiri.cmd)"
    )


class KukkiriRestore:

    CATEGORY = "kukkiri"
    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("video_path",)
    FUNCTION = "restore"
    OUTPUT_NODE = True

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "video_path": ("STRING", {"default": "", "tooltip": "the video file to restore"}),
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
                "kukkiri": ("STRING", {"default": "", "tooltip": "path to the kukkiri command, if it is not found "
                                                                 "automatically"}),
                "filename_prefix": ("STRING", {"default": "kukkiri/restored"}),
            },
        }

    def restore(self, video_path, model, sensitivity, vr, keep_fps, kukkiri="", filename_prefix="kukkiri/restored"):
        import comfy.utils

        src = Path(video_path.strip().strip('"'))
        if not src.is_file():
            raise FileNotFoundError(f"no such video: {src}")
        out_dir, name, counter, _, _ = folder_paths.get_save_image_path(filename_prefix, folder_paths.get_output_directory())
        dst = Path(out_dir) / f"{name}_{counter:05}.mp4"
        cmd = _kukkiri_command(kukkiri) + ["restore", str(src), "-o", str(dst), "--model", model, "--skip-check"]
        if sensitivity != "normal":
            cmd += ["--sensitivity", sensitivity]
        if keep_fps:
            cmd.append("--keep-fps")
        if vr != "off":
            cmd += ["--vr", "sbs"] + (["--vr-lens", "fisheye"] if "fisheye" in vr else [])
        bar = comfy.utils.ProgressBar(100)
        env = {k: v for k, v in os.environ.items() if k not in _DROP_ENV}
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1,
                             errors="replace", env=env)
        tail, buf = [], ""
        while True:
            ch = p.stdout.read(1)
            if not ch:
                break
            if ch not in "\r\n":
                buf += ch
                continue
            m = _PCT.search(buf)
            if m:
                bar.update_absolute(int(float(m.group(1))), 100)
            elif buf.strip():
                if _SHOW.search(buf.strip()):
                    print(f"[kukkiri] {buf.strip()}", flush=True)
                tail = (tail + [buf])[-20:]
            buf = ""
        if p.wait() != 0 or not dst.is_file():
            raise RuntimeError("kukkiri failed:\n" + "\n".join(tail))
        bar.update_absolute(100, 100)
        return {"ui": {"text": [str(dst)]}, "result": (str(dst),)}


NODE_CLASS_MAPPINGS = {"KukkiriRestore": KukkiriRestore}
NODE_DISPLAY_NAME_MAPPINGS = {"KukkiriRestore": "kukkiri Restore"}
