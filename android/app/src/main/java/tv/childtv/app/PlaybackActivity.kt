package tv.childtv.app

import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.view.View
import android.widget.TextView
import androidx.annotation.OptIn
import androidx.fragment.app.FragmentActivity
import androidx.media3.common.MediaItem
import androidx.media3.common.PlaybackException
import androidx.media3.common.Player
import androidx.media3.common.util.UnstableApi
import androidx.media3.datasource.okhttp.OkHttpDataSource
import androidx.media3.exoplayer.ExoPlayer
import androidx.media3.exoplayer.source.ClippingMediaSource
import androidx.media3.exoplayer.source.MediaSource
import androidx.media3.exoplayer.source.MergingMediaSource
import androidx.media3.exoplayer.source.ProgressiveMediaSource
import androidx.media3.ui.PlayerView

/**
 * Native playback: extracts a low-res (360p) stream with NewPipeExtractor and
 * plays it in ExoPlayer, so an old TV decodes it smoothly. All HTTP uses the
 * trust-all client (old TV certs). Any failure shows a message instead of crashing.
 */
@OptIn(UnstableApi::class)
class PlaybackActivity : FragmentActivity() {

    private var player: ExoPlayer? = null
    private lateinit var playerView: PlayerView
    private lateinit var statusText: TextView
    private var videoId: String? = null
    private var capSeconds = 0
    private var finished = false

    private val handler = Handler(Looper.getMainLooper())
    private val progressUpdater = object : Runnable {
        override fun run() {
            val p = player
            val id = videoId
            if (p != null && id != null && p.duration > 0) {
                ProgressStore.save(this@PlaybackActivity, id, p.currentPosition, p.duration)
            }
            handler.postDelayed(this, 1000)
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_playback)
        playerView = findViewById(R.id.player_view)
        statusText = findViewById(R.id.status_text)

        val id = intent.getStringExtra(EXTRA_VIDEO_ID)
        if (id.isNullOrEmpty()) {
            finish()
            return
        }
        videoId = id
        capSeconds = intent.getIntExtra(EXTRA_CAP_SECONDS, 0)

        // Resolve the stream off the main thread, then play on the main thread.
        Thread {
            try {
                val streams = YouTubeStreamResolver.resolve(id)
                runOnUiThread { if (!isFinishing) startPlayback(streams) }
            } catch (t: Throwable) {
                runOnUiThread { showError(t) }
            }
        }.start()
    }

    private fun startPlayback(streams: ResolvedStreams) {
        statusText.visibility = View.GONE

        val dataSourceFactory = OkHttpDataSource.Factory(TrustAllHttp.client)
        val videoSource = ProgressiveMediaSource.Factory(dataSourceFactory)
            .createMediaSource(MediaItem.fromUri(streams.videoUrl))
        var mediaSource: MediaSource = if (streams.audioUrl != null) {
            val audioSource = ProgressiveMediaSource.Factory(dataSourceFactory)
                .createMediaSource(MediaItem.fromUri(streams.audioUrl))
            MergingMediaSource(videoSource, audioSource)
        } else {
            videoSource
        }
        // Hard-stop at capSeconds (trims junk footage at the end of some episodes).
        if (capSeconds > 0) {
            mediaSource = ClippingMediaSource(mediaSource, 0L, capSeconds * 1_000_000L)
        }

        val exo = ExoPlayer.Builder(this).build()
        player = exo
        playerView.player = exo

        exo.addListener(object : Player.Listener {
            override fun onPlaybackStateChanged(playbackState: Int) {
                if (playbackState == Player.STATE_ENDED) {
                    videoId?.let { ProgressStore.markWatched(this@PlaybackActivity, it) }
                    closeOnce()
                }
            }

            override fun onPlayerError(error: PlaybackException) {
                showError(error)
            }
        })

        val startMs = ProgressStore.resumeSeconds(this, videoId ?: "") * 1000L
        exo.setMediaSource(mediaSource)
        exo.prepare()
        if (startMs > 0) exo.seekTo(startMs)
        exo.playWhenReady = true
        handler.postDelayed(progressUpdater, 1000)
        playerView.requestFocus()
    }

    private fun showError(t: Throwable) {
        val detail = (t.message ?: t.javaClass.simpleName).take(180)
        statusText.text = getString(R.string.error_playback) + "\n" +
            t.javaClass.simpleName + ": " + detail
        statusText.visibility = View.VISIBLE
    }

    private fun closeOnce() {
        if (!finished) {
            finished = true
            finish()
        }
    }

    private fun releasePlayer() {
        handler.removeCallbacks(progressUpdater)
        player?.release()
        player = null
    }

    override fun onStop() {
        super.onStop()
        releasePlayer()
    }

    companion object {
        const val EXTRA_VIDEO_ID = "videoId"
        const val EXTRA_TITLE = "title"
        const val EXTRA_CAP_SECONDS = "capSeconds"
    }
}
