package tv.childtv.app

import android.annotation.SuppressLint
import android.graphics.Color
import android.os.Bundle
import android.view.View
import android.webkit.CookieManager
import android.webkit.JavascriptInterface
import android.webkit.WebView
import android.widget.TextView
import androidx.fragment.app.FragmentActivity

/**
 * Plays an episode by loading a REAL hosted player page (kidstv-player.html on
 * your website) in a WebView. Loading a real https page — rather than faking the
 * page locally — gives YouTube the genuine origin/referrer that these videos
 * require (they play in a browser but reject the local-data WebView context).
 *
 * >>> Set PLAYER_PAGE_URL below to where you host kidstv-player.html. <<<
 */
class PlaybackActivity : FragmentActivity() {

    private lateinit var webView: WebView
    private lateinit var statusText: TextView
    private var videoId: String? = null
    private var duration = 0
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
            // Present as a normal browser (drop the WebView "; wv" marker).
            userAgentString = BROWSER_UA
        }
        CookieManager.getInstance().setAcceptCookie(true)
        CookieManager.getInstance().setAcceptThirdPartyCookies(webView, true)

        webView.addJavascriptInterface(Bridge(), "AndroidBridge")

        val start = ProgressStore.resumeSeconds(this, id)
        webView.loadUrl("$PLAYER_PAGE_URL?v=$id&t=$start")
    }

    private inner class Bridge {
        @JavascriptInterface
        fun onReady() {
            runOnUiThread { statusText.visibility = View.GONE }
        }

        @JavascriptInterface
        fun onState(state: Int) {
            if (state == 0) { // ENDED
                videoId?.let { ProgressStore.markWatched(this@PlaybackActivity, it) }
                runOnUiThread { closeOnce() }
            }
        }

        @JavascriptInterface
        fun onProgress(currentSeconds: Int, durationSeconds: Int) {
            val id = videoId ?: return
            if (durationSeconds > 0) {
                duration = durationSeconds
                ProgressStore.save(
                    this@PlaybackActivity, id,
                    currentSeconds * 1000L, durationSeconds * 1000L
                )
            }
        }

        @JavascriptInterface
        fun onError(code: Int) {
            runOnUiThread {
                statusText.text = getString(R.string.error_playback) + " (" + code + ")"
                statusText.visibility = View.VISIBLE
            }
        }
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

        // ======================================================================
        // SET THIS to where you host kidstv-player.html (must be https).
        // e.g. "https://www.example.com/kidstv-player.html"
        // ======================================================================
        const val PLAYER_PAGE_URL = "https://www.nmoore.nz/kidstv-player.html"

        private const val BROWSER_UA =
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 " +
                "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    }
}
