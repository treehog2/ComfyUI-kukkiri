# ComfyUI-kukkiri

ComfyUI nodes for [kukkiri](https://github.com/treehog2/kukkiri): restore mosaic-censored video, with kiyo-v4 or
**kiyo-ltx-v1** (Lightricks' LTX-2.5 fine-tuned to restore mosaics, with the whole detect / crop / restore / blend
pipeline around it).

## Install

1. **kukkiri** (a separate install: the node runs it as its own program, so its GPU stack stays out of ComfyUI's
   Python):
   - Windows: run the installer, https://huggingface.co/treehog/kukkiri/resolve/main/windows/kukkiri-setup.exe
   - Linux: from source with pip, as in [kukkiri's README](https://github.com/treehog2/kukkiri#install) (kiyo-ltx
     needs a few extra packages, listed there)
2. **This node pack:** ComfyUI Manager → *Install via Git URL* → `https://github.com/treehog2/ComfyUI-kukkiri`, or
   `git clone https://github.com/treehog2/ComfyUI-kukkiri` into `ComfyUI/custom_nodes`. Restart ComfyUI.

The node finds kukkiri by itself (the Windows app's install folder, or `kukkiri` on the PATH); otherwise set the
`KUKKIRI` environment variable, or the node's `kukkiri_path` input, to its command.

## Quick start

1. Open the template *kukkiri_restore* (Workflow, Browse Templates, ComfyUI-kukkiri): **Load Video**, **Kukkiri
   Mosaic Restore**, **Save Video**.
2. Pick or upload your video in Load Video and choose a `model`.
3. Queue. The first restore downloads the model weights; Save Video writes the result under `output/kukkiri/`.

## Inputs

| Input | |
|---|---|
| `video` | the video to restore (from Load Video); the node outputs the restored video |
| `model` | `kiyo-ltx-v1`: best quality; 8 GB GPU (slower below 32 GB), 15 GB download on first use. `kiyo-v4`: fast |
| `sensitivity` | `high` also finds faint or small mosaics, `low` makes fewer false detections |
| `vr` | side-by-side 180° VR, optionally with a fisheye-pixelated mosaic (VR with kiyo-ltx needs a 30 GB GPU) |
| `keep_fps` | kiyo-ltx restores 60 fps videos at 30 fps unless this is on (about twice as slow) |
| `kukkiri_path` | optional: the kukkiri command, if it is not found automatically |

## License

GPL-3.0, like kukkiri. The kiyo-ltx weights are licensed under the LTX-2.x Community License (see kukkiri's README).
