"""Generate music sections with Stable Audio Open (44.1 kHz stereo) on the GPU.
    python stableaudio.py OUT.wav SECONDS SEED "prompt" ["negative prompt"]"""
import sys, torch, soundfile as sf
from diffusers import StableAudioPipeline
out, seconds, seed, prompt = sys.argv[1], float(sys.argv[2]), int(sys.argv[3]), sys.argv[4]
neg = sys.argv[5] if len(sys.argv) > 5 else "low quality, distorted, vocals, singing, speech, harsh, noisy, lo-fi"
pipe = StableAudioPipeline.from_pretrained("stabilityai/stable-audio-open-1.0", torch_dtype=torch.float16).to("cuda")
g = torch.Generator("cuda").manual_seed(seed)
audio = pipe(prompt, negative_prompt=neg, num_inference_steps=150, audio_end_in_s=seconds, num_waveforms_per_prompt=1, generator=g).audios
sf.write(out, audio[0].T.float().cpu().numpy(), pipe.vae.sampling_rate)
print("wrote", out)
