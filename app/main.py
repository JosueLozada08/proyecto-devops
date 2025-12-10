from fastapi import FastAPI, HTTPException, Header
from typing import List, Optional

from .models import Item, ItemBase
from .database import db, get_next_id

import os
import ldclient
from ldclient.config import Config

# ---------------- LaunchDarkly ----------------
FEATURE_NEW_PRICING = "new-pricing-strategy"

LD_SDK_KEY = os.getenv("LAUNCHDARKLY_SDK_KEY")

if not LD_SDK_KEY:
    print(
        "[LaunchDarkly] WARNING: LAUNCHDARKLY_SDK_KEY no está definida. "
        "Los feature flags siempre devolverán el valor por defecto."
    )
    LD_SDK_KEY = "sdk-00000000-0000-0000-0000-000000000000"

# ✅ FORMA CORRECTA DE INICIALIZAR EL SDK
ldclient.set_config(Config(LD_SDK_KEY))
ld_client = ldclient.get()

if ld_client.is_initialized():
    print("[LaunchDarkly] Cliente inicializado correctamente ✅")
else:
    print("[LaunchDarkly] Cliente NO inicializado ❌")

# ---------------- FastAPI ----------------
app = FastAPI(
    title="API DevOps con LaunchDarkly",
    description=(
        "API de ejemplo con CRUD en memoria y un endpoint que usa LaunchDarkly "
        "para habilitar una nueva estrategia de precios."
    ),
    version="1.0.0",
)

@app.on_event("shutdown")
def shutdown_event():
    """
    Cierra el cliente de LaunchDarkly cuando se apaga la app.
    """
    ld_client.close()


# ---------------- Endpoints CRUD ----------------
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


@app.delete("/items/{item_id}", status_code=204)
def eliminar_item(item_id: int):
    if item_id not in db:
        raise HTTPException(status_code=404, detail="Item no encontrado")
    del db[item_id]
    return


# ---------------- Endpoint con LaunchDarkly ----------------
@app.get("/items/{item_id}/precio", response_model=float)
def obtener_precio_item(
    item_id: int,
    x_user_id: Optional[str] = Header(
        default="anonimo",
        alias="X-User-Id",
        description="Identificador del usuario para evaluar el feature flag",
    ),
):
    if item_id not in db:
        raise HTTPException(status_code=404, detail="Item no encontrado")

    item = db[item_id]
    user = {"key": x_user_id}

    try:
        nuevo_precio_activo = ld_client.bool_variation(
            FEATURE_NEW_PRICING,
            user,
            False,
        )
    except Exception as e:
        print(f"[LaunchDarkly] Error evaluando flag: {e}")
        nuevo_precio_activo = False

    if nuevo_precio_activo:
        return round(item.precio * 0.9, 2)
    else:
        return item.precio
