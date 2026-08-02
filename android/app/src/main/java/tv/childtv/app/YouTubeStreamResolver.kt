package tv.childtv.app

import org.schabi.newpipe.extractor.MediaFormat
import org.schabi.newpipe.extractor.NewPipe
import org.schabi.newpipe.extractor.ServiceList
import org.schabi.newpipe.extractor.stream.AudioStream
import org.schabi.newpipe.extractor.stream.DeliveryMethod
import org.schabi.newpipe.extractor.stream.Stream
import org.schabi.newpipe.extractor.stream.StreamInfo
import org.schabi.newpipe.extractor.stream.VideoStream

data class ResolvedStreams(val videoUrl: String, val audioUrl: String?)

/**
 * Resolves a videoId to a stream at (up to) MAX_HEIGHT, preferring H.264 + AAC —
 * the formats an old TV decodes in hardware. YouTube rarely has a 720p muxed
 * stream, so for 720p we take a 720p H.264 video track + an AAC audio track and
 * let ExoPlayer merge them. Falls back to a single muxed stream otherwise.
 */
object YouTubeStreamResolver {

    private const val MAX_HEIGHT = 720   // change to 480/360 if a video ever stutters

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

    private fun isH264(v: VideoStream) = v.format == MediaFormat.MPEG_4

    fun resolve(videoId: String): ResolvedStreams {
        ensureInit()
        val info = StreamInfo.getInfo(
            ServiceList.YouTube, "https://www.youtube.com/watch?v=$videoId"
        )

        // Best single muxed H.264 stream at/under the cap (often only 360p exists).
        val muxed = info.videoStreams
            .filter { usable(it) && isH264(it) && it.height in 1..MAX_HEIGHT }
            .maxByOrNull { it.height }

        // Best H.264 video-only track at/under the cap (usually up to 720p).
        val videoOnly = info.videoOnlyStreams
            .filter { usable(it) && isH264(it) && it.height in 1..MAX_HEIGHT }
            .maxByOrNull { it.height }
        val audio = bestAudio(info.audioStreams)

        val muxedHeight = muxed?.height ?: -1
        val adaptiveHeight = if (videoOnly != null && audio != null) videoOnly.height else -1

        // Use whichever reaches the higher resolution; prefer the single muxed
        // stream on a tie (one connection, no merging).
        if (muxed != null && muxedHeight >= adaptiveHeight) {
            return ResolvedStreams(muxed.content, null)
        }
        if (videoOnly != null && audio != null) {
            return ResolvedStreams(videoOnly.content, audio.content)
        }

        // Last resort: the lowest muxed stream of any format.
        info.videoStreams.filter { usable(it) }.minByOrNull { it.height }
            ?.let { return ResolvedStreams(it.content, null) }

        throw IllegalStateException("No playable stream for $videoId")
    }

    private fun bestAudio(streams: List<AudioStream>): AudioStream? {
        val usableStreams = streams.filter { usable(it) }
        // Prefer AAC (m4a) for old-TV compatibility, else the best available.
        return usableStreams.filter { it.format == MediaFormat.M4A }.maxByOrNull { it.averageBitrate }
            ?: usableStreams.maxByOrNull { it.averageBitrate }
    }
}
