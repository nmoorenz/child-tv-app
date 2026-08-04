package tv.childtv.app

import android.content.Context
import android.os.Handler
import org.json.JSONArray
import org.json.JSONObject
import java.io.File
import java.net.URL
import java.security.SecureRandom
import java.security.cert.X509Certificate
import javax.net.ssl.HostnameVerifier
import javax.net.ssl.HttpsURLConnection
import javax.net.ssl.SSLContext
import javax.net.ssl.SSLSocketFactory
import javax.net.ssl.TrustManager
import javax.net.ssl.X509TrustManager

/**
 * Provides the catalog. Reads a locally cached copy (or the bundled asset) instantly,
 * then fetches the latest from CATALOG_URL in the background so content updates never
 * require an app rebuild.
 */
object CatalogRepository {

    // ======================================================================
    // Where the auto-updated catalog is published (raw file in your GitHub repo).
    // The nightly GitHub Action regenerates and commits catalog.json there.
    // ======================================================================
    const val CATALOG_URL =
        "https://raw.githubusercontent.com/nmoorenz/child-tv-app/main/catalog.json"

    private const val CACHE_FILE = "catalog_cache.json"

    /** Instant load: cached remote copy if present, otherwise the bundled asset. */
    fun loadLocal(context: Context): Catalog {
        val cache = File(context.filesDir, CACHE_FILE)
        val text = if (cache.exists()) {
            cache.readText(Charsets.UTF_8)
        } else {
            context.assets.open("catalog.json").bufferedReader(Charsets.UTF_8).use { it.readText() }
        }
        return try {
            parse(text)
        } catch (e: Exception) {
            Catalog(emptyList())
        }
    }

    /** Fetch the latest catalog in the background; on success cache it and call back on main. */
    fun refresh(context: Context, mainHandler: Handler, onUpdated: (Catalog) -> Unit) {
        Thread {
            try {
                val json = httpGet(CATALOG_URL)
                val catalog = parse(json)
                if (catalog.channels.isNotEmpty()) {
                    File(context.filesDir, CACHE_FILE).writeText(json, Charsets.UTF_8)
                    mainHandler.post { onUpdated(catalog) }
                }
            } catch (e: Exception) {
                // Offline or fetch failed — keep showing the local copy.
            }
        }.start()
    }

    private fun httpGet(urlStr: String): String {
        val conn = URL(urlStr).openConnection() as HttpsURLConnection
        // Old TVs reject modern certs; trust the connection (personal app, own data).
        conn.sslSocketFactory = trustAllFactory()
        conn.hostnameVerifier = HostnameVerifier { _, _ -> true }
        conn.connectTimeout = 15000
        conn.readTimeout = 15000
        conn.inputStream.bufferedReader(Charsets.UTF_8).use { return it.readText() }
    }

    private fun trustAllFactory(): SSLSocketFactory {
        val trustAll = arrayOf<TrustManager>(object : X509TrustManager {
            override fun checkClientTrusted(chain: Array<out X509Certificate>?, authType: String?) {}
            override fun checkServerTrusted(chain: Array<out X509Certificate>?, authType: String?) {}
            override fun getAcceptedIssuers(): Array<X509Certificate> = arrayOf()
        })
        val ctx = SSLContext.getInstance("TLS")
        ctx.init(null, trustAll, SecureRandom())
        return ctx.socketFactory
    }

    // ------------------------------------------------------------------ parsing

    private fun parse(text: String): Catalog {
        val root = JSONObject(text)
        val channelsArr = root.optJSONArray("channels") ?: JSONArray()
        val channels = ArrayList<Channel>()
        for (i in 0 until channelsArr.length()) {
            val c = channelsArr.getJSONObject(i)
            channels.add(
                Channel(
                    id = c.optString("id", "channel-$i"),
                    title = c.optString("title", "Channel"),
                    color = c.optStringOrNull("color"),
                    layout = c.optStringOrNull("layout"),
                    collections = parseCollections(c.optJSONArray("collections"))
                )
            )
        }
        return Catalog(channels)
    }

    private fun parseCollections(arr: JSONArray?): List<Season> {
        if (arr == null) return emptyList()
        val out = ArrayList<Season>()
        for (j in 0 until arr.length()) {
            val s = arr.getJSONObject(j)
            out.add(
                Season(
                    id = s.optString("id", "col-$j"),
                    title = s.optString("title", "Season ${j + 1}"),
                    color = s.optStringOrNull("color"),
                    episodes = parseEpisodes(s.optJSONArray("episodes"))
                )
            )
        }
        return out
    }

    private fun parseEpisodes(arr: JSONArray?): List<Episode> {
        if (arr == null) return emptyList()
        val out = ArrayList<Episode>()
        for (k in 0 until arr.length()) {
            val e = arr.getJSONObject(k)
            val name = e.optStringOrNull("name") ?: e.optStringOrNull("title") ?: "Episode ${k + 1}"
            out.add(
                Episode(
                    name = name,
                    season = e.optInt("season", 0),
                    // 0 when the source has no episode numbering (e.g. Kid Crew) so
                    // the card shows just the title, no "Episode N".
                    episode = e.optInt("episode_index", e.optInt("episode", 0)),
                    videoId = e.optStringOrNull("videoId"),
                    thumbnail = e.optStringOrNull("thumbnail"),
                    url = e.optStringOrNull("url"),
                    subtitle = e.optStringOrNull("subtitle"),
                    durationText = e.optStringOrNull("durationText"),
                    capSeconds = if (e.has("capSeconds") && !e.isNull("capSeconds"))
                        e.optInt("capSeconds") else null
                )
            )
        }
        return out
    }

    private fun JSONObject.optStringOrNull(key: String): String? {
        if (!has(key) || isNull(key)) return null
        val v = optString(key, "")
        return v.ifEmpty { null }
    }
}
