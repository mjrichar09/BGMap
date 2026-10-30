"""Generate the music bed locally with MusicGen (GPU)."""
import sys, numpy as np, soundfile as sf, torch
from transformers import AutoProcessor, MusicgenForConditionalGeneration
prompt, out, seconds = sys.argv[1], sys.argv[2], float(sys.argv[3])
name = sys.argv[4] if len(sys.argv) > 4 else "facebook/musicgen-small"
proc = AutoProcessor.from_pretrained(name)
model = MusicgenForConditionalGeneration.from_pretrained(name).to("cuda")
torch.manual_seed(7)
inputs = proc(text=[prompt], padding=True, return_tensors="pt").to("cuda")
audio = model.generate(**inputs, max_new_tokens=int(seconds * 50), do_sample=True, guidance_scale=3.5)
wav = audio[0, 0].float().cpu().numpy()
sf.write(out, wav / max(1e-6, np.abs(wav).max()) * 0.9, model.config.audio_encoder.sampling_rate)
print("wrote", out, len(wav) / model.config.audio_encoder.sampling_rate, "s")
