from fastapi import FastAPI, HTTPException, Header
from typing import List, Optional

from .models import Item, ItemBase
from .database import db, get_next_id

import os
from ldclient import LDClient
from ldclient.config import Config

# ---------------- LaunchDarkly ----------------
# Coloca tu SDK KEY real en una variable de entorno LAUNCHDARKLY_SDK_KEY
LD_SDK_KEY = os.getenv("LAUNCHDARKLY_SDK_KEY", "sdk-xxx-tu-llave-aqui")
ld_client = LDClient(Config(LD_SDK_KEY))

FEATURE_NEW_PRICING = "new-pricing-strategy"  # nombre del feature flag

# -------------------------------------------------

app = FastAPI(title="API CRUD DevOps con ArgoCD y LaunchDarkly")


@app.get("/items", response_model=List[Item])
def listar_items():
    return list(db.values())


@app.post("/items", response_model=Item, status_code=201)
def crear_item(item: ItemBase):
    item_id = get_next_id()
    nuevo = Item(id=item_id, **item.dict())
    db[item_id] = nuevo
    return nuevo


@app.get("/items/{item_id}", response_model=Item)
def obtener_item(item_id: int):
    if item_id not in db:
        raise HTTPException(status_code=404, detail="Item no encontrado")
    return db[item_id]


@app.put("/items/{item_id}", response_model=Item)
def actualizar_item(item_id: int, item: ItemBase):
    if item_id not in db:
        raise HTTPException(status_code=404, detail="Item no encontrado")
    actualizado = Item(id=item_id, **item.dict())
    db[item_id] = actualizado
    return actualizado


@app.delete("/items/{item_id}", status_code=204)
def eliminar_item(item_id: int):
    if item_id not in db:
        raise HTTPException(status_code=404, detail="Item no encontrado")
    del db[item_id]
    return


# ---------------- Endpoint que usa LaunchDarkly ----------------
@app.get("/items/{item_id}/precio", response_model=float)
def obtener_precio_item(
    item_id: int,
    x_user_id: Optional[str] = Header(
        default="anonimo",
        alias="X-User-Id",
    ),
):
    """
    Ejemplo de uso de feature flag para una nueva estrategia de precios.
    Si el flag new-pricing-strategy está activo para el usuario X-User-Id,
    aplicamos un pequeño descuento (p.ej. -10%).
    """
    if item_id not in db:
        raise HTTPException(status_code=404, detail="Item no encontrado")

    item = db[item_id]

    user = {"key": x_user_id}
    nuevo_precio_activo = ld_client.bool_variation(FEATURE_NEW_PRICING, user, False)

    if nuevo_precio_activo:
        # Nueva lógica de precios (ej. 10% descuento) → "canary" vía feature flag
        return round(item.precio * 0.9, 2)
    else:
        # Lógica actual
        return item.precio
