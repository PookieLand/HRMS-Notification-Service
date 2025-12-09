"""
Redis Cache Module for Notification Service.

Provides caching utilities for notification preferences, templates, and metrics.
Uses Redis for high-performance caching with TTL support.
"""

import json
from datetime import timedelta
from typing import Any, Optional

import redis

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class CacheService:
    """
    Redis cache service for the Notification Service.
    Handles caching of notification preferences, templates, and metrics.
    """

    def __init__(self):
        self._client: Optional[redis.Redis] = None
        self._connected = False

    def connect(self) -> None:
        """Initialize Redis connection."""
        if self._client is not None and self._connected:
            return

        try:
            self._client = redis.Redis(
                host=settings.REDIS_HOST,
                port=settings.REDIS_PORT,
                db=settings.REDIS_DB,
                password=settings.REDIS_PASSWORD or None,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5,
                retry_on_timeout=True,
            )
            # Test connection
            self._client.ping()
            self._connected = True
            logger.info(
                f"Redis connected to {settings.REDIS_HOST}:{settings.REDIS_PORT}"
            )
        except redis.ConnectionError as e:
            logger.error(f"Failed to connect to Redis: {e}")
            self._connected = False
            raise
        except Exception as e:
            logger.error(f"Unexpected error connecting to Redis: {e}")
            self._connected = False
            raise

    def disconnect(self) -> None:
        """Close Redis connection."""
        if self._client is not None:
            try:
                self._client.close()
                self._connected = False
                logger.info("Redis connection closed")
            except Exception as e:
                logger.error(f"Error closing Redis connection: {e}")

    def is_connected(self) -> bool:
        """Check if Redis is connected."""
        if self._client is None:
            return False
        try:
            self._client.ping()
            return True
        except Exception:
            return False

    def _ensure_connected(self) -> None:
        """Ensure Redis is connected before operations."""
        if not self._connected or self._client is None:
            self.connect()

    # ==========================================
    # Generic Cache Operations
    # ==========================================

    def get(self, key: str) -> Optional[str]:
        """Get a value from cache."""
        self._ensure_connected()
        try:
            return self._client.get(key)
        except Exception as e:
            logger.error(f"Cache get error for key {key}: {e}")
            return None

    def set(
        self,
        key: str,
        value: str,
        ttl_seconds: Optional[int] = None,
    ) -> bool:
        """Set a value in cache with optional TTL."""
        self._ensure_connected()
        try:
            if ttl_seconds:
                self._client.setex(key, ttl_seconds, value)
            else:
                self._client.set(key, value)
            return True
        except Exception as e:
            logger.error(f"Cache set error for key {key}: {e}")
            return False

    def delete(self, key: str) -> bool:
        """Delete a key from cache."""
        self._ensure_connected()
        try:
            self._client.delete(key)
            return True
        except Exception as e:
            logger.error(f"Cache delete error for key {key}: {e}")
            return False

    def exists(self, key: str) -> bool:
        """Check if a key exists in cache."""
        self._ensure_connected()
        try:
            return bool(self._client.exists(key))
        except Exception as e:
            logger.error(f"Cache exists error for key {key}: {e}")
            return False

    def get_json(self, key: str) -> Optional[dict[str, Any]]:
        """Get a JSON value from cache."""
        value = self.get(key)
        if value is None:
            return None
        try:
            return json.loads(value)
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error for key {key}: {e}")
            return None

    def set_json(
        self,
        key: str,
        value: dict[str, Any],
        ttl_seconds: Optional[int] = None,
    ) -> bool:
        """Set a JSON value in cache."""
        try:
            json_str = json.dumps(value, default=str)
            return self.set(key, json_str, ttl_seconds)
        except (TypeError, json.JSONEncoder) as e:
            logger.error(f"JSON encode error for key {key}: {e}")
            return False

    def delete_pattern(self, pattern: str) -> int:
        """Delete all keys matching a pattern."""
        self._ensure_connected()
        try:
            keys = self._client.keys(pattern)
            if keys:
                return self._client.delete(*keys)
            return 0
        except Exception as e:
            logger.error(f"Cache delete pattern error for {pattern}: {e}")
            return 0

    # ==========================================
    # Notification Preference Caching
    # ==========================================

    def _preference_key(self, employee_id: int) -> str:
        """Generate cache key for notification preferences."""
        return f"notification:preferences:{employee_id}"

    def get_notification_preferences(
        self,
        employee_id: int,
    ) -> Optional[dict[str, Any]]:
        """Get notification preferences for an employee."""
        key = self._preference_key(employee_id)
        return self.get_json(key)

    def set_notification_preferences(
        self,
        employee_id: int,
        preferences: dict[str, Any],
        ttl_seconds: int = 3600,
    ) -> bool:
        """Cache notification preferences for an employee."""
        key = self._preference_key(employee_id)
        return self.set_json(key, preferences, ttl_seconds)

    def invalidate_notification_preferences(self, employee_id: int) -> bool:
        """Invalidate cached notification preferences."""
        key = self._preference_key(employee_id)
        return self.delete(key)

    # ==========================================
    # Email Template Caching
    # ==========================================

    def _template_key(self, template_name: str) -> str:
        """Generate cache key for email templates."""
        return f"notification:template:{template_name}"

    def get_cached_template(self, template_name: str) -> Optional[str]:
        """Get a cached email template."""
        key = self._template_key(template_name)
        return self.get(key)

    def cache_template(
        self,
        template_name: str,
        template_content: str,
        ttl_seconds: int = 3600,
    ) -> bool:
        """Cache an email template."""
        key = self._template_key(template_name)
        return self.set(key, template_content, ttl_seconds)

    def invalidate_template(self, template_name: str) -> bool:
        """Invalidate a cached template."""
        key = self._template_key(template_name)
        return self.delete(key)

    def invalidate_all_templates(self) -> int:
        """Invalidate all cached templates."""
        return self.delete_pattern("notification:template:*")

    # ==========================================
    # Notification Metrics Caching
    # ==========================================

    def _metrics_key(self, metric_type: str, date_str: str) -> str:
        """Generate cache key for notification metrics."""
        return f"notification:metrics:{metric_type}:{date_str}"

    def get_notification_metrics(
        self,
        metric_type: str,
        date_str: str,
    ) -> Optional[dict[str, Any]]:
        """Get cached notification metrics."""
        key = self._metrics_key(metric_type, date_str)
        return self.get_json(key)

    def set_notification_metrics(
        self,
        metric_type: str,
        date_str: str,
        metrics: dict[str, Any],
        ttl_seconds: int = 300,
    ) -> bool:
        """Cache notification metrics."""
        key = self._metrics_key(metric_type, date_str)
        return self.set_json(key, metrics, ttl_seconds)

    def increment_metric(
        self,
        metric_name: str,
        amount: int = 1,
    ) -> Optional[int]:
        """Increment a metric counter."""
        self._ensure_connected()
        try:
            key = f"notification:counter:{metric_name}"
            return self._client.incrby(key, amount)
        except Exception as e:
            logger.error(f"Error incrementing metric {metric_name}: {e}")
            return None

    def get_metric_counter(self, metric_name: str) -> int:
        """Get a metric counter value."""
        self._ensure_connected()
        try:
            key = f"notification:counter:{metric_name}"
            value = self._client.get(key)
            return int(value) if value else 0
        except Exception as e:
            logger.error(f"Error getting metric {metric_name}: {e}")
            return 0

    # ==========================================
    # Rate Limiting
    # ==========================================

    def _rate_limit_key(self, identifier: str, window: str) -> str:
        """Generate cache key for rate limiting."""
        return f"notification:ratelimit:{identifier}:{window}"

    def check_rate_limit(
        self,
        identifier: str,
        max_requests: int,
        window_seconds: int,
    ) -> tuple[bool, int]:
        """
        Check if a request is within rate limits.

        Args:
            identifier: Unique identifier (e.g., email, employee_id)
            max_requests: Maximum allowed requests in window
            window_seconds: Time window in seconds

        Returns:
            Tuple of (is_allowed, current_count)
        """
        self._ensure_connected()
        try:
            import time

            window = str(int(time.time()) // window_seconds)
            key = self._rate_limit_key(identifier, window)

            current = self._client.incr(key)
            if current == 1:
                self._client.expire(key, window_seconds)

            is_allowed = current <= max_requests
            return (is_allowed, current)
        except Exception as e:
            logger.error(f"Rate limit check error for {identifier}: {e}")
            return (True, 0)  # Fail open

    # ==========================================
    # Notification Queue Caching
    # ==========================================

    def _queue_key(self, queue_name: str) -> str:
        """Generate cache key for notification queue."""
        return f"notification:queue:{queue_name}"

    def enqueue_notification(
        self,
        queue_name: str,
        notification_data: dict[str, Any],
    ) -> bool:
        """Add a notification to a queue."""
        self._ensure_connected()
        try:
            key = self._queue_key(queue_name)
            json_data = json.dumps(notification_data, default=str)
            self._client.rpush(key, json_data)
            return True
        except Exception as e:
            logger.error(f"Error enqueueing notification to {queue_name}: {e}")
            return False

    def dequeue_notification(
        self,
        queue_name: str,
        timeout: int = 0,
    ) -> Optional[dict[str, Any]]:
        """Remove and return a notification from a queue."""
        self._ensure_connected()
        try:
            key = self._queue_key(queue_name)
            if timeout > 0:
                result = self._client.blpop(key, timeout=timeout)
                if result:
                    return json.loads(result[1])
            else:
                result = self._client.lpop(key)
                if result:
                    return json.loads(result)
            return None
        except Exception as e:
            logger.error(f"Error dequeuing notification from {queue_name}: {e}")
            return None

    def get_queue_length(self, queue_name: str) -> int:
        """Get the length of a notification queue."""
        self._ensure_connected()
        try:
            key = self._queue_key(queue_name)
            return self._client.llen(key)
        except Exception as e:
            logger.error(f"Error getting queue length for {queue_name}: {e}")
            return 0

    # ==========================================
    # Deduplication
    # ==========================================

    def _dedup_key(self, event_id: str) -> str:
        """Generate cache key for deduplication."""
        return f"notification:dedup:{event_id}"

    def is_duplicate_event(
        self,
        event_id: str,
        ttl_seconds: int = 86400,
    ) -> bool:
        """
        Check if an event has already been processed.

        Args:
            event_id: Unique event identifier
            ttl_seconds: How long to remember the event (default 24h)

        Returns:
            True if duplicate, False if new
        """
        self._ensure_connected()
        try:
            key = self._dedup_key(event_id)
            # SET NX returns True if key was set (new), False if exists (duplicate)
            was_set = self._client.set(key, "1", nx=True, ex=ttl_seconds)
            return not was_set
        except Exception as e:
            logger.error(f"Deduplication check error for {event_id}: {e}")
            return False  # Fail open - process the event


# Global cache service instance
_cache_service: Optional[CacheService] = None


def get_cache_service() -> CacheService:
    """Get or create the global cache service instance."""
    global _cache_service
    if _cache_service is None:
        _cache_service = CacheService()
    return _cache_service


def init_cache() -> CacheService:
    """Initialize and connect the cache service."""
    cache = get_cache_service()
    cache.connect()
    return cache


def close_cache() -> None:
    """Close the cache service connection."""
    global _cache_service
    if _cache_service is not None:
        _cache_service.disconnect()
        _cache_service = None
