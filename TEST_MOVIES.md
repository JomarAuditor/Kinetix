# Movie Playback Testing Guide

## Critical Tests (Must Pass)

### 1. Format Selection Test
**Goal**: Verify yt-dlp format resolution works without errors

**Steps**:
1. Launch Kinetix and log in
2. Go to Movies page
3. Click Play on any Popular movie
4. Wait for "Finding playable source..." toast
5. Verify player opens without "Requested format is not available" error

**Expected**:
- ✅ Player opens successfully
- ✅ Video loads and plays
- ✅ Audio is synchronized with video
- ✅ No format errors in logs

**Test Cases**:
- Recent movie (2020+): Should use DASH streams
- Older movie (2000-2010): May use combined streams
- Restricted video: Should show clear error message

---

### 2. Error Handling Test
**Goal**: Verify player handles errors gracefully without navigation loops

**Steps**:
1. Find a movie unlikely to have YouTube upload (very recent/obscure)
2. Click Play button
3. Wait for search to complete

**Expected**:
- ✅ "No free full-length upload found for '{title}' ({year})" toast appears
- ✅ Stays on Movies page (doesn't navigate)
- ✅ User can try another movie

**If error during playback**:
- ✅ Player shows error state with ⚠ icon
- ✅ Error message is clear and specific
- ✅ Play button is disabled
- ✅ User can click back button to return
- ❌ Does NOT auto-navigate to homepage

---

### 3. Movie Matching Accuracy Test
**Goal**: Verify only full-length movies are matched, not trailers/clips

**Steps**:
1. Search for "The Matrix"
2. Click Play on "The Matrix (1999)"
3. Observe what video is selected

**Expected**:
- ✅ Finds a full-length upload (90+ minutes)
- ✅ Title contains "full movie" or similar
- ❌ NOT a trailer (2-3 minutes)
- ❌ NOT a clip/scene compilation
- ❌ NOT a review/reaction video
- ❌ NOT a music video/soundtrack

**Additional test movies**:
- "Inception (2010)" - Popular, should have uploads
- "The Godfather (1972)" - Classic, check public domain matching
- "Blade Runner (1982)" - Multiple versions, check accuracy

---

### 4. UI Feedback Test
**Goal**: Verify clear user feedback at all stages

**Steps**:
1. Click Play on any movie
2. Observe toasts and loading states

**Expected**:
- ✅ Immediate toast: "Finding playable source for {title}..." (3 sec)
- ✅ If found: Player opens with video
- ✅ If not found: "No free full-length upload..." warning (6 sec)
- ✅ If error: Clear error message with reason (5-6 sec)

---

### 5. Thread Safety Test
**Goal**: Verify no crashes or freezes with rapid interactions

**Steps**:
1. Rapidly click Play on multiple movies
2. Click Play then immediately navigate away
3. Click Play while another search is in progress

**Expected**:
- ✅ No UI freeze during searches
- ✅ No crashes or exceptions
- ✅ Toasts appear in correct order
- ✅ Only latest search result is used
- ✅ Player responds to latest action

---

## Edge Cases to Test

### A. Very Long Video
- Search for "lord of the rings extended"
- Verify 3+ hour movies are accepted
- Verify 4+ hour compilations are rejected

### B. No Audio Stream
- If you encounter a video-only upload
- Should show error: "No direct audio stream available"
- Should NOT play video without sound

### C. Geo-Restricted Video
- May encounter region-locked content
- Should show: "Could not fetch video info" or similar
- Should stay on player with clear error

### D. Multiple Versions
- "Blade Runner" (theatrical vs director's cut)
- Verify closest duration match is selected
- Verify correct year matching

---

## Performance Benchmarks

**Movie page load**: < 1 second (TMDB only, no YouTube)
**Play button click → Player open**: 5-15 seconds (depends on YouTube search)
**Video buffering → Playback start**: 2-5 seconds (depends on network)

---

## Common Issues & Solutions

### Issue: "Could not get video window"
**Cause**: Tkinter window handle not ready
**Solution**: Already handled - 100ms delay before playback

### Issue: "No direct video stream available"
**Cause**: YouTube video only has HLS/DASH manifest streams
**Solution**: Code now handles these, but very rare cases may fail

### Issue: Volume resets during playback
**Cause**: VLC resets audio during buffering
**Solution**: Already handled - volume re-applied at 1s and 2.5s

### Issue: "NameError: cannot access free variable 'exc'"
**Cause**: Exception handling bug
**Solution**: ✅ FIXED - error message captured before except block exits

---

## Logs to Check

**Location**: `storage/logs/kinetix.log`

**Look for**:
```
INFO  | movie_playback | Resolved DASH for <video_id> — video: id=... | audio: id=...
INFO  | movie_playback | Resolved combined stream for <video_id> — id=...
ERROR | movie_player   | Movie playback failed: <error message>
INFO  | movie_matching | STRONG match for '<title>' (<year>): YouTube '<video_title>'
```

**Red flags**:
```
ERROR | ytdlp | yt-dlp failed
ERROR | movie_player | NameError: cannot access free variable
ERROR | Could not fetch video info (repeated)
```

---

## Success Criteria

✅ 80%+ of Popular movies play successfully
✅ Zero navigation loops on errors
✅ Zero NameError exceptions
✅ Zero "Requested format is not available" errors
✅ All trailers/clips filtered out
✅ Clear error messages in all failure cases
✅ No UI freezes during any operation

---

**Last Updated**: November 26, 2026
**Status**: Ready for testing
