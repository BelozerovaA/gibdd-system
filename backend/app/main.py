import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from jose import JWTError, jwt

from . import models, runtime
from .auth import ALGORITHM, SECRET_KEY
from .database import engine
from .routes import alerts as alerts_routes
from .routes import auth as auth_routes
from .routes import cameras as cameras_routes
from .routes import employees as employees_routes
from .routes import simulator as simulator_routes
from .routes import vehicles as vehicles_routes
from .routes import wanted as wanted_routes
from .websocket.manager import manager


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Создаём таблицы, если их ещё нет (то же делает seed.py).
    models.Base.metadata.create_all(bind=engine)
    # Симулятор камер работает в отдельном потоке и через этот loop
    # отправляет оповещения в WebSocket.
    runtime.set_main_loop(asyncio.get_running_loop())
    yield


app = FastAPI(title="GIBDD API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_routes.router, prefix="/api/auth", tags=["auth"])
app.include_router(employees_routes.router, prefix="/api/employees", tags=["employees"])
app.include_router(vehicles_routes.router, prefix="/api/vehicles", tags=["vehicles"])
app.include_router(wanted_routes.router, prefix="/api/wanted", tags=["wanted"])
app.include_router(alerts_routes.router, prefix="/api/alerts", tags=["alerts"])
app.include_router(cameras_routes.router, prefix="/api/cameras", tags=["cameras"])
app.include_router(simulator_routes.router, prefix="/api/simulator", tags=["simulator"])


@app.get("/")
def root():
    return {"message": "GIBDD API", "status": "running"}


def _employee_id_from_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("scope") == "export":
            return None  # токен для скачивания отчёта не открывает WebSocket
        return payload.get("sub")
    except JWTError:
        return None


@app.websocket("/ws/{employee_id}")
async def websocket_endpoint(websocket: WebSocket, employee_id: int, token: str = ""):
    verified_id = _employee_id_from_token(token)
    if verified_id is None or int(verified_id) != employee_id:
        await websocket.close(code=4401)
        return

    await manager.connect(employee_id, websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        manager.disconnect(employee_id, websocket)
