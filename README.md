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

1. Open the template *kukkiri_v2v_restore* (Workflow, Browse Templates, ComfyUI-kukkiri): **Load Video**, **Kukkiri
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

## The kiyo-ltx LoRA without kukkiri

The template *ltx25_v2v_restore_core_nodes* runs the kiyo-ltx LoRA on Lightricks' standard LTX-2.5 model inside ComfyUI, with
core nodes only and no kukkiri install: **Load Video**, the LoRA on **LTX-2.5 22B dev**, the video as an
**LTXVAddGuide** reference, two sampling steps (**ManualSigmas** `1.0, 0.725, 0.0`), **LTXVCropGuides**, **Save Video**.
The size and length of the generation follow the loaded video (rounded to multiples of 32 and to 8k + 1 frames).

- It needs a recent ComfyUI (with LTX-2.5 support) and these models, which the template offers to download:
  `ltx-2.5-22b-dev-transformer-comfy-int8-convrot`, `gemma4-12b-with-proj-ltx-2.5-comfy-int8-convrot` and
  `ltx-2.5-video-vae-conv-bf16` from [Lightricks/LTX-2.5](https://huggingface.co/Lightricks/LTX-2.5) (accept its
  licence on Hugging Face first), and `kiyo-ltx-v1-lora.safetensors` from
  [treehog/kukkiri](https://huggingface.co/treehog/kukkiri/tree/main/ltx-v1).
- The whole video is one generation, so keep it to a few seconds; for full videos use **Kukkiri Mosaic Restore**, which
  works through them clip by clip.

## License

GPL-3.0, like kukkiri. The kiyo-ltx weights are licensed under the LTX-2.x Community License (see kukkiri's README).
