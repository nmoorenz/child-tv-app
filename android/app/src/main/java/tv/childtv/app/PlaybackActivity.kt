package tv.childtv.app

import android.os.Bundle
import android.view.View
import android.widget.TextView
import androidx.annotation.OptIn
import androidx.fragment.app.FragmentActivity
import androidx.lifecycle.lifecycleScope
import androidx.media3.common.MediaItem
import androidx.media3.common.Player
import androidx.media3.common.util.UnstableApi
import androidx.media3.datasource.DefaultHttpDataSource
import androidx.media3.exoplayer.ExoPlayer
import androidx.media3.exoplayer.source.MediaSource
import androidx.media3.exoplayer.source.MergingMediaSource
import androidx.media3.exoplayer.source.ProgressiveMediaSource
import androidx.media3.ui.PlayerView
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

@OptIn(UnstableApi::class)
class PlaybackActivity : FragmentActivity() {

    private var player: ExoPlayer? = null
    private lateinit var playerView: PlayerView
    private lateinit var statusText: TextView

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_playback)
        playerView = findViewById(R.id.player_view)
        statusText = findViewById(R.id.status_text)

        val videoId = intent.getStringExtra(EXTRA_VIDEO_ID)
        if (videoId.isNullOrEmpty()) {
            finish()
            return
        }
        startPlayback(videoId)
    }

    private fun startPlayback(videoId: String) {
        lifecycleScope.launch {
            val streams = try {
                withContext(Dispatchers.IO) { YouTubeStreamResolver.resolve(videoId) }
            } catch (e: Exception) {
                statusText.text = getString(R.string.error_playback)
                return@launch
            }
            statusText.visibility = View.GONE
            playStreams(streams)
        }
    }

    private fun playStreams(streams: ResolvedStreams) {
        val exo = ExoPlayer.Builder(this).build()
        player = exo
        playerView.player = exo

        val httpFactory = DefaultHttpDataSource.Factory()
            .setUserAgent(USER_AGENT)
            .setAllowCrossProtocolRedirects(true)

        val videoSource = ProgressiveMediaSource.Factory(httpFactory)
            .createMediaSource(MediaItem.fromUri(streams.videoUrl))

        val mediaSource: MediaSource = if (streams.audioUrl != null) {
            val audioSource = ProgressiveMediaSource.Factory(httpFactory)
                .createMediaSource(MediaItem.fromUri(streams.audioUrl))
            MergingMediaSource(videoSource, audioSource)
        } else {
            videoSource
        }

        exo.addListener(object : Player.Listener {
            override fun onPlaybackStateChanged(playbackState: Int) {
                if (playbackState == Player.STATE_ENDED) finish()
            }
        })
        exo.setMediaSource(mediaSource)
        exo.prepare()
        exo.playWhenReady = true
        playerView.requestFocus()
    }

    private fun releasePlayer() {
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
        private const val USER_AGENT =
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 " +
                "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    }
}
