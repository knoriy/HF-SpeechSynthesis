import torch
import json
import pathlib

device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

from fairseq.checkpoint_utils import load_model_ensemble_and_task_from_hf_hub
from fairseq.models.text_to_speech.hub_interface import TTSHubInterface
import soundfile as sf

from utils import EnglishSpellingNormalizer
from database_updater import DatabaseUpdater

class Synthosiser():
    def __init__(self, model_name:str) -> None:
        self.models, self.cfg, self.task = load_model_ensemble_and_task_from_hf_hub(
            model_name,
            arg_overrides={"vocoder": "hifigan", "fp16": False}
        )

        self.model = self.models[0]

        TTSHubInterface.update_cfg_with_data_cfg(self.cfg, self.task.data_cfg)
        self.generator = self.task.build_generator(self.models, self.cfg)

        self.english_spelling_normalizer = EnglishSpellingNormalizer('/fsx/knoriy/code/text-to-speech/data/english.json')

    def get_audio(self, text):
        sample = TTSHubInterface.get_model_input(self.task, text)

        sample['net_input']['src_tokens'] = sample['net_input']['src_tokens'].to(device)
        sample['net_input']['src_lengths'] = sample['net_input']['src_lengths'].to(device)
        sample['speaker'] = sample['speaker'].to(device) if sample['speaker'] != None else torch.tensor([[0]]).to(device)

        wav, rate = TTSHubInterface.get_prediction(self.task, self.model.to(device), self.generator, sample)

        return text, wav, rate
    
    def save(self, text, wav, rate, save_dir):
        sf.write(save_dir, wav.detach().cpu().numpy(), rate)
        with open(save_dir.with_suffix('.json'), 'w') as f:
            json.dump({'filename': save_dir.name, 'text':[text], 'original_data':{'raw_text':text}}, f)

    
    def __call__(self, text, dest):
        dest = pathlib.Path(dest)
        if not dest.parent.is_dir():
            dest.parent.mkdir()

        text = self.english_spelling_normalizer(text)
        text, wav, rate = self.get_audio(text)
        self.save(text, wav, rate, dest)
        return text, wav, rate

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('-d', '--data_path', default='/fsx/knoriy/code/text-to-speech/data/wikipedia_en1.csv')
    parser.add_argument('-s', '--save_path', default='samples/')
    args = parser.parse_args()

    db = DatabaseUpdater('wikipedia_en.db')

    model_name_list = [
            "facebook/fastspeech2-en-200_speaker-cv4",
            "facebook/fastspeech2-en-ljspeech",
            "facebook/fastspeech2-en-200_speaker-cv4",
            "facebook/tts_transformer-en-ljspeech",
            "facebook/tts_transformer-tr-cv7",
            "facebook/tts_transformer-en-200_speaker-cv4",
            "facebook/tts_transformer-ar-cv7",
            "facebook/tts_transformer-es-css10",
            "facebook/tts_transformer-ru-cv7_css10",
            "facebook/tts_transformer-fr-cv7_css10",
            "facebook/tts_transformer-zh-cv7_css10",
            "facebook/tts_transformer-vi-cv7",
            ]

    model = Synthosiser(model_name_list[0])
    for i, row in enumerate(db.get_iteratior()):
        print(row)
        if row[2] == True:
            continue
        save_path = pathlib.Path(args.save_path).joinpath(str(row[0])+".flac")
        if model(row[1], save_path):
            db.set_complete(row[2])
            with open(save_path.replace('.flac', '.json'), 'w') as f:
                json.dump({'filename': save_path.name, 'text':[row[1]], 'original_data':{"language":"en"}}, f)

        break