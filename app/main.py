from fastapi import FastAPI, HTTPException, Header
from typing import List, Optional

from .models import Item, ItemBase
from .database import db, get_next_id

import os
from ldclient import LDClient
from ldclient.config import Config

# ---------------- LaunchDarkly ----------------
# La SDK key real se inyecta por la variable de entorno LAUNCHDARKLY_SDK_KEY
# En Kubernetes viene desde el Secret launchdarkly-secret (ver k8s/deployment.yaml)
LD_SDK_KEY = os.getenv("LAUNCHDARKLY_SDK_KEY", "sdk-xxx-tu-llave-aqui")
ld_client = LDClient(Config(LD_SDK_KEY))

# Nombre del feature flag configurado en LaunchDarkly
FEATURE_NEW_PRICING = "new-pricing-strategy"

# ---------------- FastAPI ----------------
app = FastAPI(title="API DevOps con LaunchDarkly y Argo CD")


@app.get("/")
def read_root():
    return {"message": "API DevOps funcionando"}


# ---------- CRUD de Items (en memoria) ----------

@app.get("/items", response_model=List[Item])
def listar_items():
    """Lista todos los items almacenados en memoria."""
    return list(db.values())


@app.post("/items", response_model=Item, status_code=201)
def crear_item(item_in: ItemBase):
    """Crea un nuevo item en la 'base de datos' en memoria."""
    new_id = get_next_id()
    item = Item(id=new_id, **item_in.dict())
    db[new_id] = item
    return item


@app.get("/items/{item_id}", response_model=Item)
def obtener_item(item_id: int):
    """Obtiene un item por ID."""
    if item_id not in db:
        raise HTTPException(status_code=404, detail="Item no encontrado")
    return db[item_id]


@app.put("/items/{item_id}", response_model=Item)
def actualizar_item(item_id: int, item_in: ItemBase):
    """Actualiza completamente un item existente."""
    if item_id not in db:
        raise HTTPException(status_code=404, detail="Item no encontrado")

    item = Item(id=item_id, **item_in.dict())
    db[item_id] = item
    return item


@app.delete("/items/{item_id}", status_code=204)
def eliminar_item(item_id: int):
    """Elimina un item por ID."""
    if item_id not in db:
        raise HTTPException(status_code=404, detail="Item no encontrado")
    del db[item_id]
    return


# ---------- Endpoint con Feature Flag (LaunchDarkly) ----------

@app.get("/items/{item_id}/precio", response_model=float)
def obtener_precio_item(
    item_id: int,
    x_user_id: Optional[str] = Header(
        default="anonimo",
        alias="X-User-Id",
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
            False  # fallback si LaunchDarkly no responde
        )
    except Exception:
        # Si algo sale mal con LaunchDarkly, no rompemos la API:
        # simplemente usamos el precio normal
        nuevo_precio_activo = False

    if nuevo_precio_activo:
        # Nueva lógica (10% de descuento)
        return round(item.precio * 0.9, 2)
    else:
        # Lógica actual
        return item.precio
