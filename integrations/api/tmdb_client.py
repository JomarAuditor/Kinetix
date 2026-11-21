"""TMDB (needs TMDB_API_KEY in .env). Search, details, popular movies."""
from typing import Dict, List, Optional

from config import settings
from config.constants import MOVIE_FIRST_YEAR, MOVIE_LAST_YEAR
from core.exceptions import ApiError, MissingApiKeyError
from integrations.api.base_client import BaseClient
from models.movie import Movie

IMAGE_BASE_POSTER = "https://image.tmdb.org/t/p/w342"
IMAGE_BASE_BACKDROP = "https://image.tmdb.org/t/p/w780"
_GENRES = {28: "Action", 12: "Adventure", 16: "Animation", 35: "Comedy", 80: "Crime", 99: "Documentary",
           18: "Drama", 10751: "Family", 14: "Fantasy", 36: "History", 27: "Horror", 10402: "Music",
           9648: "Mystery", 10749: "Romance", 878: "Sci-Fi", 53: "Thriller", 10752: "War", 37: "Western"}


class TmdbClient(BaseClient):
    def __init__(self) -> None:
        super().__init__("https://api.themoviedb.org/3")

    def _get_key(self) -> str:
        key = settings.get_tmdb_api_key()
        if not key:
            raise MissingApiKeyError("TMDB_API_KEY is not set in .env.")
        return key

    def _request(self, endpoint: str, params: Dict) -> dict:
        key = self._get_key()
        if key.startswith("eyJ"):
            return self.get_json(endpoint, params, headers={"Authorization": f"Bearer {key}"})
        return self.get_json(endpoint, {**params, "api_key": key})

    def popular_movies(self, page: int = 1, limit: int = 20) -> List[Dict[str, str]]:
        """Returns dicts with id, title, subtitle (genre and year) and image_url."""
        params = {"sort_by": "popularity.desc", "page": str(page), "include_adult": "false",
                  "primary_release_date.gte": f"{MOVIE_FIRST_YEAR}-01-01",
                  "primary_release_date.lte": f"{MOVIE_LAST_YEAR}-12-31"}
        data = self._request("discover/movie", params)
        results = data.get("results") if isinstance(data, dict) else None
        if not isinstance(results, list):
            raise ApiError("The movie service sent an unexpected answer.")
        return [movie for movie in (self._parse_simple(row) for row in results) if movie][:limit]

    def search_movies(self, query: str, page: int = 1) -> List[Movie]:
        """Search TMDB for movies by title."""
        params = {"query": query, "page": str(page), "include_adult": "false"}
        data = self._request("search/movie", params)
        results = data.get("results") if isinstance(data, dict) else None
        if not isinstance(results, list):
            return []
        movies = []
        for row in results:
            movie = self._parse_full(row)
            if movie and 1900 <= movie.release_year <= MOVIE_LAST_YEAR:
                movies.append(movie)
        return movies

    def get_movie_details(self, tmdb_id: int) -> Optional[Movie]:
        """Get full movie details by TMDB ID."""
        try:
            data = self._request(f"movie/{tmdb_id}", {})
            return self._parse_full(data) if isinstance(data, dict) else None
        except ApiError:
            return None

    def discover_by_category(self, category: str, page: int = 1, limit: int = 20) -> List[Movie]:
        """Discover movies by category.

        Categories: popular, 2000s, 2010s, 2020s, classics
        Year caps: We stop at 2022 for 'popular' and 2020s, since movies after
        that rarely have free full-length uploads on YouTube yet.
        """
        params = {"include_adult": "false", "page": str(page)}

        if category == "popular":
            # Popular movies from 2000–2022 — realistic YouTube availability window
            params["sort_by"] = "popularity.desc"
            params["primary_release_date.gte"] = "2000-01-01"
            params["primary_release_date.lte"] = "2022-12-31"
        elif category == "2000s":
            params["sort_by"] = "popularity.desc"
            params["primary_release_date.gte"] = "2000-01-01"
            params["primary_release_date.lte"] = "2009-12-31"
        elif category == "2010s":
            params["sort_by"] = "popularity.desc"
            params["primary_release_date.gte"] = "2010-01-01"
            params["primary_release_date.lte"] = "2019-12-31"
        elif category == "2020s":
            params["sort_by"] = "popularity.desc"
            params["primary_release_date.gte"] = "2020-01-01"
            params["primary_release_date.lte"] = "2022-12-31"
        elif category == "classics":
            # Pre-2000 classics — many are public domain or freely uploaded
            params["sort_by"] = "popularity.desc"
            params["primary_release_date.gte"] = "1970-01-01"
            params["primary_release_date.lte"] = "1999-12-31"
        else:
            params["sort_by"] = "popularity.desc"
            params["primary_release_date.gte"] = "2000-01-01"
            params["primary_release_date.lte"] = "2022-12-31"

        data = self._request("discover/movie", params)
        results = data.get("results") if isinstance(data, dict) else None
        if not isinstance(results, list):
            return []
        return [movie for movie in (self._parse_full(row) for row in results) if movie][:limit]

    @staticmethod
    def _parse_simple(row):
        """Simple parse for dashboard featured list."""
        if not isinstance(row, dict) or not row.get("id") or not isinstance(row.get("title"), str):
            return None
        genre_ids = row.get("genre_ids") if isinstance(row.get("genre_ids"), list) else []
        genre = next((_GENRES[g] for g in genre_ids if g in _GENRES), "")
        year = str(row.get("release_date") or "")[:4]
        poster = row.get("poster_path")
        return {
            "id": str(row["id"]),
            "title": row["title"],
            "subtitle": " \u2022 ".join(part for part in (genre, year) if part),
            "image_url": f"{IMAGE_BASE_POSTER}{poster}" if isinstance(poster, str) and poster else "",
        }

    @staticmethod
    def _parse_full(row: dict) -> Optional[Movie]:
        """Parse full movie object."""
        if not isinstance(row, dict) or not row.get("id") or not isinstance(row.get("title"), str):
            return None
        
        # Extract year from release_date
        release_date = str(row.get("release_date") or "")
        try:
            year = int(release_date[:4]) if len(release_date) >= 4 else 0
        except ValueError:
            year = 0
        
        if year == 0:
            return None

        # Genre names
        genre_ids = row.get("genre_ids") if isinstance(row.get("genre_ids"), list) else []
        genres_list = row.get("genres") if isinstance(row.get("genres"), list) else []
        if genres_list:
            genres = ", ".join(g.get("name", "") for g in genres_list if isinstance(g, dict) and g.get("name"))
        else:
            genres = ", ".join(_GENRES.get(g, "") for g in genre_ids if g in _GENRES)

        poster = row.get("poster_path")
        backdrop = row.get("backdrop_path")
        
        return Movie(
            tmdb_id=int(row["id"]),
            title=str(row["title"]),
            original_title=str(row.get("original_title") or row["title"]),
            release_year=year,
            poster_url=f"{IMAGE_BASE_POSTER}{poster}" if isinstance(poster, str) and poster else "",
            backdrop_url=f"{IMAGE_BASE_BACKDROP}{backdrop}" if isinstance(backdrop, str) and backdrop else "",
            overview=str(row.get("overview") or ""),
            genres=genres,
            rating=float(row.get("vote_average") or 0.0),
            runtime=int(row.get("runtime") or 0),
        )
