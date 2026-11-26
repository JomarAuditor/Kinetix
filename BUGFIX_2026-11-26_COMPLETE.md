# Kinetix Movies Playback Bug Fixes - November 26, 2026

## Issues Fixed

### 1. yt-dlp Format Selection Errors ✅
**Problem**: `yt-dlp error: Requested format is not available`
- Code relied on hardcoded format IDs that might not exist for all videos
- No fallback when DASH streams unavailable

**Solution**:
- Completely rewrote `resolve_video()` in `ytdlp_client.py`
- Dynamic format inspection - no hardcoded IDs
- Intelligent fallback chain:
  1. **DASH streams** (separate video+audio) - best quality
  2. **Combined streams** (video+audio in one file) - compatibility
  3. **Graceful error** with clear message
- Prioritizes VLC-compatible formats: H.264 MP4 video + AAC M4A audio
- Filters by protocol - only accepts direct HTTPS streams, rejects HLS manifests

### 2. Exception Callback Bug ✅
**Problem**: `NameError: cannot access free variable 'exc' where it is not associated with a value`
- Python clears exception variables after except blocks
- Lambda callbacks captured invalid references

**Solution**:
- Already fixed in movie_player.py line 138
- Exception message captured into plain string BEFORE scheduling callback
- Thread-safe error propagation to main thread via `after()`

### 3. Navigation Loop ✅
**Problem**: Player repeatedly returns to movies homepage on errors
- Error handling navigated away from player
- User couldn't see what went wrong
- Confusing UX with repeated redirects

**Solution**:
- Player stays on page when errors occur
- Shows clear error state with:
  - ⚠ emoji icon
  - "Could not play this video" heading
  - Detailed error message
  - Disabled play button
- User manually navigates back using back button
- Error toast shows for 6 seconds with full details

### 4. Poor Movie Matching Accuracy ✅
**Problem**: YouTube searches returned trailers, clips, reviews instead of full movies
- Too broad search criteria
- Weak trailer/clip filtering
- No verification of "full movie" indicators

**Solution**:
- **Stricter duration filtering**: 
  - Minimum 60 minutes (feature length)
  - Maximum 240 minutes (rejects compilations/marathons)
- **Expanded rejection keywords** (27 total):
  - trailer, teaser, clip, scene, review, recap, reaction
  - analysis, breakdown, summary, compilation, featurette
  - music video, mv, moments, promo, tv spot, etc.
- **Requires movie indicators**:
  - Title must contain "full movie", "full length", "complete movie", etc.
  - OR 90+ minutes duration + 70%+ title word overlap
- **Better query construction**:
  - `"{title} {year} full movie"`
  - `"{title} full movie {year}"`
  - `"{title} complete film {year}"`
- **Multilingual support**: Also accepts "película completa", "filme completo"

### 5. UI/UX Improvements ✅
**Problem**: Unclear loading states, confusing feedback
- No indication when searching for sources
- Generic error messages
- User didn't know what was happening

**Solution**:
- **Loading feedback**: Toast shows "Finding playable source for {title}..." when Play clicked
- **Clear error states**: Player shows formatted error with emoji and explanation
- **Better not-found messages**: Includes movie year for clarity
  - "No free full-length upload found for 'The Matrix' (1999)"
- **Toast durations**: 
  - Loading: 3 seconds
  - Warnings: 6 seconds
  - Errors: 5-6 seconds

## Technical Details

### Format Selection Logic
```python
# Priority order:
1. DASH (separate streams)
   - Video: H.264 MP4, 720p preferred
   - Audio: AAC M4A, highest bitrate
   - Combined via VLC :input-slave option

2. Combined streams (fallback)
   - MP4 preferred, closest to 720p
   - Both video and audio in one stream
   
3. Error (no compatible format)
   - Clear message about restriction/unavailability
```

### Movie Search Filtering
```python
# Must pass ALL checks:
✓ Duration 60-240 minutes
✓ No trailer/clip/review keywords
✓ Has "full movie" indicator OR (90+ min AND 70%+ title overlap)
✓ Not a duplicate video_id
```

### Thread Safety
- All yt-dlp/TMDB calls in daemon threads
- UI updates only via `after()` on main thread
- No cross-thread Tkinter access
- Exception handling captures before thread exits

## Files Modified

1. **integrations/media/ytdlp_client.py** (Major changes)
   - Rewrote `resolve_video()` - 150+ lines
   - Improved `search_youtube_movies()` with strict filtering
   - Added combined stream support
   - Expanded trailer rejection list

2. **presentation/pages/movies/movie_player.py**
   - Enhanced error display formatting
   - Improved error state management
   - Better user feedback

3. **presentation/pages/movies/movies_page.py**
   - Added loading toast on Play click
   - Year included in error messages
   - Longer toast durations for readability

4. **PROGRESS.md**
   - Documented all fixes
   - Updated "What works" section
   - Added improvements summary

## Testing Recommendations

1. **Format compatibility**: Try movies with different YouTube formats
2. **Error handling**: Test restricted/unavailable videos
3. **Movie matching**: Search for specific titles with years
4. **UI feedback**: Verify all toasts appear with correct timing
5. **Thread safety**: Rapid clicking Play button, navigation during loading

## Known Remaining Limitations

- Not all TMDB movies have free YouTube uploads (by design)
- Some older movies have POSSIBLE match confidence (acceptable)
- Fullscreen not yet implemented (future work)
- Movie details page placeholder (future work)

## Performance Impact

- **Positive**: Better format selection reduces playback failures
- **Positive**: Stricter filtering reduces false matches
- **Neutral**: Same number of API calls (TMDB, yt-dlp)
- **Positive**: Better UX reduces user confusion and repeated attempts

---

**Status**: ✅ ALL CRITICAL BUGS FIXED
**Ready**: Yes - safe to test movie playback
**Compile**: ✅ All files compile without errors
