package tv.childtv.app

import android.content.Intent
import android.graphics.Color
import android.os.Bundle
import android.view.View
import android.widget.Toast
import androidx.leanback.app.BrowseSupportFragment
import androidx.leanback.widget.ArrayObjectAdapter
import androidx.leanback.widget.HeaderItem
import androidx.leanback.widget.ListRow
import androidx.leanback.widget.ListRowPresenter
import androidx.leanback.widget.OnItemViewClickedListener

class MainFragment : BrowseSupportFragment() {

    private val cardAdapters = ArrayList<ArrayObjectAdapter>()

    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        super.onViewCreated(view, savedInstanceState)

        title = getString(R.string.browse_title)
        headersState = HEADERS_ENABLED
        isHeadersTransitionOnBackEnabled = true
        try {
            brandColor = Color.parseColor("#0F1220")
        } catch (_: Exception) {
        }

        setupRows()

        onItemViewClickedListener = OnItemViewClickedListener { _, item, _, _ ->
            when (item) {
                is Episode -> if (!item.videoId.isNullOrEmpty()) {
                    val intent = Intent(requireContext(), PlaybackActivity::class.java)
                    intent.putExtra(PlaybackActivity.EXTRA_VIDEO_ID, item.videoId)
                    intent.putExtra(PlaybackActivity.EXTRA_TITLE, item.name)
                    startActivity(intent)
                }
                is ChannelItem -> if (!item.enabled) {
                    Toast.makeText(
                        requireContext(),
                        getString(R.string.channel_coming_soon),
                        Toast.LENGTH_SHORT
                    ).show()
                }
            }
        }
    }

    private fun setupRows() {
        val rowsAdapter = ArrayObjectAdapter(ListRowPresenter())
        cardAdapters.clear()

        // Top "Channels" selector row (only Numberblocks for now; placeholder for more).
        val channelAdapter = ArrayObjectAdapter(ChannelCardPresenter())
        channelAdapter.add(ChannelItem("numberblocks", "Numberblocks", true))
        channelAdapter.add(ChannelItem("placeholder", "More coming soon", false))
        rowsAdapter.add(ListRow(HeaderItem(-1L, getString(R.string.channels_row)), channelAdapter))

        val catalog = CatalogRepository.load(requireContext())
        val channel = catalog.channels.firstOrNull()
        channel?.collections?.forEachIndexed { index, season ->
            val cardAdapter = ArrayObjectAdapter(CardPresenter())
            season.episodes.forEach { cardAdapter.add(it) }
            cardAdapters.add(cardAdapter)
            val header = HeaderItem(index.toLong(), season.title)
            rowsAdapter.add(ListRow(header, cardAdapter))
        }
        adapter = rowsAdapter
    }

    override fun onResume() {
        super.onResume()
        // Refresh progress bars after returning from playback.
        cardAdapters.forEach { it.notifyArrayItemRangeChanged(0, it.size()) }
    }
}
