from replit import db
from typing import Union, Optional, List, Tuple, Dict, Any
import json
import os
import re
from variable import REPLIT
from utils import get_bit_positions

if not REPLIT:
    if not os.path.isdir('data'):
        os.mkdir('data')

class DataManager:
    
    def __init__(self, type: str):
        self.type = type
        if not REPLIT:
            if not os.path.isfile(f'data/{self.type}.json'):
                with open(f'data/{self.type}.json', 'w', encoding='utf-8') as f:
                    f.write('{}')
            self.__data: Dict[str, Any] = json.load(open(f'data/{self.type}.json', 'r', encoding='utf-8'))

    """tags運作
    
    tags: Optional[list[str|int] | Tuple[str|int] | str | int]
    tags = [tag1, tag2, tag3]
    鍵值 = tag1_tag2_tag3_key
    """
    
    def get_val(self, key: str, tags: Optional[Union[List[str], Tuple[str], str, int]] = None) -> Dict[str, Any]:
        """取內容值
        
        """
        if not isinstance(key, str):
            key = str(key)
        if tags is not None and not isinstance(tags, list) and not isinstance(tags, tuple):
            tags = [str(tags)]

        k: str
        if REPLIT:
            k = '_'.join([self.type] + [ str(tag) for tag in tags or [] ] + [key])
            return json.loads(db[k]) if k in db else None
        else:
            k = '_'.join([ str(tag) for tag in tags or [] ] + [key])
            return self.__data.get(k, None)

    def set_val(self, key: str, data: Dict[str, Any], tags: Optional[Union[List[str], Tuple[str], str, int]] = None) -> None:
        """設定內容值
        
        """
        if not isinstance(key, str):
            key = str(key)
        if not isinstance(data, dict):
            raise ValueError
        if tags is not None and not isinstance(tags, list) and not isinstance(tags, tuple):
            tags = [str(tags)]
        
        k: str
        if REPLIT:
            k = '_'.join([self.type] + [ str(tag) for tag in tags or [] ] + [key])
            db[k] = json.dumps(data, separators=(',', ':'))
        else:
            k = '_'.join([ str(tag) for tag in tags or [] ] + [key])
            self.__data[k] = data
            json.dump(self.__data, open(f'data/{self.type}.json', 'w', encoding='utf-8'), indent=4)

    def del_val(self, key: str, tags: Optional[Union[List[str], Tuple[str], str, int]] = None) -> None:
        """刪除鍵值
        
        """
        if not isinstance(key, str):
            key = str(key)
        if tags is not None and not isinstance(tags, list) and not isinstance(tags, tuple):
            tags = [str(tags)]
        k: str
        if REPLIT:
            k = '_'.join([self.type] + [ str(tag) for tag in tags or [] ] + [key])
            del db[k]
        else:
            k = '_'.join([ str(tag) for tag in tags or [] ] + [key])
            del self.__data[k]
            json.dump(self.__data, open(f'data/{self.type}.json', 'w', encoding='utf-8'), indent=4)
        
    def keys(self, tags: Optional[Union[List[str], Tuple[str], str, int]] = None) -> List[Tuple[List[str], str]]:
        """取所有鍵值
        
        如有輸入tags
        回傳所有符合tags的鍵值:
        [
            ( [], key ),
            ( [], key ),
            ...
        ]
        
        如沒有輸入tags
        回傳所有鍵值:
        [
            ( tags, key ),
            ( tags, key ),
            ...
        ]
        """
        if tags is not None:
            if not isinstance(tags, list) and not isinstance(tags, tuple):
                tags = [str(tags)]

        tag_str: str = '_'.join([ str(tag) for tag in tags or [] ] + [''])
        
        if REPLIT:
            return [ 
                (tags_match.group(1).split('_') if tags_match else [], title)
                for tags_match, title in [
                    (re.search(f'{self.type}_(.*)_.*', key), re.sub(f'{self.type}_(?:.*_)*', '', key))
                    for key in db.keys()
                    if key.startswith(f'{self.type}_{tag_str}')
                ]
            ]
        else:
            return [ 
                (tags_match.group(1).split('_') if tags_match else [], title)
                for tags_match, title in [
                    (re.search(f'(.*)_.*', key), re.sub(f'(?:.*_)*', '', key))
                    for key in self.__data.keys()
                    if key.startswith(tag_str)
                ]
            ]

"""
Response
: Dict[str, Any]

ex:

{
    'phrases': [
        'Hello',
        'Hi',
        ...
    ],
    'reacts': {
        '1': [ 'World!' ]
        '3': [ '{{}} * 2' ]
    },
}
"""