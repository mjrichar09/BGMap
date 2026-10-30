"""Generate several Stable Audio Open takes with one model load.
    python stableaudio_batch.py JOBS.json   (list of {out, seconds, seed, prompt})"""
import json, sys, torch, soundfile as sf
from diffusers import StableAudioPipeline
jobs = json.load(open(sys.argv[1], encoding="utf-8"))
neg = "low quality, distorted, vocals, singing, speech, harsh, noisy, lo-fi"
pipe = StableAudioPipeline.from_pretrained("stabilityai/stable-audio-open-1.0", torch_dtype=torch.float16, device_map="cuda")
for j in jobs:
    g = torch.Generator("cuda").manual_seed(j["seed"])
    a = pipe(j["prompt"], negative_prompt=neg, num_inference_steps=150, audio_end_in_s=j["seconds"], generator=g).audios
    sf.write(j["out"], a[0].T.float().cpu().numpy(), pipe.vae.sampling_rate)
    print("wrote", j["out"], flush=True)
