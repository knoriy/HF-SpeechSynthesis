import json
import os
import random
import tarfile

from itertools import islice
from glob import glob
from tqdm import tqdm

class EnglishSpellingNormalizer:
    """
    Applies British-American spelling mappings as listed in [1].
    [1] https://www.tysto.com/uk-us-spelling-list.html
    """
    def __init__(self, data_dir:str):
        self.mapping = json.load(open(data_dir))

    def __call__(self, s: str):
        return " ".join(self.mapping.get(word, word) for word in s.split())

def chunk(arr_range, arr_size):
    arr_range = iter(arr_range)
    return iter(lambda: tuple(islice(arr_range, arr_size)), ())

def tardir(
    file_path, tar_name, n_entry_each, audio_ext=".flac", text_ext=".json", shuffle=True, start_idx=0, delete_file=False
):
    """
    This function create the tars that includes the audio and text files in the same folder
    @param file_path      | string  | the path where audio and text files located
    @param tar_name       | string  | the tar name
    @param n_entry_each   | int     | how many pairs of (audio, text) will be in a tar
    @param audio_ext      | string  | the extension of the audio
    @param text_ext       | string  | the extension of the text
    @param shuffle        | boolean | True to shuffle the file sequence before packing up
    @param start_idx      | int     | the start index of the tar
    @param delete_file    | boolean | True to delete the audio and text files after packing up
    """
    filelist = glob(file_path+'/*'+audio_ext)

    if shuffle:
        random.shuffle(filelist)
    count = 0
    n_split = len(filelist) // n_entry_each
    if n_split * n_entry_each != len(filelist):
        n_split += 1
    size_dict = {
        os.path.join(os.path.basename(tar_name), str(i) + ".tar"): n_entry_each
        for i in range(n_split)
    }
    if n_split * n_entry_each != len(filelist):
        size_dict[os.path.join(os.path.basename(tar_name), str(n_split - 1) + ".tar")] = (
            len(filelist) - (n_split - 1) * n_entry_each
        )
    for i in tqdm(range(start_idx, n_split + start_idx), desc='Creating .tar file:'):
        with tarfile.open(os.path.join(tar_name, str(i) + ".tar"), "w") as tar_handle:
            for j in range(count, len(filelist)):
                audio = filelist[j]
                basename = ".".join(audio.split(".")[:-1])
                text_file_path = os.path.join(file_path, basename + text_ext)
                audio_file_path = os.path.join(file_path, audio)
                tar_handle.add(audio_file_path)
                tar_handle.add(text_file_path)
                if delete_file:
                    os.remove(audio_file_path)
                    os.remove(text_file_path)
                if (j + 1) % n_entry_each == 0:
                    count = j + 1
                    break
        tar_handle.close()
    # Serializing json
    json_object = json.dumps(size_dict, indent=4)
    # Writing to sample.json
    with open(os.path.join(os.path.dirname(tar_name), "sizes.json"), "w") as outfile:
        outfile.write(json_object)
    return size_dict



if __name__ == '__main__':
    norm_func = EnglishSpellingNormalizer()
    print(norm_func("This is an british spelling of normalise"))