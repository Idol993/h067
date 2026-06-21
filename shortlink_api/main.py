from fastapi import FastAPI
from contextlib import asynccontextmanager

from .core.config import settings
from .core.rate_limiter import limiter, rate_limit_exceeded_handler
from .middleware.cors import setup_cors
from .middleware.logger import setup_logger
from .models.database import get_db, close_db
from .core.geoip import close_reader

from .routers import links, redirect, stats, admin


@asynccontextmanager
async def lifespan(app: FastAPI):
    await get_db()
    yield
    await close_db()
    close_reader()


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="高性能短链接服务 API，支持自定义短码、过期时间、访问密码和访问统计",
    lifespan=lifespan,
)

setup_cors(app)
setup_logger(app)

app.state.limiter = limiter
app.add_exception_handler(429, rate_limit_exceeded_handler)

@app.get("/health", tags=["health"])
async def health_check():
    return {"status": "ok", "version": settings.APP_VERSION}


@app.get("/", tags=["root"])
async def root():
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "docs": "/docs",
    }


app.include_router(links.router)
app.include_router(stats.router)
app.include_router(admin.router)
app.include_router(redirect.router)
