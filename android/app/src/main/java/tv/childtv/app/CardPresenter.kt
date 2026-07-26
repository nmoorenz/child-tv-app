package tv.childtv.app

import android.view.ViewGroup
import androidx.leanback.widget.ImageCardView
import androidx.leanback.widget.Presenter
import com.bumptech.glide.Glide

class CardPresenter : Presenter() {

    override fun onCreateViewHolder(parent: ViewGroup): ViewHolder {
        val cardView = ImageCardView(parent.context)
        cardView.isFocusable = true
        cardView.isFocusableInTouchMode = true
        cardView.setMainImageDimensions(CARD_WIDTH, CARD_HEIGHT)
        return ViewHolder(cardView)
    }

    override fun onBindViewHolder(viewHolder: ViewHolder, item: Any) {
        val ep = item as Episode
        val cardView = viewHolder.view as ImageCardView
        cardView.titleText = ep.name
        cardView.contentText = if (ep.episode > 0) "Episode ${ep.episode}" else ""
        val thumb = ep.thumbnail
            ?: ep.videoId?.let { "https://i.ytimg.com/vi/$it/hqdefault.jpg" }
        Glide.with(cardView.context)
            .load(thumb)
            .placeholder(R.drawable.default_thumb)
            .error(R.drawable.default_thumb)
            .centerCrop()
            .into(cardView.mainImageView)
    }

    override fun onUnbindViewHolder(viewHolder: ViewHolder) {
        val cardView = viewHolder.view as ImageCardView
        cardView.mainImage = null
    }

    companion object {
        private const val CARD_WIDTH = 320
        private const val CARD_HEIGHT = 180
    }
}
