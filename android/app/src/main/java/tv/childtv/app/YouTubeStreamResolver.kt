package tv.childtv.app

import org.schabi.newpipe.extractor.NewPipe
import org.schabi.newpipe.extractor.ServiceList
import org.schabi.newpipe.extractor.stream.DeliveryMethod
import org.schabi.newpipe.extractor.stream.Stream
import org.schabi.newpipe.extractor.stream.StreamInfo

data class ResolvedStreams(val videoUrl: String, val audioUrl: String?)

/**
 * Resolves a videoId to a LOW-resolution stream so an old TV can decode it
 * smoothly (the whole reason for the native player). Prefers a single 360p muxed
 * stream (itag 18) — one connection, universally decodable H.264.
 */
object YouTubeStreamResolver {

    private const val MAX_HEIGHT = 480   // yields 360p muxed; raise for sharper/heavier

    @Volatile
    private var initialized = false

    @Synchronized
    private fun ensureInit() {
        if (!initialized) {
            NewPipe.init(OkHttpDownloader.instance)
            initialized = true
        }
    }

    private fun usable(s: Stream) =
        s.isUrl && s.deliveryMethod == DeliveryMethod.PROGRESSIVE_HTTP

    /** Blocking network call — run off the main thread. */
    fun resolve(videoId: String): ResolvedStreams {
        ensureInit()
        val info = StreamInfo.getInfo(
            ServiceList.YouTube, "https://www.youtube.com/watch?v=$videoId"
        )

        // 1) Preferred: a single muxed progressive stream at/under MAX_HEIGHT (360p).
        info.videoStreams
            .filter { usable(it) && it.height in 1..MAX_HEIGHT }
            .maxByOrNull { it.height }
            ?.let { return ResolvedStreams(it.content, null) }

        // 2) Fallback: low-res video-only + audio, merged by ExoPlayer.
        val videoOnly = info.videoOnlyStreams.filter { usable(it) && it.height in 1..MAX_HEIGHT }
            .maxByOrNull { it.height }
            ?: info.videoOnlyStreams.filter { usable(it) }.minByOrNull { it.height }
        val audio = info.audioStreams.filter { usable(it) }.maxByOrNull { it.averageBitrate }
        if (videoOnly != null && audio != null) {
            return ResolvedStreams(videoOnly.content, audio.content)
        }

        // 3) Last resort: the lowest muxed stream available.
        info.videoStreams.filter { usable(it) }.minByOrNull { it.height }
            ?.let { return ResolvedStreams(it.content, null) }

        throw IllegalStateException("No playable stream for $videoId")
    }
}
