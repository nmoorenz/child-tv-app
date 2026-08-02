package tv.childtv.app

import okhttp3.RequestBody.Companion.toRequestBody
import org.schabi.newpipe.extractor.downloader.Downloader
import org.schabi.newpipe.extractor.downloader.Request
import org.schabi.newpipe.extractor.downloader.Response

/** OkHttp-backed downloader NewPipeExtractor uses (via the trust-all client). */
class OkHttpDownloader private constructor() : Downloader() {

    override fun execute(request: Request): Response {
        val builder = okhttp3.Request.Builder().url(request.url())

        var hasUserAgent = false
        for ((name, values) in request.headers()) {
            for (value in values) {
                builder.addHeader(name, value)
                if (name.equals("User-Agent", ignoreCase = true)) hasUserAgent = true
            }
        }
        if (!hasUserAgent) builder.addHeader("User-Agent", USER_AGENT)

        val data = request.dataToSend()
        val body = if (data != null) data.toRequestBody(null, 0, data.size) else null
        builder.method(request.httpMethod(), body)

        TrustAllHttp.client.newCall(builder.build()).execute().use { resp ->
            val responseBody = resp.body?.string() ?: ""
            val headers = HashMap<String, List<String>>()
            for (name in resp.headers.names()) headers[name] = resp.headers.values(name)
            return Response(
                resp.code, resp.message, headers, responseBody, resp.request.url.toString()
            )
        }
    }

    companion object {
        private const val USER_AGENT =
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 " +
                "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"

        val instance: OkHttpDownloader by lazy { OkHttpDownloader() }
    }
}
