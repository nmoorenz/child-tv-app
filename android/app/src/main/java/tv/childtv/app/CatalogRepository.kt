package tv.childtv.app

import android.content.Context
import org.json.JSONArray
import org.json.JSONObject

/** Loads catalog.json (bundled in assets) into typed models. */
object CatalogRepository {

    fun load(context: Context): Catalog {
        val text = context.assets.open("catalog.json")
            .bufferedReader(Charsets.UTF_8)
            .use { it.readText() }
        return parse(text)
    }

    private fun parse(text: String): Catalog {
        val root = JSONObject(text)
        val channelsArr = root.optJSONArray("channels") ?: JSONArray()
        val channels = ArrayList<Channel>()
        for (i in 0 until channelsArr.length()) {
            val c = channelsArr.getJSONObject(i)
            channels.add(
                Channel(
                    id = c.optString("id", "channel"),
                    title = c.optString("title", "Numberblocks"),
                    color = c.optStringOrNull("color"),
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
                    episode = e.optInt("episode_index", e.optInt("episode", k + 1)),
                    videoId = e.optStringOrNull("videoId"),
                    thumbnail = e.optStringOrNull("thumbnail"),
                    url = e.optStringOrNull("url")
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
