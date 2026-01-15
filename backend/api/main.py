"""
FastAPI Application - Main entry point.
Provides REST API and WebSocket for the Black-Box Web Intelligence system.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from ..core.config import settings
from ..memory.fsm_store import FSMStore
from ..memory.chroma_store import ChromaStore
from ..memory.global_memory import GlobalMemoryManager

from .routes import sessions, hypotheses, schemas, control, observations, fsm, stats, tech_intel, security
from .websocket import router as websocket_router


# Global instances
fsm_store: FSMStore | None = None
chroma_store: ChromaStore | None = None
memory_manager: GlobalMemoryManager | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan handler.
    Initializes and cleans up resources.
    """
    global fsm_store, chroma_store, memory_manager
    
    # Initialize stores
    print("Initializing data stores...")
    
    fsm_store = FSMStore(settings.database_path)
    await fsm_store.initialize()
    
    chroma_store = ChromaStore(settings.chroma_persist_dir)
    await chroma_store.initialize()
    
    memory_manager = GlobalMemoryManager(
        db_connection=fsm_store.db,
        chroma_client=chroma_store.client,
        fsm_store=fsm_store
    )
    
    # Store references in app state
    app.state.fsm_store = fsm_store
    app.state.chroma_store = chroma_store
    app.state.memory_manager = memory_manager
    
    print("Black-Box Web Intelligence API ready")
    
    yield
    
    # Cleanup
    print("Shutting down...")
    if fsm_store:
        await fsm_store.close()
    if chroma_store:
        await chroma_store.close()


def create_app() -> FastAPI:
    """
    Create and configure FastAPI application.
    
    Returns:
        Configured FastAPI app
    """
    app = FastAPI(
        title="Black-Box Web Intelligence",
        description=(
            "Autonomous multi-agent system for reverse-engineering backend API "
            "specifications through dynamic UI analysis. Uses the Agentic Scientific "
            "Method: Explore → Observe → Infer → Critique → Probe → Update → Repeat"
        ),
        version="0.1.0",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
    )
    
    # CORS middleware for frontend
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure appropriately for production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Include routers
    app.include_router(sessions.router, prefix="/api/sessions", tags=["Sessions"])
    app.include_router(hypotheses.router, prefix="/api/hypotheses", tags=["Hypotheses"])
    app.include_router(schemas.router, prefix="/api/schemas", tags=["Schemas"])
    app.include_router(control.router, prefix="/api/control", tags=["Control"])
    app.include_router(observations.router, prefix="/api/observations", tags=["Observations"])
    app.include_router(fsm.router, prefix="/api/fsm", tags=["FSM"])
    app.include_router(stats.router, prefix="/api/stats", tags=["Stats"])
    app.include_router(tech_intel.router, prefix="/api/tech", tags=["Technology Intelligence"])
    app.include_router(security.router, prefix="/api/security", tags=["Security Analysis"])
    app.include_router(websocket_router, prefix="/ws", tags=["WebSocket"])
    
    @app.get("/", tags=["Root"])
    async def root():
        """Root endpoint with API information."""
        return {
            "name": "Black-Box Web Intelligence",
            "version": "0.1.0",
            "status": "running",
            "docs": "/docs",
            "scientific_loop": [
                "explore", "observe", "infer", "critique", "probe", "update"
            ],
            "agents": [
                "Navigator",
                "Interceptor", 
                "Analyst",
                "BusinessLogic",
                "Critic",
                "Verifier"
            ]
        }
    
    @app.get("/health", tags=["Health"])
    async def health_check():
        """Health check endpoint."""
        return {
            "status": "healthy",
            "database": "connected" if fsm_store else "disconnected",
            "vector_store": "connected" if chroma_store else "disconnected"
        }
    
    return app


# Create app instance
app = create_app()
