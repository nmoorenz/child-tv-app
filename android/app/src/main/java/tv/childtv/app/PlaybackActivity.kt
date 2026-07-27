package tv.childtv.app

import android.os.Bundle
import android.view.View
import android.widget.TextView
import androidx.fragment.app.FragmentActivity
import com.pierfrancescosoffritti.androidyoutubeplayer.core.player.PlayerConstants
import com.pierfrancescosoffritti.androidyoutubeplayer.core.player.YouTubePlayer
import com.pierfrancescosoffritti.androidyoutubeplayer.core.player.listeners.AbstractYouTubePlayerListener
import com.pierfrancescosoffritti.androidyoutubeplayer.core.player.options.IFramePlayerOptions
import com.pierfrancescosoffritti.androidyoutubeplayer.core.player.views.YouTubePlayerView

/**
 * Plays an episode in-app with the android-youtube-player library (YouTube's
 * official IFrame player, wrapped to work reliably inside a WebView). Reports
 * progress for the tile progress bars, closes on end (skipping the "up next"
 * screen), and if a video errors it falls back to opening it in the YouTube app.
 */
class PlaybackActivity : FragmentActivity() {

    private lateinit var playerView: YouTubePlayerView
    private lateinit var statusText: TextView
    private var videoId: String? = null
    private var durationSeconds: Float = 0f
    private var finished = false

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_playback)
        playerView = findViewById(R.id.youtube_player_view)
        statusText = findViewById(R.id.status_text)

        val id = intent.getStringExtra(EXTRA_VIDEO_ID)
        if (id.isNullOrEmpty()) {
            finish()
            return
        }
        videoId = id
        lifecycle.addObserver(playerView)

        val startSeconds = ProgressStore.resumeSeconds(this, id).toFloat()
        val options = IFramePlayerOptions.Builder().controls(1).rel(0).build()

        playerView.initialize(object : AbstractYouTubePlayerListener() {
            override fun onReady(youTubePlayer: YouTubePlayer) {
                statusText.visibility = View.GONE
                youTubePlayer.loadVideo(id, startSeconds)
            }

            override fun onVideoDuration(youTubePlayer: YouTubePlayer, duration: Float) {
                durationSeconds = duration
            }

            override fun onCurrentSecond(youTubePlayer: YouTubePlayer, second: Float) {
                if (durationSeconds > 0f) {
                    ProgressStore.save(
                        this@PlaybackActivity, id,
                        (second * 1000).toLong(), (durationSeconds * 1000).toLong()
                    )
                }
            }

            override fun onStateChange(
                youTubePlayer: YouTubePlayer,
                state: PlayerConstants.PlayerState
            ) {
                if (state == PlayerConstants.PlayerState.ENDED) {
                    ProgressStore.markWatched(this@PlaybackActivity, id)
                    closeOnce()
                }
            }

            override fun onError(
                youTubePlayer: YouTubePlayer,
                error: PlayerConstants.PlayerError
            ) {
                // No YouTube fallback: show the error so we can see what happened.
                statusText.text = getString(R.string.error_playback) + " (" + error + ")"
                statusText.visibility = View.VISIBLE
            }
        }, options)
    }

    private fun closeOnce() {
        if (!finished) {
            finished = true
            finish()
        }
    }

    companion object {
        const val EXTRA_VIDEO_ID = "videoId"
        const val EXTRA_TITLE = "title"
    }
}
