from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.internal import router as internal_router
from app.api.routes.notifications import router as notifications_router
from app.core.config import settings
from app.core.database import create_db_and_tables
from app.core.logging import get_logger

logger = get_logger(__name__)

# Global state for tracking service health
service_state = {
    "kafka_connected": False,
    "redis_connected": False,
    "database_ready": False,
}


def init_kafka():
    """Initialize Kafka producer and consumer."""
    try:
        from app.core.consumers import register_all_handlers, start_consumer
        from app.core.kafka import get_consumer, get_producer
        from app.core.topics import KafkaTopics

        # Initialize producer
        producer = get_producer()
        producer.connect()
        logger.info("Kafka producer initialized")

        # Initialize consumer with all topics
        consumer = get_consumer(topics=KafkaTopics.all_subscribed_topics())
        register_all_handlers(consumer)
        consumer.start()
        logger.info("Kafka consumer started with all handlers")

        service_state["kafka_connected"] = True
    except Exception as e:
        logger.error(f"Failed to initialize Kafka: {e}")
        service_state["kafka_connected"] = False


def shutdown_kafka():
    """Shutdown Kafka connections."""
    try:
        from app.core.kafka import get_consumer, get_producer

        # Stop consumer
        consumer = get_consumer()
        consumer.stop()
        logger.info("Kafka consumer stopped")

        # Disconnect producer
        producer = get_producer()
        producer.disconnect()
        logger.info("Kafka producer disconnected")

        service_state["kafka_connected"] = False
    except Exception as e:
        logger.error(f"Error shutting down Kafka: {e}")


def init_redis():
    """Initialize Redis cache."""
    try:
        from app.core.cache import init_cache

        cache = init_cache()
        logger.info("Redis cache initialized")
        service_state["redis_connected"] = cache.is_connected()
    except Exception as e:
        logger.warning(f"Failed to initialize Redis: {e}")
        service_state["redis_connected"] = False


def shutdown_redis():
    """Shutdown Redis connection."""
    try:
        from app.core.cache import close_cache

        close_cache()
        logger.info("Redis cache closed")
        service_state["redis_connected"] = False
    except Exception as e:
        logger.error(f"Error closing Redis: {e}")


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Startup
    logger.info("Starting Notification Service...")

    # Initialize database
    logger.info("Creating database and tables...")
    create_db_and_tables()
    service_state["database_ready"] = True
    logger.info("Database and tables created successfully")

    # Initialize Redis cache
    logger.info("Initializing Redis cache...")
    init_redis()

    # Initialize Kafka
    if settings.kafka_configured:
        logger.info("Initializing Kafka...")
        init_kafka()
    else:
        logger.warning("Kafka not configured, skipping initialization")

    logger.info("Notification Service startup complete")

    yield

    # Shutdown
    logger.info("Notification Service shutting down...")

    # Shutdown Kafka
    if service_state["kafka_connected"]:
        shutdown_kafka()

    # Shutdown Redis
    if service_state["redis_connected"]:
        shutdown_redis()

    logger.info("Notification Service shutdown complete")


# Initialize FastAPI application
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="HRMS Notification Service - Handles email notifications triggered by Kafka events",
    lifespan=lifespan,
)


# Configure CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
    allow_methods=settings.CORS_ALLOW_METHODS,
    allow_headers=settings.CORS_ALLOW_HEADERS,
)


# Include routers
app.include_router(notifications_router, prefix="/api/v1/notifications")
app.include_router(internal_router, prefix="/api/v1/notifications")


@app.get("/health", tags=["health"])
async def detailed_health_check():
    """
    Detailed health check endpoint.
    Returns service status and connection states.
    """
    return {
        "status": "healthy",
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "connections": {
            "database": service_state["database_ready"],
            "kafka": service_state["kafka_connected"],
            "redis": service_state["redis_connected"],
        },
    }


@app.get("/health/ready", tags=["health"])
async def readiness_check():
    """
    Readiness probe for Kubernetes.
    Returns 200 if service is ready to accept traffic.
    """
    is_ready = service_state["database_ready"]

    if is_ready:
        return {"status": "ready"}
    else:
        from fastapi import HTTPException

        raise HTTPException(status_code=503, detail="Service not ready")


@app.get("/health/live", tags=["health"])
async def liveness_check():
    """
    Liveness probe for Kubernetes.
    Returns 200 if service is alive.
    """
    return {"status": "alive"}


@app.get("/health/kafka", tags=["health"])
async def kafka_health_check():
    """
    Kafka connection health check.
    """
    return {
        "connected": service_state["kafka_connected"],
        "bootstrap_servers": settings.KAFKA_BOOTSTRAP_SERVERS,
    }


@app.get("/health/redis", tags=["health"])
async def redis_health_check():
    """
    Redis connection health check.
    """
    connected = False
    try:
        from app.core.cache import get_cache_service

        cache = get_cache_service()
        connected = cache.is_connected()
    except Exception:
        pass

    return {
        "connected": connected,
        "host": settings.REDIS_HOST,
        "port": settings.REDIS_PORT,
    }


@app.get("/metrics/notifications", tags=["metrics"])
async def notification_metrics():
    """
    Get notification sending metrics.
    """
    try:
        from datetime import date

        from app.core.cache import get_cache_service

        cache = get_cache_service()
        today = date.today().isoformat()

        return {
            "date": today,
            "emails_sent_today": cache.get_metric_counter(f"emails_sent:{today}"),
            "emails_failed_today": cache.get_metric_counter(f"emails_failed:{today}"),
            "queue_length": cache.get_queue_length("pending"),
        }
    except Exception as e:
        logger.error(f"Error fetching metrics: {e}")
        return {
            "error": "Unable to fetch metrics",
            "detail": str(e),
        }
