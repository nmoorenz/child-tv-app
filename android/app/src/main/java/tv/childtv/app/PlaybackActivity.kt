package tv.childtv.app

import android.annotation.SuppressLint
import android.graphics.Color
import android.net.http.SslError
import android.os.Bundle
import android.view.View
import android.webkit.CookieManager
import android.webkit.JavascriptInterface
import android.webkit.SslErrorHandler
import android.webkit.WebChromeClient
import android.webkit.WebResourceError
import android.webkit.WebResourceRequest
import android.webkit.WebView
import android.webkit.WebViewClient
import android.widget.TextView
import androidx.fragment.app.FragmentActivity

/**
 * Plays an episode by loading kidstv-player.html (hosted on your website) in a
 * WebView. Loading a real https page gives YouTube the genuine origin these videos
 * require. Reports progress for the tile bars, closes on end (skipping "up next"),
 * and shows an on-screen message if a video can't play (no YouTube-app fallback).
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
            userAgentString = BROWSER_UA
        }
        CookieManager.getInstance().setAcceptCookie(true)
        CookieManager.getInstance().setAcceptThirdPartyCookies(webView, true)

        // WebChromeClient is required for the YouTube player to run inside a WebView.
        webView.webChromeClient = WebChromeClient()
        webView.webViewClient = object : WebViewClient() {
            override fun onReceivedError(
                view: WebView?,
                request: WebResourceRequest?,
                error: WebResourceError?
            ) {
                if (request?.isForMainFrame == true) {
                    showError()
                }
            }

            // Old TVs have an outdated root-certificate store and reject modern HTTPS
            // certs, which silently blanks the page. For this personal app on your own
            // TV we proceed anyway. (Acceptable here; not appropriate for a public app.)
            override fun onReceivedSslError(
                view: WebView?,
                handler: SslErrorHandler?,
                error: SslError?
            ) {
                handler?.proceed()
            }
        }

        webView.addJavascriptInterface(Bridge(), "AndroidBridge")

        val start = ProgressStore.resumeSeconds(this, id)
        webView.loadUrl("$PLAYER_PAGE_URL?v=$id&t=$start")
    }

    private fun showError() {
        runOnUiThread {
            statusText.text = getString(R.string.error_playback)
            statusText.visibility = View.VISIBLE
        }
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
                ProgressStore.save(
                    this@PlaybackActivity, id,
                    currentSeconds * 1000L, durationSeconds * 1000L
                )
            }
        }

        @JavascriptInterface
        fun onError(code: Int) {
            showError()
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
        // Where you host kidstv-player.html (must be https).
        // ======================================================================
        const val PLAYER_PAGE_URL = "https://www.nmoore.nz/kidstv-player.html"

        private const val BROWSER_UA =
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 " +
                "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    }
}
