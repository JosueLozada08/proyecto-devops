from fastapi import FastAPI, HTTPException, Header
from typing import List, Optional

from .models import Item, ItemBase
from .database import db, get_next_id

import os
from ldclient import LDClient
from ldclient.config import Config

FEATURE_NEW_PRICING = "new-pricing-strategy"

LD_SDK_KEY = os.getenv("LAUNCHDARKLY_SDK_KEY")

if not LD_SDK_KEY:
    print(
        "[LaunchDarkly] WARNING: LAUNCHDARKLY_SDK_KEY no está definida. "
        "Los feature flags siempre devolverán el valor por defecto."
    )
    LD_SDK_KEY = "sdk-00000000-0000-0000-0000-000000000000"

ld_client = LDClient(Config(LD_SDK_KEY))


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
    """
    Lista todos los ítems en la 'base de datos' en memoria.
    """
    return list(db.values())


@app.post("/items", response_model=Item, status_code=201)
def crear_item(item: ItemBase):
    """
    Crea un nuevo ítem con ID autogenerado.
    """
    item_id = get_next_id()
    nuevo = Item(id=item_id, **item.dict())
    db[item_id] = nuevo
    return nuevo


@app.get("/items/{item_id}", response_model=Item)
def obtener_item(item_id: int):
    """
    Obtiene un ítem por su ID.
    """
    if item_id not in db:
        raise HTTPException(status_code=404, detail="Item no encontrado")
    return db[item_id]


@app.delete("/items/{item_id}", status_code=204)
def eliminar_item(item_id: int):
    """
    Elimina un ítem por su ID.
    """
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
    """
    Devuelve el precio del item aplicando o no la nueva estrategia de precios
    según el feature flag 'new-pricing-strategy' en LaunchDarkly.

    - Si el flag está OFF o hay cualquier problema con LaunchDarkly → precio normal.
    - Si el flag está ON para el usuario → aplica 10 % de descuento.
    """
    if item_id not in db:
        raise HTTPException(status_code=404, detail="Item no encontrado")

    item = db[item_id]
    user = {"key": x_user_id}

    # Valor por defecto: no aplicar la nueva estrategia
    nuevo_precio_activo = False

    try:
        # Intentamos evaluar el flag en LaunchDarkly
        nuevo_precio_activo = ld_client.bool_variation(
            FEATURE_NEW_PRICING,
            user,
            False,  # fallback si LaunchDarkly no responde
        )
    except Exception as e:
        # No rompemos la API por culpa de LaunchDarkly
        print(f"[LaunchDarkly] Error evaluando flag: {e}")
        nuevo_precio_activo = False

    if nuevo_precio_activo:
        # Nueva lógica de precios (10% descuento)
        return round(item.precio * 0.9, 2)
    else:
        # Lógica actual
        return item.precio
