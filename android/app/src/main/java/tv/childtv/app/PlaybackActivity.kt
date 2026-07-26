package tv.childtv.app

import android.annotation.SuppressLint
import android.content.Intent
import android.graphics.Color
import android.net.Uri
import android.os.Bundle
import android.view.View
import android.webkit.JavascriptInterface
import android.webkit.WebView
import android.widget.TextView
import androidx.fragment.app.FragmentActivity

/**
 * Plays a YouTube video in-app using the official IFrame player embedded in a
 * WebView. No browsing UI, no stream extraction. Reports playback progress back
 * to Android (for the progress bar on tiles) and closes on end, which avoids the
 * post-video "up next" suggestions. If a video can't be embedded, it falls back
 * to opening that one episode in the YouTube app.
 */
class PlaybackActivity : FragmentActivity() {

    private lateinit var webView: WebView
    private lateinit var statusText: TextView
    private var videoId: String? = null
    private var finished = false

    @SuppressLint("SetJavaScriptEnabled")
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_playback)
        webView = findViewById(R.id.web_view)
        statusText = findViewById(R.id.status_text)

        val id = intent.getStringExtra(EXTRA_VIDEO_ID)
        if (id.isNullOrEmpty()) {
            finish()
            return
        }
        videoId = id

        webView.setBackgroundColor(Color.BLACK)
        webView.settings.apply {
            javaScriptEnabled = true
            domStorageEnabled = true
            mediaPlaybackRequiresUserGesture = false
        }
        webView.addJavascriptInterface(JsBridge(), "Android")

        val startSeconds = ProgressStore.resumeSeconds(this, id)
        webView.loadDataWithBaseURL(
            "https://www.youtube.com",
            buildHtml(id, startSeconds),
            "text/html",
            "utf-8",
            null
        )
    }

    private fun buildHtml(videoId: String, startSeconds: Int): String = """
        <!DOCTYPE html>
        <html>
        <head>
          <meta name="viewport" content="width=device-width, initial-scale=1">
          <style>
            html,body{margin:0;padding:0;background:#000;height:100%;overflow:hidden}
            #player{position:absolute;top:0;left:0;width:100%;height:100%}
          </style>
        </head>
        <body>
          <div id="player"></div>
          <script src="https://www.youtube.com/iframe_api"></script>
          <script>
            var player;
            function onYouTubeIframeAPIReady() {
              player = new YT.Player('player', {
                width: '100%', height: '100%',
                videoId: '$videoId',
                playerVars: {
                  autoplay: 1, controls: 1, rel: 0, fs: 0,
                  modestbranding: 1, playsinline: 1, iv_load_policy: 3,
                  start: $startSeconds, origin: 'https://www.youtube.com'
                },
                events: {
                  'onReady': function(e){ e.target.playVideo(); Android.onReady(); setInterval(tick, 1000); },
                  'onStateChange': function(e){ Android.onState(e.data); },
                  'onError': function(e){ Android.onError(e.data); }
                }
              });
            }
            function tick(){
              try {
                if (player && player.getDuration) {
                  Android.onProgress(Math.floor(player.getCurrentTime()), Math.floor(player.getDuration()));
                }
              } catch (e) {}
            }
          </script>
        </body>
        </html>
    """.trimIndent()

    private inner class JsBridge {
        @JavascriptInterface
        fun onReady() {
            runOnUiThread { statusText.visibility = View.GONE }
        }

        @JavascriptInterface
        fun onState(state: Int) {
            // 0 = ENDED
            if (state == 0) {
                videoId?.let { ProgressStore.markWatched(this@PlaybackActivity, it) }
                runOnUiThread { closeOnce() }
            }
        }

        @JavascriptInterface
        fun onProgress(currentSeconds: Int, durationSeconds: Int) {
            val id = videoId ?: return
            if (durationSeconds > 0) {
                ProgressStore.save(
                    this@PlaybackActivity, id,
                    currentSeconds * 1000L, durationSeconds * 1000L
                )
            }
        }

        @JavascriptInterface
        fun onError(code: Int) {
            // Includes 101/150 = embedding disabled by the uploader.
            runOnUiThread { fallbackToYouTube() }
        }
    }

    private fun fallbackToYouTube() {
        val id = videoId
        if (id != null) {
            try {
                startActivity(Intent(Intent.ACTION_VIEW, Uri.parse("https://www.youtube.com/watch?v=$id")))
            } catch (_: Exception) {
                statusText.text = getString(R.string.error_playback)
                statusText.visibility = View.VISIBLE
                return
            }
        }
        closeOnce()
    }

    private fun closeOnce() {
        if (!finished) {
            finished = true
            finish()
        }
    }

    override fun onDestroy() {
        try {
            webView.loadUrl("about:blank")
            webView.destroy()
        } catch (_: Exception) {
        }
        super.onDestroy()
    }

    companion object {
        const val EXTRA_VIDEO_ID = "videoId"
        const val EXTRA_TITLE = "title"
    }
}
