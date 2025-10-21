"""FastAPI application for report generation service."""

import logging
from datetime import datetime

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.api.exceptions import APIException
from src.api.models import ErrorResponse, HealthResponse
from src.api.routes import export, health, quality, reports

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Autonomous Report Generator API",
    description="API for generating research reports from ontologies",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Exception handlers
@app.exception_handler(APIException)
async def api_exception_handler(request: Request, exc: APIException):
    """Handle API exceptions."""
    logger.error(f"API exception: {exc.message}")
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            error=exc.__class__.__name__,
            message=exc.message,
            details=exc.details,
            timestamp=datetime.utcnow(),
        ).model_dump(),
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle validation errors."""
    logger.error(f"Validation error: {exc}")
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=ErrorResponse(
            error="ValidationError",
            message="Request validation failed",
            details={"errors": exc.errors()},
            timestamp=datetime.utcnow(),
        ).model_dump(),
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle general exceptions."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=ErrorResponse(
            error="InternalServerError",
            message="An unexpected error occurred",
            details={"error": str(exc)},
            timestamp=datetime.utcnow(),
        ).model_dump(),
    )


# Root endpoint
@app.get("/", tags=["root"])
async def root():
    """Root endpoint."""
    return {
        "name": "Autonomous Report Generator API",
        "version": "1.0.0",
        "description": "API for generating research reports from ontologies",
        "docs": "/docs",
        "health": "/health",
    }


# Include routers
app.include_router(health.router)
app.include_router(reports.router)
app.include_router(quality.router)
app.include_router(export.router)


# Startup and shutdown events
@app.on_event("startup")
async def startup_event():
    """Run on application startup."""
    logger.info("Starting Autonomous Report Generator API")
    logger.info("API documentation available at /docs")


@app.on_event("shutdown")
async def shutdown_event():
    """Run on application shutdown."""
    logger.info("Shutting down Autonomous Report Generator API")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "src.api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )
