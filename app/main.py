from typing import List, Optional
import os

from fastapi import FastAPI, HTTPException, Header

from .models import Item, ItemBase
from .database import db, get_next_id

import ldclient
from ldclient.config import Config

# ---------------- LaunchDarkly ----------------

FEATURE_NEW_PRICING = "new-pricing-strategy"

# Leemos la SDK key desde la variable de entorno
LD_SDK_KEY = os.getenv("LAUNCHDARKLY_SDK_KEY")

if not LD_SDK_KEY:
    raise RuntimeError(
        "[LaunchDarkly] ERROR: LAUNCHDARKLY_SDK_KEY no está definida en las "
        "variables de entorno. Verifica el Secret de Kubernetes "
        "(launchdarkly-secret) y el Deployment."
    )

# Configuramos el cliente de LaunchDarkly
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
        "API de ejemplo con CRUD en memoria, integración con LaunchDarkly "
        "para una nueva estrategia de precios y despliegue continuo con ArgoCD."
    ),
    version="1.0.0",
)


@app.on_event("shutdown")
def shutdown_event():
    """Cerramos el cliente de LaunchDarkly cuando se apaga la app."""
    ld_client.close()


# ---------------- Endpoints CRUD básicos ----------------

@app.get("/items", response_model=List[Item])
def listar_items():
    """Lista todos los items almacenados en la 'base de datos' en memoria."""
    return list(db.values())


@app.post("/items", response_model=Item, status_code=201)
def crear_item(item: ItemBase):
    """Crea un nuevo item con un ID autogenerado."""
    item_id = get_next_id()
    nuevo = Item(id=item_id, **item.dict())
    db[item_id] = nuevo
    return nuevo


@app.get("/items/{item_id}", response_model=Item)
def obtener_item(item_id: int):
    """Obtiene un item por ID."""
    if item_id not in db:
        raise HTTPException(status_code=404, detail="Item no encontrado")
    return db[item_id]


@app.delete("/items/{item_id}", status_code=204)
def eliminar_item(item_id: int):
    """Elimina un item por ID."""
    if item_id not in db:
        raise HTTPException(status_code=404, detail="Item no encontrado")
    del db[item_id]
    return


# ---------------- Endpoint con LaunchDarkly (precio) ----------------

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
    Devuelve el precio del item.

    Si el feature flag 'new-pricing-strategy' está activo para el usuario,
    aplica un 10% de descuento como ejemplo de nueva estrategia de precios.
    """
    if item_id not in db:
        raise HTTPException(status_code=404, detail="Item no encontrado")

    item = db[item_id]

    # Representación simple de usuario para LaunchDarkly
    user = {"key": x_user_id or "anonimo"}

    try:
        # 👇 AQUÍ ESTÁ LO IMPORTANTE
        # En el SDK Python la API correcta es 'variation', NO 'bool_variation'
        nuevo_precio_activo = bool(
            ld_client.variation(
                FEATURE_NEW_PRICING,
                user,
                False,  # valor por defecto si algo falla
            )
        )
    except Exception as e:
        print(f"[LaunchDarkly] Error evaluando flag: {e}")
        nuevo_precio_activo = False

    if nuevo_precio_activo:
        # Nueva estrategia de precios: 10% descuento
        return round(item.precio * 0.9, 2)
    else:
        # Precio original
        return item.precio


# ---------------- Endpoint de debug LaunchDarkly ----------------

@app.get("/debug/launchdarkly")
def debug_launchdarkly(
    x_user_id: Optional[str] = Header(default="debug-user", alias="X-User-Id")
):
    """
    Endpoint para verificar desde fuera si:
    - La SDK key está configurada
    - El cliente de LaunchDarkly está inicializado
    - El valor actual del flag 'new-pricing-strategy' para un usuario dado
    """
    user = {"key": x_user_id or "debug-user"}

    status = {
        "sdk_key_configurada": bool(LD_SDK_KEY),
        "cliente_inicializado": ld_client.is_initialized(),
        "flag_name": FEATURE_NEW_PRICING,
    }

    try:
        status["flag_value"] = ld_client.variation(
            FEATURE_NEW_PRICING,
            user,
            False,
        )
    except Exception as e:
        status["error"] = str(e)

    return status
