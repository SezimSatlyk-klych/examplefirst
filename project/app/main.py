from fastapi import FastAPI
from . import models, database
from .routes import router
from fastapi.staticfiles import StaticFiles
from . import crm

models.Base.metadata.create_all(bind=database.engine)

app = FastAPI()
app.include_router(router, prefix="/api")
app.include_router(crm.router, prefix="/api")

