import json
from itertools import islice


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
    

if __name__ == '__main__':
    norm_func = EnglishSpellingNormalizer()
    print(norm_func("This is an british spelling of normalise"))