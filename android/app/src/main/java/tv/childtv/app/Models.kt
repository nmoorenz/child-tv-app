package tv.childtv.app

data class Episode(
    val name: String,
    val season: Int,
    val episode: Int,
    val videoId: String?,
    val thumbnail: String?,
    val url: String?,
    val subtitle: String?,
    val durationText: String?,
    val capSeconds: Int?          // stop playback at this time (trims junk at the end)
)

data class Season(
    val id: String,
    val title: String,
    val color: String?,
    val episodes: List<Episode>
)

data class Channel(
    val id: String,
    val title: String,
    val color: String?,
    val layout: String?,          // "grid" (Kid Crew) or null (seasons/rows)
    val collections: List<Season>
)

data class Catalog(val channels: List<Channel>)

/** An item in the top "Channels" selector row. */
data class ChannelItem(val id: String, val title: String, val enabled: Boolean)
