import sqlite3
import pandas as pd
import multiprocessing
from multiprocessing import Pool
import tqdm
from itertools import repeat
from utils import EnglishSpellingNormalizer, chunk

class DatabaseUpdater:
    def __init__(self, db_path:str, table_name:str) -> None:
        self.table_name = table_name
        try:
            self.sqliteConnection = sqlite3.connect(db_path, timeout=100)
            self.cursor = self.sqliteConnection.cursor()
            print("Connected to SQLite")
            self.create(self.table_name)
        except sqlite3.Error as error:
            print("Failed to update sqlite table", error)

    def create(self, name:str="m_table", title:str="id integer PRIMARY KEY, text str, complete bool", df:pd.DataFrame=None):
        try:
            if isinstance(df, pd.DataFrame):
                df.to_sql(name, self.sqliteConnection, if_exists='replace', index = False)
            else:
                if self.cursor.execute(f''' SELECT name FROM sqlite_master WHERE type='table' AND name='{name}' ''').fetchall() == []:
                    self.cursor.execute(f'CREATE TABLE {name} ({title})')
        except sqlite3.Error as error:
            print("Failed to update sqlite table", error)

    def _insert(self, cmd:str, data:tuple):
        try:
            self.cursor.execute(cmd, data)
            self.sqliteConnection.commit()
        except sqlite3.Error as error:
            print("Failed to update sqlite table", error)
    
    def insert(self, data:tuple, name:str, batch:bool=False):
        cmd = f'''INSERT INTO {name} (text, complete) VALUES(?,?)'''
        try:
            if not batch:
                self.cursor.execute(cmd, data)
            else:
                self.cursor.executemany(cmd, data)
            self.sqliteConnection.commit()
        except sqlite3.Error as error:
            print("Failed to update sqlite table", error)

    def insert_batch(self, data:tuple, name:str):
        flattened_values = [x for tpl in data for x in tpl]
        cmd = f'''INSERT INTO {name} (text, complete) VALUES ''' + ', '.join(['(?, ?)' for _ in range(len(flattened_values)//2)])
        self._insert(cmd, flattened_values)

    def close_connection(self):
        if self.sqliteConnection:
            self.sqliteConnection.close()
            self.cursor.close()
            print("The SQLite connection is closed")
    
    def set_complete(self, id:int, name:str):
        try:
            sql_update_query = f"""Update {name} set complete = True where id = {id}"""
            self.cursor.execute(sql_update_query)
            self.sqliteConnection.commit()
            print("Record Updated successfully ")
        except sqlite3.Error as error:
            print("Failed to update sqlite table", error)
    
    def get_iteratior(self, name:str):
        return self.cursor.execute(f'SELECT * FROM {name} WHERE complete = 0')

def main(db_path, data, table_name):
    eng_nomaliser = EnglishSpellingNormalizer('./data/english.json')
    batch = []
    for i in data:
        split_text = eng_nomaliser(i['text']).strip().split('. ')
        for j in split_text:
            text = ' '.join(j.splitlines())
            text = text.split('. ')
            batch.extend([(t.strip(), False) for t in text])
    
    db = DatabaseUpdater(db_path, table_name)
    for chunked_batch in chunk(batch, 100):
        db.insert(chunked_batch, name=table_name,  batch=True)

def split_all_audio_files(db_path, data, table_name, chunksize):
    print(f'starting pool')
    with tqdm.tqdm(total=int(len(data)/chunksize)) as pbar:
        with Pool() as pool:
            for result in pool.starmap(main, zip(repeat(db_path), chunk(data, chunksize), repeat(table_name))):
                pbar.update(1)


if __name__ == '__main__':
    from datasets import load_dataset
    wikipedia_dataset = load_dataset("wikipedia", "20220301.en", split='train')
    print("wikipedia dataset loaded")
    print(f"cpu cores found: {multiprocessing.cpu_count()}")
    split_all_audio_files('wikipedia.db', wikipedia_dataset, table_name="en", chunksize=1024)


    
