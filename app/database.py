from typing import Dict
from .models import Item

# "Base de datos" en memoria
db: Dict[int, Item] = {}
_auto_id = 0


def get_next_id() -> int:
    global _auto_id
    _auto_id += 1
    return _auto_id
