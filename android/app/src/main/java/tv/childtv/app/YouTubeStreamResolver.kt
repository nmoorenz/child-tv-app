package tv.childtv.app

import org.schabi.newpipe.extractor.NewPipe
import org.schabi.newpipe.extractor.ServiceList
import org.schabi.newpipe.extractor.stream.DeliveryMethod
import org.schabi.newpipe.extractor.stream.Stream
import org.schabi.newpipe.extractor.stream.StreamInfo

data class ResolvedStreams(val videoUrl: String, val audioUrl: String?)

/**
 * Turns a YouTube videoId into playable stream URLs using NewPipeExtractor.
 * No official app, no ads, no recommendations.
 */
object YouTubeStreamResolver {

    @Volatile
    private var initialized = false

    @Synchronized
    private fun ensureInit() {
        if (!initialized) {
            NewPipe.init(OkHttpDownloader.instance)
            initialized = true
        }
    }

    private fun usable(s: Stream): Boolean =
        s.isUrl && s.deliveryMethod == DeliveryMethod.PROGRESSIVE_HTTP

    /** Blocking network call — must be run off the main thread. */
    fun resolve(videoId: String): ResolvedStreams {
        ensureInit()
        val info = StreamInfo.getInfo(
            ServiceList.YouTube,
            "https://www.youtube.com/watch?v=$videoId"
        )

        val videoOnly = info.videoOnlyStreams.filter { usable(it) }
        val audios = info.audioStreams.filter { usable(it) }

        if (videoOnly.isNotEmpty() && audios.isNotEmpty()) {
            val video = videoOnly.filter { it.height in 1..1080 }.maxByOrNull { it.height }
                ?: videoOnly.maxByOrNull { it.height }
                ?: videoOnly.first()
            val audio = audios.maxByOrNull { it.averageBitrate } ?: audios.first()
            return ResolvedStreams(video.content, audio.content)
        }

        // Fallback: a single muxed (video+audio) progressive stream.
        val muxed = info.videoStreams.filter { usable(it) }
        val best = muxed.maxByOrNull { it.height } ?: muxed.firstOrNull()
        if (best != null) return ResolvedStreams(best.content, null)

        throw IllegalStateException("No playable progressive stream for $videoId")
    }
}
