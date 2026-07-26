package tv.childtv.app

data class Episode(
    val name: String,
    val season: Int,
    val episode: Int,
    val videoId: String?,
    val thumbnail: String?,
    val url: String?
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
    val collections: List<Season>
)

data class Catalog(val channels: List<Channel>)
