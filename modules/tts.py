#!/bin/env python3

from io import BytesIO

import torch
import torchaudio
from transliterate import translit, exceptions


# Use this function to transliterate the input text to Russian, if possible
def transcript(text: str):
    try:
        text = translit(text, "ru")
    except exceptions.LanguageDetectionError:
        return "Ошибка в синтезировании текста на пятнадцатой строке модуля ттс."

    return text

def load_model():
    device = torch.device("cpu")

    model = torch.hub.load(
        repo_or_dir="snakers4/silero-models:master",
        # repo_or_dir="/home/fleef/.cache/torch/hub/snakers4_silero-models_master",
        model='silero_tts',
        language='ru',
        speaker='ru_v3',
        verbose=False
    )[0]
    model.to(device)

    return model


def synthesize_audio(model: torch.nn.Module, text: str, speaker: str = "baya"):
    text = transcript(text)
    audio = model.apply_tts(
        text=text,
        speaker=speaker,
        sample_rate=48000
    )

    torchaudio.save(buffer := BytesIO(), audio.unsqueeze(0), 48000, format='wav')
    buffer.name = "test.ogg"
    return buffer

# def main():
#     text = "Привет"
#     model = load_model()
#     buffer = synthesize_audio(model, text, "baya")
#     print(buffer)
#
# if __name__ == "__main__":
#     main()
