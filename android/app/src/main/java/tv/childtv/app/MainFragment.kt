package tv.childtv.app

import android.content.Intent
import android.graphics.Color
import android.os.Bundle
import android.view.View
import androidx.leanback.app.BrowseSupportFragment
import androidx.leanback.widget.ArrayObjectAdapter
import androidx.leanback.widget.HeaderItem
import androidx.leanback.widget.ListRow
import androidx.leanback.widget.ListRowPresenter
import androidx.leanback.widget.OnItemViewClickedListener

class MainFragment : BrowseSupportFragment() {

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
            if (item is Episode && !item.videoId.isNullOrEmpty()) {
                val intent = Intent(requireContext(), PlaybackActivity::class.java)
                intent.putExtra(PlaybackActivity.EXTRA_VIDEO_ID, item.videoId)
                intent.putExtra(PlaybackActivity.EXTRA_TITLE, item.name)
                startActivity(intent)
            }
        }
    }

    private fun setupRows() {
        val rowsAdapter = ArrayObjectAdapter(ListRowPresenter())
        val catalog = CatalogRepository.load(requireContext())
        val channel = catalog.channels.firstOrNull()
        channel?.collections?.forEachIndexed { index, season ->
            val cardAdapter = ArrayObjectAdapter(CardPresenter())
            season.episodes.forEach { cardAdapter.add(it) }
            val header = HeaderItem(index.toLong(), season.title)
            rowsAdapter.add(ListRow(header, cardAdapter))
        }
        adapter = rowsAdapter
    }
}
