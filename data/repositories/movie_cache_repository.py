"""Repository for caching TMDB movie catalog data."""
import json
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from data.connection import connection_scope
from utils.logger import get_logger

logger = get_logger("movie_cache_repo")

# Cache expiration: 6 hours for most categories, 1 hour for trending
CACHE_EXPIRATION_HOURS = 6
TRENDING_CACHE_EXPIRATION_HOURS = 1


class MovieCacheRepository:
    """Manages cached TMDB movie catalog data."""
    
    def save(self, cache_key: str, data: Any, expiration_hours: int = CACHE_EXPIRATION_HOURS) -> None:
        """Save data to cache with expiration."""
        expires_at = datetime.now(timezone.utc) + timedelta(hours=expiration_hours)
        cache_data = json.dumps(data)
        
        with connection_scope() as conn:
            conn.execute("""
                INSERT INTO movie_cache (cache_key, cache_data, expires_at)
                VALUES (?, ?, ?)
                ON CONFLICT(cache_key) DO UPDATE SET
                    cache_data = excluded.cache_data,
                    expires_at = excluded.expires_at,
                    created_at = CURRENT_TIMESTAMP
            """, (cache_key, cache_data, expires_at.isoformat()))
    
    def get(self, cache_key: str) -> Optional[Any]:
        """Get cached data if not expired."""
        with connection_scope() as conn:
            row = conn.execute("""
                SELECT cache_data, expires_at
                FROM movie_cache
                WHERE cache_key = ?
            """, (cache_key,)).fetchone()
            
            if row is None:
                return None
            
            cache_data, expires_at_str = row
            
            # Check expiration
            try:
                expires_at = datetime.fromisoformat(expires_at_str)
                if datetime.now(timezone.utc) > expires_at:
                    logger.debug(f"Cache expired for key: {cache_key}")
                    return None
            except (ValueError, TypeError):
                return None
            
            # Parse cached data
            try:
                return json.loads(cache_data)
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse cached data for key: {cache_key}")
                return None
    
    def clear_expired(self) -> int:
        """Remove expired cache entries. Returns number of rows deleted."""
        with connection_scope() as conn:
            cursor = conn.execute("""
                DELETE FROM movie_cache
                WHERE datetime(expires_at) < datetime('now')
            """)
            return cursor.rowcount
    
    def clear_all(self) -> int:
        """Clear all cache entries. Returns number of rows deleted."""
        with connection_scope() as conn:
            cursor = conn.execute("DELETE FROM movie_cache")
            return cursor.rowcount
