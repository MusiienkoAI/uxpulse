from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .db import Base, engine
from .ingest import router as ingest_router
from .issues import router as issues_router
from .llm_analysis import router as llm_analysis_router
from .link_code import router as link_code_router
from .screens import router as screens_router

app = FastAPI(title="UXPulse Local", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup() -> None:
    Base.metadata.create_all(bind=engine)


app.include_router(ingest_router)
app.include_router(llm_analysis_router)
app.include_router(issues_router)
app.include_router(screens_router)
app.include_router(link_code_router)


@app.get("/health")
def health() -> dict[str, bool]:
    return {"ok": True}
