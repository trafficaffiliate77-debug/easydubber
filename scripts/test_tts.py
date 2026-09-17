from transformers import AutoTokenizer, VitsModel
import torch
import soundfile as sf

print("Loading Tagalog TTS model...")

model_name = "facebook/mms-tts-tgl"

tokenizer = AutoTokenizer.from_pretrained(model_name)
model = VitsModel.from_pretrained(model_name)

text = "Kumusta. Ito ang unang pagsubok ng EasyDubber Tagalog voice."

inputs = tokenizer(text, return_tensors="pt")

with torch.no_grad():
    output = model(**inputs).waveform

audio = output.squeeze().cpu().numpy()

sf.write(
    "tagalog_test.wav",
    audio,
    16000
)

print("Tagalog voice created!")
print("Output: tagalog_test.wav")
