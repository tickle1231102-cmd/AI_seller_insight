from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.errors import register_error_handlers
from app.routers import analyze, health, preview

app = FastAPI(title="Seller Insight AI")

# 순서 중요: 나중에 등록한 미들웨어가 바깥에 온다.
# 오류 처리를 먼저, CORS 를 마지막에 등록해야 500 응답에도 CORS 헤더가 붙는다.
register_error_handlers(app)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(preview.router)
app.include_router(analyze.router)
