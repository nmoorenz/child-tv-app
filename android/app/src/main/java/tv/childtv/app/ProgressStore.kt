package tv.childtv.app

import android.content.Context

/**
 * Remembers how far each episode has been watched, so tiles can show a progress
 * bar and playback can resume. Backed by SharedPreferences (per videoId).
 */
object ProgressStore {

    private const val PREF = "watch_progress"

    private fun prefs(context: Context) =
        context.getSharedPreferences(PREF, Context.MODE_PRIVATE)

    fun save(context: Context, videoId: String, positionMs: Long, durationMs: Long) {
        prefs(context).edit()
            .putLong("pos_$videoId", positionMs)
            .putLong("dur_$videoId", durationMs)
            .apply()
    }

    fun markWatched(context: Context, videoId: String) {
        val p = prefs(context)
        val dur = p.getLong("dur_$videoId", 0L)
        val end = if (dur > 0L) dur else 1L
        p.edit()
            .putLong("pos_$videoId", end)
            .putLong("dur_$videoId", end)
            .apply()
    }

    /** 0f..1f fraction watched, or 0f if never played. */
    fun fraction(context: Context, videoId: String): Float {
        val p = prefs(context)
        val pos = p.getLong("pos_$videoId", 0L)
        val dur = p.getLong("dur_$videoId", 0L)
        if (dur <= 0L) return 0f
        return (pos.toFloat() / dur.toFloat()).coerceIn(0f, 1f)
    }

    /** Where to resume from (seconds); 0 if unwatched or effectively finished. */
    fun resumeSeconds(context: Context, videoId: String): Int {
        val p = prefs(context)
        val pos = p.getLong("pos_$videoId", 0L)
        val dur = p.getLong("dur_$videoId", 0L)
        if (dur > 0L && pos < dur * 0.95) return (pos / 1000L).toInt()
        return 0
    }
}
