package tv.childtv.app

import android.content.Intent
import android.graphics.Color
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.view.View
import androidx.leanback.app.BrowseSupportFragment
import androidx.leanback.widget.ArrayObjectAdapter
import androidx.leanback.widget.HeaderItem
import androidx.leanback.widget.ListRow
import androidx.leanback.widget.ListRowPresenter
import androidx.leanback.widget.OnItemViewClickedListener

class MainFragment : BrowseSupportFragment() {

    private val cardAdapters = ArrayList<ArrayObjectAdapter>()
    private val mainHandler = Handler(Looper.getMainLooper())
    private var catalog: Catalog = Catalog(emptyList())
    private var currentChannelId: String? = null

    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        super.onViewCreated(view, savedInstanceState)

        title = getString(R.string.browse_title)
        headersState = HEADERS_ENABLED
        isHeadersTransitionOnBackEnabled = true
        try {
            brandColor = Color.parseColor("#0F1220")
        } catch (_: Exception) {
        }

        onItemViewClickedListener = OnItemViewClickedListener { _, item, _, _ ->
            when (item) {
                is Episode -> if (!item.videoId.isNullOrEmpty()) {
                    val intent = Intent(requireContext(), PlaybackActivity::class.java)
                    intent.putExtra(PlaybackActivity.EXTRA_VIDEO_ID, item.videoId)
                    intent.putExtra(PlaybackActivity.EXTRA_TITLE, item.name)
                    startActivity(intent)
                }
                is ChannelItem -> if (item.enabled && item.id != currentChannelId) {
                    currentChannelId = item.id
                    buildRows()
                }
            }
        }

        // Show the local copy immediately…
        catalog = CatalogRepository.loadLocal(requireContext())
        currentChannelId = catalog.channels.firstOrNull()?.id
        buildRows()

        // …then fetch the latest in the background and refresh if it arrives.
        CatalogRepository.refresh(requireContext(), mainHandler) { fresh ->
            if (!isAdded) return@refresh
            catalog = fresh
            if (currentChannelId == null || catalog.channels.none { it.id == currentChannelId }) {
                currentChannelId = catalog.channels.firstOrNull()?.id
            }
            buildRows()
        }
    }

    private fun buildRows() {
        val rowsAdapter = ArrayObjectAdapter(ListRowPresenter())
        cardAdapters.clear()

        // Channels selector row.
        val channelAdapter = ArrayObjectAdapter(ChannelCardPresenter())
        if (catalog.channels.isEmpty()) {
            channelAdapter.add(ChannelItem("placeholder", "More coming soon", false))
        } else {
            catalog.channels.forEach { channelAdapter.add(ChannelItem(it.id, it.title, true)) }
        }
        rowsAdapter.add(ListRow(HeaderItem(-1L, getString(R.string.channels_row)), channelAdapter))

        // Selected channel.
        val channel = catalog.channels.firstOrNull { it.id == currentChannelId }
            ?: catalog.channels.firstOrNull()

        if (channel?.layout == "grid") {
            // Grid channel (e.g. Kid Crew): wide cards chunked into rows of GRID_COLS.
            val episodes = channel.collections.flatMap { it.episodes }
            val label = channel.collections.firstOrNull()?.title ?: channel.title
            episodes.chunked(GRID_COLS).forEachIndexed { rowIndex, chunk ->
                val cardAdapter = ArrayObjectAdapter(WideCardPresenter())
                chunk.forEach { cardAdapter.add(it) }
                cardAdapters.add(cardAdapter)
                val header = HeaderItem(1000L + rowIndex, if (rowIndex == 0) label else "")
                rowsAdapter.add(ListRow(header, cardAdapter))
            }
        } else {
            // Season/rows channel (e.g. Numberblocks).
            channel?.collections?.forEachIndexed { index, season ->
                val cardAdapter = ArrayObjectAdapter(CardPresenter())
                season.episodes.forEach { cardAdapter.add(it) }
                cardAdapters.add(cardAdapter)
                rowsAdapter.add(ListRow(HeaderItem(index.toLong(), season.title), cardAdapter))
            }
        }

        adapter = rowsAdapter
    }

    private companion object {
        const val GRID_COLS = 3
    }

    override fun onResume() {
        super.onResume()
        // Refresh progress bars after returning from playback.
        cardAdapters.forEach { it.notifyArrayItemRangeChanged(0, it.size()) }
    }
}
