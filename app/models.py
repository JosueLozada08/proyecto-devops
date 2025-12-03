from pydantic import BaseModel
from typing import Optional


class ItemBase(BaseModel):
    nombre: str
    descripcion: Optional[str] = None
    precio: float


class Item(ItemBase):
    id: int
