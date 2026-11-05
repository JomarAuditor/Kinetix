"""Movies page package."""
from presentation.pages.movies.movie_details import MovieDetailsView
from presentation.pages.movies.movie_search import MovieSearchSection
from presentation.pages.movies.movies_page import MoviesPage
from presentation.pages.movies.video_player import VideoPlayer

__all__ = ["MoviesPage", "MovieDetailsView", "MovieSearchSection", "VideoPlayer"]
